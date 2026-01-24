"""
Web Crawler Ability - Deep website crawling with Playwright

Uses headless Chromium to render JavaScript-heavy pages and extract:
- Full rendered content
- Product data with images
- Navigation structure
- All linked pages within the domain
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Run an async coroutine from sync code, handling nested event loops.

    Works whether called from:
    - Pure sync code (uses asyncio.run)
    - Within an existing event loop (uses nest_asyncio or new thread)
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running - use asyncio.run
        return asyncio.run(coro)

    # Event loop is running - need to handle nested async
    try:
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except ImportError:
        # nest_asyncio not available - run in new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


@dataclass
class CrawledPage:
    """Represents a single crawled page"""

    url: str
    title: str = ""
    content: str = ""
    html: str = ""
    links: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    products: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    design_metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:2000] if self.content else "",
            "links": self.links[:20],
            "images": self.images[:30],
            "products": self.products[:20],
            "metadata": self.metadata,
            "screenshot_path": self.screenshot_path,
            "design_metrics": self.design_metrics,
            "error": self.error,
        }


@dataclass
class CrawlResult:
    """Result of a complete crawl session"""

    start_url: str
    pages: List[CrawledPage] = field(default_factory=list)
    all_products: List[Dict[str, Any]] = field(default_factory=list)
    all_images: List[Dict[str, str]] = field(default_factory=list)
    site_structure: Dict[str, List[str]] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    design_analysis: Dict[str, Any] = field(default_factory=dict)
    crawl_time: float = 0.0
    pages_crawled: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_url": self.start_url,
            "crawl_time": self.crawl_time,
            "pages_crawled": self.pages_crawled,
            "pages": [p.to_dict() for p in self.pages],
            "all_products": self.all_products[:50],
            "all_images": self.all_images[:100],
            "site_structure": self.site_structure,
            "screenshots": self.screenshots,
            "design_analysis": self.design_analysis,
            "errors": self.errors,
        }


class PlaywrightCrawler:
    """
    Multi-page web crawler using Playwright for JS rendering.

    Crawls a website starting from a URL, follows internal links,
    and extracts rich content including products and images.
    """

    def __init__(
        self,
        max_pages: int = 10,
        max_depth: int = 2,
        timeout: int = 60000,
        wait_for_js: int = 5000,
        take_screenshots: bool = False,
        screenshot_dir: str = "output/screenshots",
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.wait_for_js = wait_for_js
        self.take_screenshots = take_screenshots
        self.screenshot_dir = screenshot_dir
        self.visited_urls: Set[str] = set()
        self.domain: str = ""

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        parsed = urlparse(url)
        # Remove trailing slash, fragment, and common tracking params
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc.endswith(
                f".{self.domain}"
            )
        except Exception:
            return False

    def _is_valid_page_url(self, url: str) -> bool:
        """Check if URL is worth crawling"""
        # Skip non-http URLs
        if not url.startswith(("http://", "https://")):
            return False

        # Skip common non-page resources
        skip_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".svg",
            ".ico",
            ".pdf",
            ".zip",
            ".css",
            ".js",
            ".woff",
            ".woff2",
            ".ttf",
            ".mp4",
            ".mp3",
            ".avi",
            ".mov",
        )
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False

        # Skip common non-content paths
        skip_patterns = (
            "/cdn-cgi/",
            "/wp-admin/",
            "/wp-includes/",
            "/cart",
            "/checkout",
            "/account",
            "/login",
            "/register",
            "?add-to-cart",
            "?remove-item",
        )
        if any(pattern in url.lower() for pattern in skip_patterns):
            return False

        return True

    async def _extract_page_data(self, page, url: str) -> CrawledPage:
        """Extract all relevant data from a rendered page"""
        crawled = CrawledPage(url=url)

        try:
            # Get title
            crawled.title = await page.title() or ""

            # Get meta tags
            meta_tags = await page.evaluate("""
                () => {
                    const metas = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        if (name && content) metas[name] = content;
                    });
                    return metas;
                }
            """)
            crawled.metadata = meta_tags

            # Get main text content
            crawled.content = await page.evaluate("""
                () => {
                    // Remove script and style elements
                    const clone = document.body.cloneNode(true);
                    clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    return clone.innerText.replace(/\\s+/g, ' ').trim();
                }
            """)

            # Get all internal links
            links = await page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href && !href.startsWith('javascript:') && !href.startsWith('mailto:')) {
                            links.push(href);
                        }
                    });
                    return [...new Set(links)];
                }
            """)
            crawled.links = [
                l
                for l in links
                if self._is_same_domain(l) and self._is_valid_page_url(l)
            ]

            # Get all images with context
            crawled.images = await page.evaluate("""
                () => {
                    const images = [];
                    document.querySelectorAll('img').forEach(img => {
                        const src = img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src');
                        if (src && !src.startsWith('data:')) {
                            images.push({
                                src: src,
                                alt: img.alt || '',
                                width: img.naturalWidth || img.width || 0,
                                height: img.naturalHeight || img.height || 0,
                                context: img.closest('article, .product, .item')?.innerText?.slice(0, 100) || ''
                            });
                        }
                    });
                    return images;
                }
            """)

            # Try to extract product data (common e-commerce patterns)
            crawled.products = await page.evaluate("""
                () => {
                    const products = [];

                    // Try JSON-LD structured data first
                    document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                        try {
                            const data = JSON.parse(script.textContent);
                            if (data['@type'] === 'Product' || (Array.isArray(data) && data[0]?.['@type'] === 'Product')) {
                                const items = Array.isArray(data) ? data : [data];
                                items.forEach(item => {
                                    if (item['@type'] === 'Product') {
                                        products.push({
                                            name: item.name,
                                            price: item.offers?.price || item.offers?.[0]?.price,
                                            currency: item.offers?.priceCurrency || item.offers?.[0]?.priceCurrency,
                                            image: item.image?.[0] || item.image,
                                            description: item.description?.slice(0, 200),
                                            url: item.url,
                                            source: 'json-ld'
                                        });
                                    }
                                });
                            }
                        } catch (e) {}
                    });

                    // Fallback: try common CSS selectors for product cards
                    if (products.length === 0) {
                        const selectors = [
                            '.product-card', '.product-item', '.product-tile',
                            '[data-product]', '.item-card', '.collection-item',
                            'article[class*="product"]', 'div[class*="ProductCard"]'
                        ];

                        for (const selector of selectors) {
                            document.querySelectorAll(selector).forEach(el => {
                                const nameEl = el.querySelector('h2, h3, h4, .product-name, .product-title, [class*="name"], [class*="title"]');
                                const priceEl = el.querySelector('.price, [class*="price"], [data-price]');
                                const imgEl = el.querySelector('img');
                                const linkEl = el.querySelector('a[href]');

                                if (nameEl) {
                                    products.push({
                                        name: nameEl.innerText.trim(),
                                        price: priceEl?.innerText?.trim() || null,
                                        image: imgEl?.src || imgEl?.getAttribute('data-src'),
                                        url: linkEl?.href,
                                        source: 'css-selector'
                                    });
                                }
                            });
                            if (products.length > 0) break;
                        }
                    }

                    return products;
                }
            """)

            # Extract design metrics (colors, fonts, spacing)
            crawled.design_metrics = await page.evaluate("""
                () => {
                    const design = {
                        colors: {
                            background: [],
                            text: [],
                            accent: [],
                            all: []
                        },
                        typography: {
                            fonts: [],
                            heading_sizes: [],
                            body_size: null,
                            line_heights: []
                        },
                        spacing: {
                            paddings: [],
                            margins: [],
                            gaps: []
                        },
                        buttons: {
                            styles: [],
                            colors: [],
                            border_radius: []
                        },
                        layout: {
                            max_width: null,
                            has_grid: false,
                            has_flexbox: false
                        }
                    };

                    const colorSet = new Set();
                    const fontSet = new Set();

                    // Sample elements for computed styles
                    const sampleElements = [
                        document.body,
                        document.querySelector('header'),
                        document.querySelector('main'),
                        document.querySelector('nav'),
                        document.querySelector('footer'),
                        document.querySelector('h1'),
                        document.querySelector('h2'),
                        document.querySelector('p'),
                        document.querySelector('a'),
                        document.querySelector('button, .btn, [class*="button"]'),
                    ].filter(Boolean);

                    sampleElements.forEach(el => {
                        const style = window.getComputedStyle(el);

                        // Colors
                        const bgColor = style.backgroundColor;
                        const textColor = style.color;
                        if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)') colorSet.add(bgColor);
                        if (textColor) colorSet.add(textColor);

                        // Fonts
                        const fontFamily = style.fontFamily.split(',')[0].trim().replace(/['"]/g, '');
                        if (fontFamily) fontSet.add(fontFamily);

                        // Font sizes for headings
                        if (el.tagName && el.tagName.match(/^H[1-6]$/)) {
                            design.typography.heading_sizes.push({
                                tag: el.tagName,
                                size: style.fontSize,
                                weight: style.fontWeight
                            });
                        }

                        // Body text size
                        if (el.tagName === 'P' && !design.typography.body_size) {
                            design.typography.body_size = style.fontSize;
                        }
                    });

                    // Convert colors to hex
                    const rgbToHex = (rgb) => {
                        const match = rgb.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                        if (match) {
                            const r = parseInt(match[1]).toString(16).padStart(2, '0');
                            const g = parseInt(match[2]).toString(16).padStart(2, '0');
                            const b = parseInt(match[3]).toString(16).padStart(2, '0');
                            return `#${r}${g}${b}`.toUpperCase();
                        }
                        return rgb;
                    };

                    design.colors.all = [...colorSet].map(rgbToHex).filter(c => c.startsWith('#'));
                    design.typography.fonts = [...fontSet];

                    // Extract button styles
                    const buttons = document.querySelectorAll('button, .btn, [class*="button"], a[class*="cta"]');
                    buttons.forEach(btn => {
                        const style = window.getComputedStyle(btn);
                        design.buttons.colors.push(rgbToHex(style.backgroundColor));
                        design.buttons.border_radius.push(style.borderRadius);
                    });

                    // Dedupe button data
                    design.buttons.colors = [...new Set(design.buttons.colors)].slice(0, 5);
                    design.buttons.border_radius = [...new Set(design.buttons.border_radius)].slice(0, 3);

                    // Check for grid/flexbox
                    document.querySelectorAll('*').forEach(el => {
                        const display = window.getComputedStyle(el).display;
                        if (display === 'grid') design.layout.has_grid = true;
                        if (display === 'flex') design.layout.has_flexbox = true;
                    });

                    // Get container max-width
                    const container = document.querySelector('.container, [class*="container"], main, .wrapper');
                    if (container) {
                        design.layout.max_width = window.getComputedStyle(container).maxWidth;
                    }

                    return design;
                }
            """)

        except Exception as e:
            crawled.error = str(e)
            logger.warning(f"Error extracting data from {url}: {e}")

        return crawled

    async def _take_screenshot(self, page, url: str, page_index: int) -> Optional[str]:
        """Take a full-page screenshot and save it"""
        import os

        try:
            os.makedirs(self.screenshot_dir, exist_ok=True)

            # Create safe filename from URL
            parsed = urlparse(url)
            path_part = parsed.path.replace("/", "_").strip("_") or "home"
            filename = f"{parsed.netloc}_{path_part}_{page_index}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            # Take full page screenshot
            await page.screenshot(path=filepath, full_page=True)
            logger.info(f"Screenshot saved: {filepath}")

            return filepath
        except Exception as e:
            logger.warning(f"Failed to take screenshot of {url}: {e}")
            return None

    async def crawl(self, start_url: str) -> CrawlResult:
        """
        Crawl a website starting from the given URL.

        Args:
            start_url: The URL to start crawling from

        Returns:
            CrawlResult with all crawled data
        """
        from playwright.async_api import async_playwright

        start_time = datetime.now()
        result = CrawlResult(start_url=start_url)

        # Set domain
        parsed = urlparse(start_url)
        self.domain = parsed.netloc

        # Queue: (url, depth)
        queue: List[tuple] = [(start_url, 0)]
        self.visited_urls = set()

        logger.info(
            f"Starting crawl of {start_url} (max {self.max_pages} pages, depth {self.max_depth})"
        )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                while queue and len(result.pages) < self.max_pages:
                    url, depth = queue.pop(0)
                    normalized = self._normalize_url(url)

                    if normalized in self.visited_urls:
                        continue

                    self.visited_urls.add(normalized)
                    logger.info(
                        f"Crawling [{len(result.pages) + 1}/{self.max_pages}] (depth={depth}): {url}"
                    )

                    try:
                        # Navigate and wait for JS to render
                        # Use 'domcontentloaded' for faster initial load, then wait for JS
                        await page.goto(
                            url, timeout=self.timeout, wait_until="domcontentloaded"
                        )
                        await page.wait_for_timeout(self.wait_for_js)

                        # Try to wait for body content to be visible
                        try:
                            await page.wait_for_selector("body", timeout=5000)
                        except Exception:
                            pass

                        # Extract data
                        crawled = await self._extract_page_data(page, url)

                        # Take screenshot if enabled
                        if self.take_screenshots:
                            screenshot_path = await self._take_screenshot(
                                page, url, len(result.pages)
                            )
                            if screenshot_path:
                                crawled.screenshot_path = screenshot_path
                                result.screenshots.append(screenshot_path)

                        result.pages.append(crawled)

                        # Collect products and images
                        result.all_products.extend(crawled.products)
                        result.all_images.extend(crawled.images)

                        # Track site structure
                        path = urlparse(url).path or "/"
                        if path not in result.site_structure:
                            result.site_structure[path] = []
                        result.site_structure[path] = crawled.links[:5]

                        # Add new URLs to queue if not at max depth
                        if depth < self.max_depth:
                            for link in crawled.links:
                                link_normalized = self._normalize_url(link)
                                if link_normalized not in self.visited_urls:
                                    queue.append((link, depth + 1))

                    except Exception as e:
                        error_msg = f"Failed to crawl {url}: {str(e)}"
                        logger.warning(error_msg)
                        result.errors.append(error_msg)
                        result.pages.append(CrawledPage(url=url, error=str(e)))

                await browser.close()

        except Exception as e:
            error_msg = f"Browser error: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        result.crawl_time = (datetime.now() - start_time).total_seconds()
        result.pages_crawled = len([p for p in result.pages if not p.error])

        # Deduplicate products by name
        seen_products = set()
        unique_products = []
        for p in result.all_products:
            name = p.get("name", "")
            if name and name not in seen_products:
                seen_products.add(name)
                unique_products.append(p)
        result.all_products = unique_products

        # Deduplicate images by src
        seen_images = set()
        unique_images = []
        for img in result.all_images:
            src = img.get("src", "")
            if src and src not in seen_images:
                seen_images.add(src)
                unique_images.append(img)
        result.all_images = unique_images

        # Aggregate design metrics from all pages
        result.design_analysis = self._aggregate_design_metrics(result.pages)

        logger.info(
            f"Crawl complete: {result.pages_crawled} pages, {len(result.all_products)} products, {len(result.all_images)} images in {result.crawl_time:.1f}s"
        )

        return result

    def _aggregate_design_metrics(self, pages: List[CrawledPage]) -> Dict[str, Any]:
        """Aggregate design metrics from all crawled pages"""
        all_colors = set()
        all_fonts = set()
        all_button_colors = set()
        all_button_radii = set()
        heading_sizes = []
        body_sizes = []

        for page in pages:
            metrics = page.design_metrics
            if not metrics:
                continue

            # Collect colors
            colors = metrics.get("colors", {})
            all_colors.update(colors.get("all", []))

            # Collect fonts
            typography = metrics.get("typography", {})
            all_fonts.update(typography.get("fonts", []))
            heading_sizes.extend(typography.get("heading_sizes", []))
            if typography.get("body_size"):
                body_sizes.append(typography.get("body_size"))

            # Collect button styles
            buttons = metrics.get("buttons", {})
            all_button_colors.update(buttons.get("colors", []))
            all_button_radii.update(buttons.get("border_radius", []))

        # Find most common values
        return {
            "brand_colors": list(all_colors)[:10],
            "fonts": list(all_fonts)[:5],
            "button_colors": list(all_button_colors)[:5],
            "button_border_radius": list(all_button_radii)[:3],
            "heading_sizes": heading_sizes[:5],
            "body_size": body_sizes[0] if body_sizes else None,
        }


async def _crawl_async(
    url: str,
    max_pages: int = 10,
    max_depth: int = 2,
    timeout: int = 60000,
    wait_for_js: int = 5000,
    take_screenshots: bool = False,
    screenshot_dir: str = "output/screenshots",
) -> CrawlResult:
    """Async wrapper for crawling"""
    crawler = PlaywrightCrawler(
        max_pages=max_pages,
        max_depth=max_depth,
        timeout=timeout,
        wait_for_js=wait_for_js,
        take_screenshots=take_screenshots,
        screenshot_dir=screenshot_dir,
    )
    return await crawler.crawl(url)


def web_crawler_ability(
    url: str,
    max_pages: int = 10,
    max_depth: int = 2,
) -> str:
    """
    Crawl a website deeply using Playwright for JavaScript rendering.

    Args:
        url: Starting URL to crawl
        max_pages: Maximum number of pages to crawl (default: 10)
        max_depth: Maximum link depth to follow (default: 2)

    Returns:
        JSON string with crawl results including pages, products, and images
    """
    logger.info(f"Web crawler ability called for: {url}")

    # Clean URL
    url = url.strip()
    if not url.startswith("http"):
        url_match = re.search(r"https?://[^\s]+", url)
        if url_match:
            url = url_match.group(0)
        else:
            url = f"https://{url}"

    try:
        # Run async crawler (handles nested event loops)
        result = run_async(
            _crawl_async(
                url=url,
                max_pages=max_pages,
                max_depth=max_depth,
            )
        )

        return json.dumps(result.to_dict(), indent=2)

    except Exception as e:
        logger.error(f"Web crawler failed: {e}", exc_info=True)
        return json.dumps(
            {
                "error": str(e),
                "url": url,
                "pages_crawled": 0,
            }
        )


def web_crawler_with_screenshots_ability(
    url: str,
    max_pages: int = 5,
    max_depth: int = 1,
    screenshot_dir: str = "output/screenshots",
) -> str:
    """
    Crawl a website with full-page screenshots and design analysis.

    This enhanced crawler captures:
    - Screenshots of each page visited
    - Design metrics (colors, fonts, button styles)
    - Products and images

    Args:
        url: Starting URL to crawl (or task description containing URL)
        max_pages: Maximum number of pages to crawl (default: 5)
        max_depth: Maximum link depth to follow (default: 1)
        screenshot_dir: Directory to save screenshots (default: output/screenshots)

    Returns:
        JSON string with crawl results including screenshot paths and design analysis
    """
    logger.info(f"Web crawler with screenshots called for: {url}")

    # Store original input for parameter extraction
    original_input = url

    # Extract URL from task description
    url = url.strip()
    if not url.startswith("http"):
        url_match = re.search(r"https?://[^\s]+", url)
        if url_match:
            url = url_match.group(0)
        else:
            url = f"https://{url}"

    # Extract screenshot_dir from task description if specified
    # Patterns: "Save to output/domain/screenshots/", "save screenshots to output/..."
    screenshot_dir_match = re.search(
        r"(?:save|Save).*?(?:to|in)\s+(output/[^\s,]+)", original_input
    )
    if screenshot_dir_match:
        screenshot_dir = screenshot_dir_match.group(1).rstrip("/")
        logger.info(f"Using screenshot directory from task: {screenshot_dir}")

    # Extract max_pages from task description if specified
    # Patterns: "max_pages=5", "max 5 pages", "up to 5 pages"
    max_pages_match = re.search(
        r"max_pages\s*=\s*(\d+)|max\s+(\d+)\s+pages|up\s+to\s+(\d+)\s+pages",
        original_input,
        re.IGNORECASE,
    )
    if max_pages_match:
        max_pages = int(next(g for g in max_pages_match.groups() if g))
        logger.info(f"Using max_pages from task: {max_pages}")

    try:
        # Run async crawler with screenshots enabled (handles nested event loops)
        result = run_async(
            _crawl_async(
                url=url,
                max_pages=max_pages,
                max_depth=max_depth,
                take_screenshots=True,
                screenshot_dir=screenshot_dir,
            )
        )

        return json.dumps(result.to_dict(), indent=2)

    except Exception as e:
        logger.error(f"Web crawler with screenshots failed: {e}", exc_info=True)
        return json.dumps(
            {
                "error": str(e),
                "url": url,
                "pages_crawled": 0,
            }
        )


# For direct testing
if __name__ == "__main__":
    import sys

    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://th.cos.com"
    take_screenshots = "--screenshots" in sys.argv

    print(f"Testing crawler on: {test_url}")
    print(f"Screenshots: {'enabled' if take_screenshots else 'disabled'}")

    if take_screenshots:
        result = web_crawler_with_screenshots_ability(
            test_url, max_pages=3, max_depth=1
        )
    else:
        result = web_crawler_ability(test_url, max_pages=5, max_depth=1)
    print(result)

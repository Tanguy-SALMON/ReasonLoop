"""
Website Intelligence Ability - Deep analysis for email campaign generation
Extracts brand identity, products, messaging, and customer insights from websites
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebsiteIntelligenceExtractor:
    """Extract comprehensive website intelligence for email campaigns"""

    def __init__(self, url: str):
        self.url = url
        self.domain = urlparse(url).netloc
        self.soup = None
        self.html = ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_website(self) -> bool:
        """Fetch and parse the website"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=15)
            response.raise_for_status()
            self.html = response.text
            self.soup = BeautifulSoup(self.html, "html.parser")
            logger.info(f"Successfully fetched {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to fetch {self.url}: {e}")
            return False

    def extract_brand_identity(self) -> Dict[str, Any]:
        """Extract brand name, logo, colors, fonts, tagline"""
        identity = {
            "name": "",
            "tagline": "",
            "logo_url": "",
            "colors": [],
            "fonts": [],
            "favicon_url": "",
            "mission_statement": "",
        }

        # Brand name - from title, og:site_name, or h1
        title_tag = self.soup.find("title")
        if title_tag:
            identity["name"] = title_tag.string.strip() if title_tag.string else ""

        og_site_name = self.soup.find("meta", property="og:site_name")
        if og_site_name and og_site_name.get("content"):
            identity["name"] = og_site_name["content"]

        # Logo - find img in header/navbar with logo/brand in class/id
        logo_candidates = self.soup.find_all(
            "img", class_=re.compile(r"logo|brand", re.I)
        )
        if not logo_candidates:
            logo_candidates = self.soup.find_all(
                "img", id=re.compile(r"logo|brand", re.I)
            )

        if logo_candidates:
            logo_url = logo_candidates[0].get("src", "")
            if logo_url:
                identity["logo_url"] = urljoin(self.url, logo_url)

        # Favicon
        favicon = self.soup.find("link", rel=re.compile(r"icon", re.I))
        if favicon:
            identity["favicon_url"] = urljoin(self.url, favicon.get("href", ""))

        # Tagline - look for common patterns
        tagline_candidates = self.soup.find_all(
            ["p", "div", "h2"], class_=re.compile(r"tagline|slogan|subtitle", re.I)
        )
        if tagline_candidates:
            identity["tagline"] = tagline_candidates[0].get_text(strip=True)

        # Colors - extract from CSS (simplified)
        colors = self._extract_colors()
        identity["colors"] = colors[:5]  # Top 5 colors

        # Fonts - extract from CSS
        fonts = self._extract_fonts()
        identity["fonts"] = fonts[:3]  # Top 3 fonts

        # Mission - look in About section
        about_section = self.soup.find(
            ["section", "div"], class_=re.compile(r"about|mission|story", re.I)
        )
        if about_section:
            identity["mission_statement"] = about_section.get_text(strip=True)[:300]

        return identity

    def extract_brand_voice(self) -> Dict[str, Any]:
        """Analyze tone, language patterns, CTAs"""
        voice = {
            "tone": [],
            "characteristics": "",
            "cta_patterns": [],
            "emoji_usage": False,
        }

        # Extract all text content
        text_content = self.soup.get_text()

        # Check for emojis
        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]"
        )
        voice["emoji_usage"] = bool(emoji_pattern.search(text_content))

        # Extract CTAs from buttons and links
        cta_elements = self.soup.find_all(
            ["a", "button"], class_=re.compile(r"btn|button|cta", re.I)
        )
        ctas = set()
        for cta in cta_elements[:10]:
            cta_text = cta.get_text(strip=True)
            if cta_text and len(cta_text) < 30:
                ctas.add(cta_text)
        voice["cta_patterns"] = list(ctas)

        # Tone analysis (simple heuristics)
        text_lower = text_content.lower()

        if any(
            word in text_lower for word in ["luxury", "premium", "exclusive", "elegant"]
        ):
            voice["tone"].append("luxury")
        if any(word in text_lower for word in ["fun", "playful", "enjoy", "love"]):
            voice["tone"].append("playful")
        if any(
            word in text_lower
            for word in ["professional", "enterprise", "business", "corporate"]
        ):
            voice["tone"].append("professional")
        if any(word in text_lower for word in ["simple", "easy", "quick", "fast"]):
            voice["tone"].append("accessible")

        voice["characteristics"] = (
            f"Website uses {'emojis' if voice['emoji_usage'] else 'no emojis'}, "
            f"tone appears {', '.join(voice['tone']) if voice['tone'] else 'neutral'}"
        )

        return voice

    def extract_products(self) -> Dict[str, Any]:
        """Extract product categories, featured items, pricing"""
        products = {
            "categories": [],
            "featured_items": [],
            "price_range": {"min": 0, "max": 0},
            "pricing_tier": "unknown",
        }

        # Extract categories from navigation
        nav = self.soup.find(["nav", "header"])
        if nav:
            links = nav.find_all("a")
            categories = []
            for link in links:
                text = link.get_text(strip=True)
                if (
                    text
                    and len(text) < 50
                    and text.lower() not in ["home", "about", "contact", "login"]
                ):
                    categories.append(text)
            products["categories"] = categories[:10]

        # Find featured products
        product_sections = self.soup.find_all(
            ["div", "article"], class_=re.compile(r"product|item", re.I)
        )
        featured = []
        prices = []

        for product in product_sections[:5]:
            product_name = product.find(["h2", "h3", "h4"])
            price = product.find(class_=re.compile(r"price", re.I))

            if product_name:
                product_data = {"name": product_name.get_text(strip=True)}

                if price:
                    price_text = price.get_text(strip=True)
                    # Extract numeric price
                    price_match = re.search(r"[\d,]+\.?\d*", price_text)
                    if price_match:
                        try:
                            price_value = float(price_match.group().replace(",", ""))
                            product_data["price"] = price_value
                            prices.append(price_value)
                        except ValueError:
                            pass

                featured.append(product_data)

        products["featured_items"] = featured

        if prices:
            products["price_range"] = {"min": min(prices), "max": max(prices)}
            avg_price = sum(prices) / len(prices)
            if avg_price < 50:
                products["pricing_tier"] = "budget"
            elif avg_price < 200:
                products["pricing_tier"] = "mid-range"
            else:
                products["pricing_tier"] = "premium"

        return products

    def extract_value_propositions(self) -> Dict[str, Any]:
        """Extract USPs, guarantees, quality claims"""
        usps = {"primary_usp": "", "secondary_usps": [], "guarantees": []}

        # Look for hero section
        hero = self.soup.find(
            ["section", "div"], class_=re.compile(r"hero|banner|jumbotron", re.I)
        )
        if hero:
            hero_text = hero.get_text(strip=True)
            usps["primary_usp"] = hero_text[:200]

        # Look for USP indicators
        text_content = self.soup.get_text().lower()

        usp_keywords = {
            "Free shipping": r"free\s+shipping",
            "Money-back guarantee": r"money.?back\s+guarantee",
            "Sustainable": r"sustainable|eco.?friendly",
            "Handmade": r"handmade|hand.?crafted",
            "Premium quality": r"premium\s+quality",
            "Fast delivery": r"fast\s+delivery|quick\s+shipping",
        }

        for usp_name, pattern in usp_keywords.items():
            if re.search(pattern, text_content, re.I):
                usps["secondary_usps"].append(usp_name)

        return usps

    def extract_promotions(self) -> Dict[str, Any]:
        """Find current offers, discounts, incentives"""
        promotions = {
            "current_offers": [],
            "discount_types": [],
            "first_timer_incentive": "",
        }

        # Look for promotional banners
        promo_sections = self.soup.find_all(
            ["div", "section"], class_=re.compile(r"promo|banner|offer|sale", re.I)
        )

        for promo in promo_sections[:3]:
            promo_text = promo.get_text(strip=True)
            if promo_text and len(promo_text) < 200:
                promotions["current_offers"].append(promo_text)

        # Look for discount patterns
        text_content = self.soup.get_text()
        if re.search(r"\d+%\s+off", text_content, re.I):
            promotions["discount_types"].append("percentage_discount")
        if re.search(r"free\s+shipping", text_content, re.I):
            promotions["discount_types"].append("free_shipping")
        if re.search(r"buy\s+\d+\s+get\s+\d+", text_content, re.I):
            promotions["discount_types"].append("bogo")

        # Look for newsletter signup incentive
        newsletter = self.soup.find(
            ["form", "div"], class_=re.compile(r"newsletter|subscribe", re.I)
        )
        if newsletter:
            incentive_text = newsletter.get_text(strip=True)
            promotions["first_timer_incentive"] = incentive_text[:150]

        return promotions

    def extract_audience_insights(self) -> Dict[str, Any]:
        """Extract target demographic, testimonials"""
        audience = {"target_demographic": "", "pain_points": [], "testimonials": []}

        # Look for testimonials/reviews
        testimonial_sections = self.soup.find_all(
            ["div", "section"], class_=re.compile(r"testimonial|review|quote", re.I)
        )

        for testimonial in testimonial_sections[:5]:
            text = testimonial.get_text(strip=True)
            if text and 20 < len(text) < 300:
                audience["testimonials"].append(text)

        return audience

    def extract_technical_info(self) -> Dict[str, Any]:
        """Detect platform, blog, currency"""
        technical = {"platform": "unknown", "blog_topics": [], "currency": "USD"}

        # Detect e-commerce platform
        html_lower = self.html.lower()
        if "shopify" in html_lower:
            technical["platform"] = "Shopify"
        elif "woocommerce" in html_lower:
            technical["platform"] = "WooCommerce"
        elif "magento" in html_lower:
            technical["platform"] = "Magento"
        elif "bigcommerce" in html_lower:
            technical["platform"] = "BigCommerce"

        # Look for blog
        blog_links = self.soup.find_all(
            "a", href=re.compile(r"/blog|/news|/articles", re.I)
        )
        if blog_links:
            technical["blog_topics"] = ["Blog exists - requires deeper scraping"]

        # Detect currency
        currency_symbols = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
        for symbol, code in currency_symbols.items():
            if symbol in self.soup.get_text():
                technical["currency"] = code
                break

        return technical

    def extract_seo_metadata(self) -> Dict[str, Any]:
        """Extract SEO elements"""
        seo = {"title": "", "meta_description": "", "primary_keywords": []}

        # Title
        title_tag = self.soup.find("title")
        if title_tag:
            seo["title"] = title_tag.string.strip() if title_tag.string else ""

        # Meta description
        meta_desc = self.soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            seo["meta_description"] = meta_desc.get("content", "")

        # Keywords from meta keywords tag (if present)
        meta_keywords = self.soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            keywords = meta_keywords.get("content", "").split(",")
            seo["primary_keywords"] = [k.strip() for k in keywords[:5]]

        return seo

    def extract_trust_signals(self) -> Dict[str, Any]:
        """Find security badges, payment methods, social proof"""
        trust = {
            "security_badges": [],
            "payment_methods": [],
            "press_mentions": [],
            "social_media": {},
        }

        # Look for payment logos
        payment_patterns = [
            "visa",
            "mastercard",
            "amex",
            "paypal",
            "stripe",
            "apple-pay",
            "google-pay",
        ]
        for payment in payment_patterns:
            if re.search(payment, self.html, re.I):
                trust["payment_methods"].append(payment.upper())

        # Look for social media links
        social_patterns = {
            "instagram": r"instagram\.com",
            "facebook": r"facebook\.com",
            "twitter": r"twitter\.com|x\.com",
            "tiktok": r"tiktok\.com",
            "pinterest": r"pinterest\.com",
        }

        for platform, pattern in social_patterns.items():
            links = self.soup.find_all("a", href=re.compile(pattern, re.I))
            if links:
                trust["social_media"][platform] = links[0].get("href", "")

        return trust

    def _extract_colors(self) -> List[str]:
        """Extract dominant colors from inline styles and CSS"""
        colors = set()

        # Find all style attributes
        elements_with_style = self.soup.find_all(style=True)
        for element in elements_with_style:
            style = element.get("style", "")
            # Find hex colors
            hex_colors = re.findall(r"#[0-9a-fA-F]{6}", style)
            colors.update(hex_colors)

        # Find style tags
        style_tags = self.soup.find_all("style")
        for style_tag in style_tags:
            if style_tag.string:
                hex_colors = re.findall(r"#[0-9a-fA-F]{6}", style_tag.string)
                colors.update(hex_colors)

        return list(colors)

    def _extract_fonts(self) -> List[str]:
        """Extract font families from CSS"""
        fonts = set()

        # Find style tags
        style_tags = self.soup.find_all("style")
        for style_tag in style_tags:
            if style_tag.string:
                font_matches = re.findall(
                    r"font-family:\s*([^;]+)", style_tag.string, re.I
                )
                for match in font_matches:
                    # Clean up font name
                    font = match.split(",")[0].strip().strip("\"'")
                    if font and font.lower() not in ["inherit", "initial"]:
                        fonts.add(font)

        return list(fonts)

    def extract_design_metrics(self) -> Dict[str, Any]:
        """
        Extract detailed design metrics: fonts with URLs, spacing, borders, etc.
        Critical for replicating brand design in email templates.
        """
        design = {
            "typography": {
                "font_families": [],
                "font_urls": [],
                "heading_sizes": [],
                "body_sizes": [],
                "line_heights": [],
                "font_weights": [],
            },
            "spacing": {
                "margins": [],
                "paddings": [],
                "gaps": [],
            },
            "borders": {
                "border_radius": [],
                "border_widths": [],
                "border_styles": [],
                "border_colors": [],
            },
            "buttons": {
                "styles": [],
                "border_radius": None,
                "padding": None,
                "font_weight": None,
                "text_transform": None,
            },
            "layout": {
                "max_width": None,
                "container_padding": None,
                "grid_gap": None,
            },
        }

        # Extract Google Fonts / external font URLs
        font_links = self.soup.find_all(
            "link",
            href=re.compile(
                r"fonts\.googleapis\.com|fonts\.gstatic\.com|use\.typekit\.net|fast\.fonts\.net",
                re.I,
            ),
        )
        for link in font_links:
            href = link.get("href", "")
            if href:
                design["typography"]["font_urls"].append(href)
                # Extract font names from Google Fonts URL
                if "fonts.googleapis.com" in href:
                    font_matches = re.findall(r"family=([^&:]+)", href)
                    for match in font_matches:
                        fonts = match.replace("+", " ").split("|")
                        design["typography"]["font_families"].extend(fonts)

        # Look for @font-face declarations
        style_tags = self.soup.find_all("style")
        all_css = ""
        for style_tag in style_tags:
            if style_tag.string:
                all_css += style_tag.string

        # Extract @font-face font URLs
        font_face_urls = re.findall(
            r"@font-face[^}]*url\(['\"]?([^'\")\s]+)['\"]?\)", all_css, re.I
        )
        for url in font_face_urls:
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = urljoin(self.url, url)
            design["typography"]["font_urls"].append(url)

        # Extract font-family declarations
        font_families = re.findall(r"font-family:\s*([^;]+)", all_css, re.I)
        for ff in font_families:
            font = ff.split(",")[0].strip().strip("\"'")
            if font and font.lower() not in [
                "inherit",
                "initial",
                "sans-serif",
                "serif",
                "monospace",
            ]:
                if font not in design["typography"]["font_families"]:
                    design["typography"]["font_families"].append(font)

        # Extract font sizes
        font_sizes = re.findall(r"font-size:\s*([^;]+)", all_css, re.I)
        size_values = []
        for size in font_sizes:
            size = size.strip()
            if re.match(r"^\d+\.?\d*(px|rem|em|pt)$", size):
                size_values.append(size)
        # Dedupe and sort
        size_values = list(set(size_values))
        design["typography"]["heading_sizes"] = [
            s for s in size_values if self._parse_size(s) >= 18
        ][:5]
        design["typography"]["body_sizes"] = [
            s for s in size_values if 12 <= self._parse_size(s) < 18
        ][:3]

        # Extract line heights
        line_heights = re.findall(r"line-height:\s*([^;]+)", all_css, re.I)
        design["typography"]["line_heights"] = list(
            set([lh.strip() for lh in line_heights if lh.strip()])
        )[:5]

        # Extract font weights
        font_weights = re.findall(
            r"font-weight:\s*(\d+|normal|bold|lighter|bolder)", all_css, re.I
        )
        design["typography"]["font_weights"] = list(set(font_weights))

        # Extract margins
        margins = re.findall(
            r"margin(?:-(?:top|right|bottom|left))?:\s*([^;]+)", all_css, re.I
        )
        design["spacing"]["margins"] = self._extract_common_values(margins)

        # Extract paddings
        paddings = re.findall(
            r"padding(?:-(?:top|right|bottom|left))?:\s*([^;]+)", all_css, re.I
        )
        design["spacing"]["paddings"] = self._extract_common_values(paddings)

        # Extract gaps (flexbox/grid)
        gaps = re.findall(r"(?:row-gap|column-gap|gap):\s*([^;]+)", all_css, re.I)
        design["spacing"]["gaps"] = self._extract_common_values(gaps)

        # Extract border-radius
        border_radii = re.findall(r"border-radius:\s*([^;]+)", all_css, re.I)
        design["borders"]["border_radius"] = self._extract_common_values(border_radii)

        # Extract border widths
        border_widths = re.findall(
            r"border(?:-(?:top|right|bottom|left))?-width:\s*([^;]+)", all_css, re.I
        )
        design["borders"]["border_widths"] = self._extract_common_values(border_widths)

        # Extract border styles
        border_styles = re.findall(
            r"border(?:-(?:top|right|bottom|left))?-style:\s*([^;]+)", all_css, re.I
        )
        design["borders"]["border_styles"] = list(
            set([s.strip() for s in border_styles if s.strip()])
        )

        # Extract border colors
        border_colors = re.findall(
            r"border(?:-(?:top|right|bottom|left))?-color:\s*([^;]+)", all_css, re.I
        )
        design["borders"]["border_colors"] = list(
            set([c.strip() for c in border_colors if c.strip()])
        )[:5]

        # Extract button styles
        button_css = re.findall(
            r"(?:\.btn|\.button|button)[^{]*\{([^}]+)\}", all_css, re.I
        )
        if button_css:
            btn_style = button_css[0]
            # Extract button border-radius
            btn_radius = re.search(r"border-radius:\s*([^;]+)", btn_style, re.I)
            if btn_radius:
                design["buttons"]["border_radius"] = btn_radius.group(1).strip()
            # Extract button padding
            btn_padding = re.search(r"padding:\s*([^;]+)", btn_style, re.I)
            if btn_padding:
                design["buttons"]["padding"] = btn_padding.group(1).strip()
            # Extract button font-weight
            btn_weight = re.search(r"font-weight:\s*([^;]+)", btn_style, re.I)
            if btn_weight:
                design["buttons"]["font_weight"] = btn_weight.group(1).strip()
            # Extract text-transform
            btn_transform = re.search(r"text-transform:\s*([^;]+)", btn_style, re.I)
            if btn_transform:
                design["buttons"]["text_transform"] = btn_transform.group(1).strip()

        # Extract container/layout metrics
        container_css = re.findall(
            r"(?:\.container|\.wrapper|main)[^{]*\{([^}]+)\}", all_css, re.I
        )
        if container_css:
            container_style = container_css[0]
            max_width = re.search(r"max-width:\s*([^;]+)", container_style, re.I)
            if max_width:
                design["layout"]["max_width"] = max_width.group(1).strip()
            container_padding = re.search(r"padding:\s*([^;]+)", container_style, re.I)
            if container_padding:
                design["layout"]["container_padding"] = container_padding.group(
                    1
                ).strip()

        return design

    def _parse_size(self, size: str) -> float:
        """Parse a CSS size value to pixels (approximate)"""
        try:
            if "px" in size:
                return float(size.replace("px", ""))
            elif "rem" in size:
                return float(size.replace("rem", "")) * 16
            elif "em" in size:
                return float(size.replace("em", "")) * 16
            elif "pt" in size:
                return float(size.replace("pt", "")) * 1.333
            return 0
        except:
            return 0

    def _extract_common_values(self, values: List[str], limit: int = 5) -> List[str]:
        """Extract most common CSS values"""
        from collections import Counter

        cleaned = [v.strip() for v in values if v.strip() and v.strip() != "0"]
        if not cleaned:
            return []
        counts = Counter(cleaned)
        return [v for v, _ in counts.most_common(limit)]


def website_intelligence_ability(url: str) -> str:
    """
    Extract comprehensive website intelligence for email campaign generation

    Args:
        url: Target website URL

    Returns:
        JSON string with complete website intelligence
    """
    logger.info(f"Starting website intelligence extraction for: {url}")

    # Clean URL
    url = url.strip()
    if not url.startswith("http"):
        url_match = re.search(r"https?://[^\s]+", url)
        if url_match:
            url = url_match.group(0)
        else:
            # Assume https
            url = f"https://{url}"

    try:
        extractor = WebsiteIntelligenceExtractor(url)

        # Fetch website
        if not extractor.fetch_website():
            return json.dumps({"error": "Failed to fetch website", "url": url})

        # Extract all intelligence
        intelligence = {
            "website_url": url,
            "analysis_date": "",
            "brand_identity": extractor.extract_brand_identity(),
            "brand_voice": extractor.extract_brand_voice(),
            "products": extractor.extract_products(),
            "value_propositions": extractor.extract_value_propositions(),
            "promotions": extractor.extract_promotions(),
            "audience": extractor.extract_audience_insights(),
            "technical": extractor.extract_technical_info(),
            "seo": extractor.extract_seo_metadata(),
            "trust_signals": extractor.extract_trust_signals(),
        }

        # Add timestamp
        from datetime import datetime

        intelligence["analysis_date"] = datetime.now().isoformat()

        # Generate email campaign recommendations
        intelligence["email_campaign_recommendations"] = (
            _generate_campaign_recommendations(intelligence)
        )

        logger.info(f"Website intelligence extraction completed for {url}")
        return json.dumps(intelligence, indent=2)

    except Exception as e:
        logger.error(f"Website intelligence extraction failed: {e}", exc_info=True)
        return json.dumps({"error": str(e), "url": url})


def _generate_campaign_recommendations(intelligence: Dict[str, Any]) -> Dict[str, Any]:
    """Generate email campaign recommendations based on extracted intelligence"""
    recommendations = {
        "recommended_templates": [],
        "subject_line_style": "",
        "content_suggestions": [],
        "segmentation_opportunities": [],
    }

    # Analyze voice for subject line style
    voice = intelligence.get("brand_voice", {})
    tone = voice.get("tone", [])

    if "luxury" in tone:
        recommendations["subject_line_style"] = "Elegant, exclusive, sophisticated"
        recommendations["recommended_templates"] = [
            "luxury_announcement",
            "vip_exclusive",
        ]
    elif "playful" in tone:
        recommendations["subject_line_style"] = "Fun, emoji-friendly, casual"
        recommendations["recommended_templates"] = ["casual_promo", "friendly_welcome"]
    else:
        recommendations["subject_line_style"] = "Professional, clear, benefit-focused"
        recommendations["recommended_templates"] = ["professional_promo", "value_focus"]

    # Content suggestions based on USPs
    usps = intelligence.get("value_propositions", {}).get("secondary_usps", [])
    for usp in usps:
        recommendations["content_suggestions"].append(f"Highlight: {usp}")

    # Segmentation opportunities
    products = intelligence.get("products", {})
    if products.get("categories"):
        recommendations["segmentation_opportunities"].append(
            "Category-based segmentation"
        )

    pricing_tier = products.get("pricing_tier", "")
    if pricing_tier:
        recommendations["segmentation_opportunities"].append(
            f"Price-conscious vs premium ({pricing_tier})"
        )

    return recommendations


def deep_website_intelligence_ability(
    url: str,
    max_pages: int = 10,
    max_depth: int = 2,
) -> str:
    """
    Extract comprehensive website intelligence using Playwright for JS rendering.

    This is an enhanced version that:
    - Uses headless Chromium to render JavaScript
    - Crawls multiple pages (homepage, products, about, etc.)
    - Extracts real product data with images
    - Gets fully rendered content

    Args:
        url: Target website URL
        max_pages: Maximum pages to crawl (default: 10)
        max_depth: Maximum link depth (default: 2)

    Returns:
        JSON string with comprehensive website intelligence including crawled data
    """
    from datetime import datetime

    logger.info(f"Starting DEEP website intelligence extraction for: {url}")

    # Clean URL
    url = url.strip()
    if not url.startswith("http"):
        url_match = re.search(r"https?://[^\s]+", url)
        if url_match:
            url = url_match.group(0)
        else:
            url = f"https://{url}"

    try:
        # Import and use the Playwright crawler
        from abilities.web_crawler import web_crawler_ability

        logger.info(f"Crawling {url} with Playwright (max {max_pages} pages)...")
        crawl_result_json = web_crawler_ability(
            url, max_pages=max_pages, max_depth=max_depth
        )
        crawl_result = json.loads(crawl_result_json)

        if crawl_result.get("error"):
            logger.warning(
                f"Crawler error: {crawl_result['error']}, falling back to basic extraction"
            )
            return website_intelligence_ability(url)

        # Build enhanced intelligence from crawl data
        intelligence = {
            "website_url": url,
            "analysis_date": datetime.now().isoformat(),
            "crawl_stats": {
                "pages_crawled": crawl_result.get("pages_crawled", 0),
                "crawl_time": crawl_result.get("crawl_time", 0),
                "total_products_found": len(crawl_result.get("all_products", [])),
                "total_images_found": len(crawl_result.get("all_images", [])),
            },
        }

        # Extract brand identity from homepage
        homepage = (
            crawl_result.get("pages", [{}])[0] if crawl_result.get("pages") else {}
        )

        intelligence["brand_identity"] = {
            "name": homepage.get("title", "").split("|")[0].split("-")[0].strip(),
            "tagline": homepage.get("metadata", {}).get("og:description", "")[:100],
            "logo_url": "",
            "colors": [],
            "fonts": [],
            "favicon_url": "",
            "mission_statement": "",
        }

        # Find logo from images
        for img in crawl_result.get("all_images", []):
            if (
                "logo" in img.get("alt", "").lower()
                or "logo" in img.get("src", "").lower()
            ):
                intelligence["brand_identity"]["logo_url"] = img.get("src", "")
                break

        # Extract SEO from homepage metadata
        meta = homepage.get("metadata", {})
        intelligence["seo"] = {
            "title": homepage.get("title", ""),
            "meta_description": meta.get("description", meta.get("og:description", "")),
            "primary_keywords": [],
            "og_image": meta.get("og:image", ""),
        }

        # Real products from crawler
        intelligence["products"] = {
            "categories": list(
                set(
                    [
                        p.get("category", "Uncategorized")
                        for p in crawl_result.get("all_products", [])
                        if p.get("category")
                    ]
                )
            )[:10],
            "featured_items": [
                {
                    "name": p.get("name", ""),
                    "price": p.get("price"),
                    "currency": p.get("currency", ""),
                    "image": p.get("image", ""),
                    "url": p.get("url", ""),
                }
                for p in crawl_result.get("all_products", [])[:10]
            ],
            "price_range": _calculate_price_range(crawl_result.get("all_products", [])),
            "pricing_tier": "unknown",
            "total_products": len(crawl_result.get("all_products", [])),
        }

        # Determine pricing tier
        if intelligence["products"]["price_range"]["max"] > 0:
            avg = (
                intelligence["products"]["price_range"]["min"]
                + intelligence["products"]["price_range"]["max"]
            ) / 2
            if avg < 50:
                intelligence["products"]["pricing_tier"] = "budget"
            elif avg < 200:
                intelligence["products"]["pricing_tier"] = "mid-range"
            else:
                intelligence["products"]["pricing_tier"] = "premium"

        # All images for email design
        intelligence["images"] = {
            "hero_candidates": [
                img
                for img in crawl_result.get("all_images", [])
                if img.get("width", 0) > 600 or "hero" in img.get("context", "").lower()
            ][:5],
            "product_images": [
                img
                for img in crawl_result.get("all_images", [])
                if img.get("context")
                and any(
                    kw in img.get("context", "").lower()
                    for kw in ["product", "item", "shop", "buy"]
                )
            ][:20],
            "all_images": crawl_result.get("all_images", [])[:50],
        }

        # Site structure for navigation
        intelligence["site_structure"] = crawl_result.get("site_structure", {})

        # Analyze brand voice from content
        all_content = " ".join(
            [p.get("content", "")[:500] for p in crawl_result.get("pages", [])]
        )
        intelligence["brand_voice"] = _analyze_brand_voice(all_content)

        # Value propositions (scan content for common patterns)
        intelligence["value_propositions"] = _extract_value_props(all_content)

        # Promotions from content
        intelligence["promotions"] = _extract_promotions(all_content)

        # Technical info
        intelligence["technical"] = {
            "platform": _detect_platform(homepage.get("content", "")),
            "currency": _detect_currency(all_content),
            "has_blog": any(
                "/blog" in p.get("url", "") for p in crawl_result.get("pages", [])
            ),
        }

        # Generate recommendations
        intelligence["email_campaign_recommendations"] = (
            _generate_campaign_recommendations(intelligence)
        )

        # Add raw crawl data for reference
        intelligence["_crawl_data"] = {
            "pages_summary": [
                {"url": p.get("url"), "title": p.get("title")}
                for p in crawl_result.get("pages", [])
            ],
        }

        logger.info(
            f"Deep website intelligence completed: {intelligence['crawl_stats']}"
        )
        return json.dumps(intelligence, indent=2)

    except Exception as e:
        logger.error(f"Deep website intelligence failed: {e}", exc_info=True)
        # Fall back to basic extraction
        logger.info("Falling back to basic website intelligence extraction")
        return website_intelligence_ability(url)


def _calculate_price_range(products: List[Dict]) -> Dict[str, float]:
    """Calculate min/max price from products"""
    prices = []
    for p in products:
        price = p.get("price")
        if price:
            try:
                # Handle string prices like "$99.00" or "99.00"
                if isinstance(price, str):
                    price = float(re.sub(r"[^\d.]", "", price))
                prices.append(float(price))
            except (ValueError, TypeError):
                pass

    if prices:
        return {"min": min(prices), "max": max(prices)}
    return {"min": 0, "max": 0}


def _analyze_brand_voice(content: str) -> Dict[str, Any]:
    """Analyze brand voice from content"""
    content_lower = content.lower()

    tone = []
    if any(
        word in content_lower for word in ["luxury", "premium", "exclusive", "elegant"]
    ):
        tone.append("luxury")
    if any(word in content_lower for word in ["fun", "playful", "enjoy", "love"]):
        tone.append("playful")
    if any(
        word in content_lower for word in ["professional", "enterprise", "business"]
    ):
        tone.append("professional")
    if any(word in content_lower for word in ["simple", "easy", "quick", "fast"]):
        tone.append("accessible")
    if any(
        word in content_lower for word in ["sustainable", "eco", "organic", "natural"]
    ):
        tone.append("eco-conscious")

    # Check for emojis
    emoji_pattern = re.compile(
        "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff]"
    )
    has_emojis = bool(emoji_pattern.search(content))

    return {
        "tone": tone if tone else ["neutral"],
        "characteristics": f"{'Emoji-friendly' if has_emojis else 'Professional'}, {', '.join(tone) if tone else 'balanced'}",
        "emoji_usage": has_emojis,
        "cta_patterns": [],  # Would need more analysis
    }


def _extract_value_props(content: str) -> Dict[str, Any]:
    """Extract value propositions from content"""
    content_lower = content.lower()

    usps = []
    usp_patterns = {
        "Free shipping": r"free\s+shipping",
        "Money-back guarantee": r"money.?back|refund",
        "Sustainable": r"sustainable|eco.?friendly|organic",
        "Handmade": r"handmade|hand.?crafted|artisan",
        "Premium quality": r"premium\s+quality|high.?quality",
        "Fast delivery": r"fast\s+delivery|quick\s+shipping|express",
        "Secure checkout": r"secure\s+checkout|ssl|encrypted",
    }

    for usp_name, pattern in usp_patterns.items():
        if re.search(pattern, content_lower):
            usps.append(usp_name)

    return {
        "primary_usp": usps[0] if usps else "",
        "secondary_usps": usps[1:] if len(usps) > 1 else [],
        "guarantees": [
            u for u in usps if "guarantee" in u.lower() or "return" in u.lower()
        ],
    }


def _extract_promotions(content: str) -> Dict[str, Any]:
    """Extract promotional content"""
    promotions = {
        "current_offers": [],
        "discount_types": [],
        "first_timer_incentive": "",
    }

    # Find percentage discounts
    percent_matches = re.findall(r"(\d+)%\s*off", content, re.I)
    if percent_matches:
        promotions["discount_types"].append("percentage_discount")
        promotions["current_offers"].append(f"{percent_matches[0]}% off")

    # Find free shipping
    if re.search(r"free\s+shipping", content, re.I):
        promotions["discount_types"].append("free_shipping")
        promotions["current_offers"].append("Free shipping available")

    # Find signup incentives
    signup_match = re.search(r"sign\s*up.*?(\d+%?\s*off|free)", content, re.I)
    if signup_match:
        promotions["first_timer_incentive"] = signup_match.group(0)[:100]

    return promotions


def _detect_platform(content: str) -> str:
    """Detect e-commerce platform"""
    content_lower = content.lower()

    if "shopify" in content_lower:
        return "Shopify"
    elif "woocommerce" in content_lower:
        return "WooCommerce"
    elif "magento" in content_lower:
        return "Magento"
    elif "bigcommerce" in content_lower:
        return "BigCommerce"
    return "Custom/Unknown"


def _detect_currency(content: str) -> str:
    """Detect currency from content"""
    currency_patterns = {
        "USD": r"\$\d",
        "EUR": r"€\d",
        "GBP": r"£\d",
        "THB": r"฿\d|THB",
        "JPY": r"¥\d",
    }

    for currency, pattern in currency_patterns.items():
        if re.search(pattern, content):
            return currency
    return "USD"


# Register ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability

    register_ability("website-intelligence", website_intelligence_ability)
    register_ability("deep-website-intelligence", deep_website_intelligence_ability)

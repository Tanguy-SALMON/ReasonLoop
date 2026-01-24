"""
URL normalization and optimization utilities
Determines the best base URL for web scraping and analysis
"""

import logging
import re
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> Tuple[str, str]:
    """
    Normalize a URL and determine the optimal base URL for scraping.

    Returns:
        Tuple of (base_url, domain) where:
        - base_url: The optimal URL to use for scraping
        - domain: Clean domain name for folder/file naming

    Logic:
    - Remove trailing slashes
    - Detect locale/language paths (/us/en/, /fr/, etc.)
    - Decide whether to keep or remove them based on importance
    - Extract clean domain for naming
    """
    # Clean the URL
    url = url.strip().rstrip("/")

    # Parse URL
    parsed = urlparse(url)

    # Locale/language pattern detection
    # Common patterns: /us/en/, /en-us/, /fr/, /de-de/, /jp/ja/, etc.
    locale_patterns = [
        r"/([a-z]{2})/([a-z]{2})/?$",  # /us/en/
        r"/([a-z]{2})-([a-z]{2})/?$",  # /en-us/
        r"/([a-z]{2})/?$",  # /en/
    ]

    path = parsed.path
    has_locale = False
    locale_info = ""

    for pattern in locale_patterns:
        match = re.search(pattern, path, re.IGNORECASE)
        if match:
            has_locale = True
            locale_info = match.group(0).strip("/")
            break

    # Decide on base URL strategy
    if has_locale:
        # Check if it's a country-specific site that matters
        # Keep locale for: major brands, e-commerce, region-specific content
        # Remove locale for: global sites where locale is just a redirect

        # For now, we'll KEEP the locale if:
        # 1. It's a multi-segment path (like /us/en/ suggesting regional structure)
        # 2. The domain suggests it's already global (.com, .org)

        keep_locale = _should_keep_locale(parsed.netloc, path, locale_info)

        if keep_locale:
            base_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            logger.info(f"Keeping locale path: {locale_info}")
        else:
            # Remove locale and use root
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            logger.info(f"Removing locale path '{locale_info}', using root URL")
    else:
        # No locale detected, use the URL as-is or clean to root
        if path and path not in ["/", ""]:
            # There's a path but it's not a locale
            # For general scraping, prefer root unless it's a specific product/category
            if _looks_like_specific_page(path):
                # Keep the specific path
                base_url = f"{parsed.scheme}://{parsed.netloc}{path}"
                logger.info(f"Keeping specific path: {path}")
            else:
                # Use root for broad scraping
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                logger.info(f"Using root URL for broad scraping")
        else:
            base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Generate clean domain for naming
    domain = _clean_domain_name(parsed.netloc, path if has_locale else None)

    logger.info(f"Normalized URL: {url} -> {base_url}")
    logger.info(f"Domain identifier: {domain}")

    return base_url, domain


def _should_keep_locale(netloc: str, path: str, locale_info: str) -> bool:
    """
    Determine if locale should be kept in the URL.

    Keep locale if:
    - Multi-segment locale path (/us/en/) suggests region-specific structure
    - Domain is global TLD (.com, .org) - locale matters more

    Remove locale if:
    - Country-specific domain (.co.uk, .fr, .jp) - already regional
    - Single-segment locale (/en/) on global site - likely just language toggle
    """
    # Count locale segments
    locale_segments = locale_info.count("/") + 1

    # Check if domain is already country-specific
    country_tlds = [".co.uk", ".fr", ".de", ".jp", ".ca", ".au", ".in", ".cn", ".br"]
    is_country_domain = any(netloc.endswith(tld) for tld in country_tlds)

    # Global TLDs
    global_tlds = [".com", ".org", ".net", ".io"]
    is_global_domain = any(netloc.endswith(tld) for tld in global_tlds)

    # Decision logic
    if is_country_domain:
        # Already country-specific domain, locale path is probably redundant
        return False

    if is_global_domain and locale_segments >= 2:
        # Global domain with multi-segment locale = important regional structure
        return True

    # Default: remove single-segment locales, keep multi-segment
    return locale_segments >= 2


def _looks_like_specific_page(path: str) -> bool:
    """
    Check if path looks like a specific page vs. a category/section.

    Specific page indicators:
    - Contains product ID patterns
    - Has .html extension
    - Deep nested path (4+ segments)
    """
    if not path or path == "/":
        return False

    # HTML file
    if path.endswith(".html") or path.endswith(".htm"):
        return True

    # Product ID patterns (numbers, SKUs)
    if re.search(r"/p/\d+", path) or re.search(r"/product/\d+", path):
        return True

    # Very deep nesting suggests specific content
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 4:
        return True

    return False


def _clean_domain_name(netloc: str, locale_path: Optional[str] = None) -> str:
    """
    Create a clean domain identifier for file/folder naming.

    Examples:
    - www.shiseido.com/us/en/ -> www.shiseido.com
    - www.example.com -> www.example.com
    - shop.nike.com -> shop.nike.com
    """
    # Keep the full domain including www for clarity
    return netloc


# Quick test examples
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_urls = [
        "https://www.shiseido.com/us/en/",
        "https://www.shiseido.com/",
        "https://www.nike.com/fr/",
        "https://shop.adidas.co.uk/",
        "https://www.apple.com/iphone/",
        "https://www.amazon.com/dp/B08N5WRWNW/",
    ]

    for url in test_urls:
        base, domain = normalize_url(url)
        print(f"\nInput:  {url}")
        print(f"Base:   {base}")
        print(f"Domain: {domain}")

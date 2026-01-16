"""
Web scraping ability to extract content from URLs
"""

import logging
import re
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def web_scrape_ability(url: str) -> str:
    """Extract content from a specific URL"""
    logger.info(f"Web scrape: {url}")

    # Extract URL if embedded in text
    if not url.startswith('http'):
        url_match = re.search(r'https?://[^\s]+', url)
        if url_match:
            url = url_match.group(0)
        else:
            return "Error: No valid URL found"

    # Fetch page
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove unwanted elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.extract()

    # Extract main content
    main_elements = soup.select('main, article, .content, #content, .main, #main')
    if main_elements:
        content = main_elements[0].get_text(separator='\n', strip=True)
    else:
        content = soup.body.get_text(separator='\n', strip=True)

    # Clean whitespace
    content = re.sub(r'\n+', '\n', content)
    content = re.sub(r'\s+', ' ', content)

    # Truncate if too long
    if len(content) > 8000:
        content = content[:8000] + "...\n[Truncated]"

    # Format output
    title = soup.title.string if soup.title else "No title"
    output = f"Title: {title}\nURL: {url}\n\nContent:\n{content}"

    logger.info(f"Web scrape completed: {len(content)} chars")
    return output


# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("web-scrape", web_scrape_ability)

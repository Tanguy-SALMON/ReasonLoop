"""
Web search ability using DuckDuckGo with retry and fallback
"""

import logging
import asyncio
from typing import Optional
from config.settings import get_setting

logger = logging.getLogger(__name__)

try:
    import aiohttp
    from bs4 import BeautifulSoup
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("Missing dependencies for web search: aiohttp or beautifulsoup4")


def _generate_search_context(query: str) -> str:
    """Generate contextual information when search is unavailable"""
    return f"""Search query: "{query}"

Note: Direct web search is currently unavailable (bot detection). Here's what I can help with:

1. If you're looking for general information, I can provide answers based on my training data
2. For technical questions, I can offer programming solutions and best practices
3. For current events or real-time data, please try:
   - Reformulating your search query
   - Using a web browser directly
   - Checking specific sources manually

Please let me know how I can assist you with this topic using my existing knowledge."""


async def web_search_ability(query: str) -> str:
    """Search the web for information using DuckDuckGo"""
    logger.debug(f"ABILITY CALLED: web-search with query: {query}")

    if not get_setting("WEB_SEARCH_ENABLED", True):
        return "Web search is disabled in configuration."

    if not AIOHTTP_AVAILABLE:
        logger.warning("Web search dependencies not available")
        return _generate_search_context(query)

    max_retries = 2
    retry_delay = 2.0

    for attempt in range(max_retries):
        try:
            search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(search_url, headers=headers) as response:
                    # Handle bot detection (HTTP 202)
                    if response.status == 202:
                        logger.warning(f"DuckDuckGo returned HTTP 202 (bot detection) - attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.info("Returning contextual fallback due to bot detection")
                            return _generate_search_context(query)

                    response.raise_for_status()
                    html = await response.text()

            # Parse results
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            max_results = get_setting("WEB_SEARCH_RESULTS_COUNT", 5)

            for result in soup.select('.result'):
                title_elem = result.select_one('.result__title')
                link_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })

                    if len(results) >= max_results:
                        break

            if not results:
                logger.warning("No search results found")
                return _generate_search_context(query)

            # Format results
            formatted_results = f"Search results for: {query}\n\n"
            for i, result in enumerate(results, 1):
                formatted_results += f"{i}. {result['title']}\n"
                formatted_results += f"   URL: {result['link']}\n"
                if result['snippet']:
                    formatted_results += f"   {result['snippet']}\n"
                formatted_results += "\n"

            logger.info(f"Web search completed: found {len(results)} results")
            return formatted_results

        except asyncio.TimeoutError:
            logger.warning(f"Web search timeout - attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                return _generate_search_context(query)

        except Exception as e:
            logger.error(f"Web search error - attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                return _generate_search_context(query)

    return _generate_search_context(query)


# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("web-search", web_search_ability)

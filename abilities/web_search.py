"""
Web search ability using DuckDuckGo Instant Answer API
"""

import logging
import time
import requests
from typing import Optional
from config.settings import get_setting

logger = logging.getLogger(__name__)


def _generate_search_context(query: str) -> str:
    """Generate contextual information when search is unavailable"""
    return f"""Search query: "{query}"

Note: Direct web search is currently unavailable. Here's what I can help with:

1. If you're looking for general information, I can provide answers based on my training data
2. For technical questions, I can offer programming solutions and best practices
3. For current events or real-time data, please try:
   - Reformulating your search query
   - Using a web browser directly
   - Checking specific sources manually

Please let me know how I can assist you with this topic using my existing knowledge."""


def _ddg_instant_answer(query: str) -> dict:
    """
    Query DuckDuckGo Instant Answer API

    Args:
        query: Search query string

    Returns:
        JSON response from DuckDuckGo API
    """
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    }

    headers = {
        "User-Agent": "ReasonLoop/1.0"
    }

    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def _format_ddg_response(data: dict, query: str) -> str:
    """
    Format DuckDuckGo API response into readable text

    Args:
        data: JSON response from DuckDuckGo API
        query: Original search query

    Returns:
        Formatted search results as string
    """
    results = []

    # Abstract (main answer)
    if data.get("Abstract"):
        results.append(f"## Answer\n{data['Abstract']}")
        if data.get("AbstractURL"):
            results.append(f"Source: {data['AbstractURL']}")

    # Definition
    if data.get("Definition"):
        results.append(f"## Definition\n{data['Definition']}")
        if data.get("DefinitionURL"):
            results.append(f"Source: {data['DefinitionURL']}")

    # Answer (direct answer)
    if data.get("Answer"):
        results.append(f"## Direct Answer\n{data['Answer']}")

    # Related Topics
    related_topics = data.get("RelatedTopics", [])
    if related_topics:
        results.append("\n## Related Topics")
        count = 0
        for topic in related_topics[:5]:  # Limit to 5 related topics
            if isinstance(topic, dict) and topic.get("Text"):
                count += 1
                text = topic.get("Text", "")
                url = topic.get("FirstURL", "")
                results.append(f"\n{count}. {text}")
                if url:
                    results.append(f"   URL: {url}")

    # Infobox (additional structured data)
    if data.get("Infobox"):
        infobox = data["Infobox"]
        if infobox.get("content"):
            results.append("\n## Additional Information")
            for item in infobox["content"][:5]:  # Limit to 5 items
                if isinstance(item, dict):
                    label = item.get("label", "")
                    value = item.get("value", "")
                    if label and value:
                        results.append(f"- {label}: {value}")

    if not results:
        return _generate_search_context(query)

    formatted = f"Search results for: {query}\n\n"
    formatted += "\n\n".join(results)

    return formatted


def web_search_ability(query: str) -> str:
    """
    Search the web for information using DuckDuckGo Instant Answer API

    Args:
        query: Search query string

    Returns:
        Formatted search results as string
    """
    logger.debug(f"ABILITY CALLED: web-search with query: {query}")

    if not get_setting("WEB_SEARCH_ENABLED", True):
        return "Web search is disabled in configuration."

    max_retries = 2
    retry_delay = 2.0

    for attempt in range(max_retries):
        try:
            # Query DuckDuckGo API
            data = _ddg_instant_answer(query)

            # Format the response
            formatted_results = _format_ddg_response(data, query)

            logger.info(f"Web search completed successfully for query: {query}")
            return formatted_results

        except requests.Timeout:
            logger.warning(f"Web search timeout - attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return _generate_search_context(query)

        except requests.RequestException as e:
            logger.error(f"Web search request error - attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return _generate_search_context(query)

        except Exception as e:
            logger.error(f"Web search error - attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return _generate_search_context(query)

    return _generate_search_context(query)


# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("web-search", web_search_ability)

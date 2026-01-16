"""
Web search ability using DuckDuckGo Instant Answer API
"""

import logging
import requests
from config.settings import get_setting

logger = logging.getLogger(__name__)


def web_search_ability(query: str) -> str:
    """
    Search the web for information using DuckDuckGo Instant Answer API

    Args:
        query: Search query string

    Returns:
        Formatted search results as string
    """
    logger.info(f"Web search: {query}")

    if not get_setting("WEB_SEARCH_ENABLED", True):
        return "Web search is disabled in configuration."

    # Call DuckDuckGo API
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Format response
    results = []

    # Main answer
    if data.get("Abstract"):
        results.append(f"## Answer\n{data['Abstract']}")
        if data.get("AbstractURL"):
            results.append(f"Source: {data['AbstractURL']}")

    # Definition
    if data.get("Definition"):
        results.append(f"\n## Definition\n{data['Definition']}")
        if data.get("DefinitionURL"):
            results.append(f"Source: {data['DefinitionURL']}")

    # Direct answer
    if data.get("Answer"):
        results.append(f"\n## Quick Answer\n{data['Answer']}")

    # Related topics
    topics = data.get("RelatedTopics", [])
    if topics:
        results.append("\n## Related Topics")
        for i, topic in enumerate(topics[:5], 1):
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"{i}. {topic['Text']}")
                if topic.get("FirstURL"):
                    results.append(f"   {topic['FirstURL']}")

    if not results:
        return f"No results found for: {query}"

    output = f"Search results for: {query}\n\n" + "\n".join(results)
    logger.info(f"Web search completed: {len(results)} sections found")

    return output


# Register this ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("web-search", web_search_ability)

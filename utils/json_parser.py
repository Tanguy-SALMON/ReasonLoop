"""
Utilities for parsing JSON from text
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Optional[List[Dict[str, Any]]]:
    """Extract JSON array from text"""

    # First, strip markdown code blocks if present
    # Handle ```json ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # Try to find JSON array in the text
    try:
        # First, try to parse the entire text as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Look for content between square brackets (greedy to get full array)
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            json_str = match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.debug("Failed to parse JSON array directly, trying cleanup")

    # Try to find JSON objects and combine them
    try:
        # Look for patterns like {id: 1, ...}
        matches = re.findall(r"{[^{}]*}", text)
        if matches:
            # Join the matches into an array
            combined = "[" + ",".join(matches) + "]"
            # Replace single quotes with double quotes
            combined = combined.replace("'", '"')
            # Replace unquoted keys with quoted keys
            combined = re.sub(
                r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', combined
            )
            return json.loads(combined)
    except json.JSONDecodeError:
        logger.debug("Failed to parse JSON with object extraction")

    # If all else fails, return None
    logger.warning("Could not extract JSON from text")
    return None

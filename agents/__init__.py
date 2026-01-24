"""Agent templates for ReasonLoop"""

import os
from pathlib import Path

# Path to agent templates
AGENTS_DIR = Path(__file__).parent


def get_agent_path(name: str) -> Path:
    """Get the full path to an agent template file"""
    return AGENTS_DIR / f"{name}.md"


def list_agents() -> list:
    """List all available agent templates"""
    return [f.stem for f in AGENTS_DIR.glob("*.md")]


__all__ = ["AGENTS_DIR", "get_agent_path", "list_agents"]

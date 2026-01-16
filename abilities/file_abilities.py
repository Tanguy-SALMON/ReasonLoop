"""
File operation abilities for saving agent definitions
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def write_file_ability(content: str, filename: str = None, directory: str = "templates/created") -> str:
    """
    Write content to a file in the specified directory

    Args:
        content: The content to write to the file
        filename: Optional filename (if None, will generate based on content)
        directory: Directory to save the file (default: templates/created)

    Returns:
        Path to the created file
    """
    logger.info(f"Writing file to {directory}")

    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Generate filename if not provided
    if not filename:
        # Try to extract name from YAML frontmatter
        if "---" in content and "name:" in content:
            frontmatter = content.split("---")[1]
            for line in frontmatter.split("\n"):
                if line.strip().startswith("name:"):
                    name = line.split("name:")[1].strip()
                    filename = f"{name}.md"
                    break

        # Generate generic filename if still not set
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"agent_definition_{timestamp}.md"

    # Ensure .md extension
    if not filename.endswith(".md"):
        filename += ".md"

    # Write file
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        f.write(content)

    logger.info(f"File written: {filepath}")
    return f"File saved to {filepath}"


# Register the ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability
    register_ability("write-file", write_file_ability)

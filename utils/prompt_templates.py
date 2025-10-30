"""
Prompt template management system
"""
import logging
import os
import re
import yaml
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Dictionary of available prompt templates
PROMPT_TEMPLATES = {}
def load_templates_from_directory(directory_path: str = "templates") -> None:
    """Load all template files from the specified directory"""
    logger.info(f"Loading templates from {directory_path}")

    if not os.path.exists(directory_path):
        logger.warning(f"Template directory {directory_path} not found")
        return

    for filename in os.listdir(directory_path):
        if filename.endswith(".md"):
            try:
                file_path = os.path.join(directory_path, filename)
                template_name = os.path.splitext(filename)[0]
                print(template_name)

                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                # Extract YAML frontmatter if present
                frontmatter = {}
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        try:
                            frontmatter = yaml.safe_load(parts[1])
                            content = parts[2].strip()
                        except Exception as e:
                            logger.warning(f"Error parsing frontmatter in {filename}: {e}")

                # Use the 'name' from frontmatter if available
                if frontmatter and 'name' in frontmatter:
                    template_name = frontmatter['name']

                # Add to templates dictionary
                PROMPT_TEMPLATES[template_name] = content
                logger.info(f"Loaded template: {template_name}")

            except Exception as e:
                logger.error(f"Error loading template {filename}: {e}")
    

def get_prompt_template(template_name: str, **kwargs: Any) -> str:
    """Get a prompt template and format it with the provided kwargs"""
    # Ensure templates are loaded
    if not PROMPT_TEMPLATES:
        load_templates_from_directory()

    template = PROMPT_TEMPLATES.get(template_name)
    if not template:
        logger.warning(f"Template '{template_name}' not found, using default")
        template = PROMPT_TEMPLATES.get("default_tasks")
        if not template:
            logger.error("Default template not found!")
            return f"Error: Template '{template_name}' not found and default template is missing"

    # Create a dictionary with all the keys in lowercase
    lowercase_kwargs = {k.lower(): v for k, v in kwargs.items()}
   
    try:
        # Replace placeholders manually to avoid issues with JSON braces
        result = template
        for key, value in lowercase_kwargs.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
            else:
                logger.warning(f"Placeholder '{placeholder}' not found in template")
                 
        # Check if any placeholders remain - with improved regex
        remaining_placeholders = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', result)
        if remaining_placeholders:
            logger.warning(f"Unreplaced placeholders in template: {remaining_placeholders}")

        return result.strip()
    except Exception as e:
        logger.error(f"Error formatting template: {e}")
        return template.strip()  # Return unformatted as fallback

def add_prompt_template(name: str, template: str) -> None:
    """Add a new prompt template"""
    PROMPT_TEMPLATES[name] = template
    logger.info(f"Added new prompt template: {name}")

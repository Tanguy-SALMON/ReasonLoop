"""
Save email templates ability - extracts HTML from task output and saves to emails folder
"""

import logging
import os
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


def extract_html_templates(content: str) -> List[Tuple[str, str]]:
    """
    Extract HTML templates from content.

    Looks for:
    1. HTML code blocks with template comments (TEMPLATE 1: MINIMALIST, etc.)
    2. Multiple ```html blocks
    3. Full HTML documents starting with <!DOCTYPE html>

    Returns:
        List of (template_name, html_content) tuples
    """
    templates = []

    # Pattern 1: Look for labeled templates within a single HTML block
    # e.g., <!-- TEMPLATE 1: MINIMALIST -->
    template_pattern = r"<!--\s*TEMPLATE\s*\d+:\s*(\w+)\s*-->"

    # First, try to extract HTML from code blocks
    html_blocks = re.findall(r"```html\s*([\s\S]*?)\s*```", content, re.IGNORECASE)

    if html_blocks:
        # Check if we have a single block with multiple templates
        if len(html_blocks) == 1:
            single_block = html_blocks[0]

            # Check for template markers
            markers = list(re.finditer(template_pattern, single_block, re.IGNORECASE))

            if markers:
                # Split by template markers
                for i, match in enumerate(markers):
                    template_name = match.group(1).lower()
                    start_pos = match.start()

                    # Find end position (next marker or end of content)
                    if i + 1 < len(markers):
                        end_pos = markers[i + 1].start()
                    else:
                        end_pos = len(single_block)

                    template_html = single_block[start_pos:end_pos].strip()

                    # Wrap in complete HTML if it's just a fragment
                    if not template_html.strip().startswith("<!DOCTYPE"):
                        template_html = _wrap_html_fragment(
                            template_html, template_name
                        )

                    templates.append((template_name, template_html))
            else:
                # Single template without markers
                templates.append(("email_template", single_block.strip()))
        else:
            # Multiple separate HTML blocks
            for i, block in enumerate(html_blocks):
                # Try to detect template name from content or comment
                name_match = re.search(template_pattern, block, re.IGNORECASE)
                if name_match:
                    template_name = name_match.group(1).lower()
                elif "minimalist" in block.lower():
                    template_name = "minimalist"
                elif "bold" in block.lower():
                    template_name = "bold"
                elif "elegant" in block.lower():
                    template_name = "elegant"
                else:
                    template_name = f"template_{i + 1}"

                templates.append((template_name, block.strip()))

    # If no code blocks found, try to find raw HTML
    if not templates:
        # Look for <!DOCTYPE html> sections
        doctype_pattern = r"(<!DOCTYPE html>[\s\S]*?</html>)"
        html_docs = re.findall(doctype_pattern, content, re.IGNORECASE)

        for i, doc in enumerate(html_docs):
            # Try to detect template name
            name_match = re.search(template_pattern, doc, re.IGNORECASE)
            if name_match:
                template_name = name_match.group(1).lower()
            else:
                template_name = f"template_{i + 1}"

            templates.append((template_name, doc.strip()))

    return templates


def _wrap_html_fragment(fragment: str, template_name: str) -> str:
    """Wrap an HTML fragment in a complete document structure"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template_name.title()} Email Template</title>
</head>
<body>
{fragment}
</body>
</html>"""


def save_email_templates_ability(
    content: str,
    domain: str = None,
    output_dir: str = None,
    **kwargs,
) -> str:
    """
    Extract HTML email templates from content and save them to the emails folder.

    Args:
        content: Raw content containing HTML templates (from previous task output)
        domain: Domain name for output folder (e.g., "www.shiseido.com")
        output_dir: Override output directory (default: output/[domain]/emails/)

    Returns:
        JSON string with saved file paths and status
    """
    import json

    logger.info(f"Extracting email templates for domain: {domain}")

    # Determine output directory
    if output_dir:
        emails_dir = output_dir
    elif domain:
        emails_dir = os.path.join("output", domain, "emails")
    else:
        # Try to extract domain from content
        url_match = re.search(r"https?://([^/\s]+)", content)
        if url_match:
            domain = url_match.group(1)
            emails_dir = os.path.join("output", domain, "emails")
        else:
            emails_dir = os.path.join("output", "unknown", "emails")

    # Create directory
    os.makedirs(emails_dir, exist_ok=True)
    logger.info(f"Output directory: {emails_dir}")

    # Extract templates
    templates = extract_html_templates(content)

    if not templates:
        logger.warning("No HTML templates found in content")
        return json.dumps(
            {
                "success": False,
                "error": "No HTML templates found in content",
                "saved_files": [],
                "output_dir": emails_dir,
            }
        )

    # Save templates
    saved_files = []
    for template_name, html_content in templates:
        filename = f"{template_name}.html"
        filepath = os.path.join(emails_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        saved_files.append(filepath)
        logger.info(f"Saved template: {filepath}")

    # Update summary if OutputManager is available
    try:
        from utils.output_manager import OutputManager

        if domain:
            output_manager = OutputManager(domain)
            output_manager.update_email_count(len(saved_files))
    except Exception as e:
        logger.debug(f"Could not update summary: {e}")

    result = {
        "success": True,
        "templates_found": len(templates),
        "saved_files": saved_files,
        "output_dir": emails_dir,
        "template_names": [t[0] for t in templates],
    }

    logger.info(f"Successfully saved {len(saved_files)} email templates")

    # Return formatted message
    files_list = "\n".join([f"  - {f}" for f in saved_files])
    return f"""Successfully saved {len(saved_files)} email templates to {emails_dir}:
{files_list}

{json.dumps(result, indent=2)}"""


# Register the ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability

    register_ability("save-email-templates", save_email_templates_ability)

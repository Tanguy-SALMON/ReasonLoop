"""
Visual Design Analyzer - Screenshots website and uses Vision AI to analyze design

Takes a screenshot of the website and sends it to a vision-capable LLM
to extract design metrics that CSS parsing would miss.
"""

import base64
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Result of taking a website screenshot"""

    success: bool
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    error: Optional[str] = None
    url: str = ""
    viewport: Dict[str, int] = None


def take_screenshot(
    url: str, full_page: bool = False, output_dir: str = None
) -> ScreenshotResult:
    """
    Take a screenshot of a website using Playwright.

    Args:
        url: Website URL to screenshot
        full_page: If True, capture full scrollable page
        output_dir: Directory to save screenshot (default: output/{domain}/)

    Returns:
        ScreenshotResult with image data
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ScreenshotResult(
            success=False,
            error="Playwright not installed. Run: pip install playwright && playwright install chromium",
            url=url,
        )

    from urllib.parse import urlparse

    # Extract domain for folder organization
    domain = urlparse(url).netloc  # e.g., "th.cos.com"

    # Create output directory organized by domain - output/{domain}/
    if output_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, "output", domain)

    os.makedirs(output_dir, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    screenshot_path = os.path.join(output_dir, filename)

    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)

            # Create page with desktop viewport
            page = browser.new_page(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=2,  # Retina quality
            )

            # Navigate to URL
            logger.info(f"Taking screenshot of {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for fonts and images to load
            page.wait_for_timeout(2000)

            # Take screenshot
            page.screenshot(path=screenshot_path, full_page=full_page, type="png")

            browser.close()

        # Read and encode as base64
        with open(screenshot_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        logger.info(f"Screenshot captured: {screenshot_path}")

        return ScreenshotResult(
            success=True,
            image_path=screenshot_path,
            image_base64=image_base64,
            url=url,
            viewport={"width": 1440, "height": 900},
        )

    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return ScreenshotResult(success=False, error=str(e), url=url)


def analyze_design_with_vision(image_base64: str, url: str) -> Dict[str, Any]:
    """
    Send screenshot to Vision AI (XAI Grok Vision) for design analysis.

    Args:
        image_base64: Base64 encoded PNG image
        url: Original URL for context

    Returns:
        Extracted design metrics
    """
    from config.settings import get_setting

    api_key = get_setting("XAI_API_KEY")
    if not api_key:
        return {"error": "XAI_API_KEY not configured"}

    # Vision analysis prompt
    prompt = """Analyze this website screenshot and extract precise design metrics for email template creation.

Return a JSON object with these exact fields:

{
    "typography": {
        "primary_font": "Font name (e.g., 'Helvetica Neue', 'Inter', 'Playfair Display')",
        "secondary_font": "Secondary font if visible",
        "heading_style": {
            "approximate_size": "e.g., 32px, 48px",
            "weight": "e.g., bold, 700, light",
            "case": "e.g., uppercase, normal, capitalize"
        },
        "body_style": {
            "approximate_size": "e.g., 14px, 16px",
            "line_height": "e.g., 1.5, 1.6",
            "weight": "e.g., normal, 400"
        }
    },
    "colors": {
        "primary": "#hexcode (main brand color)",
        "secondary": "#hexcode",
        "accent": "#hexcode (CTA/highlight color)",
        "background": "#hexcode",
        "text": "#hexcode",
        "text_muted": "#hexcode (secondary text)"
    },
    "spacing": {
        "overall_density": "tight/normal/spacious",
        "section_padding": "e.g., 40px, 60px, 80px",
        "element_gap": "e.g., 16px, 24px, 32px"
    },
    "borders": {
        "border_radius": "e.g., 0px (sharp), 4px (subtle), 8px (rounded), 16px+ (pill)",
        "border_style": "none/thin/prominent",
        "border_color": "#hexcode if visible"
    },
    "buttons": {
        "style": "filled/outlined/text",
        "border_radius": "e.g., 0px, 4px, 20px, pill",
        "padding": "e.g., 12px 24px",
        "text_style": "uppercase/normal/capitalize",
        "font_weight": "e.g., bold, 600"
    },
    "layout": {
        "style": "minimal/content-rich/image-heavy",
        "max_content_width": "e.g., 1200px, 1400px",
        "grid_columns": "e.g., 2, 3, 4",
        "header_style": "sticky/static/transparent"
    },
    "visual_style": {
        "overall_aesthetic": "e.g., minimalist, luxury, playful, corporate, editorial",
        "imagery_style": "e.g., lifestyle, product-focused, editorial, none",
        "whitespace_usage": "generous/moderate/minimal"
    },
    "brand_impression": {
        "perceived_tier": "budget/mid-range/premium/luxury",
        "mood": "e.g., sophisticated, energetic, calm, bold",
        "target_audience_guess": "e.g., young professionals, luxury shoppers, families"
    }
}

Be precise with color hex codes - estimate if needed.
Return ONLY the JSON, no explanation."""

    try:
        # Call XAI Vision API
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-2-vision-1212",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
        )

        response.raise_for_status()
        result = response.json()

        # Extract content
        content = result["choices"][0]["message"]["content"]

        # Parse JSON from response
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            design_metrics = json.loads(content[json_start:json_end])
            return design_metrics
        else:
            return {
                "error": "Could not parse JSON from vision response",
                "raw": content,
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Vision API request failed: {e}")
        return {"error": f"Vision API request failed: {e}"}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse vision response: {e}")
        return {"error": f"Failed to parse response: {e}", "raw": content}
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return {"error": str(e)}


def visual_design_analyzer_ability(url: str) -> str:
    """
    Screenshot a website and analyze its design using Vision AI.
    Saves both screenshot and analysis JSON to output/{domain}/.

    Args:
        url: Website URL to analyze

    Returns:
        JSON string with design metrics
    """
    from urllib.parse import urlparse

    logger.info(f"Starting visual design analysis for: {url}")

    # Clean URL
    if not url.startswith("http"):
        url = f"https://{url}"

    # Extract domain for output directory
    domain = urlparse(url).netloc
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output", domain)
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    result = {
        "url": url,
        "analysis_date": datetime.now().isoformat(),
        "screenshot": None,
        "design_metrics": None,
        "error": None,
    }

    # Step 1: Take screenshot
    screenshot = take_screenshot(url, output_dir=output_dir)

    if not screenshot.success:
        result["error"] = f"Screenshot failed: {screenshot.error}"
        return json.dumps(result, indent=2)

    result["screenshot"] = {
        "captured": True,
        "viewport": screenshot.viewport,
        "path": screenshot.image_path,
    }

    # Step 2: Analyze with Vision AI
    logger.info("Analyzing screenshot with Vision AI...")
    design_metrics = analyze_design_with_vision(screenshot.image_base64, url)

    if "error" in design_metrics:
        result["error"] = design_metrics["error"]
        result["design_metrics"] = None
    else:
        result["design_metrics"] = design_metrics

    # Step 3: Save analysis JSON to output/{domain}/
    analysis_filename = f"analysis_{timestamp}.json"
    analysis_path = os.path.join(output_dir, analysis_filename)
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    result["analysis_file"] = analysis_path
    logger.info(f"Analysis saved to: {analysis_path}")

    logger.info(f"Visual design analysis completed for: {url}")
    return json.dumps(result, indent=2)


# Register ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability

    register_ability("visual-design-analyzer", visual_design_analyzer_ability)


# CLI test
if __name__ == "__main__":
    import os
    import sys

    # Add project root to path for standalone execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    url = sys.argv[1] if len(sys.argv) > 1 else "https://th.cos.com"
    print(f"\nAnalyzing: {url}\n")

    result = visual_design_analyzer_ability(url)
    print(result)

# abilities/image_generation.py
"""
Image generation ability using XAI's grok-2-image-1212 model.
Generates images for email campaigns (hero banners, event visuals, etc.)
"""

import base64
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests

from config.settings import get_setting

logger = logging.getLogger(__name__)


class ImageGenerationProvider:
    """XAI Image Generation provider using grok-2-image-1212"""

    def __init__(self):
        self.provider_name = "xai-image"
        self.logger = logging.getLogger(f"{__name__}.{self.provider_name}")
        self.api_key = get_setting("XAI_API_KEY")
        self.api_url = get_setting(
            "XAI_IMAGE_API_URL", "https://api.x.ai/v1/images/generations"
        )
        self.model = get_setting("XAI_MODEL_VISUAL_DESIGNER", "grok-2-image-1212")

    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        response_format: str = "b64_json",
    ) -> Tuple[list, Dict]:
        """
        Generate images from a text prompt.

        Args:
            prompt: Text description of the image to generate
            size: Image size (e.g., "1024x1024", "1792x1024", "1024x1792")
            n: Number of images to generate (1-4)
            response_format: "b64_json" for base64 or "url" for URLs

        Returns:
            Tuple of (list of image data, api_response dict)
        """
        if not self.api_key:
            raise ValueError("XAI_API_KEY not configured")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": self.model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": response_format,
        }

        self.logger.info(f"Generating image with prompt: {prompt[:100]}...")

        response = requests.post(self.api_url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()

        self.logger.debug(f"Image API Response: {json.dumps(result, indent=2)[:500]}")

        images = result.get("data", [])
        return images, result

    def save_image(
        self, image_data: Dict, output_dir: str, filename: str = None
    ) -> str:
        """
        Save generated image to disk.

        Args:
            image_data: Image data from API (with b64_json or url)
            output_dir: Directory to save image
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to saved image file
        """
        os.makedirs(output_dir, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}.png"

        filepath = os.path.join(output_dir, filename)

        if "b64_json" in image_data:
            # Decode base64 and save
            image_bytes = base64.b64decode(image_data["b64_json"])
            with open(filepath, "wb") as f:
                f.write(image_bytes)
        elif "url" in image_data:
            # Download from URL
            response = requests.get(image_data["url"], timeout=60)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
        else:
            raise ValueError("Image data must contain 'b64_json' or 'url'")

        self.logger.info(f"Saved image to: {filepath}")
        return filepath


def _extract_prompt_from_input(raw_input: str) -> str:
    """
    Extract a valid image generation prompt from raw input.
    Handles JSON design specs, raw prompts, or structured data.

    Args:
        raw_input: Raw input that may be JSON, markdown, or plain text

    Returns:
        Clean text prompt suitable for image generation API
    """
    # Strip markdown code blocks if present
    cleaned = raw_input.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Try to parse as JSON
    try:
        data = json.loads(cleaned)

        # Look for explicit image prompt field
        prompt_fields = [
            "image_prompt",
            "hero_image_prompt",
            "prompt",
            "description",
            "image_description",
        ]
        for field in prompt_fields:
            if field in data and isinstance(data[field], str):
                return data[field]

        # Check hero_image structure (from visual_designer role)
        if "hero_image" in data:
            hero = data["hero_image"]
            if isinstance(hero, dict):
                for field in prompt_fields:
                    if field in hero and isinstance(hero[field], str):
                        return hero[field]
            elif isinstance(hero, str):
                return hero

        # Check nested structures
        if "visual_elements" in data:
            visual = data["visual_elements"]
            if isinstance(visual, dict):
                for field in prompt_fields:
                    if field in visual and isinstance(visual[field], str):
                        return visual[field]
                # Build prompt from visual elements
                parts = []
                if "hero_image" in visual:
                    hero = visual["hero_image"]
                    if isinstance(hero, dict):
                        for field in prompt_fields + ["concept", "theme", "style"]:
                            if field in hero:
                                parts.append(str(hero[field]))
                    elif isinstance(hero, str):
                        parts.append(hero)
                if parts:
                    return ". ".join(parts)

        # Check email_design_specs structure
        if "email_design_specs" in data:
            specs = data["email_design_specs"]
            if isinstance(specs, dict):
                # First check for image_prompt in specs
                for field in prompt_fields:
                    if field in specs and isinstance(specs[field], str):
                        return specs[field]
                if "visual_elements" in specs:
                    return _extract_prompt_from_input(json.dumps(specs))

        # Check email_template structure
        if "email_template" in data:
            template = data["email_template"]
            if isinstance(template, dict):
                for field in prompt_fields:
                    if field in template and isinstance(template[field], str):
                        return template[field]
                # Also check nested structures inside email_template
                for key in ["hero", "hero_section", "hero_image", "visual_elements"]:
                    if key in template and isinstance(template[key], dict):
                        for field in prompt_fields:
                            if field in template[key] and isinstance(
                                template[key][field], str
                            ):
                                return template[key][field]

        # Recursive search for image_prompt in any nested structure
        def find_image_prompt(obj, depth=0):
            if depth > 5:  # Prevent infinite recursion
                return None
            if isinstance(obj, dict):
                for field in prompt_fields:
                    if (
                        field in obj
                        and isinstance(obj[field], str)
                        and len(obj[field]) > 20
                    ):
                        return obj[field]
                for value in obj.values():
                    result = find_image_prompt(value, depth + 1)
                    if result:
                        return result
            return None

        recursive_prompt = find_image_prompt(data)
        if recursive_prompt:
            return recursive_prompt

        # Build prompt from available design data as fallback
        prompt_parts = ["Professional email hero banner"]

        # Extract theme/campaign info from nested structures too
        theme = None
        for key in ["theme", "campaign", "name"]:
            if key in data and isinstance(data[key], str):
                theme = data[key]
                break
            # Check inside email_template
            if "email_template" in data and isinstance(data["email_template"], dict):
                if key in data["email_template"] and isinstance(
                    data["email_template"][key], str
                ):
                    theme = data["email_template"][key]
                    break

        if theme:
            prompt_parts.append(f"for {theme}")

        # Extract persona/style from various locations
        persona = data.get("persona", "")
        if (
            not persona
            and "email_template" in data
            and isinstance(data["email_template"], dict)
        ):
            persona = data["email_template"].get("persona", "")
        # Also try to extract from name field
        if not persona:
            name = theme or ""
            name_lower = name.lower()
            if "minimalist" in name_lower:
                persona = "minimalist"
            elif "bold" in name_lower:
                persona = "bold"
            elif "elegant" in name_lower:
                persona = "elegant"

        if persona and isinstance(persona, str):
            style_map = {
                "minimalist": "clean minimalist style with lots of negative space, subtle tones",
                "bold": "vibrant energetic style with dynamic composition, bright saturated colors",
                "elegant": "sophisticated luxurious style with refined aesthetics, premium feel",
            }
            style_desc = style_map.get(persona.lower(), f"{persona} style")
            prompt_parts.append(style_desc)

        # Extract colors (properly formatted) from various locations
        colors = data.get("colors") or data.get("color_palette", {})
        if (
            not colors
            and "email_template" in data
            and isinstance(data["email_template"], dict)
        ):
            colors = data["email_template"].get("colors") or data["email_template"].get(
                "color_palette", {}
            )
        if isinstance(colors, dict):
            color_values = [
                v for v in colors.values() if isinstance(v, str) and v.startswith("#")
            ][:3]
            if color_values:
                prompt_parts.append(
                    f"color palette featuring {', '.join(color_values)}"
                )

        # Add standard image generation guidance
        prompt_parts.extend(
            [
                "high quality commercial photography",
                "clean composition with space for text overlay",
                "no text or typography in the image",
            ]
        )

        # If we have enough context, return the built prompt
        if len(prompt_parts) > 3:
            return ". ".join(prompt_parts)

        # Check for color_palette and build a generic prompt
        if "color_palette" in data:
            colors = data.get("color_palette", {})
            primary = colors.get("primary", "")
            secondary = colors.get("secondary", "")
            mood = data.get("mood", "professional")
            return f"Professional email hero banner. Color palette: {primary}, {secondary}. Mood: {mood}. Clean composition with space for text overlay. No text in image."

        # If JSON but no recognized structure, indicate error
        logger.warning(
            f"JSON input detected but no image prompt field found. Keys: {list(data.keys())}"
        )
        return None

    except json.JSONDecodeError:
        # Not JSON, treat as direct prompt
        # But check if it's too long or looks like code/specs
        if len(cleaned) > 1000:
            logger.warning("Input too long for image prompt, truncating")
            cleaned = cleaned[:500]
        return cleaned


def image_generation_ability(
    prompt: str,
    domain: str = None,
    size: str = "1024x512",  # Email hero banner aspect ratio
    save_to_disk: bool = True,
    **kwargs,
) -> str:
    """
    Generate images for email campaigns.

    Args:
        prompt: Description of the image to generate (from visual_designer).
                Can be plain text or JSON with image_prompt field.
        domain: Domain name for organizing output
        size: Image dimensions (default 1024x512 for email banners)
        save_to_disk: Whether to save images to output folder

    Returns:
        JSON string with image paths or base64 data
    """
    # Extract clean prompt from input (handles JSON design specs)
    clean_prompt = _extract_prompt_from_input(prompt)

    if not clean_prompt:
        error_msg = (
            "Could not extract image prompt from input. "
            "Expected either plain text prompt or JSON with 'image_prompt' field."
        )
        logger.error(error_msg)
        return json.dumps(
            {
                "error": error_msg,
                "hint": "Add 'image_prompt' field to your JSON with a text description of the desired image",
                "raw_input_preview": prompt[:200] + "..."
                if len(prompt) > 200
                else prompt,
            }
        )

    logger.info(f"Image generation requested: {clean_prompt[:100]}...")

    try:
        provider = ImageGenerationProvider()
        images, api_response = provider.generate(clean_prompt, size=size, n=1)

        if not images:
            return json.dumps({"error": "No images generated", "prompt": clean_prompt})

        result = {
            "prompt": clean_prompt,
            "model": provider.model,
            "size": size,
            "images": [],
        }

        # Save images if domain provided
        if save_to_disk and domain:
            output_dir = os.path.join("output", domain, "images")
            os.makedirs(output_dir, exist_ok=True)

            for i, img_data in enumerate(images):
                filename = f"hero_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.png"
                filepath = provider.save_image(img_data, output_dir, filename)
                result["images"].append(
                    {
                        "filename": filename,
                        "path": filepath,
                        "saved": True,
                    }
                )
        else:
            # Return base64 data
            for i, img_data in enumerate(images):
                if "b64_json" in img_data:
                    result["images"].append(
                        {
                            "index": i,
                            "b64_json": img_data["b64_json"][:100]
                            + "...",  # Truncate for logging
                            "saved": False,
                        }
                    )
                elif "url" in img_data:
                    result["images"].append(
                        {
                            "index": i,
                            "url": img_data["url"],
                            "saved": False,
                        }
                    )

        logger.info(f"Generated {len(images)} image(s)")
        return json.dumps(result, indent=2)

    except requests.exceptions.HTTPError as e:
        error_msg = f"Image generation API error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "prompt": clean_prompt})
    except Exception as e:
        error_msg = f"Image generation failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "prompt": clean_prompt})


def build_image_prompt(
    event: str,
    brand_colors: list = None,
    style: str = "modern",
    mood: str = "festive",
    product_focus: str = None,
) -> str:
    """
    Build an optimized image generation prompt for email banners.

    Args:
        event: Event name (e.g., "Christmas", "Black Friday", "Summer Sale")
        brand_colors: List of brand hex colors to incorporate
        style: Visual style (modern, minimalist, bold, elegant)
        mood: Emotional mood (festive, luxurious, energetic, calm)
        product_focus: Optional product to feature

    Returns:
        Optimized prompt string for image generation
    """
    prompt_parts = [
        f"Professional email marketing hero banner for {event}",
        f"Style: {style}, Mood: {mood}",
        "High quality, commercial photography style",
        "Clean composition with space for text overlay",
        "16:9 aspect ratio, centered focal point",
    ]

    if brand_colors:
        colors_str = ", ".join(brand_colors[:3])  # Limit to 3 colors
        prompt_parts.append(f"Color palette featuring: {colors_str}")

    if product_focus:
        prompt_parts.append(f"Featuring: {product_focus}")

    prompt_parts.append("No text or typography in the image")

    return ". ".join(prompt_parts)


# Register ability when module is loaded directly
if __name__ == "__main__":
    from abilities.ability_registry import register_ability

    register_ability("image-generation", image_generation_ability)

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
        prompt: Description of the image to generate (from visual_designer)
        domain: Domain name for organizing output
        size: Image dimensions (default 1024x512 for email banners)
        save_to_disk: Whether to save images to output folder

    Returns:
        JSON string with image paths or base64 data
    """
    logger.info(f"Image generation requested: {prompt[:100]}...")

    try:
        provider = ImageGenerationProvider()
        images, api_response = provider.generate(prompt, size=size, n=1)

        if not images:
            return json.dumps({"error": "No images generated", "prompt": prompt})

        result = {
            "prompt": prompt,
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
        return json.dumps({"error": error_msg, "prompt": prompt})
    except Exception as e:
        error_msg = f"Image generation failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "prompt": prompt})


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

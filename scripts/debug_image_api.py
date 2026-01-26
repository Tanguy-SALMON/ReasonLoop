#!/usr/bin/env python3
"""
Debug script for XAI Image Generation API

This script helps diagnose issues with the XAI image generation API:
- Tests API key validity
- Tests model availability
- Shows detailed error responses
- Lists available models

Usage:
    poetry run python scripts/debug_image_api.py
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_api_key():
    """Get XAI API key from environment"""
    key = os.getenv("XAI_API_KEY")
    if not key:
        print("❌ ERROR: XAI_API_KEY not found in environment")
        print("   Set it in your .env file or export it:")
        print("   export XAI_API_KEY='your-key-here'")
        return None
    return key


def test_api_key_validity(api_key: str) -> bool:
    """Test if the API key is valid by making a simple request"""
    print("\n" + "=" * 60)
    print("TEST 1: API Key Validity")
    print("=" * 60)

    # Try listing models to verify API key
    url = "https://api.x.ai/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ API Key is valid!")
            data = response.json()
            models = data.get("data", [])
            print(f"\nAvailable models ({len(models)}):")
            for model in models:
                model_id = model.get("id", "unknown")
                owned_by = model.get("owned_by", "")
                print(f"  - {model_id} (owned by: {owned_by})")
            return True
        elif response.status_code == 401:
            print("❌ API Key is INVALID (401 Unauthorized)")
            print(f"   Response: {response.text}")
            return False
        elif response.status_code == 403:
            print("❌ API Key lacks permissions (403 Forbidden)")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def test_image_generation(api_key: str, model: str = None) -> dict:
    """Test image generation with detailed error reporting"""
    print("\n" + "=" * 60)
    print("TEST 2: Image Generation")
    print("=" * 60)

    model = model or os.getenv("XAI_MODEL_VISUAL_DESIGNER", "grok-2-image-1212")
    url = "https://api.x.ai/v1/images/generations"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Simple test prompt
    payload = {
        "model": model,
        "prompt": "A simple red apple on a white background",
        "n": 1,
        "size": "1024x1024",
        "response_format": "url",  # Use URL to avoid large base64 response
    }

    print(f"Model: {model}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in [
                "content-type",
                "x-request-id",
                "x-ratelimit-remaining",
                "x-ratelimit-limit",
            ]:
                print(f"  {key}: {value}")

        if response.status_code == 200:
            print("\n✅ Image generation SUCCESSFUL!")
            data = response.json()
            images = data.get("data", [])
            for i, img in enumerate(images):
                if "url" in img:
                    print(f"  Image {i + 1} URL: {img['url'][:100]}...")
                elif "b64_json" in img:
                    print(
                        f"  Image {i + 1}: Base64 data ({len(img['b64_json'])} chars)"
                    )
            return {"success": True, "data": data}

        else:
            print(f"\n❌ Image generation FAILED!")

            # Parse error response
            try:
                error_data = response.json()
                print(f"\nError Response:")
                print(json.dumps(error_data, indent=2))

                # Common error interpretations
                error_msg = error_data.get("error", {})
                if isinstance(error_msg, dict):
                    error_type = error_msg.get("type", "")
                    error_message = error_msg.get("message", "")
                    error_code = error_msg.get("code", "")

                    print(f"\nError Analysis:")
                    print(f"  Type: {error_type}")
                    print(f"  Code: {error_code}")
                    print(f"  Message: {error_message}")

                    # Provide specific guidance
                    if (
                        "model" in error_message.lower()
                        or error_code == "model_not_found"
                    ):
                        print("\n💡 DIAGNOSIS: Model not available")
                        print(
                            "   The model 'grok-2-image-1212' may not be available on your account."
                        )
                        print(
                            "   Try checking available models with the /v1/models endpoint."
                        )

                    elif (
                        "subscription" in error_message.lower()
                        or "billing" in error_message.lower()
                    ):
                        print("\n💡 DIAGNOSIS: Subscription/Billing issue")
                        print(
                            "   Your XAI account may not have access to image generation."
                        )
                        print("   Check your subscription at https://x.ai/")

                    elif (
                        "rate" in error_message.lower()
                        or "limit" in error_message.lower()
                    ):
                        print("\n💡 DIAGNOSIS: Rate limit exceeded")
                        print("   Wait a few minutes and try again.")

                    elif "invalid" in error_message.lower():
                        print("\n💡 DIAGNOSIS: Invalid request")
                        print("   Check the payload format and parameters.")

            except json.JSONDecodeError:
                print(f"Raw Response: {response.text}")

            return {
                "success": False,
                "status_code": response.status_code,
                "response": response.text,
            }

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 120 seconds")
        return {"success": False, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {"success": False, "error": str(e)}


def test_different_models(api_key: str):
    """Test with different model names"""
    print("\n" + "=" * 60)
    print("TEST 3: Testing Different Model Names")
    print("=" * 60)

    # Possible model names to try
    model_variants = [
        "grok-2-image-1212",
        "grok-2-image",
        "grok-2-vision-1212",
        "grok-image",
        "aurora",  # Another XAI image model
    ]

    url = "https://api.x.ai/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for model in model_variants:
        print(f"\nTrying model: {model}")
        payload = {
            "model": model,
            "prompt": "A red circle",
            "n": 1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                print(f"  ✅ {model} - WORKS!")
                return model
            else:
                error = response.json().get("error", {})
                msg = (
                    error.get("message", response.text[:100])
                    if isinstance(error, dict)
                    else str(error)[:100]
                )
                print(f"  ❌ {model} - {response.status_code}: {msg}")
        except Exception as e:
            print(f"  ❌ {model} - Error: {e}")

    return None


def check_account_info(api_key: str):
    """Check account/subscription info if available"""
    print("\n" + "=" * 60)
    print("TEST 4: Account Information")
    print("=" * 60)

    # Try to get account info (endpoint may not exist)
    endpoints_to_try = [
        "https://api.x.ai/v1/account",
        "https://api.x.ai/v1/usage",
        "https://api.x.ai/v1/subscription",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for endpoint in endpoints_to_try:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"\n{endpoint}:")
                print(json.dumps(response.json(), indent=2))
            elif response.status_code != 404:
                print(f"{endpoint}: {response.status_code}")
        except Exception:
            pass

    print("\n💡 Note: Account info endpoints may not be publicly available.")
    print("   Check your account at: https://console.x.ai/ or https://x.ai/api")


def main():
    print("=" * 60)
    print("XAI Image Generation API Debug Tool")
    print("=" * 60)

    # Get API key
    api_key = get_api_key()
    if not api_key:
        sys.exit(1)

    print(f"\nAPI Key: {api_key[:8]}...{api_key[-4:]}")

    # Run tests
    key_valid = test_api_key_validity(api_key)

    if not key_valid:
        print("\n⚠️  Cannot proceed without valid API key")
        sys.exit(1)

    # Test image generation
    result = test_image_generation(api_key)

    if not result.get("success"):
        # Try different models
        working_model = test_different_models(api_key)
        if working_model:
            print(f"\n✅ Found working model: {working_model}")
            print(f"   Update your .env file:")
            print(f"   XAI_MODEL_VISUAL_DESIGNER={working_model}")

    # Check account info
    check_account_info(api_key)

    print("\n" + "=" * 60)
    print("Debug Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for Email Design Multi-Agent System

Usage:
    # Test with mock data
    python test_email_design.py

    # Test with real website intelligence
    python test_email_design.py --url https://th.cos.com

    # Test via ReasonLoop
    python main.py --template email_design_agent --objective "Create 3 email designs for https://th.cos.com"
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_mock_brand_intelligence() -> dict:
    """Return mock brand intelligence for testing without API calls"""
    return {
        "website_url": "https://th.cos.com",
        "analysis_date": datetime.now().isoformat(),
        "brand_identity": {
            "name": "COS",
            "tagline": "Modern, functional, timeless design",
            "logo_url": "https://th.cos.com/logo.svg",
            "colors": ["#000000", "#FFFFFF", "#E5E5E5", "#C4A77D"],
            "fonts": ["Helvetica Neue", "Georgia"],
            "mission_statement": "COS offers reinvented classics and wardrobe essentials for women, men and children.",
        },
        "brand_voice": {
            "tone": ["minimalist", "sophisticated", "modern"],
            "characteristics": "Clean, understated, architectural",
            "cta_patterns": ["Shop Now", "Discover", "Explore"],
            "emoji_usage": False,
        },
        "products": {
            "categories": ["Women", "Men", "Kids", "Accessories", "New Arrivals"],
            "featured_items": [
                {"name": "Oversized Wool Coat", "price": 290.00},
                {"name": "Relaxed Cashmere Sweater", "price": 175.00},
                {"name": "Wide-Leg Trousers", "price": 125.00},
            ],
            "price_range": {"min": 45, "max": 450},
            "pricing_tier": "premium",
        },
        "value_propositions": {
            "primary_usp": "Timeless design meets modern functionality",
            "secondary_usps": [
                "Free shipping over $100",
                "Sustainable materials",
                "Quality craftsmanship",
            ],
            "guarantees": ["30-day returns", "Quality guarantee"],
        },
        "promotions": {
            "current_offers": ["20% off new arrivals", "Free shipping this weekend"],
            "discount_types": ["percentage_discount", "free_shipping"],
            "first_timer_incentive": "10% off your first order",
        },
        "audience": {
            "target_demographic": "Design-conscious professionals aged 25-45 who value quality over quantity",
            "pain_points": ["Finding timeless pieces", "Sustainable fashion choices"],
            "testimonials": [
                "Impeccable quality and design",
                "My go-to for wardrobe essentials",
            ],
        },
        "technical": {"platform": "Custom", "currency": "THB", "has_blog": True},
        "trust_signals": {
            "payment_methods": ["VISA", "MASTERCARD", "PAYPAL"],
            "social_media": {
                "instagram": "https://instagram.com/cosstores",
                "facebook": "https://facebook.com/cos",
            },
        },
    }


def test_design_agent_direct():
    """Test the design agent directly without ReasonLoop"""
    print("\n" + "=" * 80)
    print("TESTING EMAIL DESIGN MULTI-AGENT SYSTEM")
    print("=" * 80)

    from abilities.email_design_agent import (
        DesignOrchestrator,
        DesignPersona,
        create_email_designs,
        save_designs_to_html,
    )

    # Get brand intelligence
    brand_data = get_mock_brand_intelligence()

    print(f"\n📊 Brand: {brand_data['brand_identity']['name']}")
    print(f"🎨 Colors: {', '.join(brand_data['brand_identity']['colors'][:3])}")
    print(f"💰 Pricing: {brand_data['products']['pricing_tier']}")
    print(f"🎯 Target: {brand_data['audience']['target_demographic'][:50]}...")

    # Create orchestrator with 3 agents
    print("\n🤖 Initializing 3 Design Agents...")
    orchestrator = DesignOrchestrator(num_designs=3)

    print(f"   Personas: {[p.value for p in orchestrator.personas]}")

    # Generate designs
    campaign_goal = "Promote the new spring collection and drive early-bird sales with emphasis on sustainable materials"

    print(f"\n📧 Campaign Goal: {campaign_goal[:60]}...")
    print("\n⏳ Generating designs (this may take 30-60 seconds)...")

    designs = orchestrator.generate_designs(
        brand_intelligence=brand_data,
        campaign_goal=campaign_goal,
        parallel=True,  # Run agents concurrently
    )

    # Display results
    print(f"\n✅ Generated {len(designs)} email designs!\n")
    print("=" * 80)

    for i, design in enumerate(designs, 1):
        print(f"\n{'─' * 80}")
        print(f"DESIGN {i}: {design.persona.upper()}")
        print(f"{'─' * 80}")
        print(f"📧 Subject: {design.subject_line}")
        print(f"👀 Preview: {design.preview_text}")
        print(f"🎯 Headline: {design.headline}")
        print(f"🔘 CTA: {design.cta_text}")
        print(f"\n🎨 Color Scheme:")
        for key, value in design.color_scheme.items():
            print(f"   • {key}: {value}")
        print(f"\n📝 Layout: {design.layout}")
        print(f"\n💡 Rationale: {design.design_rationale}")
        print(f"👥 Target Audience: {design.target_audience}")
        print(f"📈 Expected Engagement: {design.estimated_engagement}")

    # Save HTML files
    print("\n" + "=" * 80)
    print("SAVING HTML FILES")
    print("=" * 80)

    output_dir = "output/email_designs"
    paths = save_designs_to_html(designs, output_dir)

    print(f"\n✅ Saved {len(paths)} HTML files to {output_dir}/")
    for path in paths:
        print(f"   📄 {path}")

    # Save full JSON report
    report_path = os.path.join(output_dir, "designs_report.json")
    with open(report_path, "w") as f:
        json.dump(
            {
                "brand": brand_data["brand_identity"]["name"],
                "campaign_goal": campaign_goal,
                "generated_at": datetime.now().isoformat(),
                "designs": [d.to_dict() for d in designs],
            },
            f,
            indent=2,
        )

    print(f"   📊 {report_path}")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)

    return designs


def test_with_real_website(url: str):
    """Test with real website intelligence extraction"""
    print("\n" + "=" * 80)
    print(f"TESTING WITH REAL WEBSITE: {url}")
    print("=" * 80)

    from abilities.email_design_agent import email_design_ability
    from abilities.website_intelligence import website_intelligence_ability

    # Step 1: Extract website intelligence
    print("\n⏳ Step 1: Extracting website intelligence...")
    intelligence_json = website_intelligence_ability(url)
    intelligence = json.loads(intelligence_json)

    if "error" in intelligence:
        print(f"❌ Failed to extract intelligence: {intelligence['error']}")
        return None

    print(
        f"✅ Extracted intelligence for: {intelligence.get('brand_identity', {}).get('name', 'Unknown')}"
    )

    # Step 2: Generate email designs
    print("\n⏳ Step 2: Generating email designs...")
    campaign_goal = "Drive traffic to the new collection and increase email engagement"

    designs_json = email_design_ability(
        brand_intelligence_json=json.dumps(intelligence),
        campaign_goal=campaign_goal,
        num_designs=3,
        parallel=True,
    )

    result = json.loads(designs_json)

    if not result.get("success"):
        print(f"❌ Design generation failed: {result.get('error')}")
        return None

    print(f"✅ Generated {result['num_designs']} designs!")

    # Display summary
    for i, design in enumerate(result["designs"], 1):
        print(f"\n  Design {i} ({design['persona']}):")
        print(f"    Subject: {design['subject_line']}")
        print(f"    CTA: {design['cta_text']}")

    # Save output
    output_dir = "output/email_designs"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(
        output_dir, f"designs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n📄 Full results saved to: {output_path}")

    return result


def test_ability_wrapper():
    """Test the ReasonLoop ability wrapper"""
    print("\n" + "=" * 80)
    print("TESTING ABILITY WRAPPER")
    print("=" * 80)

    from abilities.email_design_agent import email_design_ability

    brand_data = get_mock_brand_intelligence()

    print("\n⏳ Calling email_design_ability()...")

    result_json = email_design_ability(
        brand_intelligence_json=json.dumps(brand_data),
        campaign_goal="Launch summer collection with emphasis on sustainable materials",
        num_designs=3,
        parallel=True,
    )

    result = json.loads(result_json)

    if result["success"]:
        print(f"✅ Success! Generated {result['num_designs']} designs")
        for d in result["designs"]:
            print(f"   • {d['persona']}: {d['subject_line'][:40]}...")
    else:
        print(f"❌ Failed: {result.get('error')}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Email Design Multi-Agent System")
    parser.add_argument("--url", help="Test with real website URL")
    parser.add_argument(
        "--wrapper-only", action="store_true", help="Only test the ability wrapper"
    )

    args = parser.parse_args()

    if args.url:
        test_with_real_website(args.url)
    elif args.wrapper_only:
        test_ability_wrapper()
    else:
        # Full test with mock data
        test_design_agent_direct()
        print("\n")
        test_ability_wrapper()

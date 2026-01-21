"""
Test script for website intelligence extraction
"""

import json

from abilities.website_intelligence import website_intelligence_ability


def test_website_intelligence(url: str):
    """Test website intelligence extraction on a given URL"""
    print(f"\n{'=' * 80}")
    print(f"TESTING WEBSITE INTELLIGENCE EXTRACTION")
    print(f"{'=' * 80}")
    print(f"Target URL: {url}\n")

    # Execute intelligence extraction
    result_json = website_intelligence_ability(url)

    # Parse result
    result = json.loads(result_json)

    # Check for errors
    if "error" in result:
        print(f"❌ ERROR: {result['error']}")
        return False

    # Display results
    print(f"✅ Analysis completed: {result.get('analysis_date', 'N/A')}\n")

    # Brand Identity
    print("=" * 80)
    print("BRAND IDENTITY")
    print("=" * 80)
    brand = result.get("brand_identity", {})
    print(f"Name: {brand.get('name', 'N/A')}")
    print(f"Tagline: {brand.get('tagline', 'N/A')}")
    print(f"Logo: {brand.get('logo_url', 'N/A')}")
    print(f"Colors: {', '.join(brand.get('colors', []))}")
    print(f"Fonts: {', '.join(brand.get('fonts', []))}")
    print(f"Mission: {brand.get('mission_statement', 'N/A')[:100]}...")

    # Brand Voice
    print("\n" + "=" * 80)
    print("BRAND VOICE")
    print("=" * 80)
    voice = result.get("brand_voice", {})
    print(f"Tone: {', '.join(voice.get('tone', []))}")
    print(f"Emoji Usage: {'Yes' if voice.get('emoji_usage') else 'No'}")
    print(f"CTA Patterns: {', '.join(voice.get('cta_patterns', [])[:5])}")
    print(f"Characteristics: {voice.get('characteristics', 'N/A')}")

    # Products
    print("\n" + "=" * 80)
    print("PRODUCTS")
    print("=" * 80)
    products = result.get("products", {})
    print(f"Categories: {', '.join(products.get('categories', [])[:5])}")
    print(f"Pricing Tier: {products.get('pricing_tier', 'N/A')}")
    price_range = products.get("price_range", {})
    print(
        f"Price Range: ${price_range.get('min', 0):.2f} - ${price_range.get('max', 0):.2f}"
    )
    print(f"\nFeatured Products:")
    for item in products.get("featured_items", [])[:3]:
        print(f"  - {item.get('name', 'N/A')}: ${item.get('price', 0):.2f}")

    # Value Propositions
    print("\n" + "=" * 80)
    print("VALUE PROPOSITIONS")
    print("=" * 80)
    usps = result.get("value_propositions", {})
    print(f"Primary USP: {usps.get('primary_usp', 'N/A')[:150]}")
    print(f"Secondary USPs:")
    for usp in usps.get("secondary_usps", []):
        print(f"  - {usp}")

    # Promotions
    print("\n" + "=" * 80)
    print("PROMOTIONS")
    print("=" * 80)
    promos = result.get("promotions", {})
    print(f"Current Offers:")
    for offer in promos.get("current_offers", []):
        print(f"  - {offer}")
    print(f"Discount Types: {', '.join(promos.get('discount_types', []))}")
    print(f"First Timer Incentive: {promos.get('first_timer_incentive', 'N/A')[:100]}")

    # Audience Insights
    print("\n" + "=" * 80)
    print("AUDIENCE INSIGHTS")
    print("=" * 80)
    audience = result.get("audience", {})
    print(f"Target Demographic: {audience.get('target_demographic', 'N/A')}")
    testimonials = audience.get("testimonials", [])
    print(f"Testimonials Found: {len(testimonials)}")
    for i, testimonial in enumerate(testimonials[:2], 1):
        print(f"  {i}. {testimonial[:100]}...")

    # Technical Info
    print("\n" + "=" * 80)
    print("TECHNICAL INFO")
    print("=" * 80)
    tech = result.get("technical", {})
    print(f"Platform: {tech.get('platform', 'Unknown')}")
    print(f"Currency: {tech.get('currency', 'N/A')}")
    print(f"Blog: {'Yes' if tech.get('blog_topics') else 'No'}")

    # SEO
    print("\n" + "=" * 80)
    print("SEO METADATA")
    print("=" * 80)
    seo = result.get("seo", {})
    print(f"Title: {seo.get('title', 'N/A')}")
    print(f"Meta Description: {seo.get('meta_description', 'N/A')[:100]}")
    print(f"Keywords: {', '.join(seo.get('primary_keywords', []))}")

    # Trust Signals
    print("\n" + "=" * 80)
    print("TRUST SIGNALS")
    print("=" * 80)
    trust = result.get("trust_signals", {})
    print(f"Payment Methods: {', '.join(trust.get('payment_methods', []))}")
    print(f"Social Media:")
    for platform, link in trust.get("social_media", {}).items():
        print(f"  - {platform.capitalize()}: {link}")

    # Email Campaign Recommendations
    print("\n" + "=" * 80)
    print("EMAIL CAMPAIGN RECOMMENDATIONS")
    print("=" * 80)
    recs = result.get("email_campaign_recommendations", {})
    print(f"Subject Line Style: {recs.get('subject_line_style', 'N/A')}")
    print(f"Recommended Templates: {', '.join(recs.get('recommended_templates', []))}")
    print(f"Content Suggestions:")
    for suggestion in recs.get("content_suggestions", []):
        print(f"  - {suggestion}")
    print(f"Segmentation Opportunities:")
    for opportunity in recs.get("segmentation_opportunities", []):
        print(f"  - {opportunity}")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)

    # Save full JSON report
    output_file = "website_intelligence_report.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n📄 Full report saved to: {output_file}")

    return True


if __name__ == "__main__":
    # Test with example URLs
    test_urls = [
        "https://www.shopify.com",  # Example e-commerce platform
        # Add your customer URLs here:
        # "https://your-customer-site.com",
    ]

    print("\n🚀 Website Intelligence Extraction Test Suite")
    print("=" * 80)

    for url in test_urls:
        try:
            success = test_website_intelligence(url)
            if not success:
                print(f"⚠️ Test failed for {url}")
        except Exception as e:
            print(f"❌ Exception occurred: {e}")

    print("\n" + "=" * 80)
    print("🎯 All tests completed!")
    print("=" * 80)

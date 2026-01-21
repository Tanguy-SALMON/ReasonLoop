# Website Intelligence Agent - Usage Guide

## Overview

The Website Intelligence Agent is a specialized ReasonLoop agent that analyzes customer websites to extract comprehensive information needed for automated email campaign generation.

## What It Extracts

The agent extracts 10 categories of intelligence from any website:

1. **Brand Identity & Visual Assets** - Name, logo, colors, fonts, mission
2. **Brand Voice & Tone** - Writing style, CTAs, emoji usage, tone characteristics
3. **Product Catalog** - Categories, featured items, pricing tiers
4. **Value Propositions** - USPs, guarantees, quality claims
5. **Promotional Strategies** - Current offers, discount patterns, incentives
6. **Audience Insights** - Target demographics, testimonials, pain points
7. **Email Campaign Triggers** - Newsletter incentives, cart recovery, loyalty programs
8. **Technical Infrastructure** - Platform detection, blog presence, currency
9. **SEO & Metadata** - Title tags, descriptions, keywords
10. **Trust Signals** - Security badges, payment methods, social proof

## How to Use

### Method 1: Using ReasonLoop Command Line (Recommended)

```bash
# Basic website analysis
python main.py --template website_intelligence_agent --objective "https://customer-website.com"

# With verbose logging
python main.py --template website_intelligence_agent --objective "https://customer-website.com" --verbose
```

The agent will:
1. Scrape the website
2. Extract all intelligence categories
3. Generate email campaign recommendations
4. Create a comprehensive JSON report

### Method 2: Direct Ability Call (Python)

```python
from abilities.website_intelligence import website_intelligence_ability
import json

# Analyze website
result_json = website_intelligence_ability("https://customer-website.com")
result = json.loads(result_json)

# Access specific intelligence
brand_name = result['brand_identity']['name']
brand_colors = result['brand_identity']['colors']
pricing_tier = result['products']['pricing_tier']
campaign_recs = result['email_campaign_recommendations']

print(f"Brand: {brand_name}")
print(f"Colors: {', '.join(brand_colors)}")
print(f"Pricing: {pricing_tier}")
```

### Method 3: Testing Script

```bash
# Edit test_website_intelligence.py and add your URLs
python test_website_intelligence.py

# This will generate a formatted report and save website_intelligence_report.json
```

## Output Format

The agent returns a JSON structure:

```json
{
  "website_url": "https://example.com",
  "analysis_date": "2025-01-21T...",
  "brand_identity": {
    "name": "Brand Name",
    "tagline": "Your tagline here",
    "logo_url": "https://...",
    "colors": ["#hex1", "#hex2"],
    "fonts": ["Font Family"],
    "favicon_url": "https://...",
    "mission_statement": "..."
  },
  "brand_voice": {
    "tone": ["casual", "playful"],
    "characteristics": "Website uses emojis, tone appears playful",
    "cta_patterns": ["Shop Now", "Discover"],
    "emoji_usage": true
  },
  "products": {
    "categories": ["Category 1", "Category 2"],
    "featured_items": [
      {"name": "Product Name", "price": 99.99}
    ],
    "price_range": {"min": 20, "max": 500},
    "pricing_tier": "mid-range"
  },
  "value_propositions": {
    "primary_usp": "Main selling point...",
    "secondary_usps": ["Free shipping", "Money-back guarantee"],
    "guarantees": []
  },
  "promotions": {
    "current_offers": ["20% off spring sale"],
    "discount_types": ["percentage_discount", "free_shipping"],
    "first_timer_incentive": "Subscribe for 10% off"
  },
  "audience": {
    "target_demographic": "Young professionals",
    "pain_points": [],
    "testimonials": ["Great products!", "Love the quality"]
  },
  "email_triggers": {
    "newsletter_incentive": "Get 10% off your first order",
    "abandoned_cart_detected": false,
    "loyalty_program": true
  },
  "technical": {
    "platform": "Shopify",
    "blog_topics": ["Blog exists"],
    "currency": "USD"
  },
  "seo": {
    "title": "Homepage Title",
    "meta_description": "Meta description content",
    "primary_keywords": ["keyword1", "keyword2"]
  },
  "trust_signals": {
    "security_badges": [],
    "payment_methods": ["VISA", "PAYPAL"],
    "press_mentions": [],
    "social_media": {
      "instagram": "https://instagram.com/...",
      "facebook": "https://facebook.com/..."
    }
  },
  "email_campaign_recommendations": {
    "recommended_templates": ["casual_promo", "friendly_welcome"],
    "subject_line_style": "Fun, emoji-friendly, casual",
    "content_suggestions": ["Highlight: Free shipping"],
    "segmentation_opportunities": ["Category-based segmentation"]
  }
}
```

## Use Cases

### 1. Onboarding New Email Campaign Clients

```bash
# Analyze client's website
python main.py --template website_intelligence_agent --objective "https://new-client.com"

# Use the output to:
# - Set up brand colors in email templates
# - Match brand voice in email copy
# - Identify products for segmentation
# - Create audience-appropriate campaigns
```

### 2. Competitive Analysis

```bash
# Analyze competitor websites
python main.py --template website_intelligence_agent --objective "https://competitor1.com"
python main.py --template website_intelligence_agent --objective "https://competitor2.com"

# Compare:
# - Promotional strategies
# - Value propositions
# - Pricing tiers
# - Email signup incentives
```

### 3. Campaign Optimization

Extract intelligence periodically to:
- Detect new promotions to feature in emails
- Update product categories for segmentation
- Refresh brand assets in templates
- Align messaging with current website tone

### 4. Automated Campaign Generation Pipeline

```python
# 1. Extract website intelligence
intelligence = website_intelligence_ability("https://client.com")
data = json.loads(intelligence)

# 2. Use segmentation agent (your existing code)
from abilities.segmentation_agent import create_segments
segments = create_segments(user_recommendations)

# 3. Generate personalized campaigns
# Use extracted brand voice, colors, USPs to create emails
# Match subject line style to brand tone
# Feature products from intelligence data
```

## Integration with Existing Fashion Campaign Code

Your segmentation agent (`abilities/segmentation_agent.py`) can now be enhanced with website intelligence:

```python
# In your campaign generation pipeline:

# Step 1: Extract brand intelligence
intelligence = website_intelligence_ability(customer_website_url)
brand_data = json.loads(intelligence)

# Step 2: Segment users (your existing code)
segments = create_segments(user_recommendations)

# Step 3: Generate campaigns using both:
for segment in segments:
    email_copy = generate_email(
        segment=segment,
        brand_colors=brand_data['brand_identity']['colors'],
        brand_voice=brand_data['brand_voice']['tone'],
        brand_usps=brand_data['value_propositions']['secondary_usps'],
        current_promos=brand_data['promotions']['current_offers']
    )
```

## Workflow for Each New Customer

```bash
# 1. Extract website intelligence
python main.py --template website_intelligence_agent --objective "https://new-customer.com"

# 2. Review the generated JSON report
# Check: website_intelligence_report.json

# 3. Use intelligence to configure campaign system
# - Set brand colors, fonts, logo
# - Configure email templates with brand voice
# - Set up product categories
# - Import USPs for email copy

# 4. Run segmentation and campaign generation
python main.py --objective "Create segmented email campaigns for fashion customers using their website data"
```

## Advanced: Batch Processing Multiple Customers

Create a script to process multiple customers:

```python
# batch_website_analysis.py
from abilities.website_intelligence import website_intelligence_ability
import json

customers = [
    {"name": "Customer A", "url": "https://customer-a.com"},
    {"name": "Customer B", "url": "https://customer-b.com"},
    {"name": "Customer C", "url": "https://customer-c.com"},
]

for customer in customers:
    print(f"Analyzing {customer['name']}...")
    
    result = website_intelligence_ability(customer['url'])
    
    # Save individual report
    filename = f"reports/{customer['name']}_intelligence.json"
    with open(filename, 'w') as f:
        f.write(result)
    
    print(f"✅ Saved: {filename}")
```

## Troubleshooting

### Issue: Website not loading
**Solution**: Check if the URL is correct and accessible. Some sites block scrapers - try adding the site to test manually first.

### Issue: Missing information
**Solution**: Not all websites expose all information publicly. The agent will note "Not publicly accessible" for private data like abandoned cart flows.

### Issue: Colors/fonts not extracted
**Solution**: Some websites load CSS dynamically. The agent extracts inline styles and style tags but may miss externally loaded CSS.

### Issue: Platform not detected
**Solution**: Custom-built sites won't show a platform. This is normal - the agent will mark as "unknown".

## Next Steps

Now that you have website intelligence extraction:

1. **Integrate with segmentation agent** - Use brand data in your email campaigns
2. **Create email templates** - Design templates that adapt to extracted brand colors/fonts
3. **Automate campaign generation** - Combine website intelligence + segmentation + email generation
4. **Build customer dashboard** - Display extracted intelligence for each customer
5. **Set up periodic updates** - Re-analyze customer websites monthly to catch changes

## Files Created

- `abilities/website_intelligence.py` - Core extraction ability
- `templates/website_intelligence_agent.md` - ReasonLoop template
- `test_website_intelligence.py` - Test script
- `WEBSITE_INTELLIGENCE_GUIDE.md` - This guide

## Example Command Reference

```bash
# Basic analysis
python main.py --template website_intelligence_agent --objective "https://example.com"

# Check registered abilities
python main.py --list-abilities

# Run test script
python test_website_intelligence.py

# Use in larger campaign workflow
python main.py --objective "Analyze https://fashion-brand.com and create email campaign strategy"
```

---

**You're ready to start analyzing customer websites for automated email campaigns!** 🚀

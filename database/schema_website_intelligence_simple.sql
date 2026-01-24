-- ============================================================================
-- Website Intelligence - Simple Single Table Schema
-- One row per website analysis with JSON columns for nested data
-- Matches output from website_intelligence_ability
-- ============================================================================

DROP TABLE IF EXISTS website_intelligence;

CREATE TABLE website_intelligence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- =========================================================================
    -- Customer & Website Info
    -- =========================================================================
    customer_name VARCHAR(255),
    website_url VARCHAR(500) NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    output_session VARCHAR(500),          -- Path to output folder (e.g., output/domain.com/)
    
    -- =========================================================================
    -- Brand Identity (from brand_identity object)
    -- =========================================================================
    brand_name VARCHAR(255),              -- brand_identity.name
    brand_tagline TEXT,                   -- brand_identity.tagline
    brand_logo_url VARCHAR(1000),         -- brand_identity.logo_url
    brand_favicon_url VARCHAR(1000),      -- brand_identity.favicon_url
    brand_mission_statement TEXT,         -- brand_identity.mission_statement
    brand_colors JSON,                    -- brand_identity.colors: ["#hex1", "#hex2", ...]
    brand_fonts JSON,                     -- brand_identity.fonts: ["Font1", "Font2", ...]
    
    -- =========================================================================
    -- Brand Voice (from brand_voice object)
    -- =========================================================================
    brand_tones JSON,                     -- brand_voice.tone: ["luxury", "playful", ...]
    voice_characteristics TEXT,           -- brand_voice.characteristics
    voice_emoji_usage BOOLEAN DEFAULT FALSE, -- brand_voice.emoji_usage
    cta_patterns JSON,                    -- brand_voice.cta_patterns: ["Shop Now", "Discover", ...]
    
    -- =========================================================================
    -- Products (from products object)
    -- =========================================================================
    product_categories JSON,              -- products.categories: ["Women", "Men", ...]
    featured_products JSON,               -- products.featured_items: [{"name": "...", "price": 99.99}, ...]
    pricing_tier ENUM('budget', 'mid-range', 'premium', 'luxury', 'unknown') DEFAULT 'unknown',
    price_range_min DECIMAL(10, 2),       -- products.price_range.min
    price_range_max DECIMAL(10, 2),       -- products.price_range.max
    
    -- =========================================================================
    -- Value Propositions (from value_propositions object)
    -- =========================================================================
    primary_usp TEXT,                     -- value_propositions.primary_usp
    secondary_usps JSON,                  -- value_propositions.secondary_usps: ["Free shipping", ...]
    guarantees JSON,                      -- value_propositions.guarantees: ["30-day return", ...]
    
    -- =========================================================================
    -- Promotions (from promotions object)
    -- =========================================================================
    current_offers JSON,                  -- promotions.current_offers: ["20% off", ...]
    discount_types JSON,                  -- promotions.discount_types: ["percentage_discount", ...]
    first_timer_incentive TEXT,           -- promotions.first_timer_incentive (newsletter signup offer)
    
    -- =========================================================================
    -- Audience (from audience object)
    -- =========================================================================
    target_demographic TEXT,              -- audience.target_demographic
    pain_points JSON,                     -- audience.pain_points: ["Problem 1", ...]
    testimonials JSON,                    -- audience.testimonials: ["Great product!", ...]
    
    -- =========================================================================
    -- Technical (from technical object)
    -- =========================================================================
    platform VARCHAR(100),                -- technical.platform: "Shopify", "Magento", etc.
    currency VARCHAR(10) DEFAULT 'USD',   -- technical.currency
    blog_topics JSON,                     -- technical.blog_topics: ["Blog exists...", ...]
    
    -- =========================================================================
    -- SEO (from seo object)
    -- =========================================================================
    seo_title VARCHAR(500),               -- seo.title
    seo_meta_description TEXT,            -- seo.meta_description
    seo_keywords JSON,                    -- seo.primary_keywords: ["keyword1", ...]
    
    -- =========================================================================
    -- Trust Signals (from trust_signals object)
    -- =========================================================================
    payment_methods JSON,                 -- trust_signals.payment_methods: ["VISA", "PAYPAL", ...]
    security_badges JSON,                 -- trust_signals.security_badges: ["SSL", ...]
    social_media JSON,                    -- trust_signals.social_media: {"instagram": "url", ...}
    press_mentions JSON,                  -- trust_signals.press_mentions: ["Forbes", ...]
    
    -- =========================================================================
    -- Design Metrics (from design_metrics object)
    -- Critical for replicating brand design in email templates
    -- =========================================================================
    design_typography JSON,               -- design_metrics.typography: {font_families, font_urls, heading_sizes, ...}
    design_spacing JSON,                  -- design_metrics.spacing: {margins, paddings, gaps}
    design_borders JSON,                  -- design_metrics.borders: {border_radius, border_widths, border_styles}
    design_shadows JSON,                  -- design_metrics.shadows: {box_shadows}
    design_buttons JSON,                  -- design_metrics.buttons: {styles, colors, hover_effects}
    design_layout JSON,                   -- design_metrics.layout: {container_widths, grid_columns}
    
    -- =========================================================================
    -- Email Campaign Recommendations (from email_campaign_recommendations object)
    -- =========================================================================
    recommended_templates JSON,           -- email_campaign_recommendations.recommended_templates: ["welcome", ...]
    subject_line_style TEXT,              -- email_campaign_recommendations.subject_line_style
    content_suggestions JSON,             -- email_campaign_recommendations.content_suggestions: [...]
    segmentation_opportunities JSON,      -- email_campaign_recommendations.segmentation_opportunities: [...]
    
    -- =========================================================================
    -- Raw Data & Metadata
    -- =========================================================================
    raw_json JSON,                        -- Full original JSON response from ability
    
    status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
    error_message TEXT,                   -- Error details if status = 'failed'
    llm_provider VARCHAR(50),             -- LLM provider used: "xai", "anthropic", "openai"
    llm_model VARCHAR(100),               -- Model used: "grok-4-1-fast-non-reasoning", "claude-opus-4-5", etc.
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- =========================================================================
    -- Indexes
    -- =========================================================================
    INDEX idx_website_url (website_url(255)),
    INDEX idx_customer_name (customer_name),
    INDEX idx_analysis_date (analysis_date),
    INDEX idx_brand_name (brand_name),
    INDEX idx_status (status),
    INDEX idx_platform (platform),
    INDEX idx_pricing_tier (pricing_tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Example Insert (from website_intelligence_ability output)
-- ============================================================================

-- INSERT INTO website_intelligence (
--     customer_name,
--     website_url,
--     output_session,
--     brand_name,
--     brand_tagline,
--     brand_logo_url,
--     brand_colors,
--     brand_fonts,
--     brand_tones,
--     voice_emoji_usage,
--     cta_patterns,
--     product_categories,
--     featured_products,
--     pricing_tier,
--     price_range_min,
--     price_range_max,
--     primary_usp,
--     secondary_usps,
--     platform,
--     currency,
--     seo_title,
--     seo_meta_description,
--     payment_methods,
--     social_media,
--     design_typography,
--     recommended_templates,
--     subject_line_style,
--     llm_provider,
--     llm_model,
--     raw_json
-- ) VALUES (
--     'Shiseido US',
--     'https://www.shiseido.com/us/en/',
--     'output/www.shiseido.com/',
--     'Shiseido',
--     'Since 1872 - The Art of Beauty',
--     'https://www.shiseido.com/logo.svg',
--     '["#000000", "#C41230", "#FFFFFF", "#F5F5F5"]',
--     '["Noto Sans", "Bodoni"]',
--     '["luxury", "sophisticated", "professional"]',
--     FALSE,
--     '["Shop Now", "Discover", "Add to Bag", "Learn More"]',
--     '["Skincare", "Makeup", "Suncare", "Best Sellers", "New Arrivals"]',
--     '[{"name": "Ultimune Power Infusing Serum", "price": 75.00}, {"name": "Future Solution LX", "price": 285.00}]',
--     'premium',
--     75.00,
--     285.00,
--     'Japanese beauty innovation since 1872',
--     '["Free shipping over $50", "Complimentary samples", "Easy returns"]',
--     'Salesforce Commerce Cloud',
--     'USD',
--     'Shiseido | Premium Japanese Skincare & Makeup',
--     'Discover Japanese beauty innovation with Shiseido. Shop premium skincare, makeup, and suncare.',
--     '["VISA", "MASTERCARD", "AMEX", "PAYPAL", "APPLE-PAY"]',
--     '{"instagram": "https://instagram.com/shiseido", "facebook": "https://facebook.com/Shiseido"}',
--     '{"font_families": ["Noto Sans", "Bodoni"], "font_urls": ["https://fonts.googleapis.com/..."]}',
--     '["welcome_series", "promotional", "product_launch", "loyalty"]',
--     'Elegant, benefit-focused with Japanese aesthetic',
--     'xai',
--     'grok-4-1-fast-non-reasoning',
--     '{...full json from website_intelligence_ability...}'
-- );

-- ============================================================================
-- Useful Queries
-- ============================================================================

-- Get all analyses for a customer
-- SELECT * FROM website_intelligence WHERE customer_name = 'Shiseido US';

-- Get latest analysis per website
-- SELECT * FROM website_intelligence wi1
-- WHERE analysis_date = (
--     SELECT MAX(analysis_date) FROM website_intelligence wi2 
--     WHERE wi2.website_url = wi1.website_url
-- );

-- Search by brand tone (luxury brands)
-- SELECT brand_name, website_url, brand_colors, pricing_tier
-- FROM website_intelligence 
-- WHERE JSON_CONTAINS(brand_tones, '"luxury"');

-- Get all premium brands with their design fonts
-- SELECT 
--     brand_name, 
--     website_url, 
--     brand_colors,
--     JSON_EXTRACT(design_typography, '$.font_families') AS fonts
-- FROM website_intelligence 
-- WHERE pricing_tier = 'premium';

-- Extract primary color
-- SELECT brand_name, JSON_EXTRACT(brand_colors, '$[0]') AS primary_color
-- FROM website_intelligence;

-- Get brands by platform
-- SELECT brand_name, website_url, platform
-- FROM website_intelligence 
-- WHERE platform = 'Shopify';

-- Get email campaign recommendations for a brand
-- SELECT 
--     brand_name,
--     recommended_templates,
--     subject_line_style,
--     content_suggestions
-- FROM website_intelligence
-- WHERE website_url LIKE '%shiseido%';

-- Compare LLM providers used
-- SELECT llm_provider, llm_model, COUNT(*) AS analysis_count
-- FROM website_intelligence
-- GROUP BY llm_provider, llm_model;

-- Find brands with specific payment methods
-- SELECT brand_name, website_url
-- FROM website_intelligence
-- WHERE JSON_CONTAINS(payment_methods, '"PAYPAL"');

-- Get design typography details
-- SELECT 
--     brand_name,
--     JSON_EXTRACT(design_typography, '$.font_families') AS fonts,
--     JSON_EXTRACT(design_typography, '$.heading_sizes') AS heading_sizes,
--     JSON_EXTRACT(design_spacing, '$.paddings') AS paddings
-- FROM website_intelligence
-- WHERE brand_name IS NOT NULL;

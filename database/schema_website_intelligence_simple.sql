-- ============================================================================
-- Website Intelligence - Simple Single Table Schema
-- One row per website analysis with JSON columns for nested data
-- ============================================================================

DROP TABLE IF EXISTS website_intelligence;

CREATE TABLE website_intelligence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Customer & Website Info
    customer_name VARCHAR(255),
    website_url VARCHAR(500) NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Brand Identity
    brand_name VARCHAR(255),
    brand_tagline TEXT,
    brand_logo_url VARCHAR(1000),
    brand_favicon_url VARCHAR(1000),
    brand_mission_statement TEXT,
    brand_colors JSON,                    -- ["#hex1", "#hex2", ...]
    brand_fonts JSON,                     -- ["Font1", "Font2", ...]
    
    -- Brand Voice
    brand_tones JSON,                     -- ["casual", "playful", ...]
    voice_characteristics TEXT,
    voice_emoji_usage BOOLEAN DEFAULT FALSE,
    cta_patterns JSON,                    -- ["Shop Now", "Discover", ...]
    
    -- Products
    product_categories JSON,              -- ["Category1", "Category2", ...]
    featured_products JSON,               -- [{"name": "...", "price": 99.99}, ...]
    pricing_tier ENUM('budget', 'mid-range', 'premium', 'luxury', 'unknown') DEFAULT 'unknown',
    price_range_min DECIMAL(10, 2),
    price_range_max DECIMAL(10, 2),
    
    -- Value Propositions
    primary_usp TEXT,
    secondary_usps JSON,                  -- ["Free shipping", "Money-back", ...]
    guarantees JSON,                      -- ["30-day return", ...]
    
    -- Promotions
    current_offers JSON,                  -- ["20% off", "Free shipping over $50", ...]
    discount_types JSON,                  -- ["percentage_discount", "free_shipping", ...]
    newsletter_incentive TEXT,
    has_abandoned_cart BOOLEAN DEFAULT FALSE,
    has_loyalty_program BOOLEAN DEFAULT FALSE,
    
    -- Audience
    target_demographic TEXT,
    pain_points JSON,                     -- ["Problem 1", "Problem 2", ...]
    testimonials JSON,                    -- ["Great product!", "Love it!", ...]
    
    -- Technical
    platform VARCHAR(100),
    currency VARCHAR(10) DEFAULT 'USD',
    has_blog BOOLEAN DEFAULT FALSE,
    
    -- SEO
    seo_title VARCHAR(500),
    seo_meta_description TEXT,
    seo_keywords JSON,                    -- ["keyword1", "keyword2", ...]
    
    -- Trust Signals
    payment_methods JSON,                 -- ["VISA", "PAYPAL", ...]
    security_badges JSON,                 -- ["SSL", "McAfee", ...]
    social_media JSON,                    -- {"instagram": "url", "facebook": "url", ...}
    press_mentions JSON,                  -- ["Forbes", "Vogue", ...]
    
    -- Email Campaign Recommendations
    recommended_templates JSON,           -- ["welcome_series", "promo", ...]
    subject_line_style TEXT,
    content_suggestions JSON,             -- ["Highlight free shipping", ...]
    segmentation_opportunities JSON,      -- ["Category-based", "Price-sensitive", ...]
    
    -- Raw Data Backup
    raw_json JSON,                        -- Full original JSON response
    
    -- Metadata
    status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_website_url (website_url(255)),
    INDEX idx_customer_name (customer_name),
    INDEX idx_analysis_date (analysis_date),
    INDEX idx_brand_name (brand_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Example Insert
-- ============================================================================

-- INSERT INTO website_intelligence (
--     customer_name,
--     website_url,
--     brand_name,
--     brand_tagline,
--     brand_colors,
--     brand_tones,
--     product_categories,
--     pricing_tier,
--     platform,
--     raw_json
-- ) VALUES (
--     'COS Thailand',
--     'https://th.cos.com',
--     'COS',
--     'Modern, functional, timeless design',
--     '["#000000", "#FFFFFF", "#E5E5E5"]',
--     '["minimalist", "luxury", "sophisticated"]',
--     '["Women", "Men", "Kids", "Accessories"]',
--     'premium',
--     'Custom',
--     '{...full json...}'
-- );

-- ============================================================================
-- Useful Queries
-- ============================================================================

-- Get all analyses for a customer
-- SELECT * FROM website_intelligence WHERE customer_name = 'COS Thailand';

-- Get latest analysis per website
-- SELECT * FROM website_intelligence wi1
-- WHERE analysis_date = (
--     SELECT MAX(analysis_date) FROM website_intelligence wi2 
--     WHERE wi2.website_url = wi1.website_url
-- );

-- Search by brand tone
-- SELECT * FROM website_intelligence 
-- WHERE JSON_CONTAINS(brand_tones, '"luxury"');

-- Get all premium brands
-- SELECT brand_name, website_url, brand_colors 
-- FROM website_intelligence 
-- WHERE pricing_tier = 'premium';

-- Extract specific color
-- SELECT brand_name, JSON_EXTRACT(brand_colors, '$[0]') AS primary_color
-- FROM website_intelligence;

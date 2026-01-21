-- ============================================================================
-- Website Intelligence Database Schema
-- For storing email campaign intelligence extracted from customer websites
-- ============================================================================

-- Drop tables if they exist (in reverse order of dependencies)
DROP TABLE IF EXISTS email_campaign_recommendations;
DROP TABLE IF EXISTS segmentation_opportunities;
DROP TABLE IF EXISTS content_suggestions;
DROP TABLE IF EXISTS social_media_links;
DROP TABLE IF EXISTS payment_methods;
DROP TABLE IF EXISTS trust_badges;
DROP TABLE IF EXISTS seo_keywords;
DROP TABLE IF EXISTS testimonials;
DROP TABLE IF EXISTS audience_pain_points;
DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS value_propositions;
DROP TABLE IF EXISTS product_items;
DROP TABLE IF EXISTS product_categories;
DROP TABLE IF EXISTS cta_patterns;
DROP TABLE IF EXISTS brand_tones;
DROP TABLE IF EXISTS brand_fonts;
DROP TABLE IF EXISTS brand_colors;
DROP TABLE IF EXISTS website_analyses;
DROP TABLE IF EXISTS customers;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Customers table (your clients who want email campaigns)
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    company_name VARCHAR(255),
    website_url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    
    INDEX idx_website_url (website_url(255)),
    INDEX idx_company_name (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Website analyses (one per analysis run)
CREATE TABLE website_analyses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    website_url VARCHAR(500) NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Brand Identity
    brand_name VARCHAR(255),
    brand_tagline TEXT,
    brand_logo_url VARCHAR(1000),
    brand_favicon_url VARCHAR(1000),
    brand_mission_statement TEXT,
    
    -- Brand Voice
    voice_characteristics TEXT,
    voice_emoji_usage BOOLEAN DEFAULT FALSE,
    
    -- Products Summary
    pricing_tier ENUM('budget', 'mid-range', 'premium', 'luxury', 'unknown') DEFAULT 'unknown',
    price_range_min DECIMAL(10, 2),
    price_range_max DECIMAL(10, 2),
    
    -- Technical Info
    platform VARCHAR(100),
    currency VARCHAR(10) DEFAULT 'USD',
    has_blog BOOLEAN DEFAULT FALSE,
    blog_url VARCHAR(500),
    
    -- SEO
    seo_title VARCHAR(500),
    seo_meta_description TEXT,
    
    -- Audience
    target_demographic TEXT,
    
    -- Promotions
    newsletter_incentive TEXT,
    has_abandoned_cart BOOLEAN DEFAULT FALSE,
    has_loyalty_program BOOLEAN DEFAULT FALSE,
    
    -- Email Recommendations
    recommended_subject_line_style TEXT,
    
    -- Raw JSON (full response backup)
    raw_intelligence_json JSON,
    
    -- Status
    status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_id (customer_id),
    INDEX idx_analysis_date (analysis_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- BRAND IDENTITY DETAILS
-- ============================================================================

-- Brand colors (multiple per analysis)
CREATE TABLE brand_colors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    color_hex VARCHAR(7) NOT NULL,
    color_name VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Brand fonts (multiple per analysis)
CREATE TABLE brand_fonts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    font_family VARCHAR(255) NOT NULL,
    font_type ENUM('primary', 'secondary', 'accent') DEFAULT 'primary',
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Brand tones (multiple per analysis)
CREATE TABLE brand_tones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    tone VARCHAR(100) NOT NULL,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_tone (tone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- CTA patterns (multiple per analysis)
CREATE TABLE cta_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    cta_text VARCHAR(255) NOT NULL,
    frequency INT DEFAULT 1,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PRODUCTS
-- ============================================================================

-- Product categories
CREATE TABLE product_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    category_name VARCHAR(255) NOT NULL,
    parent_category_id INT,
    category_url VARCHAR(500),
    sort_order INT DEFAULT 0,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_category_id) REFERENCES product_categories(id) ON DELETE SET NULL,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Featured/extracted product items
CREATE TABLE product_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    category_id INT,
    product_name VARCHAR(500) NOT NULL,
    product_url VARCHAR(1000),
    price DECIMAL(10, 2),
    original_price DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    image_url VARCHAR(1000),
    is_featured BOOLEAN DEFAULT FALSE,
    is_bestseller BOOLEAN DEFAULT FALSE,
    is_new_arrival BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES product_categories(id) ON DELETE SET NULL,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_is_featured (is_featured)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- VALUE PROPOSITIONS
-- ============================================================================

CREATE TABLE value_propositions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    proposition_text TEXT NOT NULL,
    proposition_type ENUM('primary', 'secondary', 'guarantee') DEFAULT 'secondary',
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_type (proposition_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PROMOTIONS
-- ============================================================================

CREATE TABLE promotions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    promotion_text TEXT NOT NULL,
    promotion_type ENUM('percentage_discount', 'fixed_discount', 'free_shipping', 'bogo', 'bundle', 'other') DEFAULT 'other',
    discount_value VARCHAR(50),
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- AUDIENCE INSIGHTS
-- ============================================================================

-- Audience pain points
CREATE TABLE audience_pain_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    pain_point TEXT NOT NULL,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Customer testimonials
CREATE TABLE testimonials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    testimonial_text TEXT NOT NULL,
    customer_name VARCHAR(255),
    customer_title VARCHAR(255),
    rating DECIMAL(2, 1),
    source VARCHAR(100),
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SEO & METADATA
-- ============================================================================

-- SEO keywords
CREATE TABLE seo_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    keyword_type ENUM('primary', 'secondary', 'long_tail') DEFAULT 'primary',
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_keyword (keyword)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TRUST SIGNALS
-- ============================================================================

-- Trust badges
CREATE TABLE trust_badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    badge_name VARCHAR(255) NOT NULL,
    badge_type ENUM('security', 'payment', 'certification', 'award', 'press', 'other') DEFAULT 'other',
    badge_url VARCHAR(500),
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payment methods
CREATE TABLE payment_methods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    method_name VARCHAR(100) NOT NULL,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Social media links
CREATE TABLE social_media_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    profile_url VARCHAR(500) NOT NULL,
    follower_count INT,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_platform (platform)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- EMAIL CAMPAIGN RECOMMENDATIONS
-- ============================================================================

-- Content suggestions
CREATE TABLE content_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    suggestion_text TEXT NOT NULL,
    suggestion_type ENUM('subject_line', 'body_copy', 'cta', 'image', 'general') DEFAULT 'general',
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Segmentation opportunities
CREATE TABLE segmentation_opportunities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    opportunity_name VARCHAR(255) NOT NULL,
    opportunity_description TEXT,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recommended email templates
CREATE TABLE email_campaign_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    template_type ENUM('welcome', 'promotional', 'abandoned_cart', 'newsletter', 'product_launch', 'seasonal', 'loyalty', 'win_back', 'other') DEFAULT 'other',
    priority INT DEFAULT 0,
    
    FOREIGN KEY (analysis_id) REFERENCES website_analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis_id (analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- View: Complete customer brand profile
CREATE OR REPLACE VIEW v_customer_brand_profile AS
SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    c.company_name,
    wa.id AS analysis_id,
    wa.website_url,
    wa.analysis_date,
    wa.brand_name,
    wa.brand_tagline,
    wa.brand_logo_url,
    wa.voice_emoji_usage,
    wa.pricing_tier,
    wa.platform,
    wa.currency,
    wa.target_demographic,
    wa.recommended_subject_line_style,
    GROUP_CONCAT(DISTINCT bc.color_hex) AS brand_colors,
    GROUP_CONCAT(DISTINCT bf.font_family) AS brand_fonts,
    GROUP_CONCAT(DISTINCT bt.tone) AS brand_tones
FROM customers c
JOIN website_analyses wa ON c.id = wa.customer_id
LEFT JOIN brand_colors bc ON wa.id = bc.analysis_id
LEFT JOIN brand_fonts bf ON wa.id = bf.analysis_id
LEFT JOIN brand_tones bt ON wa.id = bt.analysis_id
WHERE wa.status = 'completed'
GROUP BY c.id, wa.id;

-- View: Latest analysis per customer
CREATE OR REPLACE VIEW v_latest_customer_analysis AS
SELECT wa.*
FROM website_analyses wa
INNER JOIN (
    SELECT customer_id, MAX(analysis_date) AS latest_date
    FROM website_analyses
    WHERE status = 'completed'
    GROUP BY customer_id
) latest ON wa.customer_id = latest.customer_id AND wa.analysis_date = latest.latest_date;

-- View: Email campaign readiness
CREATE OR REPLACE VIEW v_email_campaign_readiness AS
SELECT 
    c.id AS customer_id,
    c.company_name,
    wa.id AS analysis_id,
    wa.brand_name,
    CASE WHEN wa.brand_logo_url IS NOT NULL THEN 1 ELSE 0 END AS has_logo,
    (SELECT COUNT(*) FROM brand_colors WHERE analysis_id = wa.id) AS color_count,
    (SELECT COUNT(*) FROM brand_tones WHERE analysis_id = wa.id) AS tone_count,
    (SELECT COUNT(*) FROM product_categories WHERE analysis_id = wa.id) AS category_count,
    (SELECT COUNT(*) FROM product_items WHERE analysis_id = wa.id) AS product_count,
    (SELECT COUNT(*) FROM value_propositions WHERE analysis_id = wa.id) AS usp_count,
    (SELECT COUNT(*) FROM testimonials WHERE analysis_id = wa.id) AS testimonial_count,
    wa.newsletter_incentive IS NOT NULL AS has_newsletter_incentive,
    wa.has_loyalty_program,
    wa.analysis_date
FROM customers c
JOIN website_analyses wa ON c.id = wa.customer_id
WHERE wa.status = 'completed';

-- ============================================================================
-- SAMPLE DATA INSERT (for testing)
-- ============================================================================

-- Insert a sample customer
-- INSERT INTO customers (name, email, company_name, website_url) 
-- VALUES ('Test User', 'test@example.com', 'COS Thailand', 'https://th.cos.com');

-- ============================================================================
-- USEFUL QUERIES
-- ============================================================================

-- Get full brand profile for a customer
-- SELECT * FROM v_customer_brand_profile WHERE customer_id = 1;

-- Get all products for an analysis
-- SELECT pc.category_name, pi.* 
-- FROM product_items pi 
-- LEFT JOIN product_categories pc ON pi.category_id = pc.id 
-- WHERE pi.analysis_id = 1;

-- Get campaign recommendations
-- SELECT ecr.*, cs.suggestion_text, so.opportunity_name
-- FROM email_campaign_recommendations ecr
-- LEFT JOIN content_suggestions cs ON ecr.analysis_id = cs.analysis_id
-- LEFT JOIN segmentation_opportunities so ON ecr.analysis_id = so.analysis_id
-- WHERE ecr.analysis_id = 1;

-- Get latest analysis for each customer
-- SELECT * FROM v_latest_customer_analysis;

-- Check email campaign readiness
-- SELECT * FROM v_email_campaign_readiness WHERE customer_id = 1;

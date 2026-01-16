-- ReasonLoop Database Schema
-- Database: reasonloop
-- User: magento
-- Password: Magento@COS(*)
-- Host: localhost:3306
--
-- Run this with: mysql -u magento -p reasonloop < create_admin_tables.sql

-- Drop existing tables if they exist (in correct order due to foreign keys)
DROP TABLE IF EXISTS session_metrics;
DROP TABLE IF EXISTS task_executions;
DROP TABLE IF EXISTS execution_sessions;
DROP TABLE IF EXISTS agent_configs;

-- ==============================================================================
-- Execution Sessions Table
-- Tracks each complete run of the ReasonLoop framework
-- ==============================================================================
CREATE TABLE execution_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    objective TEXT NOT NULL,
    template_name VARCHAR(100),
    provider VARCHAR(50),
    status ENUM('running', 'completed', 'failed', 'interrupted') DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    duration_seconds DECIMAL(10,2),
    
    -- Aggregated metrics
    total_tasks INT DEFAULT 0,
    completed_tasks INT DEFAULT 0,
    failed_tasks INT DEFAULT 0,
    total_prompt_tokens INT DEFAULT 0,
    total_completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0.000000,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_session_id (session_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at),
    INDEX idx_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- Task Executions Table
-- Tracks individual task executions within a session
-- ==============================================================================
CREATE TABLE task_executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    task_id INT NOT NULL,
    task_description TEXT,
    ability_name VARCHAR(100),
    role VARCHAR(50),
    
    -- Execution details
    status ENUM('pending', 'in_progress', 'completed', 'failed') DEFAULT 'pending',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    execution_time_seconds DECIMAL(10,3),
    
    -- LLM metrics
    model VARCHAR(100),
    provider VARCHAR(50),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0.000000,
    
    -- Content
    prompt_text TEXT,
    response_text TEXT,
    error_message TEXT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES execution_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_task (session_id, task_id),
    INDEX idx_ability (ability_name),
    INDEX idx_role (role),
    INDEX idx_status (status),
    INDEX idx_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- Agent Configurations Table
-- Stores reusable agent configurations and templates
-- ==============================================================================
CREATE TABLE agent_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    config_type ENUM('template', 'preset', 'custom') DEFAULT 'custom',
    
    -- Configuration
    provider VARCHAR(50),
    model VARCHAR(100),
    temperature DECIMAL(3,2),
    max_tokens INT,
    template_name VARCHAR(100),
    
    -- Settings JSON
    settings JSON,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INT DEFAULT 0,
    last_used_at TIMESTAMP NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    INDEX idx_name (name),
    INDEX idx_config_type (config_type),
    INDEX idx_is_active (is_active),
    INDEX idx_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- Session Metrics Table  
-- Daily aggregated metrics for reporting and analysis
-- ==============================================================================
CREATE TABLE session_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    
    -- Aggregated counts
    session_count INT DEFAULT 0,
    task_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    
    -- Token metrics
    total_prompt_tokens BIGINT DEFAULT 0,
    total_completion_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    
    -- Cost metrics
    total_cost_usd DECIMAL(12,6) DEFAULT 0.000000,
    avg_cost_per_session DECIMAL(10,6) DEFAULT 0.000000,
    avg_cost_per_task DECIMAL(10,6) DEFAULT 0.000000,
    
    -- Performance metrics
    avg_execution_time_seconds DECIMAL(10,3),
    avg_tokens_per_request INT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_date_provider (date, provider),
    INDEX idx_date (date),
    INDEX idx_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- Views for easy querying
-- ==============================================================================

-- Recent sessions with summary
CREATE OR REPLACE VIEW v_recent_sessions AS
SELECT 
    s.session_id,
    s.objective,
    s.provider,
    s.status,
    s.started_at,
    s.duration_seconds,
    s.total_tasks,
    s.completed_tasks,
    s.failed_tasks,
    s.total_cost_usd,
    CONCAT(s.total_prompt_tokens + s.total_completion_tokens, ' tokens') as tokens_used,
    ROUND(s.total_cost_usd / NULLIF(s.total_tasks, 0), 6) as cost_per_task
FROM execution_sessions s
ORDER BY s.started_at DESC
LIMIT 50;

-- Cost by provider
CREATE OR REPLACE VIEW v_cost_by_provider AS
SELECT 
    provider,
    COUNT(*) as session_count,
    SUM(total_tasks) as total_tasks,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost_usd) as total_cost,
    AVG(total_cost_usd) as avg_cost_per_session,
    MAX(total_cost_usd) as max_cost_session,
    MIN(started_at) as first_used,
    MAX(started_at) as last_used
FROM execution_sessions
GROUP BY provider
ORDER BY total_cost DESC;

-- Daily metrics summary
CREATE OR REPLACE VIEW v_daily_metrics AS
SELECT 
    date,
    SUM(session_count) as total_sessions,
    SUM(task_count) as total_tasks,
    SUM(success_count) as successful_tasks,
    SUM(failure_count) as failed_tasks,
    ROUND(SUM(success_count) * 100.0 / NULLIF(SUM(task_count), 0), 2) as success_rate_pct,
    SUM(total_tokens) as tokens_used,
    SUM(total_cost_usd) as daily_cost,
    GROUP_CONCAT(CONCAT(provider, ': $', ROUND(total_cost_usd, 4)) SEPARATOR ', ') as cost_by_provider
FROM session_metrics
GROUP BY date
ORDER BY date DESC;

-- ==============================================================================
-- Stored Procedures
-- ==============================================================================

DELIMITER //

-- Update session totals from task executions
CREATE PROCEDURE update_session_totals(IN p_session_id VARCHAR(255))
BEGIN
    UPDATE execution_sessions es
    SET 
        total_tasks = (SELECT COUNT(*) FROM task_executions WHERE session_id = p_session_id),
        completed_tasks = (SELECT COUNT(*) FROM task_executions WHERE session_id = p_session_id AND status = 'completed'),
        failed_tasks = (SELECT COUNT(*) FROM task_executions WHERE session_id = p_session_id AND status = 'failed'),
        total_prompt_tokens = COALESCE((SELECT SUM(prompt_tokens) FROM task_executions WHERE session_id = p_session_id), 0),
        total_completion_tokens = COALESCE((SELECT SUM(completion_tokens) FROM task_executions WHERE session_id = p_session_id), 0),
        total_tokens = COALESCE((SELECT SUM(total_tokens) FROM task_executions WHERE session_id = p_session_id), 0),
        total_cost_usd = COALESCE((SELECT SUM(cost_usd) FROM task_executions WHERE session_id = p_session_id), 0)
    WHERE session_id = p_session_id;
END//

-- Aggregate daily metrics
CREATE PROCEDURE aggregate_daily_metrics(IN p_date DATE)
BEGIN
    INSERT INTO session_metrics (
        date, provider, session_count, task_count, success_count, failure_count,
        total_prompt_tokens, total_completion_tokens, total_tokens, total_cost_usd,
        avg_cost_per_session, avg_cost_per_task, avg_execution_time_seconds, avg_tokens_per_request
    )
    SELECT 
        DATE(s.started_at) as date,
        s.provider,
        COUNT(DISTINCT s.session_id) as session_count,
        SUM(s.total_tasks) as task_count,
        SUM(s.completed_tasks) as success_count,
        SUM(s.failed_tasks) as failure_count,
        SUM(s.total_prompt_tokens) as total_prompt_tokens,
        SUM(s.total_completion_tokens) as total_completion_tokens,
        SUM(s.total_tokens) as total_tokens,
        SUM(s.total_cost_usd) as total_cost_usd,
        AVG(s.total_cost_usd) as avg_cost_per_session,
        AVG(s.total_cost_usd / NULLIF(s.total_tasks, 0)) as avg_cost_per_task,
        AVG(s.duration_seconds) as avg_execution_time_seconds,
        AVG(s.total_tokens / NULLIF(s.total_tasks, 0)) as avg_tokens_per_request
    FROM execution_sessions s
    WHERE DATE(s.started_at) = p_date
    GROUP BY DATE(s.started_at), s.provider
    ON DUPLICATE KEY UPDATE
        session_count = VALUES(session_count),
        task_count = VALUES(task_count),
        success_count = VALUES(success_count),
        failure_count = VALUES(failure_count),
        total_prompt_tokens = VALUES(total_prompt_tokens),
        total_completion_tokens = VALUES(total_completion_tokens),
        total_tokens = VALUES(total_tokens),
        total_cost_usd = VALUES(total_cost_usd),
        avg_cost_per_session = VALUES(avg_cost_per_session),
        avg_cost_per_task = VALUES(avg_cost_per_task),
        avg_execution_time_seconds = VALUES(avg_execution_time_seconds),
        avg_tokens_per_request = VALUES(avg_tokens_per_request),
        updated_at = CURRENT_TIMESTAMP;
END//

DELIMITER ;

-- ==============================================================================
-- Sample Data for Testing
-- ==============================================================================

-- Insert sample agent configurations
INSERT INTO agent_configs (name, description, config_type, provider, model, temperature, max_tokens, template_name, settings, created_by)
VALUES
('XAI Grok Standard', 'Standard configuration for XAI Grok', 'preset', 'xai', 'grok-2-1212', 0.70, 4096, 'default_tasks', '{"web_search_enabled": true}', 'system'),
('ZAI Fast Response', 'Optimized for quick responses', 'preset', 'zai', 'glm-4.6', 0.50, 2048, 'default_tasks', '{"web_search_enabled": false}', 'system'),
('Ollama Local', 'Local Ollama configuration', 'preset', 'ollama', 'llama3', 0.70, 4096, 'default_tasks', '{"web_search_enabled": true}', 'system');

-- ==============================================================================
-- Useful Queries
-- ==============================================================================

-- See recent sessions:
-- SELECT * FROM v_recent_sessions;

-- See cost breakdown by provider:
-- SELECT * FROM v_cost_by_provider;

-- See daily metrics:
-- SELECT * FROM v_daily_metrics;

-- Update session totals:
-- CALL update_session_totals('session_1234567890_20260116_143305');

-- Aggregate today's metrics:
-- CALL aggregate_daily_metrics(CURDATE());

-- Total spend by provider last 7 days:
-- SELECT provider, SUM(total_cost_usd) as cost FROM execution_sessions 
-- WHERE started_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) 
-- GROUP BY provider;

-- Average tokens per task:
-- SELECT AVG(total_tokens) as avg_tokens FROM task_executions WHERE status = 'completed';

-- Create database tables for admin pages
-- Run this with: mysql -u root -p reasonloop < create_admin_tables.sql

-- Agent Dashboard Table
CREATE TABLE IF NOT EXISTS agent_dashboard (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status ENUM('active', 'inactive', 'maintenance') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    config JSON,
    metrics JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Agent Rules Table
CREATE TABLE IF NOT EXISTS agent_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type ENUM('validation', 'transformation', 'filter', 'action') NOT NULL,
    rule_definition TEXT NOT NULL,
    priority INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    agent_id INT NULL,
    FOREIGN KEY (agent_id) REFERENCES agent_dashboard(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert sample data for agent_dashboard
INSERT INTO agent_dashboard (name, description, status, config, metrics) VALUES
('Performance Monitor', 'Monitors system performance metrics', 'active',
 '{"thresholds": {"cpu": 80, "memory": 90}, "check_interval": 60}',
 '{"total_checks": 1250, "alerts_triggered": 45}'),
('Data Validator', 'Validates incoming data integrity', 'active',
 '{"strict_mode": true, "allowed_formats": ["json", "csv"]}',
 '{"total_validations": 5420, "failed_validations": 89}'),
('Content Generator', 'Generates content based on templates', 'inactive',
 '{"template_count": 12, "max_length": 2000}',
 '{"generated_count": 340, "success_rate": 0.95}');

-- Insert sample data for agent_rules
INSERT INTO agent_rules (name, description, rule_type, rule_definition, priority, agent_id) VALUES
('CPU Threshold Check', 'Alert when CPU usage exceeds threshold', 'validation',
 'IF cpu_usage > 80 THEN trigger_alert("High CPU usage") END IF', 10, 1),
('Memory Validation', 'Validate memory usage patterns', 'validation',
 'IF memory_usage > 90 THEN log_error("Memory critical") END IF', 15, 1),
('Data Format Check', 'Validate data format before processing', 'validation',
 'IF NOT json_valid(data) THEN reject_data() END IF', 20, 2),
('Content Length Filter', 'Filter content by maximum length', 'filter',
 'IF LENGTH(content) > 2000 THEN truncate_content() END IF', 5, 3),
('Keyword Replacement', 'Replace sensitive keywords', 'transformation',
 'REPLACE(content, "sensitive_word", "***")', 8, 3);

-- Create indexes for better performance
CREATE INDEX idx_agent_dashboard_status ON agent_dashboard(status);
CREATE INDEX idx_agent_dashboard_created ON agent_dashboard(created_at);
CREATE INDEX idx_agent_rules_type ON agent_rules(rule_type);
CREATE INDEX idx_agent_rules_active ON agent_rules(is_active);
CREATE INDEX idx_agent_rules_agent ON agent_rules(agent_id);
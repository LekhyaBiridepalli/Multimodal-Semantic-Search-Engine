-- =====================================================
-- TKAG-RAG Database Setup Script
-- =====================================================

-- Drop database if exists (optional - comment out if you want to keep existing data)
-- DROP DATABASE IF EXISTS tkrag_db;

-- Create database
CREATE DATABASE IF NOT EXISTS tkrag_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tkrag_db;

-- =====================================================
-- Drop tables in reverse order of dependencies
-- =====================================================
DROP TABLE IF EXISTS activity_logs;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS knowledge_graph;
DROP TABLE IF EXISTS search_history;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS users;

-- =====================================================
-- Users table
-- =====================================================
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    full_name VARCHAR(100),
    profile_pic VARCHAR(200) DEFAULT 'default.jpg',
    bio TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_login DATETIME,
    last_active DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Search history table
-- =====================================================
CREATE TABLE search_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    search_type VARCHAR(50) DEFAULT 'full',
    results JSON,
    summary TEXT,
    pdf_path VARCHAR(500),
    execution_time FLOAT,
    status VARCHAR(20) DEFAULT 'completed',
    is_favorite BOOLEAN DEFAULT FALSE,
    views_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Favorites table
-- =====================================================
CREATE TABLE favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    search_id INT NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (search_id) REFERENCES search_history(id) ON DELETE CASCADE,
    UNIQUE KEY unique_favorite (user_id, search_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Knowledge graph table
-- =====================================================
CREATE TABLE knowledge_graph (
    id INT PRIMARY KEY AUTO_INCREMENT,
    entity_name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(50),
    relation_data JSON,
    entity_metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_entity (entity_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Activity logs table
-- =====================================================
CREATE TABLE activity_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(100),
    details JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Sessions table (for Flask session storage)
-- =====================================================
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    data TEXT,
    expiry DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Create Indexes (with IF NOT EXISTS checks)
-- =====================================================

-- Users table indexes
DELIMITER $$
CREATE PROCEDURE CreateIndexIfNotExists(
    IN p_tableName VARCHAR(100),
    IN p_indexName VARCHAR(100),
    IN p_indexDefinition TEXT
)
BEGIN
    DECLARE index_count INT;
    
    SELECT COUNT(*) INTO index_count
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
    AND table_name = p_tableName
    AND index_name = p_indexName;
    
    IF index_count = 0 THEN
        SET @sql = CONCAT('CREATE INDEX ', p_indexName, ' ON ', p_tableName, ' ', p_indexDefinition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- Create indexes using the procedure
CALL CreateIndexIfNotExists('users', 'idx_username', '(username)');
CALL CreateIndexIfNotExists('users', 'idx_email', '(email)');
CALL CreateIndexIfNotExists('users', 'idx_created', '(created_at)');

-- Search history indexes
CALL CreateIndexIfNotExists('search_history', 'idx_user_created', '(user_id, created_at)');
CALL CreateIndexIfNotExists('search_history', 'idx_keyword', '(keyword(100))');
CALL CreateIndexIfNotExists('search_history', 'idx_status', '(status)');
CALL CreateIndexIfNotExists('search_history', 'idx_favorite', '(is_favorite)');
CALL CreateIndexIfNotExists('search_history', 'idx_user_status', '(user_id, status, created_at)');
CALL CreateIndexIfNotExists('search_history', 'idx_search_user_status', '(user_id, status, created_at)');

-- Favorites indexes
CALL CreateIndexIfNotExists('favorites', 'idx_user', '(user_id)');
CALL CreateIndexIfNotExists('favorites', 'idx_created', '(created_at)');

-- Knowledge graph indexes
CALL CreateIndexIfNotExists('knowledge_graph', 'idx_entity_type', '(entity_type)');
CALL CreateIndexIfNotExists('knowledge_graph', 'idx_created', '(created_at)');
CALL CreateIndexIfNotExists('knowledge_graph', 'idx_updated', '(updated_at)');

-- Fulltext indexes (MySQL 5.6+)
ALTER TABLE search_history ADD FULLTEXT INDEX IF NOT EXISTS idx_search (keyword);
ALTER TABLE knowledge_graph ADD FULLTEXT INDEX IF NOT EXISTS idx_entity_search (entity_name);

-- Activity logs indexes
CALL CreateIndexIfNotExists('activity_logs', 'idx_user_activity', '(user_id, created_at)');
CALL CreateIndexIfNotExists('activity_logs', 'idx_action', '(action)');
CALL CreateIndexIfNotExists('activity_logs', 'idx_created', '(created_at)');

-- Sessions indexes
CALL CreateIndexIfNotExists('sessions', 'idx_session', '(session_id)');
CALL CreateIndexIfNotExists('sessions', 'idx_expiry', '(expiry)');

-- Drop the procedure
DROP PROCEDURE IF EXISTS CreateIndexIfNotExists;

-- =====================================================
-- Insert default data
-- =====================================================

-- Insert default admin user (password: admin123)
INSERT IGNORE INTO users (username, email, password_hash, full_name, is_admin, is_active) 
VALUES ('admin', 'admin@tkrag.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPjF2nKmJwXeK', 'Administrator', TRUE, TRUE);

-- Insert test user (password: test123)
INSERT IGNORE INTO users (username, email, password_hash, full_name, is_admin, is_active) 
VALUES ('testuser', 'test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPjF2nKmJwXeK', 'Test User', FALSE, TRUE);

-- Insert sample search history for testing (optional)
INSERT IGNORE INTO search_history (user_id, keyword, results, summary, execution_time, status, created_at)
SELECT 
    u.id,
    'Machine Learning',
    '{"videos": [], "books": [], "papers": []}',
    'Sample knowledge about Machine Learning',
    2.5,
    'completed',
    DATE_SUB(NOW(), INTERVAL 1 DAY)
FROM users u
WHERE u.username = 'testuser'
AND NOT EXISTS (SELECT 1 FROM search_history WHERE keyword = 'Machine Learning' AND user_id = u.id);

INSERT IGNORE INTO search_history (user_id, keyword, results, summary, execution_time, status, created_at)
SELECT 
    u.id,
    'Deep Learning',
    '{"videos": [], "books": [], "papers": []}',
    'Sample knowledge about Deep Learning',
    3.2,
    'completed',
    DATE_SUB(NOW(), INTERVAL 2 DAY)
FROM users u
WHERE u.username = 'testuser'
AND NOT EXISTS (SELECT 1 FROM search_history WHERE keyword = 'Deep Learning' AND user_id = u.id);

-- =====================================================
-- Show results
-- =====================================================
SELECT 'Database setup complete!' as 'Status';
SELECT CONCAT('Database: ', DATABASE()) as 'Database';
SELECT COUNT(*) as 'Tables Created' FROM information_schema.tables WHERE table_schema = DATABASE();

-- Show all tables
SELECT table_name, table_rows 
FROM information_schema.tables 
WHERE table_schema = DATABASE()
ORDER BY table_name;

-- Show users
SELECT id, username, email, full_name, is_admin, created_at 
FROM users;
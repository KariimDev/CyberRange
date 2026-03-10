--
-- PostgreSQL Database Dump
-- Server: prod-db.cyberrange.local:5432
-- Database: customer_data
-- Dumped on: 2026-03-01 02:00:00 UTC (automated nightly backup)
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';

-- ----------------------------
-- Table: users
-- ----------------------------
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    api_key VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO users (username, email, password_hash, role, api_key) VALUES
('admin', 'admin@cyberrange.local', '$2b$12$LJ3m4ys6Gx0Z1qXZa1234OuIS5aMAHnqTVkGpXz.CiQPOcOymqiZy', 'administrator', 'sk-admin-abc123def456'),
('jsmith', 'john.smith@cyberrange.local', '$2b$12$9Xk2VzJqmR7YhW5678901OqKLm3noPqRsTuVwXyZ.AbCdEfGhIjKl', 'developer', 'sk-dev-jsmith-789xyz'),
('mjones', 'mary.jones@cyberrange.local', '$2b$12$Abc123Def456Ghi789Jkl0MnOpQrStUvWxYzAbCdEf.GhIjKlMnOp', 'analyst', NULL),
('service-account', 'svc@cyberrange.local', '$2b$12$SvcAccountHashNotForHumanUseOnly12345678.AbCdEfGhIjKlMnOp', 'service', 'sk-svc-MASTER-key-00000');

-- ----------------------------
-- Table: api_tokens
-- ----------------------------
CREATE TABLE IF NOT EXISTS api_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token VARCHAR(128) NOT NULL,
    scope VARCHAR(50) DEFAULT 'read',
    expires_at TIMESTAMP
);

INSERT INTO api_tokens (user_id, token, scope, expires_at) VALUES
(1, 'token-admin-full-access-xyz789', 'admin', '2027-01-01 00:00:00'),
(4, 'token-svc-internal-api-abc123', 'internal', '2027-01-01 00:00:00');

-- ----------------------------
-- Table: payment_methods
-- ----------------------------
CREATE TABLE IF NOT EXISTS payment_methods (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    card_number VARCHAR(19) NOT NULL,
    expiry VARCHAR(5) NOT NULL,
    cardholder_name VARCHAR(100)
);

INSERT INTO payment_methods (user_id, card_number, expiry, cardholder_name) VALUES
(1, '4111-1111-1111-1111', '12/27', 'Admin User'),
(2, '5500-0000-0000-0004', '06/28', 'John Smith');

-- ----------------------------
-- Table: audit_log
-- ----------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100),
    detail TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO audit_log (user_id, action, detail, ip_address) VALUES
(1, 'LOGIN', 'Admin login from office VPN', '10.0.1.50'),
(1, 'CONFIG_CHANGE', 'Disabled MFA for service-account', '10.0.1.50'),
(4, 'API_CALL', 'GET /api/v1/users — 200', '10.0.2.100'),
(4, 'API_CALL', 'GET /api/v1/payments — 200', '10.0.2.100');

-- End of dump

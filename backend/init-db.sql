-- Initialize Tax Filing Database
-- This script runs automatically when the PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";   -- pgvector: required for RagDocument.embedding

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS tax_data;

-- Set search path
SET search_path TO tax_data, public;

-- Initial grants (more will be added as we create tables)
GRANT USAGE ON SCHEMA tax_data TO taxagent;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tax_data TO taxagent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tax_data TO taxagent;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Tax Filing Database initialized successfully';
END $$;

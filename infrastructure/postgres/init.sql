
-- HECATE PostgreSQL Initialization Script

-- 1. Users & RBAC
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Incidents
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(50) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    root_cause TEXT,
    confidence_score DOUBLE PRECISION,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    recovery_time_seconds INTEGER
);

-- 3. Remediations
CREATE TABLE IF NOT EXISTS remediations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    success BOOLEAN DEFAULT FALSE,
    execution_duration_ms INTEGER DEFAULT 0,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    outcome_summary TEXT
);

-- 4. Policies
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_name VARCHAR(255) UNIQUE NOT NULL,
    condition_expression TEXT NOT NULL,
    action_definition TEXT NOT NULL,
    risk_level VARCHAR(20) DEFAULT 'low',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed some initial mock data
INSERT INTO policies (policy_name, condition_expression, action_definition, risk_level, enabled)
VALUES 
('Auto-restart on OOMKilled', 'incident.rootCause contains "OOMKilled"', 'restart_pod', 'medium', true),
('Scale on high CPU', 'metric.cpu_usage > 85 FOR 5m', 'scale_horizontal(delta=2)', 'low', true)
ON CONFLICT (policy_name) DO NOTHING;

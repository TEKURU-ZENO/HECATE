import os
import sqlite3

import structlog

log = structlog.get_logger()

# Hardcoded absolute path for monorepo-wide consistency
SQLITE_DB_PATH = r"c:\Users\Dev Mehta\Desktop\HECATE\hecate_db.sqlite"

_pg_disabled = False


def get_db_connection():
    global _pg_disabled
    # Attempt PostgreSQL connection
    use_pg = False
    conn = None

    if os.environ.get("HECATE_DB_ENGINE") != "sqlite" and not _pg_disabled:
        pg_host = os.environ.get("POSTGRES_HOST", "localhost")
        pg_port = os.environ.get("POSTGRES_PORT", "5432")
        pg_db = os.environ.get("POSTGRES_DB", "hecate")
        pg_user = os.environ.get("POSTGRES_USER", "hecate")
        pg_password = os.environ.get("POSTGRES_PASSWORD", "changeme")

        try:
            import psycopg2

            conn = psycopg2.connect(
                host=pg_host,
                port=pg_port,
                database=pg_db,
                user=pg_user,
                password=pg_password,
                connect_timeout=1,
            )
            use_pg = True
            log.info("database.connected_to_postgresql", host=pg_host, db=pg_db)
            return conn, use_pg
        except Exception as e:
            _pg_disabled = True
            log.warn(
                "database.postgresql_failed_falling_back_to_sqlite",
                error=str(e),
                path=SQLITE_DB_PATH,
            )

    # SQLite Fallback
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            incident_code TEXT UNIQUE,
            title TEXT,
            severity TEXT,
            status TEXT,
            service_name TEXT,
            root_cause TEXT,
            confidence_score REAL,
            risk_score REAL,
            is_predicted INTEGER DEFAULT 0,
            prediction_confidence REAL DEFAULT 0.0,
            prediction_model TEXT DEFAULT 'none',
            lead_time_seconds INTEGER DEFAULT 0,
            prediction_status TEXT DEFAULT 'NONE',
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            recovery_time_seconds INTEGER
        )
    """)
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN risk_score REAL")
        conn.commit()
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN is_predicted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN prediction_confidence REAL DEFAULT 0.0")
        conn.commit()
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN prediction_model TEXT DEFAULT 'none'")
        conn.commit()
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN lead_time_seconds INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN prediction_status TEXT DEFAULT 'NONE'")
        conn.commit()
    except Exception:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remediations (
            id TEXT PRIMARY KEY,
            incident_id TEXT,
            action_type TEXT,
            status TEXT,
            success BOOLEAN,
            execution_duration_ms INTEGER,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            outcome_summary TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id TEXT PRIMARY KEY,
            policy_name TEXT UNIQUE,
            condition_expression TEXT,
            action_definition TEXT,
            risk_level TEXT,
            enabled BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operational_memory (
            id TEXT PRIMARY KEY,
            incident_id TEXT,
            incident_type TEXT,
            incident_title TEXT,
            root_cause_service TEXT,
            remediation_action TEXT,
            success BOOLEAN,
            recovery_time_seconds INTEGER,
            confidence_score REAL,
            effectiveness_score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id TEXT PRIMARY KEY,
            incident_id TEXT UNIQUE,
            incident_type TEXT,
            root_cause_service TEXT,
            recommended_action TEXT,
            success_probability REAL,
            avg_effectiveness REAL,
            recommendation_score REAL,
            match_tier INTEGER,
            similar_cases_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            incident_id TEXT,
            incident_type TEXT,
            recommended_action TEXT,
            root_cause_service TEXT,
            risk_level TEXT,
            recommendation_score REAL,
            status TEXT DEFAULT 'pending',
            approval_reason TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decided_at TIMESTAMP,
            decided_by TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_outcomes (
            id TEXT PRIMARY KEY,
            incident_id TEXT,
            prediction_confidence REAL,
            lead_time_seconds INTEGER,
            predicted BOOLEAN,
            actually_occurred BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check if seed policies exist
    cursor.execute("SELECT COUNT(*) FROM policies")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO policies (id, policy_name, condition_expression, action_definition, risk_level, enabled)
            VALUES 
            ('pol-001', 'Auto-restart on OOMKilled', 'incident.rootCause contains "OOMKilled"', 'restart_pod', 'medium', 1),
            ('pol-002', 'Scale on high CPU', 'metric.cpu_usage > 90', 'scale_deployment', 'low', 1)
        """)
        conn.commit()

    return conn, use_pg

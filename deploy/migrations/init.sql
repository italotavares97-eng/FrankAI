-- Frank AI OS — Initial Database Schema
-- PostgreSQL 16

-- ─── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── Unit KPIs ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS unit_kpis (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         VARCHAR(20) NOT NULL,
    snapshot_date   DATE NOT NULL,
    revenue         NUMERIC(12,2),
    transactions    INTEGER,
    avg_ticket      NUMERIC(8,2),
    cmv_pct         NUMERIC(5,2),
    ebitda_pct      NUMERIC(5,2),
    rent_pct        NUMERIC(5,2),
    payback_months  NUMERIC(5,1),
    nps_score       NUMERIC(5,2),
    audit_score     NUMERIC(5,2),
    headcount       INTEGER,
    turnover_pct    NUMERIC(5,2),
    extra_data      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(unit_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_unit_kpis_unit_date ON unit_kpis(unit_id, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_unit_kpis_date ON unit_kpis(snapshot_date DESC);

-- ─── Alerts ───────────────────────────────────────────────────────────────────
CREATE TYPE alert_severity AS ENUM ('info', 'warning', 'critical');
CREATE TYPE alert_status   AS ENUM ('open', 'acked', 'resolved');

CREATE TABLE IF NOT EXISTS alerts (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id           VARCHAR(20),
    sector            VARCHAR(50) NOT NULL,
    rule              VARCHAR(100) NOT NULL,
    severity          alert_severity NOT NULL DEFAULT 'warning',
    status            alert_status   NOT NULL DEFAULT 'open',
    title             VARCHAR(200) NOT NULL,
    message           TEXT NOT NULL,
    current_val       NUMERIC(12,4),
    limit_val         NUMERIC(12,4),
    delta_pct         NUMERIC(8,2),
    notified_email    BOOLEAN DEFAULT FALSE,
    notified_whatsapp BOOLEAN DEFAULT FALSE,
    resolved_at       TIMESTAMPTZ,
    resolved_by       VARCHAR(100),
    created_at        TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at        TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON alerts(status, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_unit_id ON alerts(unit_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_rule ON alerts(rule);

-- ─── Agent Memory ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_memory (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name    VARCHAR(100) NOT NULL,
    memory_key    VARCHAR(200) NOT NULL,
    memory_value  TEXT NOT NULL,
    memory_type   VARCHAR(50) DEFAULT 'insight',
    confidence    NUMERIC(4,3) DEFAULT 0.8,
    usage_count   INTEGER DEFAULT 0,
    context       JSONB DEFAULT '{}',
    last_used_at  TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(agent_name, memory_key)
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_memory_confidence ON agent_memory(confidence DESC);

-- ─── Decision Log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decision_log (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name         VARCHAR(100) NOT NULL,
    decision_type      VARCHAR(100) NOT NULL,
    unit_id            VARCHAR(20),
    sector             VARCHAR(50),
    input_summary      TEXT,
    analysis           TEXT,
    recommendation     TEXT,
    verdict            VARCHAR(20) NOT NULL,   -- GO, NO-GO, WAIT, OK, CRITICAL, etc.
    confidence         NUMERIC(4,3) DEFAULT 0.8,
    ceo_rules_checked  JSONB DEFAULT '{}',
    tokens_used        INTEGER DEFAULT 0,
    metadata           JSONB DEFAULT '{}',
    created_at         TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decision_log_agent ON decision_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_decision_log_verdict ON decision_log(verdict);
CREATE INDEX IF NOT EXISTS idx_decision_log_unit ON decision_log(unit_id);
CREATE INDEX IF NOT EXISTS idx_decision_log_created ON decision_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decision_log_sector ON decision_log(sector);

-- ─── Agent Actions ────────────────────────────────────────────────────────────
CREATE TYPE action_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

CREATE TABLE IF NOT EXISTS agent_actions (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type  VARCHAR(100) NOT NULL,
    triggered_by VARCHAR(100) NOT NULL,
    alert_id     UUID REFERENCES alerts(id) ON DELETE SET NULL,
    decision_id  UUID REFERENCES decision_log(id) ON DELETE SET NULL,
    status       action_status NOT NULL DEFAULT 'pending',
    payload      JSONB DEFAULT '{}',
    result       JSONB,
    retry_count  INTEGER DEFAULT 0,
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_actions_status ON agent_actions(status);
CREATE INDEX IF NOT EXISTS idx_agent_actions_type ON agent_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_agent_actions_created ON agent_actions(created_at DESC);

-- ─── Reports ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type   VARCHAR(50) NOT NULL,
    title         VARCHAR(300) NOT NULL,
    html_content  TEXT,
    pdf_content   TEXT,   -- base64 encoded
    pdf_path      VARCHAR(500),
    period_start  DATE,
    period_end    DATE,
    generated_by  VARCHAR(100) DEFAULT 'system',
    raw_data      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);

-- ─── Insight History ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS insight_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name      VARCHAR(100) NOT NULL,
    insight_type    VARCHAR(100) NOT NULL,
    unit_id         VARCHAR(20),
    sector          VARCHAR(50),
    title           VARCHAR(300) NOT NULL,
    description     TEXT NOT NULL,
    impact_score    NUMERIC(4,2) DEFAULT 5.0,
    tags            JSONB DEFAULT '[]',
    supporting_data JSONB DEFAULT '{}',
    acted_upon      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_insight_agent ON insight_history(agent_name);
CREATE INDEX IF NOT EXISTS idx_insight_sector ON insight_history(sector);
CREATE INDEX IF NOT EXISTS idx_insight_impact ON insight_history(impact_score DESC);
CREATE INDEX IF NOT EXISTS idx_insight_created ON insight_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_insight_tags ON insight_history USING GIN(tags);

-- ─── Auto-update updated_at trigger ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ─── Seed: Initial network data ──────────────────────────────────────────────
-- Dados iniciais de KPI para demonstração (serão sobrescritos por dados reais)
INSERT INTO unit_kpis (unit_id, snapshot_date, revenue, transactions, avg_ticket, cmv_pct, ebitda_pct, rent_pct, nps_score, audit_score, headcount)
VALUES
    ('DVR-SP-001', CURRENT_DATE - 1, 89420.00, 612, 46.10, 24.3, 18.7, 8.2, 72.0, 91.5, 8),
    ('DVR-SP-002', CURRENT_DATE - 1, 76150.00, 498, 52.80, 27.1, 14.2, 10.1, 68.0, 87.0, 7),
    ('DVR-SP-003', CURRENT_DATE - 1, 103200.00, 785, 43.30, 23.8, 21.4, 7.8, 78.0, 94.0, 9),
    ('DVR-SP-004', CURRENT_DATE - 1, 58900.00, 401, 61.20, 31.4, 9.8,  11.5, 61.0, 82.5, 6),
    ('DVR-RJ-001', CURRENT_DATE - 1, 94300.00, 631, 55.70, 25.9, 17.3, 9.3, 74.0, 89.0, 8),
    ('DVR-MG-001', CURRENT_DATE - 1, 67800.00, 456, 48.90, 28.7, 13.1, 10.8, 65.0, 85.5, 7),
    ('DVR-RS-001', CURRENT_DATE - 1, 71400.00, 520, 44.60, 26.2, 16.8, 9.6, 70.0, 88.0, 7)
ON CONFLICT (unit_id, snapshot_date) DO NOTHING;

-- Alerta inicial de exemplo
INSERT INTO alerts (unit_id, sector, rule, severity, status, title, message, current_val, limit_val)
VALUES (
    'DVR-SP-004',
    'financial',
    'CEO_CMV_MAX_30PCT',
    'critical',
    'open',
    'CMV acima do limite: DVR-SP-004',
    'CMV de 31.4% supera o limite máximo de 30%. Revisão urgente necessária.',
    31.4,
    30.0
)
ON CONFLICT DO NOTHING;

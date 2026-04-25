-- =============================================================================
-- SCHEMA — Frank AI OS · Davvero Gelato
-- PostgreSQL 16 · UTF-8 · Locale pt_BR
-- =============================================================================
-- Execute via: psql -U frank -d davvero -f schema.sql
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- =============================================================================
-- SCHEMA PRINCIPAL
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS davvero;
SET search_path TO davvero, public;

-- =============================================================================
-- ENUMERAÇÕES
-- =============================================================================

CREATE TYPE unit_status AS ENUM ('ativo', 'inativo', 'em_implantacao', 'suspenso', 'encerrado');
CREATE TYPE unit_format AS ENUM ('quiosque', 'loja_pequena', 'loja_completa', 'dark_kitchen');
CREATE TYPE unit_color  AS ENUM ('verde', 'amarelo', 'laranja', 'vermelho');
CREATE TYPE lead_status AS ENUM ('novo', 'qualificado', 'reuniao', 'proposta', 'contrato', 'inaugurado', 'perdido');
CREATE TYPE director_role AS ENUM ('CFO', 'COO', 'CMO', 'CSO', 'Supply', 'OPEP', 'Legal', 'BI', 'Frank');
CREATE TYPE decision_type AS ENUM ('EXECUTAR', 'NAO_EXECUTAR', 'AGUARDAR', 'ESCALAR');
CREATE TYPE alert_severity AS ENUM ('info', 'atencao', 'alerta', 'critico');

-- =============================================================================
-- 1. FRANQUEADOS
-- =============================================================================

CREATE TABLE franchisees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(200) UNIQUE,
    phone           VARCHAR(20),
    cpf_cnpj        VARCHAR(20) UNIQUE,
    address         TEXT,
    city            VARCHAR(100),
    state           CHAR(2),
    contract_start  DATE,
    contract_end    DATE,
    status          VARCHAR(20) DEFAULT 'ativo',
    royalty_pct     DECIMAL(5,3) DEFAULT 0.070,  -- 7%
    mkt_fund_pct    DECIMAL(5,3) DEFAULT 0.015,  -- 1.5%
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_franchisees_city    ON franchisees(city);
CREATE INDEX idx_franchisees_status  ON franchisees(status);

-- =============================================================================
-- 2. UNIDADES / LOJAS
-- =============================================================================

CREATE TABLE units (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    franchisee_id   UUID REFERENCES franchisees(id),
    code            VARCHAR(20) UNIQUE NOT NULL,    -- ex: DVR-SP-001
    name            VARCHAR(200) NOT NULL,
    format          unit_format DEFAULT 'loja_pequena',
    status          unit_status DEFAULT 'ativo',
    color_status    unit_color DEFAULT 'amarelo',

    -- Localização
    address         TEXT,
    city            VARCHAR(100),
    state           CHAR(2),
    shopping        VARCHAR(200),
    lat             DECIMAL(10,8),
    lng             DECIMAL(11,8),

    -- Financeiro base
    opening_date        DATE,
    initial_investment  DECIMAL(12,2),
    franchise_fee       DECIMAL(12,2),
    monthly_rent        DECIMAL(12,2),
    sqm                 DECIMAL(8,2),          -- metros quadrados

    -- Operacional
    seats               INTEGER,
    team_count          INTEGER,
    manager_name        VARCHAR(200),

    -- Cluster
    cluster             VARCHAR(100),          -- ex: "Interior SP"
    priority            INTEGER DEFAULT 2,     -- 1=P1, 2=P2, 3=P3

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_units_status       ON units(status);
CREATE INDEX idx_units_city         ON units(city);
CREATE INDEX idx_units_franchisee   ON units(franchisee_id);
CREATE INDEX idx_units_cluster      ON units(cluster);

-- =============================================================================
-- 3. FINANCEIRO — DRE MENSAL POR UNIDADE
-- =============================================================================

CREATE TABLE unit_financials (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         UUID REFERENCES units(id) NOT NULL,
    month           DATE NOT NULL,              -- primeiro dia do mês

    -- Receita
    gross_revenue       DECIMAL(12,2) NOT NULL DEFAULT 0,
    taxes_pct           DECIMAL(5,3) DEFAULT 0.060,     -- Simples Nacional ~6%
    taxes_value         DECIMAL(12,2) GENERATED ALWAYS AS (gross_revenue * taxes_pct) STORED,
    net_revenue         DECIMAL(12,2) GENERATED ALWAYS AS (gross_revenue * (1 - taxes_pct)) STORED,

    -- CMV
    cogs_value          DECIMAL(12,2) NOT NULL DEFAULT 0,   -- Custo de Mercadoria
    bonuses_received    DECIMAL(12,2) DEFAULT 0,             -- Bonificações de fornecedor
    net_cogs            DECIMAL(12,2) GENERATED ALWAYS AS (cogs_value - bonuses_received) STORED,
    cmv_pct             DECIMAL(5,3),   -- preenchido via trigger

    -- Despesas Operacionais
    rent                DECIMAL(12,2) DEFAULT 0,
    payroll             DECIMAL(12,2) DEFAULT 0,
    electricity         DECIMAL(12,2) DEFAULT 0,
    packaging           DECIMAL(12,2) DEFAULT 0,
    royalties           DECIMAL(12,2) DEFAULT 0,
    mkt_fund            DECIMAL(12,2) DEFAULT 0,
    maintenance         DECIMAL(12,2) DEFAULT 0,
    other_opex          DECIMAL(12,2) DEFAULT 0,

    -- Resultados calculados
    gross_margin        DECIMAL(12,2),   -- via trigger
    gross_margin_pct    DECIMAL(5,3),
    total_opex          DECIMAL(12,2),
    ebitda_operational  DECIMAL(12,2),
    ebitda_pct          DECIMAL(5,3),

    -- Financiamento (CTO)
    cto_monthly         DECIMAL(12,2) DEFAULT 0,
    depreciation        DECIMAL(12,2) DEFAULT 0,
    ebitda_after_cto    DECIMAL(12,2),

    -- Resultado Final
    income_tax          DECIMAL(12,2) DEFAULT 0,
    net_income          DECIMAL(12,2),
    net_margin_pct      DECIMAL(5,3),

    -- Metadados
    rent_pct            DECIMAL(5,3),       -- aluguel / faturamento bruto
    payroll_pct         DECIMAL(5,3),
    source              VARCHAR(50) DEFAULT 'erp',
    validated           BOOLEAN DEFAULT false,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(unit_id, month)
);

CREATE INDEX idx_unit_financials_unit  ON unit_financials(unit_id);
CREATE INDEX idx_unit_financials_month ON unit_financials(month);
CREATE INDEX idx_unit_financials_cmv   ON unit_financials(cmv_pct);

-- Trigger: Calcula campos derivados automaticamente
CREATE OR REPLACE FUNCTION calculate_financial_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- CMV %
    IF NEW.net_revenue > 0 THEN
        NEW.cmv_pct         := ROUND((NEW.net_cogs / NEW.net_revenue)::numeric, 4);
        NEW.gross_margin    := NEW.net_revenue - NEW.net_cogs;
        NEW.gross_margin_pct:= ROUND(((NEW.net_revenue - NEW.net_cogs) / NEW.net_revenue)::numeric, 4);
    END IF;

    -- Total OPEX
    NEW.total_opex := COALESCE(NEW.rent,0) + COALESCE(NEW.payroll,0) +
                      COALESCE(NEW.electricity,0) + COALESCE(NEW.packaging,0) +
                      COALESCE(NEW.royalties,0) + COALESCE(NEW.mkt_fund,0) +
                      COALESCE(NEW.maintenance,0) + COALESCE(NEW.other_opex,0);

    -- EBITDA Operacional
    NEW.ebitda_operational := NEW.gross_margin - NEW.total_opex;
    IF NEW.net_revenue > 0 THEN
        NEW.ebitda_pct := ROUND((NEW.ebitda_operational / NEW.net_revenue)::numeric, 4);
    END IF;

    -- EBITDA após CTO e depreciação
    NEW.ebitda_after_cto := NEW.ebitda_operational
                          - COALESCE(NEW.cto_monthly,0)
                          - COALESCE(NEW.depreciation,0);

    -- Lucro Líquido
    NEW.net_income := NEW.ebitda_after_cto - COALESCE(NEW.income_tax,0);
    IF NEW.net_revenue > 0 THEN
        NEW.net_margin_pct := ROUND((NEW.net_income / NEW.net_revenue)::numeric, 4);
    END IF;

    -- Percentuais auxiliares
    IF NEW.gross_revenue > 0 THEN
        NEW.rent_pct    := ROUND((COALESCE(NEW.rent,0) / NEW.gross_revenue)::numeric, 4);
        NEW.payroll_pct := ROUND((COALESCE(NEW.payroll,0) / NEW.gross_revenue)::numeric, 4);
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calculate_financials
    BEFORE INSERT OR UPDATE ON unit_financials
    FOR EACH ROW EXECUTE FUNCTION calculate_financial_fields();

-- =============================================================================
-- 4. KPIs OPERACIONAIS DIÁRIOS
-- =============================================================================

CREATE TABLE unit_daily_kpis (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         UUID REFERENCES units(id) NOT NULL,
    date            DATE NOT NULL,

    -- Vendas
    gross_revenue       DECIMAL(10,2) DEFAULT 0,
    transactions        INTEGER DEFAULT 0,
    avg_ticket          DECIMAL(8,2) GENERATED ALWAYS AS (
                            CASE WHEN transactions > 0
                            THEN ROUND((gross_revenue / transactions)::numeric, 2)
                            ELSE 0 END
                        ) STORED,

    -- Operacional
    team_hours          DECIMAL(6,2) DEFAULT 0,
    productivity        DECIMAL(8,2) GENERATED ALWAYS AS (
                            CASE WHEN team_hours > 0
                            THEN ROUND((gross_revenue / team_hours)::numeric, 2)
                            ELSE 0 END
                        ) STORED,
    stockout_count      INTEGER DEFAULT 0,          -- rupturas no dia
    waste_value         DECIMAL(8,2) DEFAULT 0,     -- desperdício em R$

    -- CX
    nps_responses       INTEGER DEFAULT 0,
    nps_score           DECIMAL(5,2),
    complaints          INTEGER DEFAULT 0,
    compliments         INTEGER DEFAULT 0,

    -- Produto
    top_product_1       VARCHAR(100),
    top_product_2       VARCHAR(100),
    top_product_3       VARCHAR(100),

    source              VARCHAR(20) DEFAULT 'pdv',
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(unit_id, date)
);

CREATE INDEX idx_daily_kpis_unit  ON unit_daily_kpis(unit_id);
CREATE INDEX idx_daily_kpis_date  ON unit_daily_kpis(date);

-- =============================================================================
-- 5. SUPPLY CHAIN — FORNECEDORES
-- =============================================================================

CREATE TABLE suppliers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    cnpj            VARCHAR(20) UNIQUE,
    category        VARCHAR(100),       -- leite, frutas, embalagem, etc.
    contact_name    VARCHAR(200),
    contact_email   VARCHAR(200),
    contact_phone   VARCHAR(20),

    -- Avaliação
    score           DECIMAL(5,2) DEFAULT 0,    -- 0-100
    quality_score   DECIMAL(5,2),
    price_score     DECIMAL(5,2),
    delivery_score  DECIMAL(5,2),
    payment_terms   INTEGER,                    -- dias para pagar
    lead_time_days  INTEGER,

    -- Status
    status          VARCHAR(20) DEFAULT 'ativo',    -- ativo, backup, suspenso
    is_strategic    BOOLEAN DEFAULT false,
    is_backup       BOOLEAN DEFAULT false,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 6. SUPPLY CHAIN — PEDIDOS DE COMPRA
-- =============================================================================

CREATE TABLE purchase_orders (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id     UUID REFERENCES suppliers(id) NOT NULL,
    unit_id         UUID REFERENCES units(id),          -- NULL = pedido central
    po_number       VARCHAR(50) UNIQUE,
    status          VARCHAR(20) DEFAULT 'pendente',     -- pendente, confirmado, entregue, cancelado
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_date   DATE,
    delivered_date  DATE,
    total_value     DECIMAL(12,2) DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE purchase_order_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_id           UUID REFERENCES purchase_orders(id) NOT NULL,
    product_name    VARCHAR(200) NOT NULL,
    sku             VARCHAR(50),
    quantity        DECIMAL(10,3),
    unit            VARCHAR(20),            -- kg, L, un
    unit_price      DECIMAL(10,4),
    total_price     DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    delivered_qty   DECIMAL(10,3),
    quality_ok      BOOLEAN DEFAULT true,
    notes           TEXT
);

-- =============================================================================
-- 7. ESTOQUE
-- =============================================================================

CREATE TABLE inventory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         UUID REFERENCES units(id) NOT NULL,
    product_name    VARCHAR(200) NOT NULL,
    sku             VARCHAR(50),
    category        VARCHAR(100),
    current_qty     DECIMAL(10,3) NOT NULL DEFAULT 0,
    unit            VARCHAR(20),
    min_qty         DECIMAL(10,3) DEFAULT 0,    -- estoque mínimo
    reorder_qty     DECIMAL(10,3) DEFAULT 0,    -- quantidade de reposição
    avg_cost        DECIMAL(10,4),              -- custo médio ponderado
    last_updated    TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(unit_id, sku)
);

CREATE INDEX idx_inventory_unit     ON inventory(unit_id);
CREATE INDEX idx_inventory_low      ON inventory(current_qty) WHERE current_qty <= 0;

-- =============================================================================
-- 8. CRM — CLIENTES
-- =============================================================================

CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         UUID REFERENCES units(id),
    name            VARCHAR(200),
    email           VARCHAR(200),
    phone           VARCHAR(20),
    cpf             VARCHAR(14),

    -- Segmentação
    segment         VARCHAR(20) DEFAULT 'novo',     -- vip, recorrente, novo, dormente
    first_visit     DATE,
    last_visit      DATE,
    visit_count     INTEGER DEFAULT 0,
    total_spent     DECIMAL(12,2) DEFAULT 0,
    avg_ticket      DECIMAL(8,2),
    ltv             DECIMAL(12,2),
    nps_score       INTEGER,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_unit     ON customers(unit_id);
CREATE INDEX idx_customers_segment  ON customers(segment);
CREATE INDEX idx_customers_email    ON customers(email);

-- Atualiza segmento automaticamente
CREATE OR REPLACE FUNCTION update_customer_segment()
RETURNS TRIGGER AS $$
BEGIN
    NEW.avg_ticket := CASE WHEN NEW.visit_count > 0
                     THEN ROUND((NEW.total_spent / NEW.visit_count)::numeric, 2)
                     ELSE 0 END;

    NEW.segment := CASE
        WHEN NEW.visit_count >= 8 AND NEW.avg_ticket >= 60   THEN 'vip'
        WHEN NEW.visit_count >= 2 AND NEW.last_visit >= NOW() - INTERVAL '30 days' THEN 'recorrente'
        WHEN NEW.last_visit >= NOW() - INTERVAL '30 days'    THEN 'novo'
        WHEN NEW.last_visit < NOW() - INTERVAL '60 days'     THEN 'dormente'
        ELSE 'novo'
    END;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customer_segment
    BEFORE INSERT OR UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_customer_segment();

-- =============================================================================
-- 9. LEADS B2B — PROSPECÇÃO DE FRANQUEADOS
-- =============================================================================

CREATE TABLE leads_b2b (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    phone           VARCHAR(20),
    city            VARCHAR(100),
    state           CHAR(2),
    target_cluster  VARCHAR(100),

    -- Qualificação
    status          lead_status DEFAULT 'novo',
    available_capital   DECIMAL(12,2),          -- capital disponível para investir
    has_experience      BOOLEAN DEFAULT false,  -- experiência em food
    is_operator         BOOLEAN DEFAULT true,   -- vai operar (vs investidor passivo)
    score               INTEGER DEFAULT 0,      -- 0-100
    source              VARCHAR(100),           -- linkedin, google, indicação, abf
    cac_value           DECIMAL(10,2),          -- custo de aquisição

    -- Acompanhamento
    first_contact   DATE DEFAULT CURRENT_DATE,
    last_contact    DATE,
    next_action     TEXT,
    next_action_date DATE,
    assigned_to     VARCHAR(200),

    -- Resultado
    converted_unit_id UUID REFERENCES units(id),
    lost_reason     TEXT,
    notes           TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_leads_status   ON leads_b2b(status);
CREATE INDEX idx_leads_cluster  ON leads_b2b(target_cluster);

-- =============================================================================
-- 10. FRANK — INTERAÇÕES COM IA
-- =============================================================================

CREATE TABLE frank_interactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      VARCHAR(50) NOT NULL,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    user_name       VARCHAR(100) DEFAULT 'CEO',
    director        director_role,
    question        TEXT NOT NULL,
    response        TEXT,
    decision        decision_type,
    processing_ms   INTEGER,

    -- Validação CEO
    ceo_approved    BOOLEAN DEFAULT true,
    hard_rule_violations JSONB,

    -- Contexto
    units_involved  UUID[],
    kpi_snapshot    JSONB,
    routing_data    JSONB,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_frank_session      ON frank_interactions(session_id);
CREATE INDEX idx_frank_director     ON frank_interactions(director);
CREATE INDEX idx_frank_timestamp    ON frank_interactions(timestamp);

-- =============================================================================
-- 11. FRANK — TAREFAS (MODO EXECUÇÃO via RabbitMQ)
-- =============================================================================

CREATE TABLE frank_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    interaction_id  UUID REFERENCES frank_interactions(id),
    task_type       VARCHAR(100) NOT NULL,      -- report, alert, action, scheduled
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, running, done, failed
    priority        INTEGER DEFAULT 5,          -- 1=urgente, 10=baixa
    payload         JSONB NOT NULL,
    result          JSONB,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    max_retries     INTEGER DEFAULT 3,
    scheduled_for   TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_status       ON frank_tasks(status);
CREATE INDEX idx_tasks_scheduled    ON frank_tasks(scheduled_for) WHERE status = 'pending';
CREATE INDEX idx_tasks_priority     ON frank_tasks(priority, scheduled_for);

-- =============================================================================
-- 12. ALERTAS AUTOMÁTICOS
-- =============================================================================

CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         UUID REFERENCES units(id),
    severity        alert_severity NOT NULL,
    category        VARCHAR(100) NOT NULL,  -- cmv, cashflow, nps, compliance, etc.
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    metric_value    DECIMAL(12,4),
    threshold_value DECIMAL(12,4),
    is_active       BOOLEAN DEFAULT true,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(200),
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_active      ON alerts(is_active, severity) WHERE is_active = true;
CREATE INDEX idx_alerts_unit        ON alerts(unit_id);

-- =============================================================================
-- 13. AUDITORIA DE QUALIDADE (Vistoria)
-- =============================================================================

CREATE TABLE quality_audits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id         UUID REFERENCES units(id) NOT NULL,
    audit_date      DATE NOT NULL,
    auditor_name    VARCHAR(200),
    audit_type      VARCHAR(50) DEFAULT 'presencial',   -- presencial, remoto, surpresa

    -- Scores por área (0-100 cada)
    score_visual        DECIMAL(5,2),   -- 20 pts peso
    score_product       DECIMAL(5,2),   -- 25 pts peso
    score_portioning    DECIMAL(5,2),   -- 15 pts peso
    score_service       DECIMAL(5,2),   -- 20 pts peso
    score_hygiene       DECIMAL(5,2),   -- 10 pts peso
    score_operations    DECIMAL(5,2),   -- 10 pts peso
    total_score         DECIMAL(5,2),   -- calculado via trigger

    -- Resultado
    classification      VARCHAR(20),    -- excelente, bom, regular, critico
    non_conformities    JSONB,
    action_plan         TEXT,
    deadline            DATE,
    followup_date       DATE,
    notes               TEXT,
    photos_urls         TEXT[],

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audits_unit    ON quality_audits(unit_id);
CREATE INDEX idx_audits_date    ON quality_audits(audit_date);

-- Score total calculado automaticamente
CREATE OR REPLACE FUNCTION calculate_audit_score()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_score := ROUND((
        COALESCE(NEW.score_visual,0) * 0.20 +
        COALESCE(NEW.score_product,0) * 0.25 +
        COALESCE(NEW.score_portioning,0) * 0.15 +
        COALESCE(NEW.score_service,0) * 0.20 +
        COALESCE(NEW.score_hygiene,0) * 0.10 +
        COALESCE(NEW.score_operations,0) * 0.10
    )::numeric, 2);

    NEW.classification := CASE
        WHEN NEW.total_score >= 90 THEN 'excelente'
        WHEN NEW.total_score >= 80 THEN 'bom'
        WHEN NEW.total_score >= 70 THEN 'regular'
        ELSE 'critico'
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_score
    BEFORE INSERT OR UPDATE ON quality_audits
    FOR EACH ROW EXECUTE FUNCTION calculate_audit_score();

-- =============================================================================
-- 14. LESSONS — Registro de Aprendizado do Frank
-- =============================================================================

CREATE TABLE frank_lessons (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_desc      TEXT NOT NULL,
    correction      TEXT NOT NULL,
    rule            TEXT NOT NULL,
    example         TEXT,
    director        director_role,
    source_interaction_id UUID REFERENCES frank_interactions(id),
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- VIEWS ANALÍTICAS
-- =============================================================================

-- View: DRE consolidada da rede (último mês)
CREATE OR REPLACE VIEW vw_network_dre_current AS
SELECT
    COUNT(DISTINCT uf.unit_id)          AS total_units,
    SUM(uf.gross_revenue)               AS network_gross_revenue,
    SUM(uf.net_revenue)                 AS network_net_revenue,
    SUM(uf.net_cogs)                    AS network_cogs,
    ROUND(AVG(uf.cmv_pct) * 100, 2)    AS avg_cmv_pct,
    SUM(uf.gross_margin)                AS network_gross_margin,
    ROUND(AVG(uf.gross_margin_pct)*100,2) AS avg_gross_margin_pct,
    SUM(uf.total_opex)                  AS network_total_opex,
    SUM(uf.ebitda_operational)          AS network_ebitda,
    ROUND(AVG(uf.ebitda_pct)*100,2)     AS avg_ebitda_pct,
    SUM(uf.net_income)                  AS network_net_income,
    ROUND(AVG(uf.net_margin_pct)*100,2) AS avg_net_margin_pct,
    DATE_TRUNC('month', MAX(uf.month))  AS reference_month
FROM unit_financials uf
JOIN units u ON u.id = uf.unit_id AND u.status = 'ativo'
WHERE uf.month = DATE_TRUNC('month', NOW() - INTERVAL '1 month');

-- View: Ranking de lojas por CMV
CREATE OR REPLACE VIEW vw_units_cmv_ranking AS
SELECT
    u.id,
    u.code,
    u.name,
    u.city,
    u.format,
    uf.month,
    ROUND(uf.cmv_pct * 100, 2)          AS cmv_pct,
    ROUND(uf.gross_revenue, 2)           AS gross_revenue,
    ROUND(uf.net_margin_pct * 100, 2)   AS net_margin_pct,
    ROUND(uf.rent_pct * 100, 2)         AS rent_pct,
    uf.ebitda_operational               AS ebitda,
    u.color_status,
    CASE
        WHEN uf.cmv_pct > 0.30 THEN '🔴 CRÍTICO'
        WHEN uf.cmv_pct > 0.28 THEN '🟠 ALERTA'
        WHEN uf.cmv_pct > 0.27 THEN '🟡 ATENÇÃO'
        ELSE '🟢 OK'
    END AS cmv_status
FROM unit_financials uf
JOIN units u ON u.id = uf.unit_id
WHERE uf.month = DATE_TRUNC('month', NOW() - INTERVAL '1 month')
ORDER BY uf.cmv_pct DESC;

-- View: Dashboard executivo (Frank Command Center)
CREATE OR REPLACE VIEW vw_executive_dashboard AS
SELECT
    -- Financeiro
    (SELECT SUM(gross_revenue) FROM unit_financials
     WHERE month = DATE_TRUNC('month', NOW()-INTERVAL '1 month'))  AS monthly_revenue,
    (SELECT ROUND(AVG(cmv_pct)*100,2) FROM unit_financials
     WHERE month = DATE_TRUNC('month', NOW()-INTERVAL '1 month'))  AS avg_cmv,
    (SELECT SUM(royalties) FROM unit_financials
     WHERE month = DATE_TRUNC('month', NOW()-INTERVAL '1 month'))  AS monthly_royalties,
    -- Operacional
    (SELECT COUNT(*) FROM units WHERE status='ativo')              AS active_units,
    (SELECT ROUND(AVG(avg_ticket),2) FROM unit_daily_kpis
     WHERE date >= NOW()-INTERVAL '30 days')                       AS avg_ticket_30d,
    (SELECT ROUND(AVG(nps_score),1) FROM unit_daily_kpis
     WHERE date >= NOW()-INTERVAL '30 days'
     AND nps_score IS NOT NULL)                                    AS avg_nps,
    -- Alertas
    (SELECT COUNT(*) FROM alerts WHERE is_active=true
     AND severity='critico')                                       AS critical_alerts,
    (SELECT COUNT(*) FROM frank_tasks WHERE status='pending')      AS pending_tasks;

-- View: Leads B2B por funil
CREATE OR REPLACE VIEW vw_leads_funnel AS
SELECT
    status,
    COUNT(*)                            AS total,
    ROUND(AVG(available_capital),0)     AS avg_capital,
    COUNT(*) FILTER (WHERE is_operator) AS operators,
    COUNT(*) FILTER (WHERE has_experience) AS with_experience
FROM leads_b2b
GROUP BY status
ORDER BY ARRAY_POSITION(
    ARRAY['novo','qualificado','reuniao','proposta','contrato','inaugurado','perdido']::text[],
    status::text
);

-- =============================================================================
-- FUNÇÕES UTILITÁRIAS
-- =============================================================================

-- Calcula payback de uma unidade
CREATE OR REPLACE FUNCTION fn_unit_payback(p_unit_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_investment    DECIMAL;
    v_avg_income    DECIMAL;
BEGIN
    SELECT initial_investment INTO v_investment FROM units WHERE id = p_unit_id;

    SELECT AVG(net_income) INTO v_avg_income
    FROM unit_financials
    WHERE unit_id = p_unit_id
    AND month >= NOW() - INTERVAL '6 months';

    IF v_avg_income <= 0 THEN RETURN 9999; END IF;
    RETURN ROUND((v_investment / v_avg_income)::numeric, 1);
END;
$$ LANGUAGE plpgsql;

-- Calcula ROI 24 meses de uma unidade
CREATE OR REPLACE FUNCTION fn_unit_roi_24m(p_unit_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_investment    DECIMAL;
    v_avg_income    DECIMAL;
BEGIN
    SELECT initial_investment INTO v_investment FROM units WHERE id = p_unit_id;
    SELECT AVG(net_income) INTO v_avg_income
    FROM unit_financials
    WHERE unit_id = p_unit_id
    AND month >= NOW() - INTERVAL '3 months';

    IF v_investment <= 0 THEN RETURN 0; END IF;
    RETURN ROUND(((v_avg_income * 24) / v_investment)::numeric, 2);
END;
$$ LANGUAGE plpgsql;

-- Gera alerta automático para CMV crítico
CREATE OR REPLACE FUNCTION fn_check_cmv_alerts()
RETURNS void AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN
        SELECT uf.unit_id, u.name, uf.cmv_pct, uf.month
        FROM unit_financials uf
        JOIN units u ON u.id = uf.unit_id
        WHERE uf.month = DATE_TRUNC('month', NOW()-INTERVAL '1 month')
        AND uf.cmv_pct > 0.28
        AND NOT EXISTS (
            SELECT 1 FROM alerts
            WHERE unit_id = uf.unit_id
            AND category = 'cmv'
            AND is_active = true
        )
    LOOP
        INSERT INTO alerts (unit_id, severity, category, title, description, metric_value, threshold_value)
        VALUES (
            rec.unit_id,
            CASE WHEN rec.cmv_pct > 0.30 THEN 'critico' ELSE 'alerta' END,
            'cmv',
            'CMV acima do limite — ' || rec.name,
            'CMV de ' || ROUND(rec.cmv_pct*100,1) || '% em ' || TO_CHAR(rec.month,'MM/YYYY'),
            rec.cmv_pct,
            0.28
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- GRANT DE PERMISSÕES
-- =============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA davvero TO frank;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA davvero TO frank;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA davvero TO frank;

-- =============================================================================
-- COMENTÁRIOS DE DOCUMENTAÇÃO
-- =============================================================================

COMMENT ON TABLE units               IS 'Unidades da rede Davvero Gelato (lojas e quiosques)';
COMMENT ON TABLE unit_financials     IS 'DRE mensal por unidade — calculada automaticamente via trigger';
COMMENT ON TABLE unit_daily_kpis     IS 'KPIs operacionais diários por loja';
COMMENT ON TABLE frank_interactions  IS 'Histórico de interações com Frank AI OS';
COMMENT ON TABLE frank_tasks         IS 'Fila de tarefas assíncronas — MODO EXECUÇÃO';
COMMENT ON TABLE alerts              IS 'Alertas automáticos — CMV, NPS, compliance, etc.';
COMMENT ON TABLE quality_audits      IS 'Vistorias de qualidade — checklist Parece Davvero?';
COMMENT ON TABLE frank_lessons       IS 'Lições aprendidas pelo Frank para autoaperfeiçoamento';

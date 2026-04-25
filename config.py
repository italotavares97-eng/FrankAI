# =============================================================================
# CONFIG.PY — Frank AI OS · Davvero Gelato
# Todas as constantes, variáveis de ambiente e regras de negócio
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# INFRAESTRUTURA
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
POSTGRES_URL      = os.getenv("POSTGRES_URL", "postgresql://frank:frank@localhost:5432/davvero")
REDIS_URL         = os.getenv("REDIS_URL", "redis://localhost:6379")
RABBITMQ_URL      = os.getenv("RABBITMQ_URL", "amqp://frank:frank@localhost:5672/davvero")
ENV               = os.getenv("ENV", "development")
LOG_LEVEL         = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS      = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# ---------------------------------------------------------------------------
# MODELOS CLAUDE
# ---------------------------------------------------------------------------

MODEL_MASTER    = "claude-opus-4-5"        # Frank Master + Directors
MODEL_AGENT     = "claude-sonnet-4-5"      # Agentes especializados
MODEL_FAST      = "claude-haiku-4-5"       # Roteamento, classificações rápidas

# ---------------------------------------------------------------------------
# IDENTIDADE DA MARCA
# ---------------------------------------------------------------------------

BRAND = {
    "name":         "Davvero Gelato",
    "segment":      "Gelato Premium Artesanal",
    "headquarters": "São Paulo, SP",
    "founded":      2017,
    "description":  (
        "Rede brasileira de gelato premium com foco em ingredientes naturais, "
        "identidade italiana autêntica e experiência de marca premium em shoppings e rua."
    ),
    "formats": ["quiosque", "loja_pequena", "loja_completa", "dark_kitchen"],
}

# ---------------------------------------------------------------------------
# REGRAS INVIOLÁVEIS DO CEO (Hard Rules)
# Qualquer proposta que viole estas regras é automaticamente REPROVADA
# ---------------------------------------------------------------------------

CEO_HARD_RULES = {
    "cmv_max_pct":          30.0,   # CMV máximo permitido (%)
    "payback_max_months":   30,     # Payback máximo para nova unidade (meses)
    "roi_min_multiplier":   1.5,    # ROI mínimo em 24 meses (multiplicador)
    "max_rent_pct":         12.0,   # Aluguel máximo sobre faturamento bruto (%)
    "min_ebitda_pct":       10.0,   # EBITDA mínimo sobre receita líquida (%)
    "min_gross_margin_pct": 68.0,   # Margem bruta mínima (%)
    "max_payroll_pct":      25.0,   # Folha máxima sobre faturamento (%)
}

# ---------------------------------------------------------------------------
# METAS OPERACIONAIS (Targets)
# ---------------------------------------------------------------------------

OPERATIONAL_TARGETS = {
    # Financeiro
    "cmv_target_pct":       26.5,   # Meta de CMV (%)
    "cmv_alert_pct":        28.0,   # Nível de alerta CMV
    "cmv_critical_pct":     30.0,   # Nível crítico CMV
    "gross_margin_target":  73.5,   # Meta margem bruta (%)
    "ebitda_target_pct":    18.0,   # Meta EBITDA (%)
    "net_margin_target":    12.0,   # Meta margem líquida (%)

    # Operacional
    "avg_ticket_target":    35.0,   # Ticket médio meta (R$)
    "avg_ticket_min":       30.0,   # Ticket médio mínimo (R$)
    "productivity_target":  150.0,  # Produtividade R$/hora
    "stockout_max_day":     2,      # Máximo de rupturas por dia

    # CX
    "nps_target":           70,     # NPS meta
    "nps_alert":            55,     # NPS alerta
    "nps_critical":         40,     # NPS crítico
    "audit_score_min":      80,     # Score mínimo de auditoria

    # Expansão
    "payback_target_months": 24,    # Payback ideal (meses)
    "payback_max_months":    30,    # Payback máximo (meses)
    "roi_min_24m":           1.5,   # ROI mínimo em 24 meses

    # Supply
    "max_supplier_lead_days":   5,  # Lead time máximo fornecedor (dias)
    "inventory_cover_days":    15,  # Cobertura de estoque (dias)

    # Royalties & Taxas
    "royalty_pct":          8.5,
    "mkt_fund_pct":         1.5,
    "taxes_pct":            6.0,    # Simples Nacional estimado
}

# ---------------------------------------------------------------------------
# THRESHOLDS DE ALERTA
# ---------------------------------------------------------------------------

ALERT_THRESHOLDS = {
    "cmv_alert":            0.28,
    "cmv_critical":         0.30,
    "ticket_below_target":  30.0,
    "nps_alert":            55,
    "nps_critical":         40,
    "audit_critical":       70,
    "payback_alert":        28,
    "payback_critical":     32,
    "stockout_critical":    5,
    "cashflow_days_min":    30,     # Cobertura mínima de caixa (dias)
}

# ---------------------------------------------------------------------------
# INTEGRATIONS CONFIG
# ---------------------------------------------------------------------------

SMTP_HOST       = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER       = os.getenv("SMTP_USER", "")
SMTP_PASS       = os.getenv("SMTP_PASS", "")
SMTP_FROM       = os.getenv("SMTP_FROM", "frank@davverogelato.com.br")

WHATSAPP_TOKEN      = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID   = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY     = os.getenv("WHATSAPP_VERIFY_TOKEN", "davvero_frank_2026")

META_ADS_TOKEN      = os.getenv("META_ADS_TOKEN", "")
META_ADS_ACCOUNT_ID = os.getenv("META_ADS_ACCOUNT_ID", "")

LINKEDIN_TOKEN      = os.getenv("LINKEDIN_TOKEN", "")
LINKEDIN_ORG_ID     = os.getenv("LINKEDIN_ORG_ID", "")

ERP_SULTS_URL       = os.getenv("ERP_SULTS_URL", "https://api.sults.com.br/v1")
ERP_SULTS_TOKEN     = os.getenv("ERP_SULTS_TOKEN", "")
ERP_LINX_URL        = os.getenv("ERP_LINX_URL", "")
ERP_LINX_TOKEN      = os.getenv("ERP_LINX_TOKEN", "")

SHEETS_CREDENTIALS  = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
SHEETS_DRE_ID       = os.getenv("SHEETS_DRE_ID", "")
SHEETS_KPI_ID       = os.getenv("SHEETS_KPI_ID", "")

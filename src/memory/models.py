"""Frank AI OS — Modelos de banco de dados: memória, decisões, alertas, KPIs."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, Enum as SAEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ──────────────────────────────────────────────────
class AlertSeverity(str, enum.Enum):
    critical = "critical"
    warning  = "warning"
    info     = "info"

class AlertStatus(str, enum.Enum):
    open     = "open"
    acked    = "acked"
    resolved = "resolved"

class ActionStatus(str, enum.Enum):
    pending   = "pending"
    running   = "running"
    success   = "success"
    failed    = "failed"
    skipped   = "skipped"

class ReportType(str, enum.Enum):
    daily    = "daily"
    weekly   = "weekly"
    monthly  = "monthly"
    adhoc    = "adhoc"


# ─── Unit KPIs (snapshots diários) ──────────────────────────
class UnitKPI(Base):
    __tablename__ = "unit_kpis"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    unit_id     = Column(String(20), nullable=False, index=True)
    date        = Column(DateTime, nullable=False, index=True)

    # Financeiro
    revenue     = Column(Float, default=0.0)
    cmv_pct     = Column(Float, default=0.0)
    gross_margin= Column(Float, default=0.0)
    ebitda_pct  = Column(Float, default=0.0)
    rent_pct    = Column(Float, default=0.0)

    # Operacional
    transactions= Column(Integer, default=0)
    avg_ticket  = Column(Float, default=0.0)
    nps_score   = Column(Float, default=0.0)
    audit_score = Column(Float, default=0.0)

    # Metadata
    raw_data    = Column(JSON, default={})
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_unit_kpis_unit_date", "unit_id", "date"),
    )


# ─── Alertas ────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    unit_id     = Column(String(20), nullable=True, index=True)
    sector      = Column(String(50), nullable=False)
    rule        = Column(String(100), nullable=False)
    severity    = Column(SAEnum(AlertSeverity), default=AlertSeverity.warning, index=True)
    status      = Column(SAEnum(AlertStatus), default=AlertStatus.open, index=True)

    title       = Column(String(255), nullable=False)
    message     = Column(Text, nullable=False)
    current_val = Column(Float, nullable=True)
    limit_val   = Column(Float, nullable=True)
    delta_pct   = Column(Float, nullable=True)

    notified_email    = Column(Boolean, default=False)
    notified_whatsapp = Column(Boolean, default=False)

    created_at  = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)

    actions     = relationship("AgentAction", back_populates="alert")


# ─── Memória dos Agentes ────────────────────────────────────
class AgentMemory(Base):
    __tablename__ = "agent_memory"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agent_name  = Column(String(100), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False)   # decision, insight, pattern, error
    key         = Column(String(255), nullable=False)
    value       = Column(JSON, nullable=False)
    confidence  = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    last_used   = Column(DateTime, nullable=True)
    expires_at  = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_memory_agent_key", "agent_name", "key"),
    )


# ─── Log de Decisões ────────────────────────────────────────
class DecisionLog(Base):
    __tablename__ = "decisions_log"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agent_name   = Column(String(100), nullable=False, index=True)
    sector       = Column(String(50), nullable=False)
    unit_id      = Column(String(20), nullable=True)
    decision_type= Column(String(100), nullable=False)

    context      = Column(JSON, default={})
    analysis     = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    verdict      = Column(String(20), nullable=True)   # GO, NO-GO, WAIT

    ceo_rules_checked = Column(JSON, default={})
    ceo_rules_violated = Column(JSON, default=[])

    outcome      = Column(String(20), nullable=True)   # success, failure, pending
    outcome_note = Column(Text, nullable=True)
    tokens_used  = Column(Integer, default=0)
    latency_ms   = Column(Integer, default=0)

    created_at   = Column(DateTime, default=datetime.utcnow, index=True)


# ─── Ações dos Agentes ──────────────────────────────────────
class AgentAction(Base):
    __tablename__ = "agent_actions"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    alert_id     = Column(UUID(as_uuid=False), ForeignKey("alerts.id"), nullable=True)
    agent_name   = Column(String(100), nullable=False, index=True)
    action_type  = Column(String(100), nullable=False)  # send_email, send_whatsapp, etc.
    status       = Column(SAEnum(ActionStatus), default=ActionStatus.pending, index=True)

    payload      = Column(JSON, default={})
    result       = Column(JSON, default={})
    error_msg    = Column(Text, nullable=True)
    retry_count  = Column(Integer, default=0)

    scheduled_at = Column(DateTime, nullable=True)
    started_at   = Column(DateTime, nullable=True)
    finished_at  = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, index=True)

    alert        = relationship("Alert", back_populates="actions")


# ─── Relatórios ─────────────────────────────────────────────
class Report(Base):
    __tablename__ = "reports"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    report_type  = Column(SAEnum(ReportType), nullable=False, index=True)
    title        = Column(String(255), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end   = Column(DateTime, nullable=False)

    content      = Column(JSON, default={})        # structured data
    html_content = Column(Text, nullable=True)     # HTML artifact
    pdf_path     = Column(String(500), nullable=True)

    generated_by = Column(String(100), default="frank-master")
    tokens_used  = Column(Integer, default=0)

    created_at   = Column(DateTime, default=datetime.utcnow, index=True)


# ─── Insights Histórico ─────────────────────────────────────
class InsightHistory(Base):
    __tablename__ = "insights_history"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agent_name   = Column(String(100), nullable=False, index=True)
    sector       = Column(String(50), nullable=False)
    unit_id      = Column(String(20), nullable=True)
    insight_type = Column(String(100), nullable=False)

    title        = Column(String(255), nullable=False)
    body         = Column(Text, nullable=False)
    impact_score = Column(Float, default=0.0)   # 0-100
    tags         = Column(JSON, default=[])

    acted_upon   = Column(Boolean, default=False)
    outcome      = Column(String(20), nullable=True)

    created_at   = Column(DateTime, default=datetime.utcnow, index=True)

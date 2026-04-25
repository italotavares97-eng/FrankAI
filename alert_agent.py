# =============================================================================
# ALERT_AGENT.PY — Frank AI OS · BI Sector
# Agente de Alertas Automáticos e Monitoramento Proativo
# =============================================================================

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional
from core.base_agent import BaseAgent
from config import MODEL_AGENT, ALERT_THRESHOLDS, OPERATIONAL_TARGETS

logger = logging.getLogger("frank.alert_agent")


class AlertAgent(BaseAgent):
    AGENT_NAME = "Alert Agent"
    AGENT_ROLE = "Especialista em Monitoramento e Alertas Proativos"
    DIRECTOR   = "BI"
    MODEL      = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o Agente de Alertas do Frank AI OS — Davvero Gelato.

MISSÃO:
Detectar proativamente desvios, anomalias e riscos na rede Davvero —
antes que se tornem crises. Gerar alertas acionáveis com prioridade clara.

NÍVEIS DE ALERTA:
🔴 CRÍTICO   — Ação imediata (CMV > 30%, NPS < 40, Auditoria < 70)
🟠 ALERTA    — Ação em 24h (CMV 28-30%, NPS 40-55, Ticket < R$28)
🟡 ATENÇÃO   — Monitorar (CMV 27-28%, NPS 55-65, tendência negativa)
🔵 INFO      — Informativo (dados para decisão)

THRESHOLDS:
• CMV > 28% → ALERTA | > 30% → CRÍTICO
• NPS < 55 → ALERTA | < 40 → CRÍTICO
• Score auditoria < 70 → CRÍTICO | < 80 → ALERTA
• Ticket < R$30 → ALERTA
• Ruptura > 5 itens/dia → ALERTA
• Cash flow < 30 dias cobertura → CRÍTICO
• Contrato vencendo < 30 dias → CRÍTICO

FORMATO DE ALERTA:
[NÍVEL] Unidade | Métrica | Valor atual vs. Threshold | Ação recomendada
"""

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        # Alertas ativos no banco
        active_alerts = await self.db_fetch("""
            SELECT a.severity, a.category, a.title, a.description,
                   u.name AS unit_name, u.code AS unit_code,
                   a.metric_value, a.threshold_value,
                   a.created_at
            FROM alerts a
            LEFT JOIN units u ON u.id = a.unit_id
            WHERE a.is_active = true
            ORDER BY
                CASE a.severity
                    WHEN 'critico'  THEN 1
                    WHEN 'alerta'   THEN 2
                    WHEN 'atencao'  THEN 3
                    ELSE 4
                END,
                a.created_at DESC
            LIMIT 30
        """)

        # Checa novos alertas automaticamente
        new_alerts = await self.check_and_generate_alerts()

        kpi_str     = self.format_kpi_context(kpi_context)
        active_str  = self.format_db_data(active_alerts, "Alertas Ativos")
        new_str     = f"\n🆕 NOVOS ALERTAS GERADOS AGORA: {len(new_alerts)}" if new_alerts else ""

        critical_count = sum(1 for a in active_alerts if a.get("severity") == "critico")
        alert_count    = sum(1 for a in active_alerts if a.get("severity") == "alerta")

        summary = (
            f"\n📊 RESUMO: {critical_count} críticos | {alert_count} alertas | "
            f"{len(active_alerts)} total ativos\n"
        )

        prompt = (
            f"{kpi_str}\n{summary}{active_str}{new_str}\n\n"
            f"Pergunta de {user}: {question}\n\n"
            "Priorize alertas por severidade, identifique padrões e gere plano de ação imediato."
        )
        return await self.call_claude(prompt)

    async def check_and_generate_alerts(self) -> List[Dict]:
        """
        Verifica thresholds em toda a rede e gera novos alertas automaticamente.
        Chamado proativamente pelo scheduler ou trigger manual.
        """
        new_alerts = []

        # 1. CMV crítico
        cmv_critical = await self.db_fetch("""
            SELECT uf.unit_id, u.name, u.code,
                   ROUND(uf.cmv_pct*100, 2) AS cmv_pct, uf.month
            FROM unit_financials uf
            JOIN units u ON u.id = uf.unit_id
            WHERE uf.month = DATE_TRUNC('month', NOW()-INTERVAL '1 month')
              AND uf.cmv_pct > $1
              AND NOT EXISTS (
                  SELECT 1 FROM alerts
                  WHERE unit_id = uf.unit_id AND category = 'cmv' AND is_active = true
              )
        """, ALERT_THRESHOLDS["cmv_alert"])

        for row in cmv_critical:
            severity = "critico" if row["cmv_pct"] > ALERT_THRESHOLDS["cmv_critical"] * 100 else "alerta"
            await self.db_execute("""
                INSERT INTO alerts (unit_id, severity, category, title, description, metric_value, threshold_value)
                VALUES ($1, $2, 'cmv', $3, $4, $5, $6)
            """,
                row["unit_id"], severity,
                f"CMV {severity.upper()} — {row['name']}",
                f"CMV de {row['cmv_pct']}% em {row['month']} — threshold: {ALERT_THRESHOLDS['cmv_alert']*100}%",
                row["cmv_pct"] / 100,
                ALERT_THRESHOLDS["cmv_alert"],
            )
            new_alerts.append({"unit": row["name"], "type": "cmv", "severity": severity})
            logger.info(f"[ALERT] CMV {severity} gerado para {row['name']}: {row['cmv_pct']}%")

        # 2. NPS crítico (últimos 7 dias)
        nps_critical = await self.db_fetch("""
            SELECT dk.unit_id, u.name, u.code,
                   ROUND(AVG(dk.nps_score)::numeric, 1) AS avg_nps
            FROM unit_daily_kpis dk
            JOIN units u ON u.id = dk.unit_id
            WHERE dk.date >= NOW()-INTERVAL '7 days'
              AND dk.nps_score IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM alerts
                  WHERE unit_id = dk.unit_id AND category = 'nps' AND is_active = true
              )
            GROUP BY dk.unit_id, u.name, u.code
            HAVING AVG(dk.nps_score) < $1
        """, ALERT_THRESHOLDS["nps_alert"])

        for row in nps_critical:
            severity = "critico" if row["avg_nps"] < ALERT_THRESHOLDS["nps_critical"] else "alerta"
            await self.db_execute("""
                INSERT INTO alerts (unit_id, severity, category, title, description, metric_value, threshold_value)
                VALUES ($1, $2, 'nps', $3, $4, $5, $6)
            """,
                row["unit_id"], severity,
                f"NPS {severity.upper()} — {row['name']}",
                f"NPS médio de {row['avg_nps']} (últimos 7 dias) — threshold: {ALERT_THRESHOLDS['nps_alert']}",
                float(row["avg_nps"]),
                float(ALERT_THRESHOLDS["nps_alert"]),
            )
            new_alerts.append({"unit": row["name"], "type": "nps", "severity": severity})

        # 3. Auditoria crítica
        audit_critical = await self.db_fetch("""
            SELECT qa.unit_id, u.name, qa.total_score, qa.classification, qa.audit_date
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE qa.audit_date >= NOW()-INTERVAL '30 days'
              AND qa.total_score < $1
              AND NOT EXISTS (
                  SELECT 1 FROM alerts
                  WHERE unit_id = qa.unit_id AND category = 'auditoria' AND is_active = true
              )
        """, ALERT_THRESHOLDS["audit_critical"])

        for row in audit_critical:
            await self.db_execute("""
                INSERT INTO alerts (unit_id, severity, category, title, description, metric_value, threshold_value)
                VALUES ($1, 'critico', 'auditoria', $2, $3, $4, $5)
            """,
                row["unit_id"],
                f"Auditoria CRÍTICA — {row['name']}",
                f"Score de auditoria {row['total_score']} pts em {row['audit_date']}",
                float(row["total_score"]),
                float(ALERT_THRESHOLDS["audit_critical"]),
            )
            new_alerts.append({"unit": row["name"], "type": "auditoria", "severity": "critico"})

        return new_alerts

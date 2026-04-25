"""Frank AI OS — Definições de tarefas Celery (daily, weekly, monthly)."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def _run_async(coro):
    """Executa coroutine num event loop novo (contexto Celery worker)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Core CEO Tasks ────────────────────────────────────────────────────────────

@shared_task(
    name="app.tasks.task_definitions.run_morning_briefing",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    time_limit=600,
    soft_time_limit=540,
)
def run_morning_briefing(self) -> Dict[str, Any]:
    """Gera o briefing matinal completo e envia via Email + WhatsApp."""
    logger.info("Starting morning briefing task")

    async def _execute():
        from app.agents.ceo_agent import CEOAgent
        from app.agents.base_agent import AgentContext
        from app.services.report_service import report_service
        from app.connectors.email_connector import email_connector
        from app.connectors.whatsapp_connector import whatsapp_connector
        from app.core.config import settings

        ceo = CEOAgent()
        ctx = AgentContext(period="today", metadata={"task": "morning_briefing"})

        try:
            result = await ceo.morning_briefing()

            # Gerar e salvar relatório HTML
            report = await report_service.generate_and_save_morning_briefing(result)

            # Enviar email
            await email_connector.send_daily_briefing(
                result.get("executive_report", "Sem relatório disponível.")
            )

            # Enviar WhatsApp
            summary = result.get("executive_report", "")[:800]
            await whatsapp_connector.send_morning_briefing(summary)

            logger.info("Morning briefing completed", report_id=report.id)
            return {
                "status": "success",
                "report_id": report.id,
                "alerts_count": len(result.get("all_alerts", [])),
                "sectors_analyzed": len(result.get("sector_results", {})),
            }

        except Exception as exc:
            logger.error(f"Morning briefing failed: {exc}")
            raise self.retry(exc=exc)

    return _run_async(_execute())


@shared_task(
    name="app.tasks.task_definitions.run_ceo_analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    time_limit=480,
    soft_time_limit=420,
)
def run_ceo_analysis(self) -> Dict[str, Any]:
    """Análise CEO completa (tarde/noite)."""
    logger.info("Starting CEO evening analysis")

    async def _execute():
        from app.agents.ceo_agent import CEOAgent
        from app.agents.base_agent import AgentContext
        from app.services.alert_service import alert_service

        ceo = CEOAgent()
        ctx = AgentContext(period="today")

        try:
            result = await ceo.analyze(ctx)

            # Criar alertas para violações encontradas
            all_alerts = result.get("all_alerts", [])
            if all_alerts:
                await alert_service.bulk_create_from_analysis(
                    sector="ceo_orchestrator",
                    violations=all_alerts,
                )

            return {
                "status": "success",
                "violations": len(all_alerts),
                "sectors_ok": len(result.get("sector_results", {})),
            }

        except Exception as exc:
            logger.error(f"CEO analysis failed: {exc}")
            raise self.retry(exc=exc)

    return _run_async(_execute())


@shared_task(
    name="app.tasks.task_definitions.run_weekly_report",
    bind=True,
    max_retries=2,
    time_limit=900,
    soft_time_limit=840,
)
def run_weekly_report(self) -> Dict[str, Any]:
    """Gera DRE semanal e envia relatório."""
    logger.info("Starting weekly DRE report")

    async def _execute():
        from app.agents.ceo_agent import CEOAgent
        from app.agents.base_agent import AgentContext
        from app.services.report_service import report_service
        from app.connectors.email_connector import email_connector
        from app.connectors.whatsapp_connector import whatsapp_connector

        ceo = CEOAgent()
        ctx = AgentContext(period="last_7d")

        try:
            result = await ceo.weekly_report()
            report = await report_service.generate_and_save_weekly_report(result)

            # Email com relatório
            html = report_service.build_weekly_dre_html(result)
            await email_connector.send(
                to=[__import__("app.core.config", fromlist=["settings"]).settings.alert_email],
                subject=f"📊 Frank AI OS — DRE Semanal {datetime.utcnow().strftime('%d/%m/%Y')}",
                body_html=html,
            )

            # WhatsApp link
            report_url = f"/reports/{report.id}"
            await whatsapp_connector.send_weekly_report_link(report_url)

            return {"status": "success", "report_id": report.id}

        except Exception as exc:
            logger.error(f"Weekly report failed: {exc}")
            raise self.retry(exc=exc)

    return _run_async(_execute())


@shared_task(
    name="app.tasks.task_definitions.run_monthly_report",
    bind=True,
    max_retries=2,
    time_limit=1200,
    soft_time_limit=1140,
)
def run_monthly_report(self) -> Dict[str, Any]:
    """Gera relatório mensal consolidado."""
    logger.info("Starting monthly report")

    async def _execute():
        from app.agents.ceo_agent import CEOAgent
        from app.agents.base_agent import AgentContext
        from app.services.report_service import report_service
        from app.connectors.email_connector import email_connector

        ceo = CEOAgent()
        ctx = AgentContext(period="last_30d")

        try:
            result = await ceo.monthly_report()
            report = await report_service.generate_and_save_monthly_report(result)

            html = report_service.build_monthly_html(result)
            dt = datetime.utcnow()
            await email_connector.send(
                to=[__import__("app.core.config", fromlist=["settings"]).settings.alert_email],
                subject=f"📋 Frank AI OS — Relatório Mensal {dt.strftime('%B %Y')}",
                body_html=html,
            )

            return {"status": "success", "report_id": report.id}

        except Exception as exc:
            logger.error(f"Monthly report failed: {exc}")
            raise self.retry(exc=exc)

    return _run_async(_execute())


# ─── Alert & Notification Tasks ────────────────────────────────────────────────

@shared_task(
    name="app.tasks.task_definitions.run_alert_notifications",
    bind=True,
    max_retries=3,
    time_limit=120,
)
def run_alert_notifications(self) -> Dict[str, Any]:
    """Processa alertas não notificados e envia via Email/WhatsApp."""
    logger.info("Processing pending alert notifications")

    async def _execute():
        from app.services.alert_service import alert_service
        from app.connectors.email_connector import email_connector
        from app.connectors.whatsapp_connector import whatsapp_connector
        from app.memory.models import Alert, AlertStatus
        from app.core.database import get_db_context
        from sqlalchemy import select, and_

        notified = 0
        async with get_db_context() as db:
            result = await db.execute(
                select(Alert).where(
                    Alert.status == AlertStatus.open,
                    Alert.notified_email == False,
                ).limit(20)
            )
            alerts = result.scalars().all()

            for alert in alerts:
                try:
                    alert_dict = {
                        "unit_id": alert.unit_id or "REDE",
                        "rule": alert.rule,
                        "title": alert.title,
                        "message": alert.message,
                        "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                        "current_val": str(alert.current_val or ""),
                        "limit_val": str(alert.limit_val or ""),
                    }

                    # Enviar email
                    await email_connector.send_alert(alert_dict)
                    alert.notified_email = True

                    # WhatsApp para críticos
                    if str(alert.severity) in ("critical", "AlertSeverity.critical"):
                        await whatsapp_connector.send_critical_alert(alert_dict)
                        alert.notified_whatsapp = True

                    notified += 1
                except Exception as e:
                    logger.warning(f"Failed to notify alert {alert.id}: {e}")

        return {"status": "success", "notified": notified}

    return _run_async(_execute())


@shared_task(
    name="app.tasks.task_definitions.retry_failed_actions",
    time_limit=60,
)
def retry_failed_actions() -> Dict[str, Any]:
    """Requeue ações com falha para nova tentativa."""
    async def _execute():
        from app.services.decision_service import decision_service
        count = await decision_service.retry_failed_actions(max_retries=3)
        return {"requeued": count}

    return _run_async(_execute())


# ─── Connector Health Tasks ────────────────────────────────────────────────────

@shared_task(
    name="app.tasks.task_definitions.run_meta_ads_check",
    time_limit=120,
)
def run_meta_ads_check() -> Dict[str, Any]:
    """Verifica performance dos anúncios Meta e pausa campanhas com ROAS baixo."""
    async def _execute():
        from app.connectors.meta_ads_connector import meta_connector
        from app.services.alert_service import alert_service
        from app.core.config import settings

        campaigns = await meta_connector.get_campaigns_performance(date_preset="last_7d")
        paused = []

        for camp in campaigns:
            roas = camp.get("roas", 99)
            if isinstance(roas, (int, float)) and roas < settings.min_roas_threshold:
                await meta_connector.pause_campaign(camp["campaign_id"])
                paused.append(camp["campaign_id"])
                await alert_service.create_alert(
                    unit_id=None,
                    sector="marketing",
                    rule="CEO_ROAS_MIN",
                    title=f"Campanha pausada: {camp.get('name', camp['campaign_id'])}",
                    message=f"ROAS {roas:.2f} abaixo do mínimo {settings.min_roas_threshold}",
                    severity="warning",
                    current_val=roas,
                    limit_val=settings.min_roas_threshold,
                )

        return {"campaigns_checked": len(campaigns), "paused": len(paused)}

    return _run_async(_execute())


@shared_task(
    name="app.tasks.task_definitions.run_inventory_check",
    time_limit=180,
)
def run_inventory_check() -> Dict[str, Any]:
    """Verifica estoque de todas as unidades e gera alertas de reposição."""
    async def _execute():
        from app.connectors.sults_connector import sults_connector
        from app.services.alert_service import alert_service
        from app.core.config import settings

        alerts_created = 0
        for unit_id in settings.network_units:
            try:
                inventory = await sults_connector.get_inventory(unit_id)
                items = inventory.get("items", [])
                for item in items:
                    qty = item.get("qty_kg") or item.get("qty_un") or 0
                    reorder = item.get("reorder_point", 0)
                    if qty < reorder:
                        await alert_service.create_alert(
                            unit_id=unit_id,
                            sector="supply",
                            rule="STOCK_REORDER",
                            title=f"Estoque baixo: {item.get('name')} — {unit_id}",
                            message=f"Quantidade {qty} abaixo do ponto de reposição {reorder}",
                            severity="warning",
                            current_val=float(qty),
                            limit_val=float(reorder),
                        )
                        alerts_created += 1
            except Exception as e:
                logger.warning(f"Inventory check failed for {unit_id}: {e}")

        return {"units_checked": len(settings.network_units), "alerts_created": alerts_created}

    return _run_async(_execute())

# =============================================================================
# SCHEDULER/MAIN.PY — Frank AI OS
# Scheduler de tarefas periódicas (alertas, relatórios, monitoramento)
# =============================================================================

import asyncio
import logging
import os
from datetime import datetime

import asyncpg
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import POSTGRES_URL, REDIS_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("frank.scheduler")

db_pool     = None
redis_client = None
scheduler   = AsyncIOScheduler(timezone="America/Sao_Paulo")


async def init_connections():
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(POSTGRES_URL, min_size=2, max_size=5)
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("Connections initialized")


async def check_cmv_alerts():
    """Verifica CMV e gera alertas automáticos (roda diariamente às 8h)."""
    logger.info("⏰ Verificando alertas de CMV...")
    try:
        from alert_agent import AlertAgent
        agent = AlertAgent()
        agent.db_pool = db_pool
        agent.redis_client = redis_client
        alerts = await agent.check_and_generate_alerts()
        logger.info(f"✅ {len(alerts)} novos alertas gerados")
    except Exception as e:
        logger.error(f"check_cmv_alerts error: {e}")


async def daily_kpi_report():
    """Gera relatório diário de KPIs e envia por email (roda às 7h)."""
    logger.info("⏰ Gerando relatório diário de KPIs...")
    try:
        from kpi_agent import KPIAgent
        from integrations.email import EmailConnector

        agent = KPIAgent()
        agent.db_pool = db_pool

        report = await agent.analyze(
            question="Gere o relatório diário completo de KPIs da rede",
            user="Scheduler"
        )

        recipients = os.getenv("DAILY_REPORT_EMAILS", "ceo@davverogelato.com.br").split(",")
        email = EmailConnector()
        await email.send_report(
            to=recipients,
            title=f"Relatório Diário KPIs — {datetime.now().strftime('%d/%m/%Y')}",
            content=report,
        )
        logger.info(f"✅ Relatório diário enviado para {recipients}")
    except Exception as e:
        logger.error(f"daily_kpi_report error: {e}")


async def weekly_cmv_analysis():
    """Análise semanal de CMV por unidade (toda segunda-feira às 9h)."""
    logger.info("⏰ Análise semanal de CMV...")
    try:
        from cmv_agent import CMVAgent
        from integrations.email import EmailConnector

        agent = CMVAgent()
        agent.db_pool = db_pool

        analysis = await agent.analyze(
            question="Análise completa de CMV da semana — ranking, alertas e recomendações",
            user="Scheduler"
        )

        recipients = os.getenv("CMV_REPORT_EMAILS", "cfo@davverogelato.com.br").split(",")
        email = EmailConnector()
        await email.send_report(
            to=recipients,
            title=f"Análise Semanal CMV — {datetime.now().strftime('%d/%m/%Y')}",
            content=analysis,
        )
        logger.info("✅ Análise semanal de CMV enviada")
    except Exception as e:
        logger.error(f"weekly_cmv_analysis error: {e}")


async def invalidate_kpi_cache():
    """Invalida cache de KPIs a cada 5 minutos."""
    if redis_client:
        try:
            await redis_client.delete("frank:kpi_snapshot")
        except Exception:
            pass


async def main():
    await init_connections()

    # Schedules
    scheduler.add_job(check_cmv_alerts,    CronTrigger(hour=8, minute=0),   id="cmv_alerts")
    scheduler.add_job(daily_kpi_report,    CronTrigger(hour=7, minute=0),   id="daily_report")
    scheduler.add_job(weekly_cmv_analysis, CronTrigger(day_of_week="mon", hour=9), id="weekly_cmv")
    scheduler.add_job(invalidate_kpi_cache, CronTrigger(minute="*/5"),      id="cache_invalidate")

    scheduler.start()
    logger.info("🚀 Frank Scheduler iniciado")
    logger.info(f"   Jobs: {[j.id for j in scheduler.get_jobs()]}")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        await db_pool.close()
        await redis_client.close()
        logger.info("Frank Scheduler encerrado")


if __name__ == "__main__":
    asyncio.run(main())

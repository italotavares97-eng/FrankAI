"""Frank AI OS — Airflow DAG: relatório mensal consolidado."""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "frank_ai_os",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
}


def _trigger_monthly_report(**context):
    from app.tasks.task_definitions import run_monthly_report
    result = run_monthly_report.apply_async(queue="frank_reports")
    print(f"Monthly report task queued: {result.id}")
    return result.id


def _generate_ceo_rules_summary(**context):
    """Gera sumário mensal de violações de CEO Rules."""
    import asyncio

    async def _run():
        from app.services.decision_service import decision_service
        summary = await decision_service.get_ceo_rules_violations_summary(days_back=30)
        print(f"\n=== CEO RULES — VIOLAÇÕES DO MÊS ===")
        print(f"Total: {summary['total_violations']}")
        print("Por regra:")
        for rule, count in summary.get("violations_by_rule", {}).items():
            print(f"  {rule}: {count}x")
        print("Por unidade:")
        for unit, count in summary.get("violations_by_unit", {}).items():
            print(f"  {unit}: {count}x")
        return summary

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _archive_old_alerts(**context):
    """Arquiva alertas resolvidos com mais de 30 dias."""
    import asyncio
    from datetime import datetime, timedelta

    async def _run():
        from app.core.database import get_db_context
        from app.memory.models import Alert, AlertStatus
        from sqlalchemy import select, and_

        threshold = datetime.utcnow() - timedelta(days=30)
        archived = 0

        async with get_db_context() as db:
            result = await db.execute(
                select(Alert).where(
                    and_(
                        Alert.status == AlertStatus.resolved,
                        Alert.resolved_at < threshold,
                    )
                ).limit(500)
            )
            alerts = result.scalars().all()
            for alert in alerts:
                await db.delete(alert)
                archived += 1

        print(f"Archived {archived} old resolved alerts")
        return archived

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _compute_monthly_kpi_averages(**context):
    """Calcula médias mensais de KPI por unidade e persiste."""
    import asyncio

    async def _run():
        from app.core.database import get_db_context
        from app.memory.models import UnitKPI
        from sqlalchemy import select, func
        from datetime import date
        import calendar

        today = date.today()
        first_day = date(today.year, today.month, 1)
        last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

        async with get_db_context() as db:
            result = await db.execute(
                select(
                    UnitKPI.unit_id,
                    func.avg(UnitKPI.revenue).label("avg_revenue"),
                    func.avg(UnitKPI.cmv_pct).label("avg_cmv"),
                    func.avg(UnitKPI.ebitda_pct).label("avg_ebitda"),
                    func.avg(UnitKPI.nps_score).label("avg_nps"),
                    func.sum(UnitKPI.revenue).label("total_revenue"),
                    func.count(UnitKPI.id).label("days_recorded"),
                )
                .where(UnitKPI.snapshot_date.between(first_day, last_day))
                .group_by(UnitKPI.unit_id)
            )
            rows = result.all()

        print(f"\n=== MÉDIAS MENSAIS — {today.strftime('%B %Y')} ===")
        for row in rows:
            print(f"  {row.unit_id}: Receita R${row.total_revenue:,.0f} | "
                  f"CMV {row.avg_cmv:.1f}% | EBITDA {row.avg_ebitda:.1f}% | "
                  f"NPS {row.avg_nps:.0f}")

        return [dict(row._mapping) for row in rows]

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


with DAG(
    dag_id="frank_monthly_report",
    default_args=default_args,
    description="Frank AI OS — Relatório mensal consolidado + limpeza + métricas",
    schedule_interval="0 9 1 * *",  # Dia 1 de cada mês 09:00 BRT (12:00 UTC)
    start_date=days_ago(30),
    catchup=False,
    tags=["frank", "monthly", "reports"],
    max_active_runs=1,
) as dag:

    monthly_report = PythonOperator(
        task_id="generate_monthly_report",
        python_callable=_trigger_monthly_report,
        execution_timeout=timedelta(minutes=20),
    )

    ceo_rules_summary = PythonOperator(
        task_id="ceo_rules_violations_summary",
        python_callable=_generate_ceo_rules_summary,
        execution_timeout=timedelta(minutes=10),
    )

    kpi_averages = PythonOperator(
        task_id="compute_monthly_kpi_averages",
        python_callable=_compute_monthly_kpi_averages,
        execution_timeout=timedelta(minutes=10),
    )

    archive_alerts = PythonOperator(
        task_id="archive_old_alerts",
        python_callable=_archive_old_alerts,
        execution_timeout=timedelta(minutes=5),
    )

    # Executa tudo em paralelo, archive no final
    [monthly_report, ceo_rules_summary, kpi_averages] >> archive_alerts

"""Frank AI OS — Airflow DAG: relatório semanal."""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "frank_ai_os",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def _trigger_weekly_dre(**context):
    from app.tasks.task_definitions import run_weekly_report
    result = run_weekly_report.apply_async(queue="frank_reports")
    print(f"Weekly DRE task queued: {result.id}")
    return result.id


def _trigger_insights_summary(**context):
    """Gera resumo dos top insights da semana."""
    import asyncio

    async def _run():
        from app.memory.memory_service import memory_service
        insights = await memory_service.get_top_insights(days_back=7, limit=10)
        print(f"Top insights this week: {len(insights)}")
        for i in insights:
            print(f"  [{i['impact_score']:.1f}] {i['title'][:60]}")
        return insights

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _trigger_decision_patterns(**context):
    """Analisa padrões de decisão da semana."""
    import asyncio

    async def _run():
        from app.services.decision_service import decision_service
        patterns = await decision_service.get_patterns(days_back=7)
        print(f"Decision patterns (7d): {patterns}")
        return patterns

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


with DAG(
    dag_id="frank_weekly_report",
    default_args=default_args,
    description="Frank AI OS — DRE semanal, insights e análise de padrões",
    schedule_interval="0 8 * * 1",  # Segunda-feira 08:00 BRT (11:00 UTC)
    start_date=days_ago(7),
    catchup=False,
    tags=["frank", "weekly", "reports"],
    max_active_runs=1,
) as dag:

    weekly_dre = PythonOperator(
        task_id="generate_weekly_dre",
        python_callable=_trigger_weekly_dre,
        execution_timeout=timedelta(minutes=15),
    )

    insights = PythonOperator(
        task_id="insights_summary",
        python_callable=_trigger_insights_summary,
        execution_timeout=timedelta(minutes=5),
    )

    patterns = PythonOperator(
        task_id="decision_patterns",
        python_callable=_trigger_decision_patterns,
        execution_timeout=timedelta(minutes=5),
    )

    # DRE gera em paralelo com análises internas
    weekly_dre >> [insights, patterns]

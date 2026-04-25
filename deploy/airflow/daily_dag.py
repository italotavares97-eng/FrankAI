"""Frank AI OS — Airflow DAG: rotinas diárias."""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "frank_ai_os",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _trigger_morning_briefing(**context):
    """Aciona o briefing matinal via Celery."""
    from app.tasks.task_definitions import run_morning_briefing
    result = run_morning_briefing.apply_async(queue="frank_critical")
    print(f"Morning briefing task queued: {result.id}")
    return result.id


def _trigger_alert_check(**context):
    """Aciona verificação e envio de alertas pendentes."""
    from app.tasks.task_definitions import run_alert_notifications
    result = run_alert_notifications.apply_async(queue="frank_critical")
    print(f"Alert notifications task queued: {result.id}")
    return result.id


def _trigger_meta_ads_check(**context):
    """Aciona verificação de performance Meta Ads."""
    from app.tasks.task_definitions import run_meta_ads_check
    result = run_meta_ads_check.apply_async(queue="frank_default")
    print(f"Meta Ads check task queued: {result.id}")
    return result.id


def _trigger_inventory_check(**context):
    """Aciona verificação de estoque de todas as unidades."""
    from app.tasks.task_definitions import run_inventory_check
    result = run_inventory_check.apply_async(queue="frank_default")
    print(f"Inventory check task queued: {result.id}")
    return result.id


def _trigger_evening_analysis(**context):
    """Aciona análise CEO do fim do dia."""
    from app.tasks.task_definitions import run_ceo_analysis
    result = run_ceo_analysis.apply_async(queue="frank_default")
    print(f"CEO evening analysis task queued: {result.id}")
    return result.id


with DAG(
    dag_id="frank_daily_operations",
    default_args=default_args,
    description="Frank AI OS — Rotinas diárias: briefing, alertas, Meta Ads, estoque, análise CEO",
    schedule_interval="0 7 * * *",  # 07:00 BRT (10:00 UTC)
    start_date=days_ago(1),
    catchup=False,
    tags=["frank", "daily", "operations"],
    max_active_runs=1,
    doc_md="""
    ## Frank AI OS — DAG Diário

    Executa em ordem:
    1. **Briefing Matinal** (07:00) — CEO Analysis + Email + WhatsApp
    2. **Alert Check** (07:15) — Notifica alertas abertos não enviados
    3. **Meta Ads Check** (09:00) — Verifica ROAS e pausa campanhas ruins
    4. **Inventory Check** (08:30) — Monitora estoque de 7 unidades
    5. **Evening CEO Analysis** (19:00) — Análise completa do dia
    """,
) as dag:

    morning_briefing = PythonOperator(
        task_id="morning_briefing",
        python_callable=_trigger_morning_briefing,
        execution_timeout=timedelta(minutes=10),
    )

    alert_check = PythonOperator(
        task_id="alert_notifications",
        python_callable=_trigger_alert_check,
        execution_timeout=timedelta(minutes=3),
    )

    meta_ads = PythonOperator(
        task_id="meta_ads_check",
        python_callable=_trigger_meta_ads_check,
        execution_timeout=timedelta(minutes=5),
    )

    inventory = PythonOperator(
        task_id="inventory_check",
        python_callable=_trigger_inventory_check,
        execution_timeout=timedelta(minutes=5),
    )

    evening_analysis = PythonOperator(
        task_id="evening_ceo_analysis",
        python_callable=_trigger_evening_analysis,
        execution_timeout=timedelta(minutes=10),
        trigger_rule="all_done",  # Executa mesmo se tasks anteriores falharem
    )

    # Fluxo: briefing → alertas em paralelo com meta+estoque → análise noturna
    morning_briefing >> alert_check
    morning_briefing >> [meta_ads, inventory]
    [alert_check, meta_ads, inventory] >> evening_analysis

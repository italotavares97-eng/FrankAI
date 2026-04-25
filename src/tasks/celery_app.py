"""Frank AI OS — Celery app com RedBeat scheduler."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "frank_ai_os",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.task_definitions"],
)

celery_app.conf.update(
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,

    # Resultado / expiração
    result_expires=86400,  # 24h
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # RedBeat (cron scheduler)
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.redis_url,
    redbeat_key_prefix="frank:beat:",
    beat_max_loop_interval=5,

    # Filas
    task_default_queue="frank_default",
    task_queues={
        "frank_default": {"exchange": "frank_default"},
        "frank_critical": {"exchange": "frank_critical"},
        "frank_reports": {"exchange": "frank_reports"},
    },
    task_routes={
        "app.tasks.task_definitions.run_morning_briefing": {"queue": "frank_critical"},
        "app.tasks.task_definitions.run_weekly_report": {"queue": "frank_reports"},
        "app.tasks.task_definitions.run_monthly_report": {"queue": "frank_reports"},
        "app.tasks.task_definitions.run_ceo_analysis": {"queue": "frank_default"},
        "app.tasks.task_definitions.run_alert_notifications": {"queue": "frank_critical"},
        "app.tasks.task_definitions.retry_failed_actions": {"queue": "frank_default"},
        "app.tasks.task_definitions.run_meta_ads_check": {"queue": "frank_default"},
        "app.tasks.task_definitions.run_inventory_check": {"queue": "frank_default"},
    },

    # Beat schedule (cron jobs)
    beat_schedule={
        # ── Diário ─────────────────────────────────────────────────
        "morning-briefing": {
            "task": "app.tasks.task_definitions.run_morning_briefing",
            "schedule": crontab(hour=7, minute=0),  # 07:00 BRT
            "options": {"queue": "frank_critical"},
        },
        "ceo-evening-analysis": {
            "task": "app.tasks.task_definitions.run_ceo_analysis",
            "schedule": crontab(hour=19, minute=0),  # 19:00 BRT
            "options": {"queue": "frank_default"},
        },
        "alert-notifications": {
            "task": "app.tasks.task_definitions.run_alert_notifications",
            "schedule": crontab(minute="*/15"),  # a cada 15 min
            "options": {"queue": "frank_critical"},
        },
        "meta-ads-check": {
            "task": "app.tasks.task_definitions.run_meta_ads_check",
            "schedule": crontab(hour="9,13,17", minute=0),
            "options": {"queue": "frank_default"},
        },
        "inventory-check": {
            "task": "app.tasks.task_definitions.run_inventory_check",
            "schedule": crontab(hour=8, minute=30),
            "options": {"queue": "frank_default"},
        },
        "retry-failed-actions": {
            "task": "app.tasks.task_definitions.retry_failed_actions",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "frank_default"},
        },

        # ── Semanal ────────────────────────────────────────────────
        "weekly-dre-report": {
            "task": "app.tasks.task_definitions.run_weekly_report",
            "schedule": crontab(day_of_week=1, hour=8, minute=0),  # Segunda 08:00
            "options": {"queue": "frank_reports"},
        },

        # ── Mensal ─────────────────────────────────────────────────
        "monthly-report": {
            "task": "app.tasks.task_definitions.run_monthly_report",
            "schedule": crontab(day_of_month=1, hour=9, minute=0),  # Dia 1 09:00
            "options": {"queue": "frank_reports"},
        },
    },
)

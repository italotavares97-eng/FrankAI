# =============================================================================
# WORKER/MAIN.PY — Frank AI OS
# Consumidor RabbitMQ para processamento assíncrono de tarefas, alertas e
# relatórios. Roda como serviço independente no Docker.
# =============================================================================

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from datetime import datetime
from typing import Any, Dict

import aio_pika
import asyncpg
import redis.asyncio as redis

from config import POSTGRES_URL, REDIS_URL, RABBITMQ_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("frank.worker")

WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "4"))

# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------

db_pool: asyncpg.Pool | None = None
redis_client: redis.Redis | None = None
rabbitmq_conn: aio_pika.Connection | None = None
rabbitmq_channel: aio_pika.Channel | None = None

# Graceful shutdown flag
_shutdown = asyncio.Event()


async def init_connections():
    global db_pool, redis_client, rabbitmq_conn, rabbitmq_channel
    db_pool      = await asyncpg.create_pool(POSTGRES_URL, min_size=2, max_size=8)
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
    rabbitmq_conn    = await aio_pika.connect_robust(RABBITMQ_URL)
    rabbitmq_channel = await rabbitmq_conn.channel()
    await rabbitmq_channel.set_qos(prefetch_count=WORKER_CONCURRENCY)
    logger.info("Worker connections initialized")


async def close_connections():
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()
    if rabbitmq_conn:
        await rabbitmq_conn.close()
    logger.info("Worker connections closed")


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------

async def handle_task(payload: Dict[str, Any]) -> Dict:
    """
    Processa tarefas genéricas do frank_tasks queue.
    task_type: analyze | report | action | cmv_check | alert
    """
    task_type = payload.get("task_type", "analyze")
    logger.info(f"[TASK] type={task_type} id={payload.get('task_id', 'N/A')}")

    try:
        if task_type == "analyze":
            return await _task_analyze(payload)
        elif task_type == "cmv_check":
            return await _task_cmv_check(payload)
        elif task_type == "report":
            return await _task_report(payload)
        elif task_type == "action":
            return await _task_action(payload)
        else:
            logger.warning(f"Unknown task_type: {task_type}")
            return {"status": "skipped", "reason": f"unknown type {task_type}"}
    except Exception as e:
        logger.error(f"handle_task error: {e}", exc_info=True)
        raise


async def _task_analyze(payload: Dict) -> Dict:
    """Roda análise de uma pergunta via FrankMaster."""
    from frank_master import FrankMaster
    master = FrankMaster()
    master.db_pool     = db_pool
    master.redis_client = redis_client
    try:
        question   = payload.get("question", "")
        session_id = payload.get("session_id", "worker")
        user       = payload.get("user", "Worker")

        result = await master.frank_pipeline(question=question, session_id=session_id, user=user)

        # Persiste resultado se task_id presente
        if payload.get("task_id"):
            await db_pool.execute(
                """UPDATE frank_tasks SET status='done', result=$1, updated_at=NOW()
                   WHERE id=$2""",
                json.dumps(result, ensure_ascii=False),
                payload["task_id"]
            )
        return {"status": "done", "result": result}
    finally:
        await master.close()


async def _task_cmv_check(payload: Dict) -> Dict:
    """Verifica CMV de uma unidade e cria alertas se necessário."""
    unit_id = payload.get("unit_id")
    query = """
        SELECT u.name, fm.revenue, fm.cogs, fm.cmv_pct
        FROM financial_monthly fm
        JOIN units u ON u.id = fm.unit_id
        WHERE fm.unit_id = $1
        ORDER BY fm.year DESC, fm.month DESC
        LIMIT 1
    """
    row = await db_pool.fetchrow(query, unit_id) if unit_id else None

    if not row:
        return {"status": "skipped", "reason": "no data"}

    cmv_pct = float(row["cmv_pct"] or 0)
    alerts_created = 0

    if cmv_pct > 30.0:
        severity = "critical" if cmv_pct > 35 else "warning"
        await db_pool.execute(
            """INSERT INTO alerts (unit_id, alert_type, severity, message, created_at)
               VALUES ($1, 'cmv_high', $2, $3, NOW())
               ON CONFLICT DO NOTHING""",
            unit_id, severity,
            f"CMV em {cmv_pct:.1f}% na unidade {row['name']} — limite CEO: 30%"
        )
        alerts_created += 1
        # Invalida cache
        await redis_client.delete(f"frank:unit:{unit_id}")

    return {"status": "done", "cmv_pct": cmv_pct, "alerts_created": alerts_created}


async def _task_report(payload: Dict) -> Dict:
    """Gera relatório diário/semanal e envia por e-mail."""
    report_type = payload.get("report_type", "daily_kpi")
    recipients  = payload.get("recipients", [])

    from kpi_agent import KPIAgent
    from integrations.email import EmailConnector

    agent = KPIAgent()
    agent.db_pool = db_pool

    question_map = {
        "daily_kpi":   "Gere o relatório diário completo de KPIs da rede",
        "weekly_cmv":  "Análise completa de CMV da semana — ranking, alertas e recomendações",
        "monthly_dre": "Gere o DRE consolidado do mês com análise de variações",
    }

    content = await agent.analyze(
        question=question_map.get(report_type, question_map["daily_kpi"]),
        user="Worker"
    )

    if recipients:
        email = EmailConnector()
        await email.send_report(
            to=recipients,
            title=f"Relatório {report_type.upper()} — {datetime.now().strftime('%d/%m/%Y')}",
            content=content,
        )

    return {"status": "done", "report_type": report_type, "sent_to": recipients}


async def _task_action(payload: Dict) -> Dict:
    """Executa uma ação específica (envio WhatsApp, e-mail, etc.)."""
    action_type = payload.get("action_type")
    data        = payload.get("data", {})

    if action_type == "whatsapp":
        from integrations.whatsapp import WhatsAppConnector
        wa = WhatsAppConnector()
        await wa.send_text(data["to"], data["message"])
        return {"status": "done", "channel": "whatsapp"}

    elif action_type == "email":
        from integrations.email import EmailConnector
        email = EmailConnector()
        await email.send_email(**data)
        return {"status": "done", "channel": "email"}

    elif action_type == "cache_invalidate":
        pattern = data.get("pattern", "frank:*")
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
        return {"status": "done", "keys_deleted": len(keys)}

    else:
        return {"status": "skipped", "reason": f"unknown action {action_type}"}


# ---------------------------------------------------------------------------
# Alert handler
# ---------------------------------------------------------------------------

async def handle_alert(payload: Dict[str, Any]) -> Dict:
    """
    Processa mensagens da frank_alerts queue.
    Notifica via WhatsApp e e-mail conforme configurado.
    """
    logger.info(f"[ALERT] severity={payload.get('severity')} unit={payload.get('unit_id')}")
    try:
        from integrations.whatsapp import WhatsAppConnector
        from integrations.email    import EmailConnector

        message  = payload.get("message", "Alerta sem mensagem")
        severity = payload.get("severity", "warning")
        unit     = payload.get("unit_name", "N/A")

        # WhatsApp para grupo de operações
        wa_group = os.getenv("WA_OPS_GROUP_ID")
        if wa_group:
            wa = WhatsAppConnector()
            icon = "🔴" if severity == "critical" else "⚠️"
            await wa.send_text(wa_group, f"{icon} *ALERTA FRANK* — {unit}\n\n{message}")

        # E-mail para gestores
        ops_email = os.getenv("OPS_ALERT_EMAIL", "ops@davverogelato.com.br")
        email_conn = EmailConnector()
        await email_conn.send_alert(
            to=[ops_email],
            subject=f"[{severity.upper()}] Alerta Frank — {unit}",
            message=message,
            severity=severity
        )

        # Persiste no banco
        await db_pool.execute(
            "UPDATE alerts SET notified=TRUE, notified_at=NOW() WHERE id=$1",
            payload.get("alert_id")
        )
        return {"status": "done"}

    except Exception as e:
        logger.error(f"handle_alert error: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Report handler
# ---------------------------------------------------------------------------

async def handle_report(payload: Dict[str, Any]) -> Dict:
    """Processa fila frank_reports — geração de relatórios assíncronos."""
    return await handle_task({**payload, "task_type": "report"})


# ---------------------------------------------------------------------------
# Message dispatcher
# ---------------------------------------------------------------------------

async def dispatch_message(queue_name: str, message: aio_pika.IncomingMessage):
    async with message.process(requeue=True):
        try:
            body    = message.body.decode()
            payload = json.loads(body)
            payload["_queue"]    = queue_name
            payload["_msg_id"]   = str(message.message_id or "")
            payload["_received"] = datetime.utcnow().isoformat()

            t0 = time.monotonic()

            if queue_name == "frank_tasks":
                result = await handle_task(payload)
            elif queue_name == "frank_alerts":
                result = await handle_alert(payload)
            elif queue_name == "frank_reports":
                result = await handle_report(payload)
            else:
                result = {"status": "skipped"}

            elapsed = (time.monotonic() - t0) * 1000
            logger.info(f"[{queue_name}] processed in {elapsed:.0f}ms — {result.get('status')}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {queue_name}: {e}")
            # Não reencaminha mensagem malformada
            await message.nack(requeue=False)
        except Exception as e:
            logger.error(f"dispatch_message error [{queue_name}]: {e}", exc_info=True)
            # aio_pika faz requeue automático pelo context manager com requeue=True
            raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _handle_signal(sig, frame):
    logger.info(f"Signal {sig} received — shutting down...")
    _shutdown.set()


async def main():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    await init_connections()

    vhost = "davvero"  # conforme definitions.json

    # Declara / obtém queues (idempotente)
    queues_cfg = [
        ("frank_tasks",   {"x-message-ttl": 86400000, "x-dead-letter-exchange": "frank.deadletter", "x-max-priority": 10}),
        ("frank_alerts",  {"x-message-ttl": 3600000,  "x-max-priority": 10}),
        ("frank_reports", {"x-message-ttl": 86400000}),
    ]

    consumers = []
    for q_name, q_args in queues_cfg:
        queue = await rabbitmq_channel.declare_queue(
            q_name, durable=True, arguments=q_args, passive=True
        )
        consumer_tag = await queue.consume(
            lambda msg, qn=q_name: dispatch_message(qn, msg)
        )
        consumers.append((q_name, consumer_tag))
        logger.info(f"Consuming {q_name}")

    logger.info(
        f"🚀 Frank Worker iniciado — concurrency={WORKER_CONCURRENCY} "
        f"queues={[c[0] for c in consumers]}"
    )

    await _shutdown.wait()

    logger.info("Canceling consumers...")
    for q_name, consumer_tag in consumers:
        try:
            queue = await rabbitmq_channel.declare_queue(q_name, passive=True)
            await queue.cancel(consumer_tag)
        except Exception:
            pass

    await close_connections()
    logger.info("Frank Worker encerrado")


if __name__ == "__main__":
    asyncio.run(main())

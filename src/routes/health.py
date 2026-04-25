"""Frank AI OS — Health check routes."""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    components: Dict[str, Any] = {}


@router.get("", response_model=HealthResponse)
async def health_check():
    """Liveness probe — sempre retorna 200 se o processo estiver rodando."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness probe — verifica DB e Redis."""
    components = {}
    overall = "ok"

    # Checar PostgreSQL
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        components["database"] = "ok"
    except Exception as e:
        components["database"] = f"error: {str(e)[:50]}"
        overall = "degraded"

    # Checar Redis
    try:
        from app.core.redis_client import cache
        await cache.redis.ping()
        components["redis"] = "ok"
    except Exception as e:
        components["redis"] = f"error: {str(e)[:50]}"
        overall = "degraded"

    return HealthResponse(
        status=overall,
        timestamp=datetime.utcnow().isoformat(),
        components=components,
    )


@router.get("/deep")
async def deep_health():
    """Deep health — verifica todos os componentes incluindo conectores."""
    from app.core.config import settings

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "mock" if settings.mock_external_apis else "production",
        "network_units": settings.network_units,
        "features": {
            "email": settings.enable_email,
            "whatsapp": settings.enable_whatsapp,
            "mock_apis": settings.mock_external_apis,
        },
    }

    # DB check
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            row = await conn.execute(text("SELECT COUNT(*) FROM alerts"))
            count = row.scalar()
        results["database"] = {"status": "ok", "alerts_count": count}
    except Exception as e:
        results["database"] = {"status": "error", "detail": str(e)[:100]}

    # Redis check
    try:
        from app.core.redis_client import cache
        await cache.redis.ping()
        info = await cache.redis.info("memory")
        results["redis"] = {
            "status": "ok",
            "used_memory_human": info.get("used_memory_human", "?"),
        }
    except Exception as e:
        results["redis"] = {"status": "error", "detail": str(e)[:100]}

    # Celery check
    try:
        from app.tasks.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=2)
        active = inspect.active()
        results["celery"] = {"status": "ok", "active_workers": len(active or {})}
    except Exception as e:
        results["celery"] = {"status": "unreachable", "detail": str(e)[:100]}

    return results

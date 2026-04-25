"""Frank AI OS — FastAPI application factory."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown do Frank AI OS."""
    logger.info(
        "frank_starting",
        env="mock" if settings.mock_external_apis else "production",
        units=settings.network_units,
        version="1.0.0",
    )

    # ── Startup ──────────────────────────────────────────────────────────────
    # Criar tabelas no banco (se não existirem)
    try:
        from app.core.database import create_tables
        await create_tables()
        logger.info("database_tables_ready")
    except Exception as e:
        logger.error("database_startup_error", error=str(e))

    # Testar conexão Redis
    try:
        from app.core.redis_client import cache
        await cache.redis.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_startup_warning", error=str(e))

    logger.info("frank_ai_os_ready", api_docs="/docs")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("frank_shutting_down")
    try:
        from app.core.redis_client import cache
        await cache.redis.aclose()
        logger.info("redis_disconnected")
    except Exception:
        pass

    try:
        from app.core.database import engine
        await engine.dispose()
        logger.info("database_disconnected")
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="Frank AI OS",
        description=(
            "Sistema de Inteligência Empresarial Multi-Agentes — Davvero Gelato\n\n"
            "CEO Orchestrator com 9 agentes setoriais rodando em paralelo. "
            "Alertas automáticos via Email e WhatsApp. "
            "Relatórios HTML + PDF. Memory system com decisões e insights."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        contact={
            "name": "Davvero Gelato — Frank AI OS",
            "email": settings.alert_email,
        },
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restringir em produção
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timing middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"

        # Log requests lentas (> 5s)
        if elapsed_ms > 5000:
            logger.warning(
                "slow_request",
                path=request.url.path,
                method=request.method,
                ms=round(elapsed_ms, 1),
            )
        return response

    # ── Global error handler ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": str(exc) if settings.debug else "An unexpected error occurred",
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.routes.health import router as health_router
    from app.routes.agents import router as agents_router
    from app.routes.alerts import router as alerts_router
    from app.routes.reports import router as reports_router

    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(alerts_router)
    app.include_router(reports_router)

    # ── Root ──────────────────────────────────────────────────────────────────
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "Frank AI OS",
            "tagline": "Davvero Gelato — Multi-Agent Business Intelligence",
            "version": "1.0.0",
            "status": "online",
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "ready": "/health/ready",
                "agents": "/agents",
                "alerts": "/alerts",
                "reports": "/reports",
            },
            "ceo_rules": {
                "cmv_max_pct": settings.ceo_rule_cmv_max,
                "ebitda_min_pct": settings.ceo_rule_ebitda_min,
                "rent_max_pct": settings.ceo_rule_rent_max,
                "payback_max_months": settings.ceo_rule_payback_max,
                "roi_24m_min": settings.ceo_rule_roi_24m_min,
            },
            "network": {
                "units": settings.network_units,
                "mock_mode": settings.mock_external_apis,
            },
        }

    # ── Metrics endpoint (Prometheus-compatible) ───────────────────────────────
    @app.get("/metrics", tags=["observability"], include_in_schema=False)
    async def metrics():
        from app.core.database import get_db_context
        from app.memory.models import Alert, AlertStatus
        from sqlalchemy import select, func

        try:
            async with get_db_context() as db:
                open_alerts = await db.execute(
                    select(func.count(Alert.id)).where(Alert.status == AlertStatus.open)
                )
                open_count = open_alerts.scalar() or 0
        except Exception:
            open_count = -1

        # Prometheus text format
        lines = [
            "# HELP frank_open_alerts Number of open alerts",
            "# TYPE frank_open_alerts gauge",
            f"frank_open_alerts {open_count}",
            "# HELP frank_up Whether Frank AI OS is running",
            "# TYPE frank_up gauge",
            "frank_up 1",
        ]
        return Response(content="\n".join(lines) + "\n", media_type="text/plain")

    return app


app = create_app()

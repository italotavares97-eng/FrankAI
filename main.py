# =============================================================================
# MAIN.PY — Frank AI OS · FastAPI
# Davvero Gelato · API Principal
# =============================================================================
# Inicia com: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Docs:       http://localhost:8000/docs
# =============================================================================

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import aio_pika

from config import (
    ANTHROPIC_API_KEY, POSTGRES_URL, REDIS_URL, RABBITMQ_URL,
    CEO_HARD_RULES, OPERATIONAL_TARGETS, BRAND
)
from frank_master import FrankMaster

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("frank_api")

# ---------------------------------------------------------------------------
# APP STATE — conexões globais
# ---------------------------------------------------------------------------

class AppState:
    frank: FrankMaster = None
    db_pool: asyncpg.Pool = None
    redis_client: redis.Redis = None
    rabbitmq_conn: aio_pika.Connection = None

app_state = AppState()

# ---------------------------------------------------------------------------
# LIFESPAN — inicializa e encerra recursos
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    logger.info("🚀 Frank AI OS inicializando...")

    # PostgreSQL
    app_state.db_pool = await asyncpg.create_pool(
        POSTGRES_URL,
        min_size=5,
        max_size=20,
        command_timeout=30,
        server_settings={"search_path": "davvero,public"}
    )
    logger.info("✅ PostgreSQL conectado")

    # Redis
    app_state.redis_client = await redis.from_url(
        REDIS_URL,
        decode_responses=True,
        max_connections=20
    )
    await app_state.redis_client.ping()
    logger.info("✅ Redis conectado")

    # RabbitMQ
    try:
        app_state.rabbitmq_conn = await aio_pika.connect_robust(RABBITMQ_URL)
        logger.info("✅ RabbitMQ conectado")
    except Exception as e:
        logger.warning(f"⚠️ RabbitMQ não disponível: {e}")

    # Frank Master
    app_state.frank = FrankMaster()
    app_state.frank.db_pool = app_state.db_pool
    app_state.frank.redis_client = app_state.redis_client
    logger.info("✅ Frank AI OS pronto")

    yield  # Aplicação rodando

    # Shutdown
    logger.info("Frank AI OS encerrando...")
    await app_state.frank.close()
    await app_state.db_pool.close()
    await app_state.redis_client.close()
    if app_state.rabbitmq_conn:
        await app_state.rabbitmq_conn.close()
    logger.info("✅ Frank encerrado com sucesso")


# ---------------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Frank AI OS — Davvero Gelato",
    description="""
    Sistema Operacional de IA da Davvero Gelato.
    Orquestra agentes de CFO, COO, CMO, CSO, Supply, OPEP, Legal e BI.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "core",        "description": "Frank AI — Orquestrador principal"},
        {"name": "financeiro",  "description": "CFO — DRE, CMV, Fluxo de Caixa"},
        {"name": "operacoes",   "description": "COO — Lojas, Qualidade, Performance"},
        {"name": "marketing",   "description": "CMO — Campanhas, CRM, B2B"},
        {"name": "expansao",    "description": "CSO — Novas Unidades, Mercado"},
        {"name": "supply",      "description": "Supply — Fornecedores, Estoque"},
        {"name": "bi",          "description": "BI — KPIs, Alertas, Forecast"},
        {"name": "units",       "description": "CRUD — Unidades e Franqueados"},
        {"name": "health",      "description": "Saúde da aplicação"},
    ]
)

# ---------------------------------------------------------------------------
# MIDDLEWARES
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Restringir em produção via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Adiciona X-Request-ID em todas as respostas"""
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    response = await call_next(request)
    elapsed = round((time.monotonic() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed}ms"
    return response

# ---------------------------------------------------------------------------
# DEPENDÊNCIAS
# ---------------------------------------------------------------------------

async def get_db():
    """Dependência: conexão com PostgreSQL"""
    async with app_state.db_pool.acquire() as conn:
        yield conn

async def get_frank() -> FrankMaster:
    """Dependência: instância do Frank"""
    if not app_state.frank:
        raise HTTPException(status_code=503, detail="Frank AI OS não inicializado")
    return app_state.frank

async def get_redis() -> redis.Redis:
    return app_state.redis_client

# ---------------------------------------------------------------------------
# SCHEMAS PYDANTIC
# ---------------------------------------------------------------------------

class FrankRequest(BaseModel):
    question:   str     = Field(..., min_length=5, max_length=2000,
                                description="Pergunta ou instrução para o Frank")
    user:       str     = Field(default="CEO", description="Quem está perguntando")
    director:   Optional[str] = Field(None, description="Forçar diretor específico")
    context:    Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")
    stream:     bool    = Field(default=False, description="Resposta em streaming")

class FrankResponse(BaseModel):
    session_id:         str
    timestamp:          str
    director:           str
    response:           str
    ceo_approved:       bool
    violations:         List[str] = []
    decision:           Optional[str] = None
    processing_time_ms: int
    kpi_snapshot:       Optional[Dict] = None

class UnitCreate(BaseModel):
    code:               str     = Field(..., description="Código único ex: DVR-SP-001")
    name:               str
    franchisee_id:      Optional[str] = None
    format:             str     = Field(default="loja_pequena")
    city:               str
    state:              str     = Field(..., min_length=2, max_length=2)
    address:            Optional[str] = None
    shopping:           Optional[str] = None
    opening_date:       Optional[date] = None
    initial_investment: Optional[float] = None
    franchise_fee:      Optional[float] = None
    monthly_rent:       Optional[float] = None
    cluster:            Optional[str] = None

class FinancialInput(BaseModel):
    unit_id:            str
    month:              date
    gross_revenue:      float   = Field(..., gt=0)
    cogs_value:         float   = Field(..., gt=0)
    bonuses_received:   float   = Field(default=0)
    rent:               float   = Field(default=0)
    payroll:            float   = Field(default=0)
    electricity:        float   = Field(default=0)
    packaging:          float   = Field(default=0)
    royalties:          float   = Field(default=0)
    mkt_fund:           float   = Field(default=0)
    maintenance:        float   = Field(default=0)
    other_opex:         float   = Field(default=0)
    cto_monthly:        float   = Field(default=0)
    depreciation:       float   = Field(default=0)
    notes:              Optional[str] = None

class KPIDailyInput(BaseModel):
    unit_id:            str
    date:               date
    gross_revenue:      float
    transactions:       int
    team_hours:         float   = Field(default=8.0)
    stockout_count:     int     = Field(default=0)
    waste_value:        float   = Field(default=0)
    nps_score:          Optional[float] = None

class AlertAcknowledge(BaseModel):
    alert_id:   str
    acknowledged_by: str
    resolution_notes: Optional[str] = None

class ROISimulation(BaseModel):
    investment:         float   = Field(..., description="Investimento total em R$")
    monthly_revenue:    float   = Field(..., description="Faturamento mensal projetado")
    monthly_rent:       float
    royalty_pct:        float   = Field(default=0.085)
    cmv_pct:            float   = Field(default=0.265)
    payroll_pct:        float   = Field(default=0.22)
    other_costs_pct:    float   = Field(default=0.08)

class CMVAnalysis(BaseModel):
    unit_id:            Optional[str] = None
    start_month:        date
    end_month:          date

# ---------------------------------------------------------------------------
# ── HEALTH ──────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"], summary="Status da aplicação")
async def health_check():
    """Verifica saúde de todos os serviços"""
    checks = {}

    # PostgreSQL
    try:
        async with app_state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"erro: {e}"

    # Redis
    try:
        await app_state.redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"erro: {e}"

    # Frank
    checks["frank"] = "ok" if app_state.frank else "não inicializado"

    healthy = all(v == "ok" for v in checks.values())

    return {
        "status":   "healthy" if healthy else "degraded",
        "version":  "2.0.0",
        "brand":    BRAND["name"],
        "services": checks,
        "timestamp": datetime.now().isoformat()
    }


# ---------------------------------------------------------------------------
# ── FRANK CORE ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.post("/frank/ask", tags=["core"], response_model=FrankResponse,
          summary="Pergunta para o Frank AI OS")
async def frank_ask(
    body: FrankRequest,
    background_tasks: BackgroundTasks,
    frank: FrankMaster = Depends(get_frank),
    db = Depends(get_db)
):
    """
    Endpoint principal do Frank AI OS.

    Recebe uma pergunta, roteia para o diretor correto,
    aplica validação CEO e retorna diagnóstico estruturado.

    **Formato de resposta:** 10 blocos (diagnóstico → decisão)
    """
    try:
        result = await frank.frank_pipeline(
            question=body.question,
            user=body.user
        )

        # Salvar tarefa em background se há decisão de execução
        if "EXECUTAR" in result.get("response", ""):
            background_tasks.add_task(
                enqueue_task,
                task_type="approved_action",
                payload={
                    "interaction_id": result.get("session_id"),
                    "question": body.question,
                    "user": body.user
                }
            )

        violations = [
            v["rule"] for v in result.get("ceo_validation", {}).get("violations", [])
        ]

        return FrankResponse(
            session_id=result["session_id"],
            timestamp=result["timestamp"],
            director=result["routing"].get("director", "Frank"),
            response=result["response"],
            ceo_approved=result["ceo_validation"]["approved"],
            violations=violations,
            processing_time_ms=result["processing_time_ms"],
            kpi_snapshot=result.get("kpi_data")
        )

    except Exception as e:
        logger.exception(f"Erro no Frank pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/frank/ask/stream", tags=["core"],
          summary="Pergunta com resposta em streaming SSE")
async def frank_ask_stream(
    body: FrankRequest,
    frank: FrankMaster = Depends(get_frank)
):
    """
    Versão streaming do endpoint Frank.
    Retorna tokens conforme gerados (Server-Sent Events).
    """
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    from frank_master import FRANK_MASTER_SYSTEM

    async def stream_response():
        yield f"data: {json.dumps({'type': 'start', 'session': frank.session_id})}\n\n"

        routing = await frank._route_question(body.question)
        yield f"data: {json.dumps({'type': 'routing', 'director': routing.get('director')})}\n\n"

        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=FRANK_MASTER_SYSTEM,
            messages=[{"role": "user", "content": body.question}]
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/frank/history", tags=["core"], summary="Histórico de interações")
async def frank_history(
    limit:  int  = Query(default=20, le=100),
    offset: int  = Query(default=0),
    director: Optional[str] = None,
    db = Depends(get_db)
):
    """Retorna histórico de perguntas e respostas do Frank"""
    where = "WHERE 1=1"
    params = []
    if director:
        where += " AND director = $1"
        params.append(director)

    rows = await db.fetch(f"""
        SELECT id, session_id, timestamp, user_name, director,
               LEFT(question, 200) as question,
               LEFT(response, 500) as response_preview,
               ceo_approved, processing_ms
        FROM frank_interactions
        {where}
        ORDER BY timestamp DESC
        LIMIT {limit} OFFSET {offset}
    """, *params)

    return {"total": len(rows), "interactions": [dict(r) for r in rows]}


@app.get("/frank/lessons", tags=["core"], summary="Lições aprendidas pelo Frank")
async def get_lessons(db = Depends(get_db)):
    """Retorna todas as lições registradas no sistema de autoaperfeiçoamento"""
    rows = await db.fetch("""
        SELECT id, error_desc, correction, rule, example, director, created_at
        FROM frank_lessons
        WHERE is_active = true
        ORDER BY created_at DESC
    """)
    return {"lessons": [dict(r) for r in rows]}


@app.post("/frank/lessons", tags=["core"], summary="Registra nova lição")
async def add_lesson(
    error_desc: str,
    correction: str,
    rule: str,
    example: Optional[str] = None,
    director: Optional[str] = None,
    db = Depends(get_db)
):
    """Registra manualmente uma lição aprendida"""
    row = await db.fetchrow("""
        INSERT INTO frank_lessons (error_desc, correction, rule, example, director)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, created_at
    """, error_desc, correction, rule, example, director)
    return {"id": str(row["id"]), "created_at": row["created_at"].isoformat()}


# ---------------------------------------------------------------------------
# ── FINANCEIRO (CFO) ─────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/financeiro/dre/rede", tags=["financeiro"],
         summary="DRE consolidada da rede")
async def network_dre(db = Depends(get_db)):
    """Retorna DRE consolidada de todos as unidades ativas no mês anterior"""
    row = await db.fetchrow("SELECT * FROM vw_network_dre_current")
    if not row:
        raise HTTPException(status_code=404, detail="Sem dados financeiros para o período")
    return dict(row)


@app.get("/financeiro/dre/{unit_id}", tags=["financeiro"],
         summary="DRE de uma unidade específica")
async def unit_dre(
    unit_id: str,
    months:  int = Query(default=6, le=24, description="Últimos N meses"),
    db = Depends(get_db)
):
    """DRE mensal dos últimos N meses de uma unidade"""
    rows = await db.fetch("""
        SELECT
            month, gross_revenue, net_revenue, net_cogs,
            ROUND(cmv_pct*100,2) AS cmv_pct,
            gross_margin, ROUND(gross_margin_pct*100,2) AS gross_margin_pct,
            total_opex, ebitda_operational,
            ROUND(ebitda_pct*100,2) AS ebitda_pct,
            net_income, ROUND(net_margin_pct*100,2) AS net_margin_pct,
            ROUND(rent_pct*100,2) AS rent_pct,
            cto_monthly, validated
        FROM unit_financials
        WHERE unit_id = $1
        ORDER BY month DESC
        LIMIT $2
    """, unit_id, months)

    if not rows:
        raise HTTPException(status_code=404, detail="Unidade sem dados financeiros")

    return {"unit_id": unit_id, "months": len(rows), "dre": [dict(r) for r in rows]}


@app.post("/financeiro/dre", tags=["financeiro"],
          summary="Lança DRE mensal de uma unidade")
async def create_financial(body: FinancialInput, db = Depends(get_db)):
    """Lança ou atualiza a DRE de uma unidade para um mês específico"""
    try:
        row = await db.fetchrow("""
            INSERT INTO unit_financials (
                unit_id, month, gross_revenue, cogs_value, bonuses_received,
                rent, payroll, electricity, packaging, royalties, mkt_fund,
                maintenance, other_opex, cto_monthly, depreciation, notes
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
            ON CONFLICT (unit_id, month) DO UPDATE SET
                gross_revenue=EXCLUDED.gross_revenue, cogs_value=EXCLUDED.cogs_value,
                bonuses_received=EXCLUDED.bonuses_received, rent=EXCLUDED.rent,
                payroll=EXCLUDED.payroll, electricity=EXCLUDED.electricity,
                packaging=EXCLUDED.packaging, royalties=EXCLUDED.royalties,
                mkt_fund=EXCLUDED.mkt_fund, maintenance=EXCLUDED.maintenance,
                other_opex=EXCLUDED.other_opex, cto_monthly=EXCLUDED.cto_monthly,
                depreciation=EXCLUDED.depreciation, notes=EXCLUDED.notes,
                updated_at=NOW()
            RETURNING id, cmv_pct, net_margin_pct, ebitda_pct
        """,
            body.unit_id, body.month, body.gross_revenue, body.cogs_value,
            body.bonuses_received, body.rent, body.payroll, body.electricity,
            body.packaging, body.royalties, body.mkt_fund, body.maintenance,
            body.other_opex, body.cto_monthly, body.depreciation, body.notes
        )
        return {
            "id": str(row["id"]),
            "cmv_pct": float(row["cmv_pct"] or 0),
            "net_margin_pct": float(row["net_margin_pct"] or 0),
            "ebitda_pct": float(row["ebitda_pct"] or 0),
            "cmv_status": "CRÍTICO" if (row["cmv_pct"] or 0) > 0.30
                          else "ALERTA" if (row["cmv_pct"] or 0) > 0.28
                          else "OK"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/financeiro/cmv/ranking", tags=["financeiro"],
         summary="Ranking de CMV por unidade")
async def cmv_ranking(db = Depends(get_db)):
    """Ranking de CMV de todas as unidades — do pior para o melhor"""
    rows = await db.fetch("SELECT * FROM vw_units_cmv_ranking")
    
    network_avg = None
    if rows:
        network_avg = round(sum(r["cmv_pct"] for r in rows) / len(rows), 2)

    return {
        "network_avg_cmv": network_avg,
        "target_cmv": 26.5,
        "alert_threshold": 28.0,
        "critical_threshold": 30.0,
        "competitive_advantage_pp": round(35.0 - (network_avg or 26.5), 1),
        "units": [dict(r) for r in rows]
    }


@app.post("/financeiro/roi/simular", tags=["financeiro"],
          summary="Simula ROI de nova unidade")
async def simulate_roi(body: ROISimulation):
    """Simula payback e ROI de uma nova unidade — valida Hard Rules CEO"""
    net_revenue = body.monthly_revenue * (1 - 0.06)    # desconta impostos ~6%
    cogs = net_revenue * body.cmv_pct
    gross_margin = net_revenue - cogs

    rent_value    = body.monthly_revenue * (body.monthly_rent / body.monthly_revenue) if body.monthly_rent else body.monthly_revenue * 0.12
    payroll_value = body.monthly_revenue * body.payroll_pct
    royalties     = body.monthly_revenue * body.royalty_pct
    other         = body.monthly_revenue * body.other_costs_pct

    total_opex    = rent_value + payroll_value + royalties + other
    net_income    = gross_margin - total_opex

    payback_months = round(body.investment / net_income, 1) if net_income > 0 else 9999
    roi_24m = round((net_income * 24) / body.investment, 2) if body.investment > 0 else 0
    rent_pct = round((rent_value / body.monthly_revenue) * 100, 1)

    # Validações CEO
    violations = []
    if body.cmv_pct > CEO_HARD_RULES["cmv_max_pct"] / 100:
        violations.append(f"CMV {body.cmv_pct*100:.1f}% > {CEO_HARD_RULES['cmv_max_pct']}% máximo")
    if payback_months > CEO_HARD_RULES["payback_max_months"]:
        violations.append(f"Payback {payback_months:.0f}m > {CEO_HARD_RULES['payback_max_months']}m máximo")
    if roi_24m < CEO_HARD_RULES["roi_min_multiplier"]:
        violations.append(f"ROI {roi_24m:.1f}x < {CEO_HARD_RULES['roi_min_multiplier']}x mínimo")

    approved = len(violations) == 0

    return {
        "approved": approved,
        "violations": violations,
        "simulation": {
            "monthly_revenue": body.monthly_revenue,
            "net_revenue": round(net_revenue, 2),
            "cogs": round(cogs, 2),
            "gross_margin": round(gross_margin, 2),
            "gross_margin_pct": round((gross_margin / net_revenue) * 100, 1),
            "total_opex": round(total_opex, 2),
            "net_income": round(net_income, 2),
            "net_margin_pct": round((net_income / net_revenue) * 100, 1) if net_revenue > 0 else 0,
        },
        "kpis": {
            "payback_months": payback_months,
            "roi_24m": roi_24m,
            "rent_pct": rent_pct,
            "cmv_pct": round(body.cmv_pct * 100, 1),
        },
        "recommendation": "✅ APROVAR" if approved else "❌ REPROVAR — Hard Rules violadas"
    }


# ---------------------------------------------------------------------------
# ── OPERAÇÕES (COO) ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/operacoes/kpis/diario", tags=["operacoes"],
         summary="KPIs diários da rede")
async def daily_kpis(
    days: int = Query(default=30, le=90),
    db = Depends(get_db)
):
    """KPIs operacionais dos últimos N dias — consolidado da rede"""
    rows = await db.fetch("""
        SELECT
            date,
            COUNT(DISTINCT unit_id)         AS units_reporting,
            SUM(gross_revenue)              AS network_revenue,
            SUM(transactions)               AS total_transactions,
            ROUND(AVG(avg_ticket)::numeric,2) AS avg_ticket,
            ROUND(AVG(productivity)::numeric,2) AS avg_productivity,
            SUM(stockout_count)             AS total_stockouts,
            SUM(waste_value)                AS total_waste,
            ROUND(AVG(nps_score)::numeric,1) AS avg_nps
        FROM unit_daily_kpis
        WHERE date >= NOW() - INTERVAL '1 day' * $1
        GROUP BY date
        ORDER BY date DESC
    """, days)
    return {"days": days, "data": [dict(r) for r in rows]}


@app.post("/operacoes/kpis/diario", tags=["operacoes"],
          summary="Registra KPI diário de uma unidade")
async def create_daily_kpi(body: KPIDailyInput, db = Depends(get_db)):
    """Lança KPI diário de uma loja"""
    try:
        row = await db.fetchrow("""
            INSERT INTO unit_daily_kpis (
                unit_id, date, gross_revenue, transactions,
                team_hours, stockout_count, waste_value, nps_score
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            ON CONFLICT (unit_id, date) DO UPDATE SET
                gross_revenue=EXCLUDED.gross_revenue,
                transactions=EXCLUDED.transactions,
                team_hours=EXCLUDED.team_hours,
                stockout_count=EXCLUDED.stockout_count,
                waste_value=EXCLUDED.waste_value,
                nps_score=EXCLUDED.nps_score
            RETURNING id, avg_ticket, productivity
        """, body.unit_id, body.date, body.gross_revenue, body.transactions,
             body.team_hours, body.stockout_count, body.waste_value, body.nps_score)

        return {
            "id": str(row["id"]),
            "avg_ticket": float(row["avg_ticket"] or 0),
            "productivity": float(row["productivity"] or 0),
            "ticket_status": "OK" if (row["avg_ticket"] or 0) >= 35 else "ABAIXO DO TARGET"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/operacoes/ranking", tags=["operacoes"],
         summary="Ranking operacional das lojas")
async def units_ranking(
    metric: str = Query(default="cmv", description="cmv | revenue | ticket | nps"),
    db = Depends(get_db)
):
    """Ranking de unidades por métrica escolhida"""
    order_map = {
        "cmv":     "uf.cmv_pct ASC",
        "revenue": "uf.gross_revenue DESC",
        "ticket":  "AVG(dk.avg_ticket) DESC",
        "nps":     "AVG(dk.nps_score) DESC",
    }
    order = order_map.get(metric, "uf.cmv_pct ASC")

    rows = await db.fetch(f"""
        SELECT
            u.code, u.name, u.city, u.format,
            ROUND(uf.cmv_pct*100,2) AS cmv_pct,
            uf.gross_revenue,
            ROUND(AVG(dk.avg_ticket)::numeric,2) AS avg_ticket,
            ROUND(AVG(dk.nps_score)::numeric,1) AS avg_nps,
            u.color_status
        FROM units u
        LEFT JOIN unit_financials uf ON uf.unit_id=u.id
            AND uf.month=DATE_TRUNC('month', NOW()-INTERVAL '1 month')
        LEFT JOIN unit_daily_kpis dk ON dk.unit_id=u.id
            AND dk.date >= NOW()-INTERVAL '30 days'
        WHERE u.status='ativo'
        GROUP BY u.code,u.name,u.city,u.format,uf.cmv_pct,uf.gross_revenue,u.color_status
        ORDER BY {order}
    """)
    return {"metric": metric, "ranking": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# ── BI — DASHBOARDS & ALERTAS ───────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/bi/dashboard", tags=["bi"],
         summary="Dashboard executivo — Frank Command Center")
async def executive_dashboard(db = Depends(get_db)):
    """KPIs do painel executivo central — 16 indicadores"""
    row = await db.fetchrow("SELECT * FROM vw_executive_dashboard")
    
    # Adiciona benchmarks e status
    cmv = float(row["avg_cmv"] or 26.5)
    return {
        "financial": {
            "monthly_revenue":      float(row["monthly_revenue"] or 0),
            "avg_cmv_pct":          cmv,
            "cmv_status":           "CRÍTICO" if cmv > 30 else "ALERTA" if cmv > 28 else "OK",
            "cmv_vs_market":        round(35.0 - cmv, 1),  # vantagem competitiva pp
            "monthly_royalties":    float(row["monthly_royalties"] or 0),
        },
        "operational": {
            "active_units":         int(row["active_units"] or 0),
            "avg_ticket_30d":       float(row["avg_ticket_30d"] or 0),
            "ticket_target":        35.0,
            "avg_nps":              float(row["avg_nps"] or 0),
            "nps_target":           70,
        },
        "alerts": {
            "critical_count":       int(row["critical_alerts"] or 0),
            "pending_tasks":        int(row["pending_tasks"] or 0),
        },
        "targets": OPERATIONAL_TARGETS,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/bi/alertas", tags=["bi"], summary="Alertas ativos da rede")
async def get_alerts(
    severity: Optional[str] = None,
    unit_id:  Optional[str] = None,
    db = Depends(get_db)
):
    """Lista todos os alertas ativos com filtros opcionais"""
    where = "WHERE is_active = true"
    params = []
    i = 1
    if severity:
        where += f" AND severity = ${i}"; params.append(severity); i += 1
    if unit_id:
        where += f" AND unit_id = ${i}"; params.append(unit_id); i += 1

    rows = await db.fetch(f"""
        SELECT a.id, u.name AS unit_name, a.severity, a.category,
               a.title, a.description, a.metric_value, a.threshold_value,
               a.created_at
        FROM alerts a
        LEFT JOIN units u ON u.id = a.unit_id
        {where}
        ORDER BY
            CASE severity WHEN 'critico' THEN 1 WHEN 'alerta' THEN 2
                         WHEN 'atencao' THEN 3 ELSE 4 END,
            a.created_at DESC
    """, *params)

    return {
        "total": len(rows),
        "critical": sum(1 for r in rows if r["severity"] == "critico"),
        "alerts": [dict(r) for r in rows]
    }


@app.post("/bi/alertas/acknowledge", tags=["bi"],
          summary="Reconhece e resolve um alerta")
async def acknowledge_alert(body: AlertAcknowledge, db = Depends(get_db)):
    """Marca alerta como reconhecido e inicia resolução"""
    await db.execute("""
        UPDATE alerts SET
            is_active = false,
            acknowledged_at = NOW(),
            acknowledged_by = $1,
            resolved_at = NOW()
        WHERE id = $2
    """, body.acknowledged_by, body.alert_id)
    return {"acknowledged": True, "alert_id": body.alert_id}


@app.post("/bi/cmv/verificar-alertas", tags=["bi"],
          summary="Executa verificação de alertas CMV")
async def run_cmv_alerts(db = Depends(get_db)):
    """Trigger manual para verificação de CMV e geração de alertas"""
    await db.execute("SELECT fn_check_cmv_alerts()")
    rows = await db.fetch("SELECT COUNT(*) as total FROM alerts WHERE is_active=true")
    return {"message": "Verificação executada", "active_alerts": int(rows[0]["total"])}


# ---------------------------------------------------------------------------
# ── EXPANSÃO (CSO) ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/expansao/leads", tags=["expansao"], summary="Pipeline de leads B2B")
async def leads_pipeline(db = Depends(get_db)):
    """Funil de leads para novos franqueados"""
    rows = await db.fetch("SELECT * FROM vw_leads_funnel")
    total = sum(r["total"] for r in rows if r["status"] != "perdido")

    return {
        "total_active": total,
        "conversion_rate": None,
        "funnel": [dict(r) for r in rows]
    }


@app.get("/expansao/unidades/payback", tags=["expansao"],
         summary="Payback de todas as unidades ativas")
async def units_payback(db = Depends(get_db)):
    """Calcula payback atual de cada unidade"""
    rows = await db.fetch("""
        SELECT u.code, u.name, u.city, u.opening_date,
               u.initial_investment,
               fn_unit_payback(u.id) AS payback_months,
               fn_unit_roi_24m(u.id) AS roi_24m
        FROM units u
        WHERE u.status = 'ativo'
        AND u.initial_investment > 0
        ORDER BY payback_months ASC
    """)

    result = []
    for r in rows:
        d = dict(r)
        pb = float(d["payback_months"] or 9999)
        d["payback_status"] = (
            "✅ EXCELENTE" if pb <= 18 else
            "✅ OK" if pb <= 24 else
            "⚠️ ALERTA" if pb <= 30 else
            "🔴 CRÍTICO"
        )
        result.append(d)

    return {
        "hard_rule_payback_max": CEO_HARD_RULES["payback_max_months"],
        "hard_rule_roi_min": CEO_HARD_RULES["roi_min_multiplier"],
        "units": result
    }


# ---------------------------------------------------------------------------
# ── UNIDADES — CRUD ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/unidades", tags=["units"], summary="Lista todas as unidades")
async def list_units(
    status: Optional[str] = Query(default="ativo"),
    city:   Optional[str] = None,
    db = Depends(get_db)
):
    where = "WHERE 1=1"
    params = []
    i = 1
    if status:
        where += f" AND u.status = ${i}"; params.append(status); i += 1
    if city:
        where += f" AND u.city ILIKE ${i}"; params.append(f"%{city}%"); i += 1

    rows = await db.fetch(f"""
        SELECT u.*, f.name AS franchisee_name
        FROM units u
        LEFT JOIN franchisees f ON f.id = u.franchisee_id
        {where}
        ORDER BY u.name
    """, *params)
    return {"total": len(rows), "units": [dict(r) for r in rows]}


@app.post("/unidades", tags=["units"], status_code=status.HTTP_201_CREATED,
          summary="Cadastra nova unidade")
async def create_unit(body: UnitCreate, db = Depends(get_db)):
    """Cadastra nova unidade/loja na rede"""
    try:
        row = await db.fetchrow("""
            INSERT INTO units (
                code, name, franchisee_id, format, city, state,
                address, shopping, opening_date, initial_investment,
                franchise_fee, monthly_rent, cluster
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            RETURNING id, code, name, created_at
        """, body.code, body.name, body.franchisee_id, body.format,
             body.city, body.state, body.address, body.shopping,
             body.opening_date, body.initial_investment,
             body.franchise_fee, body.monthly_rent, body.cluster)

        return {"id": str(row["id"]), "code": row["code"],
                "name": row["name"], "created_at": row["created_at"].isoformat()}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"Unidade {body.code} já cadastrada")


@app.get("/unidades/{unit_id}", tags=["units"],
         summary="Detalhes de uma unidade")
async def get_unit(unit_id: str, db = Depends(get_db)):
    """Retorna dados completos de uma unidade incluindo KPIs recentes"""
    unit = await db.fetchrow("""
        SELECT u.*, f.name AS franchisee_name, f.email AS franchisee_email
        FROM units u
        LEFT JOIN franchisees f ON f.id = u.franchisee_id
        WHERE u.id = $1 OR u.code = $1
    """, unit_id)

    if not unit:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    uid = str(unit["id"])
    last_fin = await db.fetchrow("""
        SELECT month, ROUND(cmv_pct*100,2) as cmv_pct,
               gross_revenue, net_income, ROUND(net_margin_pct*100,2) as net_margin_pct,
               ROUND(rent_pct*100,2) as rent_pct, ebitda_operational
        FROM unit_financials WHERE unit_id=$1
        ORDER BY month DESC LIMIT 1
    """, uid)

    last_audit = await db.fetchrow("""
        SELECT audit_date, total_score, classification
        FROM quality_audits WHERE unit_id=$1
        ORDER BY audit_date DESC LIMIT 1
    """, uid)

    return {
        "unit": dict(unit),
        "last_financial": dict(last_fin) if last_fin else None,
        "last_audit": dict(last_audit) if last_audit else None,
        "payback_months": float(await db.fetchval("SELECT fn_unit_payback($1)", uid) or 0),
        "roi_24m": float(await db.fetchval("SELECT fn_unit_roi_24m($1)", uid) or 0),
    }


@app.patch("/unidades/{unit_id}/status", tags=["units"],
           summary="Atualiza status de uma unidade")
async def update_unit_status(
    unit_id: str,
    new_status: str = Query(..., description="verde|amarelo|laranja|vermelho"),
    db = Depends(get_db)
):
    await db.execute("""
        UPDATE units SET color_status=$1, updated_at=NOW() WHERE id=$2 OR code=$2
    """, new_status, unit_id)
    return {"updated": True, "new_status": new_status}


# ---------------------------------------------------------------------------
# ── TAREFAS (MODO EXECUÇÃO) ──────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.get("/tasks", tags=["core"], summary="Lista tarefas do Frank")
async def list_tasks(
    status: Optional[str] = Query(default="pending"),
    db = Depends(get_db)
):
    rows = await db.fetch("""
        SELECT id, task_type, status, priority, scheduled_for,
               started_at, completed_at,
               LEFT(payload::text, 200) as payload_preview
        FROM frank_tasks
        WHERE ($1::text IS NULL OR status=$1)
        ORDER BY priority ASC, scheduled_for ASC
        LIMIT 50
    """, status)
    return {"total": len(rows), "tasks": [dict(r) for r in rows]}


async def enqueue_task(task_type: str, payload: dict):
    """Envia tarefa para fila RabbitMQ — execução assíncrona"""
    if not app_state.db_pool:
        return
    async with app_state.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO frank_tasks (task_type, payload)
            VALUES ($1, $2)
        """, task_type, json.dumps(payload))

    if app_state.rabbitmq_conn:
        try:
            channel = await app_state.rabbitmq_conn.channel()
            queue = await channel.declare_queue("frank_tasks", durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps({"type": task_type, "payload": payload}).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue.name
            )
        except Exception as e:
            logger.warning(f"RabbitMQ publish falhou: {e}")


# ---------------------------------------------------------------------------
# ── ERROR HANDLERS ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404,
        content={"error": "Recurso não encontrado", "path": str(request.url)})

@app.exception_handler(500)
async def internal_error(request: Request, exc):
    logger.exception(f"Erro interno: {exc}")
    return JSONResponse(status_code=500,
        content={"error": "Erro interno do Frank AI OS", "detail": str(exc)})


# ---------------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

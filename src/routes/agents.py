"""Frank AI OS — Agent routes: análises on-demand e execução de swarms."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["agents"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    period: str = "today"
    unit_id: Optional[str] = None
    sectors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = {}


class AnalysisResponse(BaseModel):
    task_id: Optional[str] = None
    status: str
    started_at: str
    result: Optional[Dict[str, Any]] = None
    message: str = ""


class ExpansionRequest(BaseModel):
    city: str
    state: str
    neighborhood: Optional[str] = None
    estimated_investment: Optional[float] = None
    candidate_name: Optional[str] = None
    metadata: Optional[Dict] = {}


# ─── CEO Orchestrator ──────────────────────────────────────────────────────────

@router.post("/ceo/analyze", response_model=AnalysisResponse)
async def ceo_full_analysis(req: AnalysisRequest):
    """Executa análise CEO completa (todos os 9 setores em paralelo)."""
    from app.agents.ceo_agent import CEOAgent
    from app.agents.base_agent import AgentContext

    ceo = CEOAgent()
    ctx = AgentContext(
        unit_id=req.unit_id,
        period=req.period,
        metadata=req.metadata or {},
    )

    try:
        result = await ceo.analyze(ctx)
        return AnalysisResponse(
            status="completed",
            started_at=datetime.utcnow().isoformat(),
            result=result,
            message=f"Análise concluída. Alertas: {len(result.get('all_alerts', []))}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ceo/morning-briefing")
async def ceo_morning_briefing():
    """Gera briefing matinal on-demand."""
    from app.agents.ceo_agent import CEOAgent

    try:
        ceo = CEOAgent()
        result = await ceo.morning_briefing()
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ceo/weekly-report")
async def ceo_weekly_report():
    """Gera relatório semanal on-demand."""
    from app.agents.ceo_agent import CEOAgent
    try:
        ceo = CEOAgent()
        result = await ceo.weekly_report()
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Sector Endpoints ──────────────────────────────────────────────────────────

@router.post("/cfo/analyze")
async def cfo_analysis(req: AnalysisRequest):
    """Análise CFO: CMV, EBITDA, rentabilidade por unidade."""
    from app.agents.financial.cfo_agent import CFOAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = CFOAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coo/analyze")
async def coo_analysis(req: AnalysisRequest):
    """Análise COO: NPS, auditoria, processos operacionais."""
    from app.agents.operations.coo_agent import COOAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = COOAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cmo/analyze")
async def cmo_analysis(req: AnalysisRequest):
    """Análise CMO: Meta Ads, engajamento, CRM, pipeline B2B."""
    from app.agents.marketing.cmo_agent import CMOAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = CMOAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/legal/analyze")
async def legal_analysis(req: AnalysisRequest):
    """Análise Jurídica: contratos, COF, eSocial, marcas."""
    from app.agents.legal.legal_agent import LegalAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = LegalAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hr/analyze")
async def hr_analysis(req: AnalysisRequest):
    """Análise RH: headcount, turnover, treinamentos, eNPS."""
    from app.agents.hr.hr_agent import HRAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = HRAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expansion/analyze")
async def expansion_analysis(req: AnalysisRequest):
    """Análise CSO: pipeline de expansão, scoring de leads."""
    from app.agents.expansion.cso_agent import CSOAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = CSOAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expansion/viability")
async def expansion_viability(req: ExpansionRequest):
    """Avalia viabilidade de expansão para nova praça (swarm paralelo)."""
    from app.agents.expansion.cso_agent import CSOAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = CSOAgent()
        ctx = AgentContext(period="expansion_analysis", metadata=req.dict())
        result = await agent.run(ctx, opportunity=req.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supply/analyze")
async def supply_analysis(req: AnalysisRequest):
    """Análise Supply: estoque, desperdício, fornecedores."""
    from app.agents.supply.supply_agent import SupplyAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = SupplyAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bi/analyze")
async def bi_analysis(req: AnalysisRequest):
    """Análise BI: tendências, forecast, anomalias, correlações."""
    from app.agents.intelligence.bi_agent import BIAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = BIAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/implementation/analyze")
async def impl_analysis(req: AnalysisRequest):
    """Análise Implantação: aberturas em andamento, checklists GO-LIVE."""
    from app.agents.implementation.impl_agent import ImplantacaoAgent
    from app.agents.base_agent import AgentContext
    try:
        agent = ImplantacaoAgent()
        ctx = AgentContext(unit_id=req.unit_id, period=req.period)
        result = await agent.run(ctx)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Swarm Endpoints ───────────────────────────────────────────────────────────

@router.post("/swarm/financial-ops")
async def swarm_financial_ops(req: AnalysisRequest):
    """Swarm paralelo: CFO + COO + Supply simultaneamente."""
    from app.agents.financial.cfo_agent import CFOAgent
    from app.agents.operations.coo_agent import COOAgent
    from app.agents.supply.supply_agent import SupplyAgent
    from app.agents.base_agent import AgentContext, ParallelSwarm

    ctx = AgentContext(unit_id=req.unit_id, period=req.period)
    swarm = ParallelSwarm([CFOAgent(), COOAgent(), SupplyAgent()])
    try:
        result = await swarm.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swarm/growth")
async def swarm_growth(req: AnalysisRequest):
    """Swarm paralelo: CMO + CSO + BI simultaneamente."""
    from app.agents.marketing.cmo_agent import CMOAgent
    from app.agents.expansion.cso_agent import CSOAgent
    from app.agents.intelligence.bi_agent import BIAgent
    from app.agents.base_agent import AgentContext, ParallelSwarm

    ctx = AgentContext(unit_id=req.unit_id, period=req.period)
    swarm = ParallelSwarm([CMOAgent(), CSOAgent(), BIAgent()])
    try:
        result = await swarm.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Memory ────────────────────────────────────────────────────────────────────

@router.get("/memory/{agent_name}")
async def get_agent_memory(
    agent_name: str,
    memory_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
):
    """Busca memórias de um agente específico."""
    from app.memory.memory_service import memory_service
    return await memory_service.get_agent_memories(agent_name, memory_type=memory_type, limit=limit)


@router.get("/decisions/patterns")
async def get_decision_patterns(
    sector: Optional[str] = Query(None),
    days_back: int = Query(30, le=90),
):
    """Padrões de decisão dos agentes."""
    from app.services.decision_service import decision_service
    return await decision_service.get_patterns(days_back=days_back, sector=sector)


@router.get("/decisions/violations-summary")
async def get_violations_summary(days_back: int = Query(7, le=30)):
    """Resumo de violações das CEO Rules."""
    from app.services.decision_service import decision_service
    return await decision_service.get_ceo_rules_violations_summary(days_back=days_back)

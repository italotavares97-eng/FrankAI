"""Frank AI OS — Report routes: geração e consulta de relatórios."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
async def list_reports(
    report_type: Optional[str] = Query(None),
    limit: int = Query(10, le=50),
):
    """Lista relatórios recentes."""
    from app.services.report_service import report_service
    return await report_service.get_recent_reports(report_type=report_type, limit=limit)


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(report_id: str):
    """Retorna HTML renderizado de um relatório."""
    from app.services.report_service import report_service
    html = await report_service.get_report_html(report_id)
    if not html:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=html)


@router.post("/generate/morning-briefing")
async def generate_morning_briefing():
    """Gera briefing matinal on-demand e persiste."""
    from app.agents.ceo_agent import CEOAgent
    from app.agents.base_agent import AgentContext
    from app.services.report_service import report_service
    try:
        ceo = CEOAgent()
        result = await ceo.morning_briefing()
        report = await report_service.generate_and_save_morning_briefing(result)
        return {"report_id": report.id, "status": "generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/weekly-dre")
async def generate_weekly_dre():
    """Gera DRE semanal on-demand."""
    from app.agents.ceo_agent import CEOAgent
    from app.agents.base_agent import AgentContext
    from app.services.report_service import report_service
    try:
        ceo = CEOAgent()
        result = await ceo.weekly_report()
        report = await report_service.generate_and_save_weekly_report(result)
        return {"report_id": report.id, "status": "generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/cmv-audit")
async def generate_cmv_audit():
    """Gera relatório de auditoria CMV."""
    from app.agents.financial.cfo_agent import CFOAgent
    from app.agents.base_agent import AgentContext
    from app.services.report_service import report_service
    from datetime import datetime
    try:
        agent = CFOAgent()
        ctx = AgentContext(period="today")
        result = await agent.run(ctx, date=datetime.utcnow().strftime("%Y-%m-%d"))

        # Montar estrutura para template CMV
        units = result.get("units", [])
        html = report_service.build_cmv_audit_html({"units": units})

        report = await report_service.save_report(
            report_type="cmv_audit",
            title=f"Auditoria CMV — {datetime.utcnow().strftime('%d/%m/%Y')}",
            html_content=html,
            generated_by="cfo_agent",
            raw_data=result,
        )
        return {"report_id": report.id, "status": "generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/top")
async def get_top_insights(
    sector: Optional[str] = Query(None),
    days_back: int = Query(30, le=90),
    limit: int = Query(10, le=50),
):
    """Top insights de maior impacto."""
    from app.memory.memory_service import memory_service
    return await memory_service.get_top_insights(
        sector=sector,
        days_back=days_back,
        limit=limit,
    )

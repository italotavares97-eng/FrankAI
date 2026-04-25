"""Frank AI OS — Serviço de relatórios: HTML artifacts + PDF + armazenamento."""

import asyncio
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.memory.models import Report

logger = get_logger("report_service")


# ─── Templates HTML ────────────────────────────────────────────────────────────

REPORT_BASE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0F172A; --card: #1E293B; --border: #334155;
      --text: #F1F5F9; --muted: #94A3B8; --primary: #1A56DB;
      --success: #057A55; --warning: #F59E0B; --danger: #E02424;
      --accent: #8B5CF6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif;
           font-size: 14px; line-height: 1.6; padding: 24px; }}
    .header {{ display: flex; align-items: center; justify-content: space-between;
               border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 28px; }}
    .logo {{ font-size: 22px; font-weight: 700; color: var(--primary); }}
    .logo span {{ color: var(--text); }}
    .meta {{ color: var(--muted); font-size: 12px; text-align: right; }}
    .section {{ margin-bottom: 32px; }}
    .section-title {{ font-size: 16px; font-weight: 600; color: var(--primary);
                      border-left: 3px solid var(--primary); padding-left: 10px; margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
    .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
                 padding: 16px; }}
    .kpi-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 28px; font-weight: 700; margin: 6px 0 2px; }}
    .kpi-delta {{ font-size: 12px; }}
    .kpi-delta.up {{ color: var(--success); }}
    .kpi-delta.down {{ color: var(--danger); }}
    .kpi-delta.neutral {{ color: var(--muted); }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 16px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
    .badge-success {{ background: rgba(5,122,85,.2); color: var(--success); }}
    .badge-warning {{ background: rgba(245,158,11,.2); color: var(--warning); }}
    .badge-danger  {{ background: rgba(224,36,36,.2); color: var(--danger); }}
    .badge-info    {{ background: rgba(26,86,219,.2); color: var(--primary); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: rgba(26,86,219,.15); color: var(--primary); font-weight: 600;
          padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
    td {{ padding: 9px 12px; border-bottom: 1px solid rgba(51,65,85,.5); }}
    tr:hover td {{ background: rgba(255,255,255,.03); }}
    .alert-item {{ border-left: 3px solid var(--danger); padding: 12px 16px; margin-bottom: 8px;
                   background: rgba(224,36,36,.08); border-radius: 0 6px 6px 0; }}
    .alert-item.warning {{ border-color: var(--warning); background: rgba(245,158,11,.08); }}
    .footer {{ border-top: 1px solid var(--border); padding-top: 16px; margin-top: 40px;
               color: var(--muted); font-size: 11px; text-align: center; }}
    pre {{ background: rgba(255,255,255,.05); border-radius: 6px; padding: 14px; white-space: pre-wrap;
           font-size: 12px; color: var(--text); border: 1px solid var(--border); }}
    .ceo-summary {{ background: linear-gradient(135deg, rgba(26,86,219,.15), rgba(139,92,246,.1));
                    border: 1px solid var(--primary); border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
    .go-badge {{ background: var(--success); color: #fff; padding: 4px 12px; border-radius: 6px; font-weight: 700; }}
    .nogo-badge {{ background: var(--danger); color: #fff; padding: 4px 12px; border-radius: 6px; font-weight: 700; }}
  </style>
</head>
<body>
<div class="header">
  <div class="logo">Frank<span> AI OS</span> · Davvero Gelato</div>
  <div class="meta"><strong>{report_type}</strong><br/>{period}<br/>Gerado em {generated_at}</div>
</div>
{body}
<div class="footer">Frank AI OS · Davvero Gelato · {generated_at} · Confidencial</div>
</body>
</html>"""


def _kpi_card(label: str, value: str, delta: str = "", delta_dir: str = "neutral") -> str:
    delta_html = f'<div class="kpi-delta {delta_dir}">{delta}</div>' if delta else ""
    return f"""<div class="kpi-card">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {delta_html}
</div>"""


def _badge(text: str, kind: str = "info") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


class ReportService:

    # ─── HTML Builders ─────────────────────────────────────────────────────────

    def build_morning_briefing_html(self, data: Dict[str, Any]) -> str:
        """Gera HTML do briefing matinal."""
        sector_results = data.get("sector_results", {})
        alerts = data.get("all_alerts", [])
        executive_report = data.get("executive_report", "")

        # KPIs principais
        cfo = sector_results.get("cfo", {})
        coo = sector_results.get("coo", {})

        kpis = "".join([
            _kpi_card("Receita Rede (7d)", f"R$ {cfo.get('total_revenue_7d', 0):,.0f}",
                      f"{cfo.get('revenue_delta_pct', 0):+.1f}% vs sem anterior",
                      "up" if cfo.get("revenue_delta_pct", 0) >= 0 else "down"),
            _kpi_card("CMV Médio Rede", f"{cfo.get('avg_cmv_pct', 0):.1f}%",
                      "✓ OK" if cfo.get("avg_cmv_pct", 30) <= 30 else "⚠ Acima do limite",
                      "success" if cfo.get("avg_cmv_pct", 30) <= 30 else "down"),
            _kpi_card("NPS Médio Rede", f"{coo.get('avg_nps', 0):.0f}",
                      "Promotores: " + str(coo.get("promoters_pct", 0)) + "%",
                      "success" if coo.get("avg_nps", 0) >= 60 else "warning"),
            _kpi_card("Alertas Abertos", str(len(alerts)),
                      f"{sum(1 for a in alerts if a.get('severity') == 'critical')} críticos",
                      "danger" if any(a.get("severity") == "critical" for a in alerts) else "warning"),
        ])

        # Alertas críticos
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        alert_html = ""
        for alert in critical_alerts[:5]:
            alert_html += f"""<div class="alert-item">
  <strong>{alert.get('rule', 'REGRA CEO')}</strong> · {alert.get('unit_id', 'REDE')}
  <br/><span style="color:var(--muted)">{alert.get('message', '')}</span>
</div>"""

        # CEO Summary
        ceo_html = f"""<div class="ceo-summary">
  <div style="font-size:12px;color:var(--muted);margin-bottom:8px">SÍNTESE EXECUTIVA — CEO</div>
  <pre>{executive_report[:2000]}</pre>
</div>"""

        body = f"""
{ceo_html}
<div class="section">
  <div class="section-title">📊 KPIs da Rede</div>
  <div class="grid">{kpis}</div>
</div>
{"<div class='section'><div class='section-title'>🔴 Alertas Críticos</div>" + alert_html + "</div>" if critical_alerts else ""}
"""
        now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        return REPORT_BASE_HTML.format(
            title="Briefing Matinal — Frank AI OS",
            report_type="BRIEFING MATINAL",
            period=f"Data: {datetime.utcnow().strftime('%d/%m/%Y')}",
            generated_at=now,
            body=body,
        )

    def build_weekly_dre_html(self, data: Dict[str, Any]) -> str:
        """Gera HTML do DRE semanal por unidade."""
        sector_results = data.get("sector_results", {})
        cfo = sector_results.get("cfo", {})
        units_data = cfo.get("units", [])

        rows = ""
        for u in units_data:
            cmv = u.get("cmv_pct", 0)
            ebitda = u.get("ebitda_pct", 0)
            cmv_badge = _badge(f"{cmv:.1f}%", "success" if cmv <= 30 else "danger")
            ebitda_badge = _badge(f"{ebitda:.1f}%", "success" if ebitda >= 10 else "warning")
            rows += f"""<tr>
  <td><strong>{u.get('unit_id', '-')}</strong></td>
  <td>R$ {u.get('revenue', 0):,.0f}</td>
  <td>R$ {u.get('transactions', 0):,}</td>
  <td>{cmv_badge}</td>
  <td>{ebitda_badge}</td>
  <td>R$ {u.get('rent_pct', 0):.1f}%</td>
</tr>"""

        table = f"""<div class="card">
<table>
<thead><tr>
  <th>Unidade</th><th>Receita</th><th>Transações</th>
  <th>CMV%</th><th>EBITDA%</th><th>Aluguel%</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>"""

        body = f"""
<div class="section">
  <div class="section-title">📋 DRE por Unidade — Semana</div>
  {table}
</div>
"""
        now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        return REPORT_BASE_HTML.format(
            title="DRE Semanal — Frank AI OS",
            report_type="RELATÓRIO SEMANAL",
            period=f"Semana de {(datetime.utcnow() - timedelta(days=7)).strftime('%d/%m')} a {datetime.utcnow().strftime('%d/%m/%Y')}",
            generated_at=now,
            body=body,
        )

    def build_monthly_html(self, data: Dict[str, Any]) -> str:
        """Gera HTML do relatório mensal consolidado."""
        exec_report = data.get("executive_report", "")
        sector_results = data.get("sector_results", {})

        sector_cards = ""
        sector_icons = {
            "cfo": "💰", "coo": "⚙️", "cmo": "📣",
            "legal": "⚖️", "rh": "👥", "cso": "🗺️",
            "supply": "📦", "bi": "🧠", "implantacao": "🏗️",
        }
        for sector, icon in sector_icons.items():
            res = sector_results.get(sector, {})
            summary = res.get("summary", res.get("analysis", str(res))[:200] if res else "—")
            if isinstance(summary, dict):
                summary = str(summary)[:200]
            sector_cards += f"""<div class="card">
  <div style="font-size:18px;margin-bottom:8px">{icon} <strong style="color:var(--primary)">{sector.upper()}</strong></div>
  <div style="color:var(--muted);font-size:13px">{str(summary)[:300]}</div>
</div>"""

        body = f"""
<div class="ceo-summary">
  <div style="font-size:12px;color:var(--muted);margin-bottom:8px">RELATÓRIO EXECUTIVO MENSAL</div>
  <pre>{exec_report[:3000]}</pre>
</div>
<div class="section">
  <div class="section-title">🏢 Resultados por Setor</div>
  {sector_cards}
</div>
"""
        now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        dt = datetime.utcnow()
        return REPORT_BASE_HTML.format(
            title=f"Relatório Mensal {dt.strftime('%B %Y')} — Frank AI OS",
            report_type="RELATÓRIO MENSAL",
            period=dt.strftime("%B %Y"),
            generated_at=now,
            body=body,
        )

    def build_cmv_audit_html(self, data: Dict[str, Any]) -> str:
        """Gera HTML de auditoria CMV."""
        units = data.get("units", [])

        rows = ""
        for u in units:
            cmv = u.get("cmv_pct", 0)
            status = "OK" if cmv <= 30 else ("⚠ ATENÇÃO" if cmv <= 33 else "🔴 CRÍTICO")
            badge_kind = "success" if cmv <= 30 else ("warning" if cmv <= 33 else "danger")
            rows += f"""<tr>
  <td><strong>{u.get('unit_id')}</strong></td>
  <td>R$ {u.get('revenue', 0):,.0f}</td>
  <td>{_badge(f"{cmv:.1f}%", badge_kind)}</td>
  <td>{_badge(status, badge_kind)}</td>
  <td>{u.get('main_driver', '—')}</td>
</tr>"""

        body = f"""
<div class="section">
  <div class="section-title">🔍 Auditoria CMV por Unidade</div>
  <div class="card">
  <table>
  <thead><tr><th>Unidade</th><th>Receita</th><th>CMV%</th><th>Status</th><th>Driver Principal</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>
</div>
"""
        now = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        return REPORT_BASE_HTML.format(
            title="Auditoria CMV — Frank AI OS",
            report_type="AUDITORIA CMV",
            period=f"Data: {datetime.utcnow().strftime('%d/%m/%Y')}",
            generated_at=now,
            body=body,
        )

    # ─── PDF Generation ────────────────────────────────────────────────────────

    def _generate_pdf_bytes(self, html_content: str, title: str = "Relatório Frank AI OS") -> bytes:
        """Gera PDF a partir do HTML usando ReportLab (fallback sem WeasyPrint)."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            import io

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()

            header_style = ParagraphStyle(
                "Frank_Header", parent=styles["Heading1"],
                fontSize=18, textColor=colors.HexColor("#1A56DB"), spaceAfter=12,
            )
            body_style = ParagraphStyle(
                "Frank_Body", parent=styles["Normal"],
                fontSize=10, leading=14, textColor=colors.HexColor("#0F172A"),
            )

            # Strip HTML tags for basic PDF
            import re
            clean_text = re.sub(r"<[^>]+>", " ", html_content)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            story = [
                Paragraph(title, header_style),
                Spacer(1, 0.5*cm),
                Paragraph(f"Frank AI OS · Davvero Gelato · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC", body_style),
                Spacer(1, 0.5*cm),
                Paragraph(clean_text[:8000], body_style),
            ]
            doc.build(story)
            return buffer.getvalue()
        except Exception as e:
            logger.warning("pdf_fallback_error", error=str(e))
            return b""

    # ─── Storage ───────────────────────────────────────────────────────────────

    async def save_report(
        self,
        report_type: str,
        title: str,
        html_content: str,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        generated_by: str = "system",
        raw_data: Optional[Dict] = None,
        generate_pdf: bool = False,
    ) -> Report:
        """Persiste um relatório no banco de dados."""
        pdf_bytes = b""
        if generate_pdf:
            pdf_bytes = self._generate_pdf_bytes(html_content, title)

        async with get_db_context() as db:
            report = Report(
                report_type=report_type,
                title=title,
                html_content=html_content,
                period_start=period_start,
                period_end=period_end,
                generated_by=generated_by,
                raw_data=raw_data or {},
            )
            if pdf_bytes:
                import base64
                report.pdf_content = base64.b64encode(pdf_bytes).decode()
            db.add(report)
            await db.flush()
            logger.info("report_saved", id=report.id, type=report_type, title=title[:50])
            return report

    async def get_recent_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Busca relatórios recentes."""
        async with get_db_context() as db:
            query = select(Report).order_by(Report.created_at.desc())
            if report_type:
                query = query.where(Report.report_type == report_type)
            query = query.limit(limit)
            result = await db.execute(query)
            reports = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "type": r.report_type,
                    "title": r.title,
                    "period_start": r.period_start.isoformat() if r.period_start else None,
                    "period_end": r.period_end.isoformat() if r.period_end else None,
                    "generated_by": r.generated_by,
                    "created_at": r.created_at.isoformat(),
                    "has_pdf": bool(getattr(r, "pdf_content", None)),
                }
                for r in reports
            ]

    async def get_report_html(self, report_id: str) -> Optional[str]:
        """Retorna HTML de um relatório específico."""
        async with get_db_context() as db:
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalar_one_or_none()
            return report.html_content if report else None

    # ─── Convenience Methods ──────────────────────────────────────────────────

    async def generate_and_save_morning_briefing(self, ceo_result: Dict) -> Report:
        html = self.build_morning_briefing_html(ceo_result)
        return await self.save_report(
            report_type="morning_briefing",
            title=f"Briefing Matinal — {datetime.utcnow().strftime('%d/%m/%Y')}",
            html_content=html,
            period_start=date.today(),
            period_end=date.today(),
            generated_by="ceo_agent",
            raw_data=ceo_result,
        )

    async def generate_and_save_weekly_report(self, ceo_result: Dict) -> Report:
        html = self.build_weekly_dre_html(ceo_result)
        end = date.today()
        start = end - timedelta(days=7)
        return await self.save_report(
            report_type="weekly_dre",
            title=f"DRE Semanal — {start.strftime('%d/%m')} a {end.strftime('%d/%m/%Y')}",
            html_content=html,
            period_start=start,
            period_end=end,
            generated_by="ceo_agent",
            raw_data=ceo_result,
            generate_pdf=True,
        )

    async def generate_and_save_monthly_report(self, ceo_result: Dict) -> Report:
        html = self.build_monthly_html(ceo_result)
        dt = datetime.utcnow()
        start = date(dt.year, dt.month, 1)
        return await self.save_report(
            report_type="monthly",
            title=f"Relatório Mensal — {dt.strftime('%B %Y')}",
            html_content=html,
            period_start=start,
            period_end=date.today(),
            generated_by="ceo_agent",
            raw_data=ceo_result,
            generate_pdf=True,
        )


report_service = ReportService()

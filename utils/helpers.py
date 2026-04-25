# =============================================================================
# UTILS/HELPERS.PY — Frank AI OS
# Funções utilitárias: formatação, cálculos, análise de tendências
# =============================================================================

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# FORMATAÇÃO
# ---------------------------------------------------------------------------

def format_brl(value: float, decimals: int = 2) -> str:
    """Formata valor em Real brasileiro. Ex: 1234567.89 → R$ 1.234.567,89"""
    if value is None:
        return "R$ —"
    try:
        s = f"{abs(value):,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        prefix = "R$ -" if value < 0 else "R$ "
        return f"{prefix}{s}"
    except (ValueError, TypeError):
        return "R$ —"

def format_pct(value: float, decimals: int = 1) -> str:
    """Formata percentual. Ex: 26.5 → 26,5%"""
    if value is None:
        return "—%"
    try:
        s = f"{value:.{decimals}f}".replace(".", ",")
        return f"{s}%"
    except (ValueError, TypeError):
        return "—%"

def format_k(value: float) -> str:
    """Formata número grande. Ex: 1234567 → R$ 1.234k"""
    if value is None:
        return "—"
    if abs(value) >= 1_000_000:
        return f"R$ {value/1_000_000:.1f}M".replace(".", ",")
    if abs(value) >= 1_000:
        return f"R$ {value/1_000:.1f}k".replace(".", ",")
    return format_brl(value)

def fmt_date(d: Union[date, datetime, str], fmt: str = "%d/%m/%Y") -> str:
    """Formata data de forma segura."""
    if d is None:
        return "—"
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d)
        except ValueError:
            return d
    return d.strftime(fmt)

def fmt_month(d: Union[date, datetime, str]) -> str:
    """Formata mês/ano. Ex: 2025-01-01 → Jan/2025"""
    months_pt = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d)
        except ValueError:
            return d
    return f"{months_pt.get(d.month, d.month)}/{d.year}"


# ---------------------------------------------------------------------------
# CÁLCULOS FINANCEIROS
# ---------------------------------------------------------------------------

def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divisão segura — retorna default se denominador é 0."""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default

def calc_cmv_pct(cogs: float, net_revenue: float) -> float:
    """Calcula CMV %."""
    return round(safe_div(cogs, net_revenue) * 100, 2)

def calc_gross_margin(revenue: float, cogs: float) -> Tuple[float, float]:
    """Retorna (margem_bruta_R$, margem_bruta_%)."""
    gross = revenue - cogs
    pct = safe_div(gross, revenue) * 100
    return round(gross, 2), round(pct, 2)

def calc_payback(investment: float, monthly_income: float) -> float:
    """Calcula payback em meses."""
    if monthly_income <= 0:
        return 9999
    return round(investment / monthly_income, 1)

def calc_roi_24m(investment: float, monthly_income: float) -> float:
    """Calcula ROI em 24 meses."""
    if investment <= 0:
        return 0
    return round((monthly_income * 24) / investment, 2)

def calc_net_revenue(gross: float, tax_pct: float = 6.0) -> float:
    """Receita líquida após impostos."""
    return round(gross * (1 - tax_pct / 100), 2)

def calc_rent_pct(rent: float, gross_revenue: float) -> float:
    """Percentual de aluguel sobre faturamento bruto."""
    return round(safe_div(rent, gross_revenue) * 100, 2)


# ---------------------------------------------------------------------------
# ANÁLISE DE TENDÊNCIAS
# ---------------------------------------------------------------------------

def trend_arrow(current: float, previous: float, higher_is_better: bool = True) -> str:
    """
    Retorna emoji de tendência com variação.
    Ex: trend_arrow(27.5, 26.0, higher_is_better=False) → "🔴 +1,5pp"
    """
    if previous == 0:
        return "—"
    delta = current - previous
    delta_str = f"{abs(delta):.1f}".replace(".", ",")

    if abs(delta) < 0.1:
        return f"➡️ {delta_str}"

    is_good = (delta > 0 and higher_is_better) or (delta < 0 and not higher_is_better)
    sign = "+" if delta > 0 else "-"

    if is_good:
        icon = "🟢" if abs(delta) >= 1 else "🟡"
    else:
        icon = "🔴" if abs(delta) >= 2 else "🟠"

    return f"{icon} {sign}{delta_str}"

def classify_cmv(cmv_pct: float) -> Tuple[str, str]:
    """Classifica CMV e retorna (status, emoji)."""
    if cmv_pct > 30:
        return "CRÍTICO", "🔴"
    elif cmv_pct > 28:
        return "ALERTA", "🟠"
    elif cmv_pct > 27:
        return "ATENÇÃO", "🟡"
    else:
        return "OK", "🟢"

def classify_nps(nps: float) -> Tuple[str, str]:
    if nps >= 70:
        return "EXCELENTE", "🟢"
    elif nps >= 55:
        return "BOM", "🟡"
    elif nps >= 40:
        return "ALERTA", "🟠"
    else:
        return "CRÍTICO", "🔴"

def classify_ticket(ticket: float, target: float = 35.0) -> Tuple[str, str]:
    deviation = ticket / target
    if deviation >= 1.0:
        return "ACIMA DO TARGET", "🟢"
    elif deviation >= 0.9:
        return "PRÓXIMO DO TARGET", "🟡"
    else:
        return "ABAIXO DO TARGET", "🔴"


# ---------------------------------------------------------------------------
# PARSING E EXTRAÇÃO
# ---------------------------------------------------------------------------

def extract_percentages(text: str) -> List[float]:
    """Extrai todos os percentuais de um texto."""
    pattern = r"(\d{1,3}(?:[.,]\d+)?)\s*%"
    matches = re.findall(pattern, text)
    return [float(m.replace(",", ".")) for m in matches]

def extract_monetary(text: str) -> List[float]:
    """Extrai valores monetários de um texto."""
    pattern = r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)"
    matches = re.findall(pattern, text)
    result = []
    for m in matches:
        clean = m.replace(".", "").replace(",", ".")
        try:
            result.append(float(clean))
        except ValueError:
            pass
    return result

def sanitize_json(text: str) -> Optional[Dict]:
    """Extrai e parseia JSON de uma resposta de LLM."""
    # Remove markdown code fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.startswith("json"):
                text = part[4:].strip()
                break
            elif "{" in part:
                text = part.strip()
                break

    # Tenta parsear
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Tenta extrair objeto JSON do texto
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


# ---------------------------------------------------------------------------
# TABELAS ASCII PARA RELATÓRIOS
# ---------------------------------------------------------------------------

def make_table(headers: List[str], rows: List[List[Any]], title: str = "") -> str:
    """Cria tabela ASCII para relatórios em texto."""
    if not rows:
        return f"{title}: sem dados"

    # Calcula larguras
    all_rows = [headers] + [[str(c) for c in row] for row in rows]
    widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
    widths = [max(w, 4) for w in widths]

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    def fmt_row(row):
        cells = [f" {str(r):<{w}} " for r, w in zip(row, widths)]
        return "|" + "|".join(cells) + "|"

    lines = []
    if title:
        lines.append(f"\n{title.upper()}")
    lines.append(sep)
    lines.append(fmt_row(headers))
    lines.append(sep.replace("-", "="))
    for row in rows:
        lines.append(fmt_row([str(c) for c in row]))
    lines.append(sep)
    return "\n".join(lines)

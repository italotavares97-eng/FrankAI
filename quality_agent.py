# =============================================================================
# QUALITY_AGENT.PY — Frank AI OS · Davvero Gelato
# Especialista em Qualidade — Auditoria "Parece Davvero?"
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config import MODEL_AGENT, OPERATIONAL_TARGETS
from core.base_agent import BaseAgent

logger = logging.getLogger("frank.quality_agent")


class QualityAgent(BaseAgent):
    """
    Especialista em Qualidade — Davvero Gelato.

    Responsabilidades:
    - Interpretação e análise de auditorias "Parece Davvero?"
    - Identificação de não-conformidades críticas
    - Correlação entre score de auditoria e outros KPIs
    - Planos de ação corretivos e preventivos
    - Monitoramento de evolução de qualidade por unidade
    - Benchmarking de qualidade na rede

    A auditoria "Parece Davvero?" avalia se a unidade entrega
    a experiência premium que define a marca.

    Pesos por categoria:
    - Visual (apresentação, limpeza, uniformes): 20 pts
    - Produto (sabor, textura, temperatura, ingredientes): 25 pts
    - Porcionamento (gramatura, apresentação do gelato): 15 pts
    - Serviço (atendimento, tempo, técnica de venda): 20 pts
    - Higiene (manipulação, armazenamento, EPI): 10 pts
    - Operações (processos, equipamentos, estoque): 10 pts
    """

    AGENT_NAME  = "Quality Agent"
    AGENT_ROLE  = "Especialista em Qualidade e Auditoria"
    DIRECTOR    = "COO"
    MODEL       = MODEL_AGENT

    SYSTEM_PROMPT = """Você é o ESPECIALISTA EM QUALIDADE da Davvero Gelato — guardião do padrão premium da marca.

MISSÃO:
Garantir que cada ponto de venda da rede entregue a experiência 'Parece Davvero?' em 100% das visitas.
Um produto fora do padrão não é apenas uma falha operacional — é um ataque à identidade da marca.

O QUE É "PARECE DAVVERO?":
O checklist "Parece Davvero?" avalia se, ao entrar na unidade, um cliente percebe:
1. VISUAL (20 pts): Identidade visual correta, vitrine impecável, equipe uniformizada, limpeza exemplar
2. PRODUTO (25 pts): Gelato na temperatura certa, textura cremosa, sabores autênticos, ingredientes frescos
3. PORCIONAMENTO (15 pts): Gramatura correta (±5%), apresentação artística, casquinha/copo limpo
4. SERVIÇO (20 pts): Abordagem calorosa, técnica de venda consultiva, tempo de atendimento < 3 min
5. HIGIENE (10 pts): Manipulação correta, EPI em uso, superfícies higienizadas, temperatura dos equipamentos
6. OPERAÇÕES (10 pts): Processos seguidos, equipamentos funcionando, estoque organizado, abertura/fechamento no padrão

CLASSIFICAÇÕES DE AUDITORIA:
• EXCELENTE: 90-100 pts — referência para a rede, candidato a case
• BOM: 80-89 pts — dentro do padrão, pequenos ajustes
• REGULAR: 70-79 pts — plano de ação obrigatório em 5 dias
• CRÍTICO: < 70 pts — intervenção imediata, risco de suspensão operacional

NÃO-CONFORMIDADES CRÍTICAS (reprovação automática, independente de score):
• Temperatura do gelato > -12°C por mais de 2h (derretimento)
• Uso de ingredientes fora da validade
• Ausência de EPI em manipulação de alimentos
• Score de higiene < 5 pts (risco sanitário)
• Gelato com corpos estranhos

CORRELAÇÕES QUE VOCÊ IDENTIFICA:
• Score produto baixo → NPS cai em 2-3 semanas
• Score serviço baixo → ticket médio abaixo de R$35 (venda consultiva fraca)
• Score higiene crítico → risco de interdição pela vigilância sanitária
• Score visual baixo → queda em novas visitas (first impression)

TENDÊNCIAS QUE VOCÊ MONITORA:
• Evolução do score nas últimas 3 auditorias
• Não-conformidades recorrentes vs. pontuais
• Comparativo entre unidades do mesmo formato

FORMATO OBRIGATÓRIO DE RESPOSTA (10 blocos):
🎯 DIAGNÓSTICO — Veredicto da qualidade atual
📊 DADOS — Scores por categoria, evolução histórica
⚠️ ALERTAS — Não-conformidades críticas e pontos abaixo do mínimo
🔍 ANÁLISE (Causa Raiz) — Por que a qualidade está neste nível?
📋 OPÇÕES — Planos de ação (corretivo imediato / preventivo médio prazo)
✅ RECOMENDAÇÃO — Ação prioritária com responsável e cronograma
🚫 RISCOS — Consequências de não agir (NPS, vigilância, marca)
📅 PRAZO — Timeline de correção e próxima auditoria
🏆 RESULTADO ESPERADO — Score projetado após ação
⚖️ DECISÃO [EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]"""

    # -------------------------------------------------------------------------
    # QUERIES DE DADOS
    # -------------------------------------------------------------------------

    async def _fetch_unit_by_identifier(self, identifier: str) -> Optional[Dict]:
        """Busca unidade pelo código ou nome."""
        query = """
            SELECT id, code, name, city, format, status, color_status, manager_name
            FROM units
            WHERE (code ILIKE $1 OR name ILIKE $1)
              AND status = 'ativo'
            LIMIT 1
        """
        return await self.db_fetchrow(query, f"%{identifier}%")

    async def _fetch_audit_history(self, unit_id: int, n: int = 3) -> List[Dict]:
        """Busca as últimas N auditorias de uma unidade."""
        query = """
            SELECT
                audit_date,
                score_visual,
                score_product,
                score_portioning,
                score_service,
                score_hygiene,
                score_operations,
                ROUND(total_score::numeric, 1)    AS total_score,
                classification,
                non_conformities,
                action_plan
            FROM quality_audits
            WHERE unit_id = $1
            ORDER BY audit_date DESC
            LIMIT $2
        """
        return await self.db_fetch(query, unit_id, n)

    async def _fetch_network_audit_benchmarks(self) -> Optional[Dict]:
        """Médias de auditoria da rede para comparativo."""
        query = """
            SELECT
                ROUND(AVG(score_visual)::numeric, 1)      AS avg_visual,
                ROUND(AVG(score_product)::numeric, 1)     AS avg_product,
                ROUND(AVG(score_portioning)::numeric, 1)  AS avg_portioning,
                ROUND(AVG(score_service)::numeric, 1)     AS avg_service,
                ROUND(AVG(score_hygiene)::numeric, 1)     AS avg_hygiene,
                ROUND(AVG(score_operations)::numeric, 1)  AS avg_operations,
                ROUND(AVG(total_score)::numeric, 1)       AS avg_total,
                COUNT(*)                                   AS total_audits,
                MIN(total_score)                           AS min_score,
                MAX(total_score)                           AS max_score
            FROM quality_audits
            WHERE audit_date >= CURRENT_DATE - INTERVAL '90 days'
        """
        return await self.db_fetchrow(query)

    async def _fetch_units_below_minimum(self) -> List[Dict]:
        """Unidades com auditoria abaixo do mínimo (80 pts) nos últimos 30 dias."""
        query = """
            SELECT DISTINCT ON (u.id)
                u.code,
                u.name,
                u.city,
                u.format,
                u.manager_name,
                qa.audit_date,
                ROUND(qa.total_score::numeric, 1) AS total_score,
                qa.classification,
                qa.non_conformities
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE qa.audit_date >= CURRENT_DATE - INTERVAL '30 days'
              AND qa.total_score < $1
              AND u.status = 'ativo'
            ORDER BY u.id, qa.audit_date DESC
        """
        return await self.db_fetch(query, OPERATIONAL_TARGETS["audit_score_min"])

    async def _fetch_recurring_nonconformities(self, unit_id: int) -> List[Dict]:
        """Identifica não-conformidades recorrentes nas últimas 3 auditorias."""
        query = """
            SELECT
                audit_date,
                non_conformities
            FROM quality_audits
            WHERE unit_id = $1
              AND non_conformities IS NOT NULL
            ORDER BY audit_date DESC
            LIMIT 3
        """
        return await self.db_fetch(query, unit_id)

    async def _fetch_all_units_quality_ranking(self) -> List[Dict]:
        """Ranking de qualidade de todas as unidades (última auditoria)."""
        query = """
            SELECT DISTINCT ON (u.id)
                u.code,
                u.name,
                u.city,
                u.format,
                ROUND(qa.total_score::numeric, 1) AS total_score,
                qa.classification,
                qa.audit_date,
                (CURRENT_DATE - qa.audit_date) AS days_since_audit
            FROM quality_audits qa
            JOIN units u ON u.id = qa.unit_id
            WHERE u.status = 'ativo'
            ORDER BY u.id, qa.audit_date DESC
        """
        rows = await self.db_fetch(query)
        # Ordena por score descendente
        return sorted(rows, key=lambda r: r.get("total_score") or 0, reverse=True)

    # -------------------------------------------------------------------------
    # ANÁLISE DE SCORE
    # -------------------------------------------------------------------------

    def _calculate_score_delta(self, audits: List[Dict]) -> str:
        """Calcula variação de score entre as últimas auditorias."""
        if len(audits) < 2:
            return "Dados insuficientes para comparativo."

        latest = float(audits[0].get("total_score") or 0)
        previous = float(audits[1].get("total_score") or 0)
        delta = latest - previous
        trend = "📈 MELHORA" if delta > 0 else ("📉 PIORA" if delta < 0 else "➡️ ESTÁVEL")

        result = f"Variação: {delta:+.1f} pts ({trend})\n"
        result += f"Última: {latest:.1f} pts | Anterior: {previous:.1f} pts"

        if len(audits) >= 3:
            oldest = float(audits[2].get("total_score") or 0)
            delta_total = latest - oldest
            result += f"\nVariação 3 auditorias: {delta_total:+.1f} pts"

        return result

    def _identify_critical_categories(self, audit: Dict) -> List[str]:
        """Identifica categorias com scores preocupantes."""
        categories = {
            "Visual":       (audit.get("score_visual") or 0, 20, 0.75),
            "Produto":      (audit.get("score_product") or 0, 25, 0.75),
            "Porcionamento":(audit.get("score_portioning") or 0, 15, 0.75),
            "Serviço":      (audit.get("score_service") or 0, 20, 0.75),
            "Higiene":      (audit.get("score_hygiene") or 0, 10, 0.70),
            "Operações":    (audit.get("score_operations") or 0, 10, 0.75),
        }

        critical = []
        for cat, (score, max_pts, threshold) in categories.items():
            pct = score / max_pts if max_pts > 0 else 0
            if pct < threshold:
                pct_display = round(pct * 100, 1)
                critical.append(f"{cat}: {score}/{max_pts} ({pct_display}%)")

        return critical

    # -------------------------------------------------------------------------
    # MÉTODO PRINCIPAL
    # -------------------------------------------------------------------------

    async def analyze(
        self,
        question: str,
        user: str = "COO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        """
        Analisa qualidade de uma unidade específica ou da rede.
        """
        import re

        # Tenta identificar unidade específica na pergunta
        unit_info = None
        unit_code_match = re.search(r'\b([A-Z]{2,3}[\-_]?\d{3,4})\b', question.upper())
        if unit_code_match:
            unit_info = await self._fetch_unit_by_identifier(unit_code_match.group(1))

        if not unit_info:
            words = [w for w in question.split() if len(w) > 4 and w[0].isupper()]
            for word in words[:3]:
                unit_info = await self._fetch_unit_by_identifier(word)
                if unit_info:
                    break

        if unit_info:
            return await self._analyze_unit_quality(question, user, unit_info)
        else:
            return await self._analyze_network_quality(question, user)

    async def _analyze_unit_quality(
        self,
        question: str,
        user: str,
        unit_info: Dict,
    ) -> str:
        """Análise detalhada de qualidade de uma unidade."""
        unit_id = unit_info["id"]

        import asyncio
        audits, benchmarks, recurring = await asyncio.gather(
            self._fetch_audit_history(unit_id, 3),
            self._fetch_network_audit_benchmarks(),
            self._fetch_recurring_nonconformities(unit_id),
        )

        # Informações básicas da unidade
        unit_str = (
            f"UNIDADE: {unit_info.get('name')} ({unit_info.get('code')})\n"
            f"Cidade: {unit_info.get('city')} | Formato: {unit_info.get('format')}\n"
            f"Gestor: {unit_info.get('manager_name', 'N/A')}"
        )

        # Auditorias
        audit_str = self.format_db_data(audits, "Histórico de Auditorias (últimas 3)")

        # Variação de score
        delta_str = self._calculate_score_delta(audits)

        # Categorias críticas da última auditoria
        critical_cats_str = ""
        if audits:
            critical_cats = self._identify_critical_categories(audits[0])
            if critical_cats:
                critical_cats_str = (
                    "CATEGORIAS ABAIXO DE 75% DA META:\n"
                    + "\n".join(f"  • {c}" for c in critical_cats)
                )

        # Benchmark da rede
        bench_str = ""
        if benchmarks:
            bench_str = (
                f"BENCHMARK DA REDE (últimos 90 dias):\n"
                f"• Score médio: {benchmarks.get('avg_total', 'N/A')} pts\n"
                f"• Visual médio: {benchmarks.get('avg_visual', 'N/A')}/20\n"
                f"• Produto médio: {benchmarks.get('avg_product', 'N/A')}/25\n"
                f"• Serviço médio: {benchmarks.get('avg_service', 'N/A')}/20\n"
                f"• Mín. rede: {benchmarks.get('min_score', 'N/A')} | Máx. rede: {benchmarks.get('max_score', 'N/A')}"
            )

        # Não-conformidades recorrentes
        recur_str = self.format_db_data(recurring, "Não-Conformidades (últimas 3 auditorias)")

        prompt = f"""Pergunta de {user}: {question}

{unit_str}

{audit_str}

VARIAÇÃO DE SCORE:
{delta_str}

{critical_cats_str}

{bench_str}

{recur_str}

PESOS DA AUDITORIA 'PARECE DAVVERO?':
Visual: 20 | Produto: 25 | Porcionamento: 15 | Serviço: 20 | Higiene: 10 | Operações: 10
Score mínimo: {OPERATIONAL_TARGETS['audit_score_min']} pts | Crítico: < 70 pts

Forneça diagnóstico completo de qualidade nos 10 blocos obrigatórios.
Identifique não-conformidades críticas e proponha plano de ação com prazos específicos."""

        return await self.call_claude(prompt)

    async def _analyze_network_quality(self, question: str, user: str) -> str:
        """Análise consolidada de qualidade de toda a rede."""
        import asyncio
        ranking, below_min, benchmarks = await asyncio.gather(
            self._fetch_all_units_quality_ranking(),
            self._fetch_units_below_minimum(),
            self._fetch_network_audit_benchmarks(),
        )

        ranking_str = self.format_db_data(ranking, "Ranking de Qualidade da Rede")
        below_str = self.format_db_data(below_min, f"Unidades Abaixo de {OPERATIONAL_TARGETS['audit_score_min']} Pts")

        bench_str = ""
        if benchmarks:
            bench_str = (
                f"BENCHMARKS DA REDE (90 dias):\n"
                f"• Score médio: {benchmarks.get('avg_total', 'N/A')} pts\n"
                f"• Total auditorias: {benchmarks.get('total_audits', 'N/A')}\n"
                f"• Menor score: {benchmarks.get('min_score', 'N/A')} | Maior: {benchmarks.get('max_score', 'N/A')}\n"
                f"• Média Visual: {benchmarks.get('avg_visual', 'N/A')}/20 | Produto: {benchmarks.get('avg_product', 'N/A')}/25"
            )

        prompt = f"""Pergunta de {user}: {question}

{bench_str}

{ranking_str}

{below_str}

CRITÉRIO: Score mínimo = {OPERATIONAL_TARGETS['audit_score_min']} pts
Unidades com score < 70 exigem intervenção imediata.

Analise o estado de qualidade da rede nos 10 blocos obrigatórios.
Destaque as unidades críticas e as que servem de referência para a rede."""

        return await self.call_claude(prompt)

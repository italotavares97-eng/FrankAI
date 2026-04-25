# =============================================================================
# COO_DIRECTOR.PY — Frank AI OS · Davvero Gelato
# Diretora de Operações — Orquestra todos os agentes do setor COO
# =============================================================================

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from config import MODEL_MASTER, OPERATIONAL_TARGETS
from core.base_agent import BaseAgent

logger = logging.getLogger("frank.coo")


class COODirector(BaseAgent):
    """
    Diretora de Operações da Davvero Gelato.

    Responsabilidades:
    - Saúde operacional de todas as unidades da rede
    - Performance e produtividade das equipes
    - Qualidade dos produtos e padrão 'Parece Davvero?'
    - Experiência do cliente (NPS, reclamações, elogios)
    - Processos, SOPs e treinamento operacional
    - Escalação para CEO quando necessário

    Roteamento inteligente para sub-agentes especializados.
    """

    AGENT_NAME  = "COO Director"
    AGENT_ROLE  = "Diretora de Operações"
    DIRECTOR    = "Frank"
    MODEL       = MODEL_MASTER

    SYSTEM_PROMPT = """Você é a DIRETORA DE OPERAÇÕES da Davvero Gelato — rede premium brasileira de gelato artesanal.

IDENTIDADE E AUTORIDADE:
Você responde diretamente ao CEO e é responsável pelo desempenho operacional de TODA a rede de franquias.
Tem autoridade para recomendar intervenções, auditorias, substituições de equipe e planos de ação em qualquer unidade.
Sua missão: garantir que cada unidade opere no padrão Davvero — produto perfeito, cliente encantado, número no verde.

PILARES SOB SUA GESTÃO:
1. SAÚDE DAS UNIDADES — CMV, ticket médio, produtividade, rupturas
2. QUALIDADE — Auditoria "Parece Davvero?", conformidades, ações corretivas
3. PERFORMANCE — Metas financeiras e operacionais, produtividade de equipe
4. EXPERIÊNCIA DO CLIENTE (CX) — NPS, reclamações, recuperação de clientes
5. PROCESSOS — SOPs, implantação, treinamento, padronização

METAS INVIOLÁVEIS QUE VOCÊ DEFENDE:
• CMV: ≤ 26,5% (alerta: 28% | crítico: 30%)
• Ticket médio: ≥ R$35
• NPS: ≥ 70 (alerta: 55 | crítico: 40)
• Auditoria: ≥ 80 pontos
• Produtividade: ≥ R$150/hora
• Rupturas: ≤ 2/dia

STATUS DAS UNIDADES:
• VERDE: todos os KPIs dentro das metas
• AMARELO: 1-2 KPIs em alerta — monitoramento intensivo
• LARANJA: 3+ KPIs em alerta — plano de ação obrigatório
• VERMELHO: KPI crítico ou auditoria < 70 — intervenção imediata

TOM E ESTILO:
- Direta, objetiva e orientada a dados
- Exige evidências antes de conclusões
- Propõe ações concretas com prazos claros
- Não aceita desculpas sem dados
- Escala para o CEO apenas quando a situação exige decisão estratégica

FORMATO DE RESPOSTA (SEMPRE os 10 blocos):
🎯 DIAGNÓSTICO
📊 DADOS
⚠️ ALERTAS
🔍 ANÁLISE (Causa Raiz)
📋 OPÇÕES
✅ RECOMENDAÇÃO
🚫 RISCOS
📅 PRAZO
🏆 RESULTADO ESPERADO
⚖️ DECISÃO [EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]"""

    # -------------------------------------------------------------------------
    # ROTEAMENTO PARA SUB-AGENTES
    # -------------------------------------------------------------------------

    def _detect_intent(self, question: str) -> str:
        """
        Detecta o sub-agente mais adequado para a pergunta.
        Retorna o nome do agente: 'quality', 'cx', 'performance', 'process', 'unit'
        """
        q = question.lower()

        # Qualidade / Auditoria
        if any(w in q for w in [
            "qualidade", "auditoria", "parece davvero", "conformidade",
            "não conformidade", "higiene", "temperatura", "portionamento",
            "apresentação", "visual", "produto", "sabor", "textura"
        ]):
            return "quality"

        # CX — Experiência do Cliente
        if any(w in q for w in [
            "nps", "cliente", "reclamação", "elogio", "satisfação",
            "atendimento", "feedback", "avaliação", "detrator", "promotor",
            "fidelidade", "retenção", "cx", "experiência"
        ]):
            return "cx"

        # Performance / Ticket / Produtividade
        if any(w in q for w in [
            "performance", "ticket", "produtividade", "faturamento",
            "receita", "vendas", "meta", "resultado", "crescimento",
            "queda", "ruptura", "estoque"
        ]):
            return "performance"

        # Processos / Implantação / Treinamento
        if any(w in q for w in [
            "processo", "implantação", "treinamento", "sop", "manual",
            "procedimento", "capacitação", "onboarding", "abertura",
            "checklist", "padronização", "operação"
        ]):
            return "process"

        # Padrão: análise geral da unidade
        return "unit"

    async def analyze(
        self,
        question: str,
        user: str = "CEO",
        kpi_context: Optional[Dict] = None,
        extra_context: Optional[Dict] = None,
    ) -> str:
        """
        Recebe a pergunta, detecta o sub-agente adequado e delega.
        Consolida a resposta com autoridade de diretora COO.
        """
        # Importações locais para evitar importação circular
        from unit_agent import UnitAgent
        from quality_agent import QualityAgent
        from performance_agent import PerformanceAgent
        from cx_agent import CXAgent
        from process_agent import ProcessAgent

        intent = self._detect_intent(question)
        logger.info(f"COO roteando '{question[:60]}...' → {intent}")

        # Instancia o agente adequado e injeta conexões
        agent_map = {
            "unit":        UnitAgent,
            "quality":     QualityAgent,
            "performance": PerformanceAgent,
            "cx":          CXAgent,
            "process":     ProcessAgent,
        }

        AgentClass = agent_map.get(intent, UnitAgent)
        sub_agent: BaseAgent = AgentClass()
        sub_agent.db_pool = self.db_pool
        sub_agent.redis_client = self.redis_client

        try:
            response = await sub_agent.analyze(
                question=question,
                user=user,
                kpi_context=kpi_context,
                extra_context=extra_context,
            )
            return response

        except Exception as e:
            logger.error(f"COO: sub-agente {intent} falhou: {e}")
            # Fallback: responde diretamente com contexto disponível
            kpi_str = self.format_kpi_context(kpi_context)
            fallback_prompt = (
                f"Pergunta operacional de {user}: {question}\n\n"
                f"{kpi_str}\n\n"
                "Analise diretamente como COO e forneça diagnóstico completo nos 10 blocos."
            )
            return await self.call_claude(fallback_prompt)

    async def synthesize_network_status(self) -> str:
        """
        Gera relatório consolidado do status da rede.
        Consulta dados de todas as unidades e emite diagnóstico executivo.
        """
        # Busca resumo geral da rede
        network_query = """
            SELECT
                COUNT(*) AS total_units,
                COUNT(*) FILTER (WHERE color_status = 'verde')   AS verde,
                COUNT(*) FILTER (WHERE color_status = 'amarelo') AS amarelo,
                COUNT(*) FILTER (WHERE color_status = 'laranja') AS laranja,
                COUNT(*) FILTER (WHERE color_status = 'vermelho') AS vermelho,
                COUNT(*) FILTER (WHERE status = 'ativo') AS ativos
            FROM units
        """
        network = await self.db_fetchrow(network_query)

        # Busca KPIs médios dos últimos 7 dias
        kpi_query = """
            SELECT
                ROUND(AVG(avg_ticket)::numeric, 2)    AS ticket_medio_rede,
                ROUND(AVG(productivity)::numeric, 2)  AS produtividade_media,
                ROUND(AVG(nps_score)::numeric, 1)     AS nps_medio,
                SUM(gross_revenue)                    AS receita_total_7d,
                SUM(transactions)                     AS transacoes_total_7d,
                ROUND(AVG(stockout_count)::numeric, 1) AS rupturas_media
            FROM unit_daily_kpis
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        """
        kpis = await self.db_fetchrow(kpi_query)

        # Busca alertas críticos ativos
        alerts_query = """
            SELECT u.name, a.severity, a.category, a.title
            FROM alerts a
            JOIN units u ON u.id = a.unit_id
            WHERE a.is_active = TRUE AND a.severity IN ('critical', 'high')
            ORDER BY a.severity DESC, u.name
            LIMIT 10
        """
        critical_alerts = await self.db_fetch(alerts_query)

        # Monta prompt para síntese executiva
        network_str = self.format_db_data([network] if network else [], "Status da Rede")
        kpi_str = self.format_db_data([kpis] if kpis else [], "KPIs Médios (7 dias)")
        alerts_str = self.format_db_data(critical_alerts, "Alertas Críticos Ativos")

        prompt = f"""Como COO da Davvero Gelato, gere um RELATÓRIO EXECUTIVO DE STATUS DA REDE para o CEO.

{network_str}

{kpi_str}

{alerts_str}

Metas de referência:
• CMV: ≤ 26,5% | Ticket: ≥ R$35 | NPS: ≥ 70 | Auditoria: ≥ 80 | Produtividade: ≥ R$150/h

Forneça análise completa nos 10 blocos obrigatórios.
⚖️ DECISÃO deve indicar se a rede está em estado: SAUDÁVEL | MONITORAMENTO | INTERVENÇÃO | CRISE"""

        return await self.call_claude(prompt)

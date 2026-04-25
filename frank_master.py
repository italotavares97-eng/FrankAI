# =============================================================================
# FRANK_MASTER.PY — Frank AI OS · Davvero Gelato
# CEO Agent — Orquestrador Central do Sistema
# =============================================================================
# Frank é o sistema operacional de IA do CEO da Davvero Gelato.
# Recebe qualquer input, roteia ao diretor correto, valida contra
# Hard Rules do CEO e retorna resposta executiva estruturada em 10 blocos.
# =============================================================================

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic

from config import (
    ANTHROPIC_API_KEY, MODEL_MASTER, MODEL_FAST,
    CEO_HARD_RULES, OPERATIONAL_TARGETS, BRAND,
)

logger = logging.getLogger("frank_master")

# =============================================================================
# SYSTEM PROMPT — Frank AI OS
# =============================================================================

FRANK_MASTER_SYSTEM = f"""Você é Frank, o Sistema Operacional de IA da Davvero Gelato — v2.0.

════════════════════════════════════════════════════════════════
IDENTIDADE
════════════════════════════════════════════════════════════════
Você é o CEO Virtual da Davvero Gelato. Age como braço direito do CEO humano,
fornecendo diagnósticos precisos, decisões fundamentadas em dados e coordenando
8 diretores virtuais:

  CFO · COO · CMO · CSO · Supply · OPEP · Legal · BI

════════════════════════════════════════════════════════════════
A EMPRESA — DAVVERO GELATO
════════════════════════════════════════════════════════════════
• Rede de gelato premium artesanal | São Paulo, SP | Fundada 2017
• Formatos: quiosque, loja pequena, loja completa, dark kitchen
• Vantagem competitiva central: CMV de 26,5% vs mercado de 35% (+8,5 pp)
• Royalties: 8,5% | Fundo de Marketing: 1,5%
• Ticket médio meta: R$35 | NPS meta: 70

════════════════════════════════════════════════════════════════
REGRAS INVIOLÁVEIS DO CEO (HARD RULES)
════════════════════════════════════════════════════════════════
1. CMV NUNCA ultrapassa 30% → acima = emergência e suspensão imediata
2. Payback de nova unidade NUNCA supera 30 meses
3. ROI em 24 meses deve ser MÍNIMO 1,5x o investimento
4. Aluguel NUNCA supera 12% do faturamento bruto
5. EBITDA operacional mínimo de 10% sobre receita líquida
6. Qualquer proposta que viole estas regras é REPROVADA automaticamente

════════════════════════════════════════════════════════════════
FORMATO OBRIGATÓRIO DE RESPOSTA (10 BLOCOS)
════════════════════════════════════════════════════════════════
Toda resposta deve seguir exatamente este formato:

🎯 DIAGNÓSTICO
[Situação atual em 1-2 frases diretas]

📊 DADOS
[Números relevantes, KPIs, comparativos com meta]

⚠️ ALERTAS
[Desvios críticos identificados — se não houver, escreva "Nenhum"]

🔍 ANÁLISE (Causa Raiz)
[Por que está acontecendo — vá além do sintoma]

📋 OPÇÕES
[2-3 alternativas de ação com prós/contras resumidos]

✅ RECOMENDAÇÃO
[Ação preferida com justificativa baseada em dados]

🚫 RISCOS
[O que pode dar errado se executar a recomendação]

📅 PRAZO
[Quando executar: IMEDIATO / CURTO PRAZO (7d) / MÉDIO PRAZO (30d)]

🏆 RESULTADO ESPERADO
[Impacto projetado em números — CMV, ticket, receita, etc.]

⚖️ DECISÃO
[EXECUTAR | NÃO EXECUTAR | AGUARDAR | ESCALAR]

════════════════════════════════════════════════════════════════
PRINCÍPIOS DE ATUAÇÃO
════════════════════════════════════════════════════════════════
• Seja direto — o CEO não tem tempo para rodeios
• Use dados concretos. "Provavelmente" sem base = inaceitável
• Identifique causa raiz, não apenas sintoma
• Cash flow saudável > crescimento a qualquer custo
• Franqueado rentável > expansão agressiva
• Se dados forem insuficientes, diga e peça o que precisa
• Linguagem: português brasileiro, tom executivo, sem jargão desnecessário
"""

# Prompt de roteamento (leve, usa MODEL_FAST)
ROUTING_SYSTEM = """Você é o roteador do Frank AI OS.
Classifique a pergunta e retorne JSON com o campo "director" sendo UM de:
CFO, COO, CMO, CSO, Supply, OPEP, Legal, BI, Frank

Regras:
- CFO → finanças, DRE, CMV, fluxo de caixa, royalties, valuation, budget
- COO → operações, lojas, qualidade, auditoria, performance, equipe, CX
- CMO → marketing, campanhas, redes sociais, mídia paga, conteúdo, CRM, B2C
- CSO → expansão, novos franqueados, leads B2B, novos mercados, ROI de unidades
- Supply → fornecedores, compras, estoque, insumos, pedidos
- OPEP → processos, implantação, treinamento, franquia operacional
- Legal → contratos, compliance, COF, regulatório, jurídico
- BI → dashboards, KPIs, alertas, forecasts, análises de dados
- Frank → questões estratégicas amplas, cross-funcional, visão CEO

Retorne APENAS JSON, exemplo: {"director": "CFO", "confidence": 0.95, "keywords": ["CMV", "custo"]}"""


# =============================================================================
# FRANK MASTER — Classe Principal
# =============================================================================

class FrankMaster:
    """Orquestrador central do Frank AI OS."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.session_id = str(uuid.uuid4())[:8]
        self.db_pool = None      # Injetado pelo main.py
        self.redis_client = None # Injetado pelo main.py
        self._directors: Dict[str, Any] = {}
        self._init_directors()

    def _init_directors(self):
        """Inicializa os diretores de forma lazy para evitar imports circulares."""
        from cfo_director   import CFODirector
        from coo_director   import COODirector
        from cmo_director   import CMODirector
        from cso_director   import CSODirector
        from supply_director import SupplyDirector
        from opep_director  import OPEPDirector
        from legal_director import LegalDirector
        from bi_director    import BIDirector

        self._directors = {
            "CFO":    CFODirector(),
            "COO":    COODirector(),
            "CMO":    CMODirector(),
            "CSO":    CSODirector(),
            "Supply": SupplyDirector(),
            "OPEP":   OPEPDirector(),
            "Legal":  LegalDirector(),
            "BI":     BIDirector(),
        }

    # -------------------------------------------------------------------------
    # PIPELINE PRINCIPAL
    # -------------------------------------------------------------------------

    async def frank_pipeline(
        self,
        question: str,
        user: str = "CEO",
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Pipeline completo:
        1. Roteia para o diretor correto
        2. Busca KPI snapshot para contexto
        3. Director processa com seus agentes
        4. Valida resposta contra Hard Rules do CEO
        5. Salva interação no banco
        6. Retorna resposta estruturada
        """
        start = time.monotonic()
        session_id = f"{self.session_id}-{str(uuid.uuid4())[:4]}"

        logger.info(f"[{session_id}] Pergunta de {user}: {question[:80]}...")

        # 1. Roteia
        routing = await self._route_question(question)
        director_name = routing.get("director", "Frank")
        logger.info(f"[{session_id}] Roteado → {director_name}")

        # 2. KPI Snapshot para enriquecer contexto
        kpi_data = await self._get_kpi_snapshot()

        # 3. Processa com o diretor
        if director_name in self._directors:
            director = self._directors[director_name]
            director.db_pool     = self.db_pool
            director.redis_client = self.redis_client
            raw_response = await director.analyze(
                question=question,
                user=user,
                kpi_context=kpi_data,
                extra_context=context,
            )
        else:
            # Frank responde diretamente (questão estratégica ampla)
            raw_response = await self._frank_direct(question, kpi_data)

        # 4. Validação CEO (Hard Rules)
        ceo_validation = await self._ceo_validate(question, raw_response)

        # 5. Salva interação
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await self._save_interaction(
            session_id=session_id,
            user=user,
            director=director_name,
            question=question,
            response=raw_response,
            ceo_validation=ceo_validation,
            processing_ms=elapsed_ms,
            kpi_snapshot=kpi_data,
            routing=routing,
        )

        return {
            "session_id":       session_id,
            "timestamp":        datetime.now().isoformat(),
            "routing":          routing,
            "response":         raw_response,
            "ceo_validation":   ceo_validation,
            "processing_time_ms": elapsed_ms,
            "kpi_data":         kpi_data,
        }

    # -------------------------------------------------------------------------
    # ROTEAMENTO
    # -------------------------------------------------------------------------

    async def _route_question(self, question: str) -> Dict[str, Any]:
        """Usa MODEL_FAST para classificar e rotear a pergunta."""
        try:
            msg = await self.client.messages.create(
                model=MODEL_FAST,
                max_tokens=150,
                system=ROUTING_SYSTEM,
                messages=[{"role": "user", "content": question}],
            )
            text = msg.content[0].text.strip()
            # Remove markdown code fences se presentes
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Routing fallback: {e}")
            return {"director": "Frank", "confidence": 0.5, "keywords": []}

    # -------------------------------------------------------------------------
    # RESPOSTA DIRETA DO FRANK (questões cross-funcionais)
    # -------------------------------------------------------------------------

    async def _frank_direct(self, question: str, kpi_data: dict) -> str:
        """Frank responde diretamente questões estratégicas amplas."""
        context_str = json.dumps(kpi_data, ensure_ascii=False, default=str)
        msg = await self.client.messages.create(
            model=MODEL_MASTER,
            max_tokens=4000,
            system=[
                {
                    "type": "text",
                    "text": FRANK_MASTER_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Contexto atual da rede (KPIs):\n{context_str}\n\n"
                        f"Pergunta: {question}"
                    ),
                }
            ],
        )
        return msg.content[0].text

    # -------------------------------------------------------------------------
    # VALIDAÇÃO CEO — Hard Rules
    # -------------------------------------------------------------------------

    async def _ceo_validate(self, question: str, response: str) -> Dict[str, Any]:
        """
        Verifica se a resposta recomenda algo que viola Hard Rules.
        Retorna {"approved": bool, "violations": [...], "override_message": str|None}
        """
        violations = []

        # Detecção por palavras-chave + valores na resposta
        resp_lower = response.lower()

        # CMV
        if any(kw in resp_lower for kw in ["cmv", "custo de mercadoria"]):
            import re
            pcts = re.findall(r"(\d{2,3}(?:[.,]\d+)?)\s*%", response)
            for p in pcts:
                val = float(p.replace(",", "."))
                if 25 <= val <= 50:  # range plausível para CMV
                    if val > CEO_HARD_RULES["cmv_max_pct"]:
                        violations.append({
                            "rule":  "CMV_MAX",
                            "detail": f"CMV {val}% > limite {CEO_HARD_RULES['cmv_max_pct']}%",
                            "severity": "critico",
                        })

        # Payback
        if "payback" in resp_lower or "retorno" in resp_lower:
            import re
            months = re.findall(r"(\d+)\s*mes", resp_lower)
            for m in months:
                val = int(m)
                if 12 <= val <= 60:
                    if val > CEO_HARD_RULES["payback_max_months"]:
                        violations.append({
                            "rule":  "PAYBACK_MAX",
                            "detail": f"Payback {val}m > limite {CEO_HARD_RULES['payback_max_months']}m",
                            "severity": "critico",
                        })

        approved = len(violations) == 0
        return {
            "approved":         approved,
            "violations":       violations,
            "hard_rules_checked": list(CEO_HARD_RULES.keys()),
            "override_message": (
                "⛔ REPROVADO PELO CEO — Hard Rules violadas. Revisar antes de executar."
                if not approved else None
            ),
        }

    # -------------------------------------------------------------------------
    # KPI SNAPSHOT
    # -------------------------------------------------------------------------

    async def _get_kpi_snapshot(self) -> Dict[str, Any]:
        """Busca KPIs atuais do Redis (cache) ou PostgreSQL."""
        # Tenta Redis primeiro
        if self.redis_client:
            try:
                cached = await self.redis_client.get("frank:kpi_snapshot")
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        # Fallback: PostgreSQL
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT * FROM vw_executive_dashboard")
                    if row:
                        snapshot = dict(row)
                        # Cacheia por 5 minutos
                        if self.redis_client:
                            await self.redis_client.setex(
                                "frank:kpi_snapshot", 300,
                                json.dumps(snapshot, default=str)
                            )
                        return snapshot
            except Exception as e:
                logger.warning(f"KPI snapshot DB error: {e}")

        # Retorna estrutura vazia se não há dados
        return {
            "monthly_revenue":  None,
            "avg_cmv":          None,
            "active_units":     None,
            "avg_ticket_30d":   None,
            "avg_nps":          None,
            "critical_alerts":  0,
            "pending_tasks":    0,
            "note":             "KPIs não disponíveis — banco sem dados",
        }

    # -------------------------------------------------------------------------
    # SAVE INTERACTION
    # -------------------------------------------------------------------------

    async def _save_interaction(
        self,
        session_id: str,
        user: str,
        director: str,
        question: str,
        response: str,
        ceo_validation: dict,
        processing_ms: int,
        kpi_snapshot: dict,
        routing: dict,
    ) -> None:
        """Persiste interação no PostgreSQL."""
        if not self.db_pool:
            return
        try:
            # Determina decision type da resposta
            decision = None
            resp_upper = response.upper()
            for dt in ["EXECUTAR", "NAO_EXECUTAR", "AGUARDAR", "ESCALAR"]:
                if dt.replace("_", " ") in resp_upper or dt in resp_upper:
                    decision = dt
                    break

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO frank_interactions (
                        session_id, user_name, director, question, response,
                        decision, processing_ms, ceo_approved,
                        hard_rule_violations, kpi_snapshot, routing_data
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    """,
                    session_id,
                    user,
                    director,
                    question,
                    response,
                    decision,
                    processing_ms,
                    ceo_validation.get("approved", True),
                    json.dumps(ceo_validation.get("violations", [])),
                    json.dumps(kpi_snapshot, default=str),
                    json.dumps(routing),
                )
        except Exception as e:
            logger.warning(f"Falha ao salvar interação: {e}")

    # -------------------------------------------------------------------------
    # CLOSE
    # -------------------------------------------------------------------------

    async def close(self):
        """Encerra conexões do Frank Master."""
        await self.client.close()
        logger.info("Frank Master encerrado.")

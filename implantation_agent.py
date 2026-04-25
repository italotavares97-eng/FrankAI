"""
Implantation Agent — Gestão de Abertura de Novas Lojas
Gerencia projetos de implantação de novas unidades com checklist 5W2H e cronograma.
"""

import json
import logging
from datetime import date, timedelta
from typing import Any

from core.base_agent import BaseAgent
from config import MODEL_AGENT, CEO_HARD_RULES

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = f"""Você é o Especialista de Implantação da Davvero Gelato,
responsável por garantir que cada nova loja abra dentro do prazo, padrão e orçamento.

RESPONSABILIDADES:
- Gestão de projetos de abertura de lojas (do contrato à inauguração)
- Checklist pré-abertura com 200+ itens críticos
- Coordenação entre arquitetura, obras, equipamentos, treinamento e marketing
- Cronograma mestre com marcos e dependências
- Homologação de fornecedores locais
- Inspeção pré-abertura e emissão de "Go/No-Go"

FASES DE IMPLANTAÇÃO DAVVERO:
1. PROJETOS (semanas 1-4): aprovação de layout, planta técnica, licenças
2. OBRAS (semanas 5-12): construção/reforma, instalações, equipamentos
3. SETUP (semanas 13-15): mobiliário, decoração, sistemas (PDV, Wi-Fi, câmeras)
4. TREINAMENTO (semanas 14-16): equipe completa, simulados, abertura suave
5. PRÉ-ABERTURA (semana 16): auditoria de inauguração, liberação Go/No-Go
6. INAUGURAÇÃO: soft-opening + grand opening

REGRAS INVIOLÁVEIS:
{json.dumps(CEO_HARD_RULES, ensure_ascii=False, indent=2)}

Formato de resposta obrigatório:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO"""


# Full 5W2H opening checklist template
OPENING_CHECKLIST_5W2H = {
    "PROJETOS": {
        "items": [
            "Aprovação de layout pelo arquiteto Davvero",
            "Projeto técnico (elétrico, hidráulico, HVAC)",
            "AVCB e alvará de funcionamento protocolados",
            "Contrato de locação assinado e registrado",
            "Seguro do estabelecimento contratado",
            "Plano de obra aprovado pelo franqueador",
        ],
        "prazo_semanas": 4,
        "responsavel": "Franqueado + Suporte Davvero",
    },
    "OBRAS": {
        "items": [
            "Empresa de obras contratada e aprovada",
            "Piso, paredes e teto conforme padrão visual",
            "Instalação elétrica dimensionada para equipamentos",
            "Ponto de água e esgoto para área de produção",
            "Câmara fria instalada e testada",
            "Vitrine de gelato instalada e calibrada",
            "Ar-condicionado instalado e testado",
            "Sistema de exaustão aprovado pela Vigilância Sanitária",
        ],
        "prazo_semanas": 8,
        "responsavel": "Empreiteiro + Supervisor Davvero",
    },
    "EQUIPAMENTOS": {
        "items": [
            "Máquinas de gelato (mantecadoras) entregues e instaladas",
            "Pasteurizador instalado e calibrado",
            "Freezer de conservação instalado",
            "PDV (sistema de caixa) instalado e configurado",
            "Balança homologada pelo INMETRO",
            "Uniforme da equipe entregue",
            "Embalagens e descartáveis em estoque",
        ],
        "prazo_semanas": 2,
        "responsavel": "Fornecedores Homologados",
    },
    "SETUP_E_VISUAL": {
        "items": [
            "Mobiliário e decoração instalados",
            "Placas e sinalização (fachada, cardápio, proibições)",
            "Wi-Fi e câmeras instalados e funcionando",
            "Cardápio digital ou físico impresso",
            "Material de marketing de inauguração",
            "Página no Google Meu Negócio criada",
            "Instagram e iFood configurados",
        ],
        "prazo_semanas": 2,
        "responsavel": "Franqueado + Marketing Davvero",
    },
    "TREINAMENTO": {
        "items": [
            "Gerente certificado pela Academia Davvero",
            "Equipe completa treinada em produção de gelato",
            "Treinamento de atendimento ao cliente concluído",
            "Simulado de abertura realizado (pelo menos 2x)",
            "Checklist diário de abertura/fechamento dominado",
            "Estoque inicial recebido e conferido",
        ],
        "prazo_semanas": 3,
        "responsavel": "TrainingAgent + Gerente",
    },
    "PRE_ABERTURA": {
        "items": [
            "Auditoria pré-abertura realizada (score mínimo 85/100)",
            "Alvará de funcionamento em mãos",
            "Vigilância Sanitária vistoriada e aprovada",
            "CNPJ da unidade ativo e fiscal configurado",
            "Caixa inicial disponível",
            "Plano de comunicação de inauguração aprovado",
            "Franqueador emitiu autorização Go/No-Go",
        ],
        "prazo_semanas": 1,
        "responsavel": "ImplantationAgent + Franqueador",
    },
}


class ImplantationAgent(BaseAgent):
    """
    Gerencia projetos de abertura de novas unidades Davvero Gelato.
    Cria planos 5W2H, acompanha status e emite Go/No-Go.
    """

    def __init__(self):
        super().__init__(
            agent_name="ImplantationAgent",
            model=MODEL_AGENT,
            system_prompt=SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    async def analyze(self, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Fetch units in implantation status, build opening plans with 5W2H format.
        """
        logger.info(f"[ImplantationAgent] analyze called | query={query[:80]!r}")

        implantation_units = await self._fetch_implantation_units()
        pipeline_units = await self._fetch_pipeline_units()
        recent_openings = await self._fetch_recent_openings()

        prompt = f"""
CONSULTA DE IMPLANTAÇÃO: {query}

=== UNIDADES EM IMPLANTAÇÃO ATIVA ===
{implantation_units}

=== PIPELINE DE FUTURAS UNIDADES ===
{pipeline_units}

=== ABERTURAS RECENTES (REFERÊNCIA) ===
{recent_openings}

=== CHECKLIST 5W2H DAVVERO GELATO ===
{json.dumps(OPENING_CHECKLIST_5W2H, ensure_ascii=False, indent=2)}

Com base nesses dados, forneça:
1. Status atual de cada unidade em implantação (% de conclusão estimada)
2. Principais riscos e gargalos por projeto
3. Plano de ação 5W2H para as próximas 2 semanas de cada unidade crítica:
   - O QUÊ: ação específica
   - QUEM: responsável nomeado
   - QUANDO: data limite
   - ONDE: localização/frente de trabalho
   - POR QUÊ: impacto se não feito
   - COMO: método/recurso
   - QUANTO: custo estimado se aplicável
4. Recomendação de Go/No-Go para qualquer unidade próxima da inauguração

Responda no formato:
🎯 DIAGNÓSTICO | 📊 DADOS | ⚠️ ALERTAS | 🔍 ANÁLISE | 📋 OPÇÕES | ✅ RECOMENDAÇÃO | 🚫 RISCOS | 📅 PRAZO | 🏆 RESULTADO ESPERADO | ⚖️ DECISÃO
"""
        response = await self.call_claude(user_message=prompt)
        logger.info("[ImplantationAgent] analyze completed")
        return response

    # ------------------------------------------------------------------
    # Specific methods
    # ------------------------------------------------------------------

    async def generate_opening_plan(self, unit_code: str) -> str:
        """Generate a complete opening project plan for a specific unit."""
        unit = await self.db_fetchrow(
            """
            SELECT u.*, f.name AS franchisee_name, f.email AS franchisee_email
            FROM units u
            LEFT JOIN franchisees f ON f.id = (
                SELECT id FROM franchisees
                WHERE status = 'ativo'
                ORDER BY contract_start DESC
                LIMIT 1
            )
            WHERE u.code = $1
            """,
            unit_code,
        )
        if not unit:
            return f"Unidade {unit_code} não encontrada."

        opening_date = unit.get("opening_date")
        today = date.today()
        days_to_opening = (opening_date - today).days if opening_date else None

        prompt = f"""
UNIDADE: {unit.get('name')} ({unit_code})
CIDADE: {unit.get('city')} | FORMATO: {unit.get('format')}
STATUS ATUAL: {unit.get('status')}
DATA PREVISTA DE ABERTURA: {opening_date}
DIAS ATÉ A ABERTURA: {days_to_opening if days_to_opening is not None else 'não definido'}
GERENTE: {unit.get('manager_name', 'a definir')}
FRANQUEADO: {unit.get('franchisee_name', 'não informado')}

Crie um plano de implantação COMPLETO com:
1. Cronograma mestre com todas as fases e marcos (Gantt simplificado)
2. Checklist priorizado pelas próximas 4 semanas (5W2H)
3. Matriz de riscos (probabilidade x impacto)
4. Plano de comunicação com franqueado
5. Critérios de Go/No-Go para inauguração
6. Estimativa de investimento em implantação

Considere {'URGÊNCIA MÁXIMA — abertura em menos de 30 dias!' if days_to_opening and days_to_opening < 30 else 'prazo adequado para planejamento'}

Responda no formato estruturado completo.
"""
        return await self.call_claude(user_message=prompt)

    async def go_no_go_assessment(self, unit_code: str) -> str:
        """Perform a Go/No-Go assessment for a unit about to open."""
        unit = await self.db_fetchrow(
            "SELECT * FROM units WHERE code = $1", unit_code
        )
        tasks = await self.db_fetch(
            """
            SELECT task_type, status, priority, payload
            FROM frank_tasks
            WHERE payload->>'unit_code' = $1
              AND status != 'completed'
            ORDER BY priority DESC
            LIMIT 30
            """,
            unit_code,
        )
        tasks_text = self.format_db_data(tasks, title="Tarefas Pendentes")

        prompt = f"""
AVALIAÇÃO GO/NO-GO — Unidade: {unit_code}
{json.dumps(dict(unit or {}), default=str, ensure_ascii=False)}

TAREFAS PENDENTES:
{tasks_text}

CRITÉRIOS GO/NO-GO DAVVERO:
- Auditoria pré-abertura ≥ 85/100
- Todos os itens críticos do checklist concluídos
- Alvará e licenças em mãos
- Equipe treinada e certificada
- Estoque inicial disponível
- Sistemas (PDV, fiscal) operacionais

Emita um parecer formal de GO ou NO-GO com:
1. Score de prontidão (0-100)
2. Itens bloqueadores (se NO-GO)
3. Itens de atenção (riscos pós-abertura)
4. Prazo recomendado para revisão (se NO-GO)
5. Assinatura digital do agente

Formato obrigatório de resposta estruturada.
"""
        return await self.call_claude(user_message=prompt)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_implantation_units(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT code, name, city, format, status,
                   opening_date,
                   manager_name, team_count,
                   (opening_date - CURRENT_DATE) AS days_to_opening
            FROM units
            WHERE status = 'em_implantacao'
            ORDER BY opening_date ASC NULLS LAST
            """
        )
        return self.format_db_data(rows, title="Unidades em Implantação")

    async def _fetch_pipeline_units(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT code, name, city, format, status, opening_date
            FROM units
            WHERE status IN ('contrato_assinado', 'projeto_aprovado', 'em_obras')
            ORDER BY opening_date ASC NULLS LAST
            """
        )
        return self.format_db_data(rows, title="Pipeline de Novas Unidades")

    async def _fetch_recent_openings(self) -> str:
        rows = await self.db_fetch(
            """
            SELECT code, name, city, format, opening_date,
                   manager_name, team_count
            FROM units
            WHERE status = 'ativa'
              AND opening_date >= CURRENT_DATE - INTERVAL '12 months'
            ORDER BY opening_date DESC
            LIMIT 5
            """
        )
        return self.format_db_data(rows, title="Aberturas Recentes (referência)")

# =============================================================================
# TASKS/TASK_MANAGER.PY — Frank AI OS
# Sistema de Tarefas — Geração, Priorização e Acompanhamento
# =============================================================================

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger("frank.tasks")


class TaskPriority(str, Enum):
    CRITICO   = "critico"    # Executar agora (P1)
    URGENTE   = "urgente"    # Executar hoje (P2)
    ALTO      = "alto"       # Esta semana (P3)
    MEDIO     = "medio"      # Próximos 15 dias (P4)
    BAIXO     = "baixo"      # Backlog (P5)


class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    CANCELLED = "cancelled"


PRIORITY_DAYS = {
    TaskPriority.CRITICO: 0,
    TaskPriority.URGENTE: 1,
    TaskPriority.ALTO:    7,
    TaskPriority.MEDIO:   15,
    TaskPriority.BAIXO:   30,
}

PRIORITY_SCORES = {
    TaskPriority.CRITICO: 1,
    TaskPriority.URGENTE: 2,
    TaskPriority.ALTO:    3,
    TaskPriority.MEDIO:   5,
    TaskPriority.BAIXO:   8,
}


class Task:
    """Representa uma tarefa executável do Frank AI OS."""

    def __init__(
        self,
        title: str,
        description: str,
        owner: str,
        sector: str,
        priority: TaskPriority = TaskPriority.MEDIO,
        task_type: str = "action",
        unit_id: Optional[str] = None,
        deadline: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        kpis: Optional[Dict] = None,
        steps: Optional[List[str]] = None,
        expected_outcome: Optional[str] = None,
        payload: Optional[Dict] = None,
    ):
        self.id              = str(uuid.uuid4())
        self.title           = title
        self.description     = description
        self.owner           = owner
        self.sector          = sector
        self.priority        = priority
        self.task_type       = task_type
        self.unit_id         = unit_id
        self.deadline        = deadline or (
            datetime.now() + timedelta(days=PRIORITY_DAYS[priority])
        )
        self.tags            = tags or []
        self.kpis            = kpis or {}
        self.steps           = steps or []
        self.expected_outcome = expected_outcome
        self.payload         = payload or {}
        self.status          = TaskStatus.PENDING
        self.created_at      = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "id":               self.id,
            "title":            self.title,
            "description":      self.description,
            "owner":            self.owner,
            "sector":           self.sector,
            "priority":         self.priority.value,
            "task_type":        self.task_type,
            "unit_id":          self.unit_id,
            "deadline":         self.deadline.isoformat(),
            "tags":             self.tags,
            "kpis":             self.kpis,
            "steps":            self.steps,
            "expected_outcome": self.expected_outcome,
            "status":           self.status.value,
            "created_at":       self.created_at.isoformat(),
        }

    def to_5w2h(self) -> str:
        """Formata tarefa no modelo 5W2H."""
        days_left = (self.deadline - datetime.now()).days
        deadline_str = self.deadline.strftime("%d/%m/%Y")

        lines = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📋 TAREFA: {self.title.upper()}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔴 WHAT (O QUÊ):  {self.title}",
            f"👤 WHO (QUEM):    {self.owner} [{self.sector}]",
            f"📅 WHEN (QUANDO): {deadline_str} ({days_left}d restantes)",
            f"📍 WHERE (ONDE):  {self.unit_id or 'Rede / Central'}",
            f"❓ WHY (POR QUÊ): {self.description}",
            f"💰 HOW MUCH:      {self._format_kpis()}",
            f"⚙️  HOW (COMO):    ",
        ]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"    {i}. {step}")
        if self.expected_outcome:
            lines.append(f"🏆 RESULTADO:     {self.expected_outcome}")
        lines.append(f"🚦 PRIORIDADE:    {self.priority.value.upper()}")
        return "\n".join(lines)

    def _format_kpis(self) -> str:
        if not self.kpis:
            return "—"
        return " | ".join(f"{k}: {v}" for k, v in self.kpis.items())


class TaskManager:
    """
    Gerenciador de tarefas do Frank AI OS.
    Cria, persiste, prioriza e monitora tarefas executáveis.
    """

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.db_pool = db_pool
        self._queue: List[Task] = []  # Cache em memória

    # -------------------------------------------------------------------------
    # CRIAÇÃO DE TAREFAS
    # -------------------------------------------------------------------------

    async def create_task(self, task: Task) -> Task:
        """Cria e persiste uma tarefa."""
        self._queue.append(task)
        await self._persist_task(task)
        logger.info(f"Tarefa criada: [{task.priority.value.upper()}] {task.title} → {task.owner}")
        return task

    async def create_from_analysis(
        self,
        analysis_text: str,
        sector: str,
        unit_id: Optional[str] = None,
    ) -> List[Task]:
        """
        Extrai e cria tarefas automaticamente de uma análise do Frank.
        Busca por padrões de ação na resposta.
        """
        tasks = []
        lines = analysis_text.split("\n")

        for line in lines:
            line = line.strip()
            # Detecta ações recomendadas
            if any(marker in line.upper() for marker in [
                "AÇÃO:", "EXECUTAR:", "TAREFA:", "TODO:", "FAZER:"
            ]):
                title = line.split(":", 1)[-1].strip()
                if len(title) > 10:
                    priority = TaskPriority.MEDIO
                    if any(w in line.upper() for w in ["IMEDIATO", "URGENTE", "CRÍTICO"]):
                        priority = TaskPriority.URGENTE
                    elif any(w in line.upper() for w in ["HOJE", "AGORA"]):
                        priority = TaskPriority.ALTO

                    task = Task(
                        title=title[:200],
                        description=f"Gerado automaticamente por Frank AI OS — {sector}",
                        owner=self._infer_owner(sector),
                        sector=sector,
                        priority=priority,
                        unit_id=unit_id,
                    )
                    tasks.append(await self.create_task(task))

        return tasks

    # -------------------------------------------------------------------------
    # TEMPLATES DE TAREFAS COMUNS
    # -------------------------------------------------------------------------

    async def create_cmv_alert_task(
        self,
        unit_name: str,
        unit_id: str,
        cmv_pct: float,
        target_pct: float = 26.5,
    ) -> Task:
        """Cria tarefa de ação para CMV crítico."""
        task = Task(
            title=f"Reduzir CMV — {unit_name}",
            description=(
                f"CMV de {cmv_pct:.1f}% está acima da meta de {target_pct:.1f}%. "
                f"Desvio de {cmv_pct - target_pct:.1f} pp. Ação imediata necessária."
            ),
            owner="COO / Gerente de Unidade",
            sector="COO",
            priority=TaskPriority.CRITICO if cmv_pct > 30 else TaskPriority.URGENTE,
            unit_id=unit_id,
            tags=["cmv", "financeiro", "urgente"],
            kpis={"cmv_atual": f"{cmv_pct:.1f}%", "meta": f"{target_pct:.1f}%", "desvio": f"+{cmv_pct - target_pct:.1f}pp"},
            steps=[
                "Auditar entrada de mercadoria (pesagem, nota fiscal vs recebimento)",
                "Identificar produtos com maior desvio de custo",
                "Revisar fichas técnicas e porcionamento",
                "Verificar estoque e possível desperdício",
                "Renegociar com fornecedores se necessário",
                "Implementar controle diário de CMV por 30 dias",
            ],
            expected_outcome=f"Redução do CMV para {target_pct:.1f}% em 30 dias",
        )
        return await self.create_task(task)

    async def create_nps_recovery_task(
        self,
        unit_name: str,
        unit_id: str,
        nps_score: float,
        target: int = 70,
    ) -> Task:
        """Cria tarefa de recuperação de NPS."""
        task = Task(
            title=f"Plano de recuperação NPS — {unit_name}",
            description=f"NPS de {nps_score:.0f} está abaixo da meta de {target}. Ação de CX necessária.",
            owner="COO / CX Lead",
            sector="COO",
            priority=TaskPriority.ALTO,
            unit_id=unit_id,
            tags=["nps", "cx", "qualidade"],
            kpis={"nps_atual": str(nps_score), "meta": str(target)},
            steps=[
                "Analisar comentários negativos dos últimos 30 dias",
                "Realizar reunião com equipe da loja",
                "Identificar top 3 pontos de atrito",
                "Implementar treinamento de atendimento",
                "Criar rotina de feedback diário com equipe",
                "Monitorar NPS semanalmente por 60 dias",
            ],
            expected_outcome=f"NPS ≥ {target} em 60 dias",
        )
        return await self.create_task(task)

    async def create_expansion_evaluation_task(
        self,
        location: str,
        lead_id: str,
    ) -> Task:
        """Cria tarefa de avaliação de nova unidade."""
        task = Task(
            title=f"Avaliar abertura — {location}",
            description=f"Lead qualificado para nova unidade em {location}. Iniciar análise de viabilidade.",
            owner="CSO / Expansão",
            sector="CSO",
            priority=TaskPriority.MEDIO,
            tags=["expansão", "lead", "viabilidade"],
            steps=[
                "Visita técnica ao ponto comercial",
                "Análise de fluxo e perfil do cliente",
                "Simulação de ROI com dados reais de aluguel",
                "Validação do perfil do franqueado",
                "Aprovação final pelo CEO (Hard Rules check)",
            ],
            expected_outcome="Aprovação ou reprovação da abertura com laudo completo",
        )
        return await self.create_task(task)

    # -------------------------------------------------------------------------
    # CONSULTA
    # -------------------------------------------------------------------------

    async def get_pending_tasks(
        self,
        sector: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Retorna tarefas pendentes do banco."""
        if not self.db_pool:
            # Retorna da fila em memória
            tasks = [t for t in self._queue if t.status == TaskStatus.PENDING]
            if sector:
                tasks = [t for t in tasks if t.sector == sector]
            tasks.sort(key=lambda t: PRIORITY_SCORES.get(t.priority, 5))
            return [t.to_dict() for t in tasks[:limit]]

        try:
            async with self.db_pool.acquire() as conn:
                where = "WHERE status='pending'"
                params = []
                if sector:
                    where += " AND payload->>'sector' = $1"
                    params.append(sector)

                rows = await conn.fetch(
                    f"""SELECT * FROM frank_tasks {where}
                    ORDER BY priority ASC, scheduled_for ASC
                    LIMIT {limit}""",
                    *params,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Get pending tasks error: {e}")
            return []

    async def complete_task(self, task_id: str, result: Optional[Dict] = None) -> bool:
        """Marca tarefa como concluída."""
        for t in self._queue:
            if t.id == task_id:
                t.status = TaskStatus.DONE
                break

        if not self.db_pool:
            return True
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE frank_tasks SET status='done', completed_at=NOW(), result=$1 WHERE id=$2",
                    json.dumps(result or {}), task_id,
                )
            return True
        except Exception as e:
            logger.warning(f"Complete task error: {e}")
            return False

    # -------------------------------------------------------------------------
    # PERSISTÊNCIA
    # -------------------------------------------------------------------------

    async def _persist_task(self, task: Task) -> None:
        if not self.db_pool:
            return
        try:
            priority_num = PRIORITY_SCORES.get(task.priority, 5)
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO frank_tasks (task_type, status, priority, payload, scheduled_for)
                    VALUES ($1, 'pending', $2, $3, $4)""",
                    task.task_type,
                    priority_num,
                    json.dumps(task.to_dict()),
                    task.deadline,
                )
        except Exception as e:
            logger.warning(f"Persist task error: {e}")

    def _infer_owner(self, sector: str) -> str:
        owners = {
            "CFO": "Diretor Financeiro",
            "COO": "Gerente de Operações",
            "CMO": "Gerente de Marketing",
            "CSO": "Diretor de Expansão",
            "Supply": "Gerente de Supply Chain",
            "OPEP": "Gerente de Processos",
            "Legal": "Assessor Jurídico",
            "BI": "Analista de Dados",
        }
        return owners.get(sector, "Responsável da Área")

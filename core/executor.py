# =============================================================================
# CORE/EXECUTOR.PY — Frank AI OS
# Executor de Ações Automáticas
# =============================================================================

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger("frank.executor")


class Executor:
    """
    Executa ações automáticas geradas pelos agentes.
    Suporta: email, whatsapp, task, erp, sheets, campaign.
    """

    def execute(self, actions: List[Dict[str, Any]]) -> None:
        """Executa lista de ações (síncrono — wrapper para CLI)."""
        for action in actions:
            try:
                action_type = action.get("type", "unknown")

                if action_type == "email":
                    self._exec_email(action)

                elif action_type == "whatsapp":
                    self._exec_whatsapp(action)

                elif action_type == "task":
                    self._exec_task(action)

                elif action_type == "erp_order":
                    self._exec_erp_order(action)

                elif action_type == "campaign":
                    self._exec_campaign(action)

                elif action_type == "sheets_update":
                    self._exec_sheets_update(action)

                elif action_type == "alert":
                    self._exec_alert(action)

                else:
                    logger.warning(f"Tipo de ação desconhecido: {action_type}")

            except Exception as e:
                logger.error(f"Executor error ({action.get('type')}): {e}")

    async def execute_async(self, actions: List[Dict[str, Any]]) -> List[Dict]:
        """Versão assíncrona — usada pela API FastAPI."""
        results = []
        for action in actions:
            result = await self._execute_action_async(action)
            results.append(result)
        return results

    async def _execute_action_async(self, action: Dict) -> Dict:
        action_type = action.get("type", "unknown")
        try:
            if action_type == "email":
                from integrations.email import EmailConnector
                conn = EmailConnector()
                success = await conn.send_email(
                    to=action.get("to", ["ceo@davverogelato.com.br"]),
                    subject=action.get("subject", "Notificação Frank AI OS"),
                    body=action.get("body", ""),
                )
                return {"type": "email", "success": success}

            elif action_type == "whatsapp":
                from integrations.whatsapp import WhatsAppConnector
                conn = WhatsAppConnector()
                result = await conn.send_text(
                    to=action.get("to", ""),
                    message=action.get("message", ""),
                )
                await conn.close()
                return {"type": "whatsapp", "result": result}

            elif action_type == "task":
                from tasks.task_manager import TaskManager, Task, TaskPriority
                tm = TaskManager()
                task = Task(
                    title=action.get("title", action.get("description", "Tarefa Frank AI OS")),
                    description=action.get("description", ""),
                    owner=action.get("owner", "Responsável"),
                    sector=action.get("sector", "Frank"),
                    priority=TaskPriority[action.get("priority", "MEDIO").upper()]
                    if action.get("priority") else TaskPriority.MEDIO,
                )
                await tm.create_task(task)
                return {"type": "task", "id": task.id, "title": task.title}

            else:
                return {"type": action_type, "status": "not_implemented"}

        except Exception as e:
            logger.error(f"Async executor error ({action_type}): {e}")
            return {"type": action_type, "error": str(e)}

    # -------------------------------------------------------------------------
    # EXECUTORES SÍNCRONOS (modo CLI)
    # -------------------------------------------------------------------------

    def _exec_email(self, action: Dict) -> None:
        subject = action.get("subject", "Notificação Frank AI OS")
        body    = action.get("body", "")
        to      = action.get("to", ["ceo@davverogelato.com.br"])
        print(f"  📧 EMAIL → {to} | Assunto: {subject}")
        # Em produção: asyncio.run(EmailConnector().send_email(to, subject, body))

    def _exec_whatsapp(self, action: Dict) -> None:
        to      = action.get("to", "")
        message = action.get("message", action.get("body", ""))
        print(f"  💬 WHATSAPP → {to} | {message[:80]}...")

    def _exec_task(self, action: Dict) -> None:
        desc     = action.get("description", action.get("title", "Tarefa sem título"))
        priority = action.get("priority", "MÉDIO")
        owner    = action.get("owner", "Responsável")
        print(f"  📌 TAREFA [{priority}] → {owner}: {desc}")

    def _exec_erp_order(self, action: Dict) -> None:
        supplier = action.get("supplier", "Fornecedor")
        items    = action.get("items", [])
        print(f"  🛒 PEDIDO ERP → {supplier} | {len(items)} itens")

    def _exec_campaign(self, action: Dict) -> None:
        name     = action.get("name", "Nova Campanha")
        platform = action.get("platform", "Meta Ads")
        budget   = action.get("budget", 0)
        print(f"  📢 CAMPANHA → {platform} | {name} | Budget: R${budget:,.0f}")

    def _exec_sheets_update(self, action: Dict) -> None:
        sheet    = action.get("sheet", "")
        unit     = action.get("unit", "")
        print(f"  📊 SHEETS → {sheet} | Unidade: {unit}")

    def _exec_alert(self, action: Dict) -> None:
        severity = action.get("severity", "info").upper()
        msg      = action.get("message", "")
        print(f"  🔔 ALERTA [{severity}] → {msg}")

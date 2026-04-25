# =============================================================================
# INTEGRATIONS/WHATSAPP.PY — Frank AI OS
# Conector WhatsApp Business Cloud API (Meta)
# =============================================================================

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_VERIFY

logger = logging.getLogger("frank.whatsapp")

WA_API_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
WA_HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
}


class WhatsAppConnector:
    """
    Conector para WhatsApp Business Cloud API.
    Suporta: texto, template, lista interativa, botões.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)

    async def send_text(self, to: str, message: str) -> Dict:
        """Envia mensagem de texto simples."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        return await self._send(payload)

    async def send_alert(
        self,
        to: str,
        unit_name: str,
        severity: str,
        detail: str,
        metric: Optional[str] = None,
    ) -> Dict:
        """Envia alerta formatado para WhatsApp."""
        icons = {"critico": "🔴", "alerta": "🟠", "atencao": "🟡", "info": "🔵"}
        icon = icons.get(severity, "⚠️")

        message = (
            f"{icon} *ALERTA FRANK AI OS*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"*Unidade:* {unit_name}\n"
            f"*Severidade:* {severity.upper()}\n"
            f"*Detalhe:* {detail}\n"
        )
        if metric:
            message += f"*Métrica:* {metric}\n"

        message += f"━━━━━━━━━━━━━━━━━━\n_Frank AI OS · Davvero Gelato_"
        return await self.send_text(to, message)

    async def send_report_summary(
        self,
        to: str,
        title: str,
        summary: str,
        kpis: Optional[Dict] = None,
    ) -> Dict:
        """Envia resumo de relatório."""
        message = f"📊 *{title}*\n━━━━━━━━━━━━━━━━━━\n{summary}"
        if kpis:
            message += "\n\n*KPIs:*\n"
            for k, v in kpis.items():
                message += f"• {k}: {v}\n"
        message += "\n_Frank AI OS · Davvero Gelato_"
        return await self.send_text(to, message)

    async def send_buttons(
        self,
        to: str,
        header: str,
        body: str,
        buttons: List[Dict[str, str]],
        footer: str = "Frank AI OS",
    ) -> Dict:
        """
        Envia mensagem com botões interativos (máx 3).
        buttons: [{"id": "btn_1", "title": "Aprovar"}]
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "footer": {"text": footer},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }
        return await self._send(payload)

    async def send_list(
        self,
        to: str,
        header: str,
        body: str,
        button_text: str,
        sections: List[Dict],
    ) -> Dict:
        """
        Envia mensagem com lista de opções.
        sections: [{"title": "Ações", "rows": [{"id": "1", "title": "Ver DRE", "description": "..."}]}]
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._format_phone(to),
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "action": {"button": button_text, "sections": sections},
            },
        }
        return await self._send(payload)

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verifica webhook do WhatsApp."""
        if mode == "subscribe" and token == WHATSAPP_VERIFY:
            logger.info("WhatsApp webhook verificado")
            return challenge
        return None

    def parse_webhook(self, payload: Dict) -> Optional[Dict]:
        """
        Extrai mensagem recebida do payload do webhook.
        Retorna {"from": str, "text": str, "type": str} ou None.
        """
        try:
            entry = payload["entry"][0]["changes"][0]["value"]
            if "messages" not in entry:
                return None
            msg = entry["messages"][0]
            sender = msg["from"]
            msg_type = msg["type"]

            text = None
            if msg_type == "text":
                text = msg["text"]["body"]
            elif msg_type == "interactive":
                if msg["interactive"]["type"] == "button_reply":
                    text = msg["interactive"]["button_reply"]["title"]
                elif msg["interactive"]["type"] == "list_reply":
                    text = msg["interactive"]["list_reply"]["title"]

            return {"from": sender, "text": text, "type": msg_type, "raw": msg}
        except (KeyError, IndexError):
            return None

    async def _send(self, payload: Dict) -> Dict:
        """Envia payload para a API do WhatsApp."""
        if not WHATSAPP_TOKEN:
            logger.warning("WHATSAPP_TOKEN não configurado — mock mode")
            return {"status": "mock", "payload": payload}
        try:
            resp = await self.client.post(WA_API_URL, headers=WA_HEADERS, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error {e.response.status_code}: {e.response.text}")
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return {"error": str(e)}

    def _format_phone(self, phone: str) -> str:
        """Formata número para padrão E.164 (55 + DDD + número)."""
        clean = "".join(c for c in phone if c.isdigit())
        if not clean.startswith("55"):
            clean = "55" + clean
        return clean

    async def close(self):
        await self.client.aclose()

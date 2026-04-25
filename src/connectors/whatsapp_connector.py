"""Frank AI OS — Conector WhatsApp via Z-API / Evolution API."""

import httpx
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("whatsapp_connector")


class WhatsAppConnector:
    """Envia mensagens via Z-API (padrão) ou Evolution API."""

    def __init__(self):
        self.base_url = settings.whatsapp_api_url
        self.headers = {
            "Client-Token": settings.whatsapp_token,
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
    async def send_text(self, phone: str, message: str) -> bool:
        if not settings.enable_whatsapp:
            logger.info("whatsapp_disabled", phone=phone)
            return True

        if settings.mock_external_apis:
            logger.info("whatsapp_mock_sent", phone=phone, preview=message[:80])
            return True

        payload = {"phone": phone, "message": message}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/send-text",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()

        logger.info("whatsapp_sent", phone=phone)
        return True

    async def send_critical_alert(self, alert: dict) -> bool:
        unit = alert.get("unit_id", "REDE")
        rule = alert.get("rule", "CEO RULE")
        val = alert.get("current_val", "?")
        limit = alert.get("limit_val", "?")

        msg = (
            f"🔴 *FRANK AI OS — ALERTA CRÍTICO*\n\n"
            f"📍 Unidade: {unit}\n"
            f"⚠️ Regra: {rule}\n"
            f"📊 Valor atual: {val}\n"
            f"🎯 Limite: {limit}\n\n"
            f"_{alert.get('message', '')}_\n\n"
            f"👉 Acesse o dashboard para detalhes."
        )
        return await self.send_text(settings.alert_whatsapp or settings.whatsapp_admin_number, msg)

    async def send_morning_briefing(self, summary: str) -> bool:
        from datetime import datetime
        today = datetime.utcnow().strftime("%d/%m/%Y")
        msg = f"🌅 *Frank AI OS — Briefing {today}*\n\n{summary[:1000]}"
        return await self.send_text(settings.alert_whatsapp or settings.whatsapp_admin_number, msg)

    async def send_weekly_report_link(self, report_url: str) -> bool:
        from datetime import datetime
        msg = (
            f"📊 *Frank AI OS — Relatório Semanal*\n"
            f"Data: {datetime.utcnow().strftime('%d/%m/%Y')}\n\n"
            f"Acesse o relatório completo:\n{report_url}"
        )
        return await self.send_text(settings.alert_whatsapp or settings.whatsapp_admin_number, msg)


whatsapp_connector = WhatsAppConnector()

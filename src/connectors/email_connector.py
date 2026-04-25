"""Frank AI OS — Conector de email via SMTP assíncrono."""

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger("email_connector")

# Templates HTML
TEMPLATES = {
    "critical_alert": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0F172A;color:#F1F5F9;padding:24px;border-radius:12px">
  <h2 style="color:#E02424;margin:0 0 16px">🔴 ALERTA CRÍTICO — Frank AI OS</h2>
  <p><strong>Regra:</strong> {rule}</p>
  <p><strong>Unidade:</strong> {unit_id}</p>
  <p><strong>Valor atual:</strong> {current_val}</p>
  <p><strong>Limite:</strong> {limit_val}</p>
  <p><strong>Mensagem:</strong> {message}</p>
  <p style="color:#94A3B8;font-size:12px;margin-top:24px">Frank AI OS · Davvero Gelato · {timestamp}</p>
</div>
""",
    "daily_briefing": """
<div style="font-family:sans-serif;max-width:700px;margin:0 auto;background:#0F172A;color:#F1F5F9;padding:24px;border-radius:12px">
  <h2 style="color:#1A56DB">🌅 Briefing Matinal — Frank AI OS</h2>
  <pre style="background:#1E293B;padding:16px;border-radius:8px;color:#F1F5F9;white-space:pre-wrap">{report}</pre>
  <p style="color:#94A3B8;font-size:12px;margin-top:24px">Frank AI OS · Davvero Gelato · {timestamp}</p>
</div>
""",
    "warning_alert": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0F172A;color:#F1F5F9;padding:24px;border-radius:12px">
  <h2 style="color:#F59E0B">⚠️ ATENÇÃO — Frank AI OS</h2>
  <p><strong>Tipo:</strong> {rule}</p>
  <p><strong>Unidade:</strong> {unit_id}</p>
  <p><strong>Detalhe:</strong> {message}</p>
  <p style="color:#94A3B8;font-size:12px;margin-top:24px">Frank AI OS · Davvero Gelato · {timestamp}</p>
</div>
""",
}


class EmailConnector:

    def _render_template(self, template_name: str, **kwargs) -> str:
        from datetime import datetime
        kwargs.setdefault("timestamp", datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"))
        template = TEMPLATES.get(template_name, "<p>{message}</p>")
        return template.format(**{k: str(v) for k, v in kwargs.items()})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    async def send(
        self,
        to: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> bool:
        if not settings.enable_email:
            logger.info("email_disabled", to=to, subject=subject)
            return True

        if settings.mock_external_apis:
            logger.info("email_mock_sent", to=to, subject=subject)
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        async with aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=False,
            start_tls=True,
        ) as smtp:
            await smtp.login(settings.smtp_user, settings.smtp_password)
            await smtp.send_message(msg)

        logger.info("email_sent", to=to, subject=subject)
        return True

    async def send_alert(self, alert: dict) -> bool:
        body = self._render_template(
            "critical_alert" if alert.get("severity") == "critical" else "warning_alert",
            **alert,
        )
        return await self.send(
            to=[settings.alert_email],
            subject=f"{'🔴' if alert.get('severity') == 'critical' else '⚠️'} Frank AI OS — {alert.get('title', 'Alerta')}",
            body_html=body,
        )

    async def send_daily_briefing(self, report: str) -> bool:
        from datetime import datetime
        body = self._render_template("daily_briefing", report=report)
        return await self.send(
            to=[settings.alert_email],
            subject=f"🌅 Frank AI OS — Briefing Matinal {datetime.utcnow().strftime('%d/%m/%Y')}",
            body_html=body,
        )


email_connector = EmailConnector()

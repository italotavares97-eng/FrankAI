# =============================================================================
# INTEGRATIONS/EMAIL.PY — Frank AI OS
# Conector de e-mail via SMTP (aiosmtplib) com templates Jinja2
# =============================================================================

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import aiosmtplib
from jinja2 import Environment, BaseLoader

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM

logger = logging.getLogger("frank.email")

# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES = {
    "alert": """
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
<div style="background:#1a1a2e;color:#eee;padding:20px;border-radius:8px 8px 0 0">
  <h2 style="margin:0">⚠️ Alerta Frank AI OS</h2>
  <p style="margin:5px 0;color:#aaa">{{ subject }}</p>
</div>
<div style="padding:20px;border:1px solid #ddd;border-radius:0 0 8px 8px">
  <p><strong>Unidade:</strong> {{ unit_name }}</p>
  <p><strong>Severidade:</strong> <span style="color:{{ severity_color }}">{{ severity }}</span></p>
  <p><strong>Detalhe:</strong> {{ detail }}</p>
  <pre style="background:#f5f5f5;padding:15px;border-radius:4px;overflow-x:auto">{{ body }}</pre>
  <hr>
  <small style="color:#999">Frank AI OS · Davvero Gelato · {{ timestamp }}</small>
</div></body></html>""",

    "report": """
<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto">
<div style="background:#0f3460;color:#eee;padding:20px;border-radius:8px 8px 0 0">
  <h2 style="margin:0">📊 {{ title }}</h2>
  <p style="margin:5px 0;color:#aaa">Davvero Gelato · {{ period }}</p>
</div>
<div style="padding:20px;border:1px solid #ddd;border-radius:0 0 8px 8px">
  <pre style="background:#f5f5f5;padding:15px;border-radius:4px;white-space:pre-wrap">{{ content }}</pre>
  <hr>
  <small style="color:#999">Gerado por Frank AI OS · {{ timestamp }}</small>
</div></body></html>""",

    "task": """
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
<div style="background:#16213e;color:#eee;padding:20px;border-radius:8px 8px 0 0">
  <h2 style="margin:0">✅ Nova Tarefa Gerada</h2>
</div>
<div style="padding:20px;border:1px solid #ddd;border-radius:0 0 8px 8px">
  <table style="width:100%;border-collapse:collapse">
    <tr><td style="padding:8px;font-weight:bold;color:#555">Título</td><td>{{ title }}</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold;color:#555">Responsável</td><td>{{ owner }}</td></tr>
    <tr><td style="padding:8px;font-weight:bold;color:#555">Prazo</td><td>{{ deadline }}</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold;color:#555">Prioridade</td><td>{{ priority }}</td></tr>
    <tr><td style="padding:8px;font-weight:bold;color:#555">Setor</td><td>{{ sector }}</td></tr>
  </table>
  <div style="margin-top:15px;padding:15px;background:#f5f5f5;border-radius:4px">
    <strong>Descrição:</strong><br>{{ description }}
  </div>
  <hr>
  <small style="color:#999">Frank AI OS · {{ timestamp }}</small>
</div></body></html>""",
}

jinja_env = Environment(loader=BaseLoader())


class EmailConnector:
    """Envia e-mails via SMTP com suporte a templates HTML."""

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: bool = True,
        cc: Optional[List[str]] = None,
    ) -> bool:
        """
        Envia e-mail simples.

        Args:
            to: lista de destinatários
            subject: assunto
            body: corpo (texto plano ou HTML)
            html: True para HTML, False para texto
            cc: cópia (opcional)

        Returns:
            True se enviado com sucesso
        """
        msg = MIMEMultipart("alternative")
        msg["From"]    = SMTP_FROM
        msg["To"]      = ", ".join(to)
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        part = MIMEText(body, "html" if html else "plain", "utf-8")
        msg.attach(part)

        try:
            await aiosmtplib.send(
                msg,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASS,
                start_tls=True,
            )
            logger.info(f"Email enviado para {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Falha ao enviar email: {e}")
            return False

    async def send_alert(
        self,
        to: List[str],
        unit_name: str,
        severity: str,
        detail: str,
        body: str,
    ) -> bool:
        """Envia alerta formatado."""
        from datetime import datetime
        severity_colors = {
            "critico": "#e74c3c",
            "alerta":  "#e67e22",
            "atencao": "#f1c40f",
            "info":    "#3498db",
        }
        template = jinja_env.from_string(TEMPLATES["alert"])
        html = template.render(
            subject=f"Alerta {severity.upper()} — {unit_name}",
            unit_name=unit_name,
            severity=severity.upper(),
            severity_color=severity_colors.get(severity, "#e74c3c"),
            detail=detail,
            body=body,
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        return await self.send_email(
            to=to,
            subject=f"⚠️ [{severity.upper()}] {unit_name} — Frank AI OS",
            body=html,
        )

    async def send_report(
        self,
        to: List[str],
        title: str,
        content: str,
        period: str = "",
    ) -> bool:
        """Envia relatório formatado."""
        from datetime import datetime
        template = jinja_env.from_string(TEMPLATES["report"])
        html = template.render(
            title=title,
            content=content,
            period=period or datetime.now().strftime("%B/%Y"),
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        return await self.send_email(to=to, subject=f"📊 {title}", body=html)

    async def send_task_notification(
        self,
        to: List[str],
        title: str,
        owner: str,
        deadline: str,
        priority: str,
        sector: str,
        description: str,
    ) -> bool:
        """Envia notificação de nova tarefa."""
        from datetime import datetime
        template = jinja_env.from_string(TEMPLATES["task"])
        html = template.render(
            title=title, owner=owner, deadline=deadline,
            priority=priority, sector=sector, description=description,
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        return await self.send_email(
            to=to,
            subject=f"✅ Nova tarefa: {title}",
            body=html,
        )

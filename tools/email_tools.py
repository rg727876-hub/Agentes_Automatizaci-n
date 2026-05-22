import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT


def send_report_email(to_email: str, subject: str, body: str) -> str:
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return json.dumps({
            "error": (
                "Email no configurado. Agrega EMAIL_SENDER y EMAIL_PASSWORD "
                "al archivo .env para habilitar el envío de reportes."
            )
        }, ensure_ascii=False)

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())

        return json.dumps({
            "success": True,
            "message": f"Reporte enviado exitosamente a {to_email}",
            "subject": subject,
        }, ensure_ascii=False)

    except smtplib.SMTPAuthenticationError:
        return json.dumps({
            "error": (
                "Error de autenticación. Verifica EMAIL_SENDER y EMAIL_PASSWORD en .env. "
                "Para Gmail, usa una 'Contraseña de aplicación' (no tu contraseña normal)."
            )
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error al enviar email: {str(e)}"}, ensure_ascii=False)


EMAIL_TOOLS = [
    {
        "name": "send_report_email",
        "description": (
            "Envía un reporte o informe por correo electrónico. "
            "Úsalo cuando el usuario pida enviar un reporte a un correo, "
            "o cuando generes un informe y el usuario quiera recibirlo por email."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to_email": {
                    "type": "string",
                    "description": "Dirección de correo electrónico del destinatario"
                },
                "subject": {
                    "type": "string",
                    "description": "Asunto del correo (ej: 'Reporte Ejecutivo - Mayo 2026')"
                },
                "body": {
                    "type": "string",
                    "description": "Contenido completo del reporte en texto plano"
                },
            },
            "required": ["to_email", "subject", "body"],
        },
    }
]


def execute_email_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "send_report_email":
        return send_report_email(**tool_input)
    return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})

"""Monitor automático de alertas de inventario.

Corre en un hilo de fondo y, cada ALERT_CHECK_INTERVAL minutos:
  1. Detecta productos con stock bajo/crítico/sin stock en la BD.
  2. Crea nuevas alertas en inventory_alerts si aún no existen.
  3. Envía un email resumen con todas las alertas no notificadas.
  4. Marca esas alertas como notificadas.
"""
import smtplib
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    ALERT_CHECK_INTERVAL,
    ALERT_EMAIL_TO,
    EMAIL_PASSWORD,
    EMAIL_SENDER,
    EMAIL_SMTP_PORT,
    EMAIL_SMTP_SERVER,
)
from database import get_connection

# ── thresholds ────────────────────────────────────────────────────────────────
_TYPE_SIN_STOCK = "sin_stock"
_TYPE_CRITICO = "stock_critico"
_TYPE_BAJO = "stock_bajo"

# stock_critico: quantity > 0 pero <= 50 % del reorder_point
_CRITICO_RATIO = 0.5


# ── helpers de BD ─────────────────────────────────────────────────────────────

def _detect_and_upsert_alerts(conn) -> None:
    """Revisa inventario en vivo y crea alertas nuevas cuando corresponde."""
    rows = conn.execute(
        """
        SELECT p.id AS product_id, p.name, p.reorder_point,
               i.quantity
        FROM   products p
        JOIN   inventory i ON i.product_id = p.id
        """
    ).fetchall()

    for row in rows:
        pid = row["product_id"]
        qty = row["quantity"]
        rp = row["reorder_point"] or 10
        name = row["name"]

        if qty == 0:
            alert_type = _TYPE_SIN_STOCK
            message = f"CRÍTICO: {name} sin stock (0 unidades). Reponer de inmediato."
        elif qty <= rp * _CRITICO_RATIO:
            alert_type = _TYPE_CRITICO
            message = (
                f"ALERTA: {name} con stock crítico ({qty} u. / punto de reorden {rp} u.)."
            )
        elif qty <= rp:
            alert_type = _TYPE_BAJO
            message = (
                f"AVISO: {name} con stock bajo ({qty} u. / punto de reorden {rp} u.)."
            )
        else:
            continue  # stock OK → no hay alerta

        # Evita duplicados: solo inserta si no hay alerta activa del mismo tipo
        existing = conn.execute(
            """
            SELECT id FROM inventory_alerts
            WHERE  product_id = %s
              AND  alert_type = %s
              AND  is_resolved = 0
            """,
            (pid, alert_type),
        ).fetchone()

        if not existing:
            conn.execute(
                """
                INSERT INTO inventory_alerts
                    (product_id, alert_type, message, is_resolved, notified)
                VALUES (%s, %s, %s, 0, FALSE)
                """,
                (pid, alert_type, message),
            )

    conn.commit()


def _get_unnotified_alerts(conn) -> list:
    """Devuelve todas las alertas activas aún no enviadas por email."""
    rows = conn.execute(
        """
        SELECT ia.id, ia.alert_type, ia.message,
               ia.created_at, p.name AS product_name
        FROM   inventory_alerts ia
        JOIN   products p ON p.id = ia.product_id
        WHERE  ia.is_resolved = 0
          AND  ia.notified    = FALSE
        ORDER  BY ia.alert_type, p.name
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _mark_notified(conn, alert_ids: list[int]) -> None:
    if not alert_ids:
        return
    placeholders = ", ".join(["%s"] * len(alert_ids))
    conn.execute(
        f"UPDATE inventory_alerts SET notified = TRUE WHERE id IN ({placeholders})",
        alert_ids,
    )
    conn.commit()


# ── email ─────────────────────────────────────────────────────────────────────

def _build_email_body(alerts: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"SISTEMA MULTIAGENTE — Reporte de Alertas de Inventario",
        f"Generado: {now}",
        f"Total de alertas activas: {len(alerts)}",
        "=" * 60,
        "",
    ]

    icons = {
        _TYPE_SIN_STOCK: "🔴 SIN STOCK",
        _TYPE_CRITICO: "🟠 STOCK CRÍTICO",
        _TYPE_BAJO: "🟡 STOCK BAJO",
    }

    for a in alerts:
        label = icons.get(a["alert_type"], a["alert_type"].upper())
        created = str(a.get("created_at", ""))[:16]
        lines.append(f"[{label}]  {a['product_name']}")
        lines.append(f"  {a['message']}")
        lines.append(f"  Detectado: {created}")
        lines.append("")

    lines += [
        "=" * 60,
        "Este es un mensaje automático del Sistema Multiagente de Inventario.",
        "Para resolver alertas, usa el agente de inventario.",
    ]
    return "\n".join(lines)


def _send_alert_email(alerts: list[dict]) -> bool:
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not ALERT_EMAIL_TO:
        print(
            "  [AlertMonitor] Email no configurado (EMAIL_SENDER / EMAIL_PASSWORD / ALERT_EMAIL_TO)."
        )
        return False

    body = _build_email_body(alerts)
    subject = f"[Inventario] {len(alerts)} alerta(s) activa(s) — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_SENDER
    msg["To"] = ALERT_EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, ALERT_EMAIL_TO, msg.as_string())
        print(f"  [AlertMonitor] Email enviado a {ALERT_EMAIL_TO} ({len(alerts)} alertas).")
        return True
    except Exception as e:
        print(f"  [AlertMonitor] Error al enviar email: {e}")
        return False


# ── ciclo principal ───────────────────────────────────────────────────────────

def run_check(db_path=None) -> None:
    """Ejecuta un ciclo completo: detectar → email → marcar notificado."""
    try:
        conn = get_connection(db_path)
        try:
            _detect_and_upsert_alerts(conn)
            alerts = _get_unnotified_alerts(conn)

            if not alerts:
                return

            sent = _send_alert_email(alerts)
            if sent:
                _mark_notified(conn, [a["id"] for a in alerts])
        finally:
            conn.close()
    except Exception as e:
        print(f"  [AlertMonitor] Error en ciclo de verificación: {e}")


def start_background_monitor(db_path=None) -> threading.Thread:
    """Lanza el monitor en un hilo daemon. Retorna el hilo."""
    interval_seconds = ALERT_CHECK_INTERVAL * 60

    def _loop():
        print(
            f"  [AlertMonitor] Iniciado — revisión cada {ALERT_CHECK_INTERVAL} min → {ALERT_EMAIL_TO}"
        )
        while True:
            run_check(db_path)
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="AlertMonitor")
    t.start()
    return t

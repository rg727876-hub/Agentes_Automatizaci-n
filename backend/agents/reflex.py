"""Respuestas 'por reflejo': atajos instantáneos SIN gastar tokens.

Para mensajes triviales (saludos, agradecimientos, despedidas) responde con
reglas simples, evitando una llamada al LLM y al grafo de agentes. Es la primera
línea de control de costo: lo que se puede resolver sin modelo, no usa modelo.

Devuelve `None` cuando el mensaje requiere razonamiento real — ahí toma el
control el orquestador.
"""
import re

_SALUDOS = {
    "hola", "buenas", "buenos dias", "buenos dias", "buenas tardes",
    "buenas noches", "hey", "que tal", "saludos", "holi", "buenas buenas",
}
_AGRADECIMIENTOS = {
    "gracias", "muchas gracias", "mil gracias", "te lo agradezco",
    "muy amable", "perfecto gracias", "ok gracias", "genial gracias",
}
_DESPEDIDAS = {
    "adios", "chao", "hasta luego", "nos vemos", "hasta pronto", "bye",
}

_RESP_SALUDO = (
    "¡Hola! Soy tu asistente de inventario retail. Puedo ayudarte con stock, "
    "ventas, pronósticos de demanda, proveedores, órdenes de compra y reportes. "
    "¿Qué necesitas?"
)
_RESP_GRACIAS = "¡Con gusto! ¿Hay algo más en lo que pueda ayudarte?"
_RESP_DESPEDIDA = "¡Hasta pronto! Aquí estaré cuando me necesites."


def _normalize(text: str) -> str:
    """minúsculas, sin signos de puntuación ni acentos relevantes para el match."""
    text = text.strip().lower()
    text = re.sub(r"[¡!¿?.,;:]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def reflex_response(message: str):
    """Devuelve una respuesta inmediata para mensajes triviales, o None."""
    msg = _normalize(message)
    if not msg:
        return None
    if msg in _SALUDOS:
        return _RESP_SALUDO
    if msg in _AGRADECIMIENTOS:
        return _RESP_GRACIAS
    if msg in _DESPEDIDAS:
        return _RESP_DESPEDIDA
    return None

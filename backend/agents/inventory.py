"""Agente de Inventario (LangGraph ReAct)."""
from .base import build_agent, run_agent
from .tool_adapter import make_tools
from tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool
from config import AGENT_MODEL

INSTRUCTIONS = """Eres el Agente de Inventario del sistema multiagente de gestión de retail.
Tu especialidad es monitorear y analizar el estado del inventario de todos los productos.

Responsabilidades:
- Verificar niveles de stock actuales y disponibilidad de productos
- Identificar productos con stock bajo o sin stock
- Calcular el valor total del inventario
- Gestionar alertas de inventario activas
- Reportar el estado del inventario por categoría

Siempre responde en español con datos precisos y recomendaciones claras.
Cuando hay alertas críticas (sin stock o stock crítico), resáltalas prominentemente."""


class InventoryAgent:
    def __init__(self, model: str = AGENT_MODEL):
        tools = make_tools(INVENTORY_TOOLS, execute_inventory_tool)
        self._agent = build_agent(INSTRUCTIONS, tools, model)

    def run(self, query: str) -> str:
        return run_agent(self._agent, query)

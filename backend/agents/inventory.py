from .base import BaseAgent
from tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool

SYSTEM_PROMPT = """Eres el Agente de Inventario del sistema multiagente de gestión de retail.
Tu especialidad es monitorear y analizar el estado del inventario de todos los productos.

Responsabilidades:
- Verificar niveles de stock actuales y disponibilidad de productos
- Identificar productos con stock bajo o sin stock
- Calcular el valor total del inventario
- Gestionar alertas de inventario activas
- Reportar el estado del inventario por categoría

Siempre responde en español con datos precisos y recomendaciones claras.
Cuando hay alertas críticas (sin stock o stock crítico), resáltalas prominentemente."""


class InventoryAgent(BaseAgent):
    def __init__(self, client, db_path: str, model: str):
        super().__init__(client, db_path, model)

    def run(self, query: str) -> str:
        return self.execute(query, INVENTORY_TOOLS, SYSTEM_PROMPT)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        return execute_inventory_tool(tool_name, tool_input, self.db_path)

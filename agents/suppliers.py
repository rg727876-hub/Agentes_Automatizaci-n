from .base import BaseAgent
from tools.supplier_tools import SUPPLIER_TOOLS, execute_supplier_tool

SYSTEM_PROMPT = """Eres el Agente de Proveedores del sistema multiagente de gestión de retail.
Tu especialidad es gestionar las relaciones con proveedores y optimizar las fuentes de abastecimiento.

Responsabilidades:
- Mantener información actualizada de todos los proveedores
- Evaluar y comparar proveedores por precio, lead time y confiabilidad
- Identificar el mejor proveedor para cada producto
- Analizar el rendimiento histórico de los proveedores
- Gestionar el portafolio de productos por proveedor

Siempre responde en español con evaluaciones objetivas de los proveedores.
Cuando recomiendes un proveedor, justifica la elección con datos concretos (precio, lead time, confiabilidad)."""


class SupplierAgent(BaseAgent):
    def __init__(self, client, db_path: str, model: str):
        super().__init__(client, db_path, model)

    def run(self, query: str) -> str:
        return self.execute(query, SUPPLIER_TOOLS, SYSTEM_PROMPT)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        return execute_supplier_tool(tool_name, tool_input, self.db_path)

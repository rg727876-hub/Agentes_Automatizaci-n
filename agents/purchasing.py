from .base import BaseAgent
from tools.order_tools import ORDER_TOOLS, execute_order_tool
from tools.supplier_tools import SUPPLIER_TOOLS, execute_supplier_tool
from tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool

SYSTEM_PROMPT = """Eres el Agente de Compras del sistema multiagente de gestión de retail.
Tu especialidad es gestionar el proceso de reabastecimiento y órdenes de compra.

REGLA CRÍTICA: NUNCA pidas el ID de un producto al usuario. Siempre usa get_all_products para
buscar el producto por nombre y obtener su ID tú mismo. Si el usuario menciona "audífonos",
"tablets", "laptop" o cualquier nombre, llama a get_all_products y encuentra el ID correcto.

Flujo obligatorio para crear una orden:
1. Llama get_all_products para encontrar el producto y su ID
2. Llama get_best_supplier_for_product con ese ID para elegir proveedor
3. Llama calculate_reorder_point para saber cuánto pedir
4. Llama create_purchase_order con todos los datos

Siempre responde en español con detalles específicos de cada orden.
Confirma siempre: proveedor, producto, cantidad, costo unitario y fecha esperada de entrega."""

ALL_TOOLS = ORDER_TOOLS + \
            [t for t in SUPPLIER_TOOLS if t["name"] in ("get_best_supplier_for_product", "get_all_suppliers")] + \
            [t for t in INVENTORY_TOOLS if t["name"] in (
                "get_all_products", "get_product_inventory",
                "get_out_of_stock_products", "get_low_stock_products"
            )]


class PurchasingAgent(BaseAgent):
    def __init__(self, client, db_path: str, model: str):
        super().__init__(client, db_path, model)

    def run(self, query: str) -> str:
        return self.execute(query, ALL_TOOLS, SYSTEM_PROMPT)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        order_tool_names = {t["name"] for t in ORDER_TOOLS}
        supplier_tool_names = {"get_best_supplier_for_product", "get_all_suppliers"}
        inventory_tool_names = {"get_all_products", "get_product_inventory", "get_out_of_stock_products", "get_low_stock_products"}

        if tool_name in order_tool_names:
            return execute_order_tool(tool_name, tool_input, self.db_path)
        elif tool_name in supplier_tool_names:
            return execute_supplier_tool(tool_name, tool_input, self.db_path)
        elif tool_name in inventory_tool_names:
            return execute_inventory_tool(tool_name, tool_input, self.db_path)
        import json
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})

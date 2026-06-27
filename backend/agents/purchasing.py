"""Agente de Compras (LangGraph ReAct)."""
from .base import build_agent, run_agent
from .tool_adapter import make_tools
from tools.order_tools import ORDER_TOOLS, execute_order_tool
from tools.supplier_tools import SUPPLIER_TOOLS, execute_supplier_tool
from tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool
from config import AGENT_MODEL

_SUPPLIER_SUBSET = [t for t in SUPPLIER_TOOLS if t["name"] in ("get_best_supplier_for_product", "get_all_suppliers")]
_INVENTORY_SUBSET = [t for t in INVENTORY_TOOLS if t["name"] in (
    "get_all_products", "get_product_inventory",
    "get_out_of_stock_products", "get_low_stock_products",
)]

INSTRUCTIONS = """Eres el Agente de Compras del sistema multiagente de gestión de retail.
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


class PurchasingAgent:
    def __init__(self, model: str = AGENT_MODEL):
        tools = (
            make_tools(ORDER_TOOLS, execute_order_tool)
            + make_tools(_SUPPLIER_SUBSET, execute_supplier_tool)
            + make_tools(_INVENTORY_SUBSET, execute_inventory_tool)
        )
        self._agent = build_agent(INSTRUCTIONS, tools, model)

    def run(self, query: str) -> str:
        return run_agent(self._agent, query)

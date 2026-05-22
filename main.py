import fix_ssl  # debe ser el primer import
import sys
import io
import json
from google import genai

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

from config import GEMINI_API_KEY, DB_PATH
from database import setup_database, get_connection
from agents import OrchestratorAgent
from memory import VectorMemory

BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║     SISTEMA MULTIAGENTE DE INVENTARIO RETAIL                    ║
║     Powered by Google Gemini + ChromaDB                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Agentes activos:                                               ║
║    • Inventario   • Ventas      • Demanda                       ║
║    • Proveedores  • Compras     • Reportes (+ envío por email)  ║
╠══════════════════════════════════════════════════════════════════╣
║  Comandos especiales:                                           ║
║    /historial   - Ver conversaciones guardadas                  ║
║    /buscar <x>  - Búsqueda semántica de productos               ║
║    /memoria     - Ver estadísticas de la memoria                ║
║    /limpiar     - Limpiar historial de conversaciones           ║
║    salir        - Terminar la sesión                            ║
╚══════════════════════════════════════════════════════════════════╝

Escribe tu consulta en lenguaje natural. Ejemplos:
  - "¿Qué productos están sin stock?"
  - "Muéstrame las ventas de los últimos 30 días"
  - "¿Qué productos están en riesgo de desabasto?"
  - "Genera un reporte ejecutivo completo"
  - "Genera el reporte y envíalo a gerencia@empresa.com"
  - "¿Cuál es el mejor proveedor para productos de electrónica?"
"""


def _load_products_for_index(db_path: str) -> list:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, p.unit_price, i.quantity "
            "FROM products p JOIN inventory i ON p.id = i.product_id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def handle_special_command(cmd: str, memory: VectorMemory) -> bool:
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()

    if command == "/historial":
        entries = memory.get_history(limit=10)
        if not entries:
            print("No hay conversaciones guardadas aún.\n")
        else:
            print(f"\n--- Últimas {len(entries)} conversaciones ---")
            for i, e in enumerate(entries, 1):
                ts = e.get("timestamp", "")[:16].replace("T", " ")
                agents = json.loads(e.get("agents_used", "[]"))
                names = [a.replace("invoke_", "").replace("_agent", "") for a in agents]
                print(f"{i}. [{ts}] {e.get('query', '')[:80]}")
                if names:
                    print(f"   Agentes: {', '.join(names)}")
            print()
        return True

    if command == "/buscar":
        if len(parts) < 2:
            print("Uso: /buscar <texto>\n")
            return True
        results = memory.search_products(parts[1], n_results=5)
        if not results:
            print("Sin resultados.\n")
        else:
            print(f"\n--- Productos similares a '{parts[1]}' ---")
            for r in results:
                bar = "#" * int(r["relevance"] * 10)
                print(f"  [{bar:<10}] {r['relevance']:.2f}  {r['document'][:100]}")
            print()
        return True

    if command == "/memoria":
        stats = memory.get_stats()
        print(f"\n  Conversaciones guardadas : {stats['total_conversations']}")
        print(f"  Productos indexados      : {stats['total_products_indexed']}\n")
        return True

    if command == "/limpiar":
        confirm = input("¿Limpiar historial? (s/n): ").strip().lower()
        if confirm == "s":
            memory.clear_conversations()
            print("Historial limpiado.\n")
        else:
            print("Cancelado.\n")
        return True

    return False


def main():
    if not GEMINI_API_KEY:
        print("ERROR: Configura tu GEMINI_API_KEY en el archivo .env")
        print("Obtén tu clave gratis en: https://aistudio.google.com/apikey")
        sys.exit(1)

    print(BANNER)

    print("Inicializando base de datos SQLite...", end=" ", flush=True)
    setup_database(DB_PATH)
    print("OK")

    print("Inicializando memoria vectorial ChromaDB...", end=" ", flush=True)
    memory = VectorMemory(persist_dir="./vector_store")
    products = _load_products_for_index(DB_PATH)
    memory.index_products(products)
    stats = memory.get_stats()
    print(f"OK ({stats['total_conversations']} conversaciones | {stats['total_products_indexed']} productos)")

    print("Conectando con Gemini...", end=" ", flush=True)
    client = genai.Client(api_key=GEMINI_API_KEY)
    orchestrator = OrchestratorAgent(client, DB_PATH, memory=memory)
    print("OK\n")

    while True:
        try:
            query = input("Tu consulta: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSesión finalizada.")
            break

        if not query:
            continue

        if query.lower() in ("salir", "exit", "quit", "q"):
            print("Hasta luego.")
            break

        if query.startswith("/"):
            handle_special_command(query, memory)
            continue

        print("\nProcesando...\n")
        try:
            response = orchestrator.execute(query)
            print("=" * 66)
            print(response)
            print("=" * 66 + "\n")
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()

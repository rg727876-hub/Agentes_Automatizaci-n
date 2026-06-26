"""Router de memoria: historial de conversaciones y búsqueda semántica."""
from fastapi import APIRouter

from api.state import get_memory
from api.utils import parse_json

router = APIRouter(tags=["memory"])


@router.get("/history")
def history(limit: int = 10):
    memory = get_memory()
    if memory is None:
        return {"history": []}
    entries = memory.get_history(limit=limit)
    out = []
    for e in entries:
        agents = parse_json(e.get("agents_used", "[]")) or []
        out.append({
            "query": e.get("query", ""),
            "timestamp": e.get("timestamp", ""),
            "agents": [a.replace("invoke_", "").replace("_agent", "") for a in agents],
        })
    return {"history": out}


@router.get("/search")
def search(q: str):
    memory = get_memory()
    if memory is None or not q.strip():
        return {"results": []}
    results = memory.search_products(q.strip(), n_results=8)
    return {"results": results}


@router.get("/memory/stats")
def memory_stats():
    memory = get_memory()
    if memory is None:
        return {"total_conversations": 0, "total_products_indexed": 0}
    return memory.get_stats()

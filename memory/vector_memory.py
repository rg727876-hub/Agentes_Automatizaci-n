import uuid
import json
from datetime import datetime
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Usa la API de Gemini para generar embeddings, sin descargar modelos locales."""

    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:
        result = []
        for text in input:
            response = self._client.models.embed_content(
                model=self._model,
                contents=text,
            )
            result.append(list(response.embeddings[0].values))
        return result


class VectorMemory:
    """
    Memoria vectorial persistente usando ChromaDB + embeddings de Gemini.

    Almacena cada interacción (consulta + respuesta) como un vector semántico.
    En la próxima sesión busca conversaciones similares para darle contexto
    al orquestador, haciendo que el sistema recuerde consultas previas.
    """

    def __init__(self, persist_dir: str = "./vector_store", embedding_function=None):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.ef = embedding_function

        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )
        self.product_index = self.client.get_or_create_collection(
            name="product_index",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Conversaciones
    # ------------------------------------------------------------------

    def save_interaction(self, query: str, response: str, agents_used: list = None) -> str:
        doc_id = str(uuid.uuid4())
        document = f"CONSULTA: {query}\n\nRESPUESTA DEL SISTEMA: {response}"
        self.conversations.add(
            ids=[doc_id],
            documents=[document],
            metadatas=[{
                "query": query[:500],
                "timestamp": datetime.now().isoformat(),
                "agents_used": json.dumps(agents_used or []),
                "response_length": len(response),
            }],
        )
        return doc_id

    def get_relevant_context(self, query: str, n_results: int = 3, similarity_threshold: float = 0.75) -> str:
        count = self.conversations.count()
        if count == 0:
            return ""
        results = self.conversations.query(
            query_texts=[query],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )
        if not results["documents"] or not results["documents"][0]:
            return ""
        relevant = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if distance <= (1.0 - similarity_threshold):
                ts = meta.get("timestamp", "")[:10]
                agents = json.loads(meta.get("agents_used", "[]"))
                agent_str = ", ".join(
                    a.replace("invoke_", "").replace("_agent", "") for a in agents
                ) if agents else "desconocido"
                relevant.append(f"[{ts} | agentes: {agent_str}]\n{doc[:700]}")
        return "\n\n---\n\n".join(relevant) if relevant else ""

    def get_history(self, limit: int = 10) -> list:
        count = self.conversations.count()
        if count == 0:
            return []
        results = self.conversations.get(include=["metadatas"], limit=min(limit, count))
        entries = sorted(
            results["metadatas"],
            key=lambda m: m.get("timestamp", ""),
            reverse=True,
        )
        return entries[:limit]

    # ------------------------------------------------------------------
    # Indice de productos
    # ------------------------------------------------------------------

    def index_products(self, products: list):
        if self.product_index.count() > 0:
            return
        ids, documents, metadatas = [], [], []
        for p in products:
            ids.append(str(p["id"]))
            documents.append(
                f"{p['name']}. Categoria: {p['category']}. "
                f"SKU: {p['sku']}. Precio: ${p['unit_price']:,.0f}. "
                f"Stock: {p['quantity']} unidades."
            )
            metadatas.append({
                "sku": p["sku"],
                "category": p["category"],
                "unit_price": str(p["unit_price"]),
                "quantity": str(p["quantity"]),
            })
        if ids:
            self.product_index.add(ids=ids, documents=documents, metadatas=metadatas)

    def search_products(self, query: str, n_results: int = 5) -> list:
        count = self.product_index.count()
        if count == 0:
            return []
        results = self.product_index.query(
            query_texts=[query],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )
        if not results["documents"] or not results["documents"][0]:
            return []
        return [
            {"document": doc, "metadata": meta, "relevance": round(1 - dist, 3)}
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    # ------------------------------------------------------------------
    # Estadisticas y mantenimiento
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        return {
            "total_conversations": self.conversations.count(),
            "total_products_indexed": self.product_index.count(),
        }

    def clear_conversations(self):
        self.client.delete_collection("conversations")
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

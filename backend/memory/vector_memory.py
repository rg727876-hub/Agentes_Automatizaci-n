"""Memoria vectorial persistente sobre PostgreSQL + pgvector.

Sustituye a ChromaDB local: los embeddings viven en la misma base de datos
Supabase (extensión `vector`), por lo que la memoria es **persistente** y
**compartida entre instancias** — clave para desplegar en AWS App Runner, donde
el sistema de archivos del contenedor es efímero.

Los embeddings se generan con la API de embeddings de Gemini
(`text-embedding-004`, 768 dimensiones), reutilizando el mismo cliente `genai`
que ya usan los agentes.

La interfaz pública (save_interaction, get_relevant_context, get_history,
index_products, search_products, get_stats, clear_conversations) se mantiene
idéntica a la versión ChromaDB, así que el resto del sistema no cambia.

Las tablas (`memory_conversations`, `memory_product_index`) y la extensión se
crean desde `database/schema.sql` (fuente de verdad) al iniciar el sistema.
"""
import json
import uuid

from google.genai import types

from config import EMBED_MODEL, EMBED_DIM
from database import get_connection


class VectorMemory:
    def __init__(self, client, embed_model: str = EMBED_MODEL, embed_dim: int = EMBED_DIM):
        self.client = client  # cliente genai (para generar embeddings)
        self.embed_model = embed_model
        self.embed_dim = embed_dim

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    def _embed_config(self) -> types.EmbedContentConfig:
        # gemini-embedding-001 emite 3072 dims por defecto; fijamos la dimensión
        # para que coincida con vector(EMBED_DIM) en pgvector.
        return types.EmbedContentConfig(output_dimensionality=self.embed_dim)

    def _embed(self, text: str) -> list:
        resp = self.client.models.embed_content(
            model=self.embed_model, contents=text, config=self._embed_config()
        )
        return list(resp.embeddings[0].values)

    def _embed_batch(self, texts: list) -> list:
        resp = self.client.models.embed_content(
            model=self.embed_model, contents=texts, config=self._embed_config()
        )
        return [list(e.values) for e in resp.embeddings]

    @staticmethod
    def _vec(values: list) -> str:
        """Serializa un vector al literal que entiende pgvector: '[a,b,c]'."""
        return "[" + ",".join(repr(float(v)) for v in values) + "]"

    # ------------------------------------------------------------------
    # Conversaciones
    # ------------------------------------------------------------------
    def save_interaction(self, query: str, response: str, agents_used: list = None) -> str:
        doc_id = str(uuid.uuid4())
        document = f"CONSULTA: {query}\n\nRESPUESTA DEL SISTEMA: {response}"
        try:
            embedding = self._vec(self._embed(document))
        except Exception as e:  # noqa: BLE001
            print(f"[VectorMemory] No se pudo generar embedding (interacción no guardada): {e}")
            return doc_id
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO memory_conversations "
                "(id, query, response, document, agents_used, response_length, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?, ?::vector)",
                (doc_id, query[:500], response, document,
                 json.dumps(agents_used or []), len(response), embedding),
            )
            conn.commit()
        finally:
            conn.close()
        return doc_id

    def get_relevant_context(self, query: str, n_results: int = 3, similarity_threshold: float = 0.75) -> str:
        try:
            vec = self._vec(self._embed(query))
        except Exception:
            return ""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT document, agents_used, created_at, "
                "(embedding <=> ?::vector) AS distance "
                "FROM memory_conversations WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> ?::vector LIMIT ?",
                (vec, vec, n_results),
            ).fetchall()
        except Exception:
            return ""
        finally:
            conn.close()

        relevant = []
        max_distance = 1.0 - similarity_threshold
        for r in rows:
            distance = r["distance"]
            if distance is None or distance > max_distance:
                continue
            ts = str(r["created_at"])[:10]
            agents = json.loads(r["agents_used"] or "[]")
            agent_str = ", ".join(
                a.replace("invoke_", "").replace("_agent", "") for a in agents
            ) if agents else "desconocido"
            relevant.append(f"[{ts} | agentes: {agent_str}]\n{r['document'][:700]}")
        return "\n\n---\n\n".join(relevant) if relevant else ""

    def get_history(self, limit: int = 10) -> list:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT query, agents_used, created_at FROM memory_conversations "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except Exception:
            return []
        finally:
            conn.close()
        return [
            {
                "query": r["query"],
                "timestamp": str(r["created_at"]),
                "agents_used": r["agents_used"] or "[]",
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Índice de productos
    # ------------------------------------------------------------------
    def index_products(self, products: list):
        if not products:
            return
        conn = get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM memory_product_index").fetchone()
            if row and row["c"] > 0:
                return  # ya indexado

            docs = [
                f"{p['name']}. Categoria: {p['category']}. "
                f"SKU: {p['sku']}. Precio: ${p['unit_price']:,.0f}. "
                f"Stock: {p['quantity']} unidades."
                for p in products
            ]
            try:
                embeddings = self._embed_batch(docs)
            except Exception as e:  # noqa: BLE001
                print(f"[VectorMemory] No se pudieron indexar productos: {e}")
                return

            for p, doc, emb in zip(products, docs, embeddings):
                conn.execute(
                    "INSERT INTO memory_product_index "
                    "(id, document, sku, category, unit_price, quantity, embedding) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?::vector) "
                    "ON CONFLICT (id) DO NOTHING",
                    (str(p["id"]), doc, p["sku"], p["category"],
                     str(p["unit_price"]), str(p["quantity"]), self._vec(emb)),
                )
            conn.commit()
        finally:
            conn.close()

    def search_products(self, query: str, n_results: int = 5) -> list:
        try:
            vec = self._vec(self._embed(query))
        except Exception:
            return []
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT document, sku, category, unit_price, quantity, "
                "(embedding <=> ?::vector) AS distance "
                "FROM memory_product_index WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> ?::vector LIMIT ?",
                (vec, vec, n_results),
            ).fetchall()
        except Exception:
            return []
        finally:
            conn.close()
        return [
            {
                "document": r["document"],
                "metadata": {
                    "sku": r["sku"],
                    "category": r["category"],
                    "unit_price": r["unit_price"],
                    "quantity": r["quantity"],
                },
                "relevance": round(1 - r["distance"], 3) if r["distance"] is not None else 0.0,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Estadísticas y mantenimiento
    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        conn = get_connection()
        try:
            convs = conn.execute("SELECT COUNT(*) AS c FROM memory_conversations").fetchone()["c"]
            prods = conn.execute("SELECT COUNT(*) AS c FROM memory_product_index").fetchone()["c"]
        except Exception:
            return {"total_conversations": 0, "total_products_indexed": 0}
        finally:
            conn.close()
        return {"total_conversations": convs, "total_products_indexed": prods}

    def clear_conversations(self):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM memory_conversations")
            conn.commit()
        finally:
            conn.close()

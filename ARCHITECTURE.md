# 🏛️ Arquitectura del Sistema

Documento de referencia de la arquitectura del **Sistema Multiagente de
Inventario Retail**. Describe cómo está organizado el código por capas, dónde va
cada cosa nueva que agreguemos, y cómo se despliega en **AWS App Runner**.

> Objetivo de este documento: que cualquier persona (o agente) que llegue al
> proyecto sepa **dónde poner cada cosa** y **cómo llega a producción**, sin
> tener que adivinar.

---

## 1. Visión general

Es una aplicación web de un solo servicio: **una API FastAPI que también sirve el
frontend estático**. La inteligencia está en un **orquestador** que coordina 6
agentes especializados (Gemini con *function calling*). Los datos viven en
**PostgreSQL (Supabase)** y la **memoria semántica** usa **pgvector** sobre esa
misma base.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Navegador (cliente)                         │
│            Dashboard + Chat  (HTML / CSS / JS, sin build)          │
└───────────────────────────────┬──────────────────────────────────┘
                                 │ HTTPS
┌───────────────────────────────▼──────────────────────────────────┐
│                  AWS App Runner  (contenedor Docker)               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI (Uvicorn)                                           │  │
│  │   ├─ api/        Capa de presentación (routers REST)         │  │
│  │   ├─ agents/     Orquestador + 6 agentes (Gemini)            │  │
│  │   ├─ tools/      Lógica de negocio / acceso a datos          │  │
│  │   ├─ memory/     Memoria vectorial (pgvector)                │  │
│  │   ├─ database/   Conexión + esquema + seed                   │  │
│  │   └─ frontend/   Estáticos servidos por el mismo proceso     │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────┬─────────────────────────────────┬────────────────────┘
            │ psycopg2 (SSL)                   │ HTTPS
┌───────────▼───────────────┐    ┌────────────▼─────────────────────┐
│  Supabase PostgreSQL       │    │  Google Gemini API               │
│   ├─ tablas de negocio     │    │   ├─ modelos de chat (agentes)   │
│   └─ pgvector (memoria)    │    │   └─ embeddings (memoria)        │
└────────────────────────────┘    └──────────────────────────────────┘
            │
┌───────────▼───────────────┐
│  SMTP (Gmail) — reportes   │
│  y alertas por email       │
└────────────────────────────┘
```

---

## 2. Arquitectura por capas

El código vive bajo `backend/`, que es la **raíz de import** (`PYTHONPATH`). Por
eso los imports son planos: `from config import ...`, `from agents import ...`.
Mantener esta raíz es intencional; mover `config.py` a un subpaquete rompería
todos los módulos.

| Capa | Carpeta | Responsabilidad | Regla de oro |
|---|---|---|---|
| **Presentación** | `backend/api/` | Endpoints REST, validación de entrada/salida (Pydantic), serialización. | No contiene lógica de negocio: delega en agentes o tools. |
| **Orquestación / Agentes** | `backend/agents/` | Razonamiento con Gemini, enrutado de consultas, *function calling*. | Los agentes llaman a `tools/`, nunca a la BD directamente. |
| **Dominio / Servicios** | `backend/tools/` | Lógica de negocio y consultas: inventario, ventas, demanda, compras, etc. | Devuelven JSON (str). Único lugar con SQL de negocio. |
| **Memoria** | `backend/memory/` | Memoria semántica (embeddings + búsqueda vectorial) sobre pgvector. | Interfaz estable; el resto del sistema no sabe que por debajo es pgvector. |
| **Datos** | `backend/database/` | Conexión a Postgres, esquema (DDL) y datos semilla. | Fuente de verdad del modelo: `schema.sql`. |
| **Configuración / Bootstrap** | `backend/config.py`, `backend/fix_ssl.py` | Variables de entorno, modelos, SSL. | Todo secreto entra por variables de entorno, nunca hardcodeado. |

**Dirección de dependencias** (de arriba hacia abajo, nunca al revés):

```
api  ──►  agents  ──►  tools  ──►  database
  │                       ▲
  └────►  memory  ────────┘   (memory usa database para pgvector)
```

---

## 3. Estructura de carpetas (objetivo)

```
agente_automatizacion/
├── ARCHITECTURE.md            # Este documento
├── README.md                  # Guía de uso / instalación
├── Dockerfile                 # Imagen para AWS App Runner
├── .dockerignore
├── apprunner.yaml             # Config de App Runner (modo source, alternativa)
├── .env.example               # Plantilla de variables de entorno
├── run.ps1 / run.bat          # Lanzadores locales (Windows)
│
├── backend/                   # ── Raíz de la aplicación (PYTHONPATH) ──
│   ├── app.py                 # Punto de entrada: arma FastAPI y monta todo
│   ├── cli.py                 # Cliente de terminal (modo desarrollo/demo)
│   ├── config.py              # Configuración y variables de entorno
│   ├── fix_ssl.py             # Certificados SSL (no-op fuera de Windows)
│   ├── requirements.txt
│   │
│   ├── api/                   # Capa de presentación (routers REST)
│   │   ├── __init__.py        # api_router: agrupa todos los routers bajo /api
│   │   ├── state.py           # Estado compartido + lifespan (init de sistema)
│   │   ├── utils.py           # Helpers (parseo/llamada tolerante a fallos)
│   │   ├── chat.py            # POST /api/chat
│   │   ├── dashboard.py       # GET  /api/dashboard
│   │   ├── catalog.py         # GET  /api/products, /api/suppliers
│   │   ├── memory.py          # GET  /api/history, /api/search, /api/memory/stats
│   │   └── health.py          # GET  /api/health
│   │
│   ├── agents/                # Orquestador + agentes especializados
│   ├── tools/                 # Lógica de negocio por dominio
│   ├── memory/                # Memoria vectorial (pgvector)
│   ├── database/              # Conexión + schema.sql + seed
│   └── scripts/              # Utilidades (smoke_test_db, etc.)
│
└── frontend/                  # Interfaz web (sin build)
    ├── index.html
    └── static/ (app.js, styles.css)
```

---

## 4. Cómo agregar cosas nuevas (convenciones)

Para que el proyecto siga ordenado a medida que crece, sigue estos patrones.

### 4.1 Un endpoint nuevo
1. Crea/edita un router en `backend/api/` (agrúpalo por dominio, p. ej.
   `catalog.py`).
2. Define el `APIRouter()` y sus rutas; toma el estado con los helpers de
   `api/state.py` (`get_orchestrator()`, `get_memory()`).
3. Regístralo en `backend/api/__init__.py` con `api_router.include_router(...)`.
4. La lógica pesada **no** va en el router: va en `tools/` o en un agente.

### 4.2 Un agente nuevo
1. Crea `backend/agents/<nombre>.py` heredando de `BaseAgent`.
2. Define sus `tools` (esquema OpenAPI-like) e implementa `_execute_tool`.
3. Regístralo en `agents/__init__.py` y en `OrchestratorAgent._agents` +
   `_ORCHESTRATOR_TOOL_DEFS` (`invoke_<nombre>_agent`).
4. Actualiza el `SYSTEM_PROMPT` del orquestador para que sepa cuándo usarlo.

### 4.3 Una herramienta (tool) de negocio
1. Crea/edita `backend/tools/<dominio>_tools.py`.
2. Cada función recibe `db_path` (compat) y devuelve **JSON como string**.
3. Todo el SQL de negocio vive aquí; usa `get_connection()` de `database/`.

### 4.4 Un cambio de modelo de datos
1. Edita `backend/database/schema.sql` (fuente de verdad, idempotente con
   `IF NOT EXISTS` / `ALTER ... ADD COLUMN IF NOT EXISTS`).
2. Si necesitas datos de ejemplo, ajusta `database/seed.py`.

---

## 5. Datos y memoria

- **Base de datos:** PostgreSQL gestionada por **Supabase**. La conexión se hace
  con `psycopg2` vía `DATABASE_URL` (usar el *Session pooler*, compatible IPv4).
  `database/connection.py` ofrece una capa de compatibilidad estilo SQLite
  (placeholders `?` → `%s`).
- **Esquema:** `database/schema.sql` es la fuente de verdad. `setup_database()`
  lo aplica en cada arranque (idempotente) y carga el seed la primera vez.
- **Memoria vectorial (pgvector):** los embeddings se guardan en la **misma base
  Postgres**, en las tablas `memory_conversations` y `memory_product_index`
  (columnas `vector(768)`). Esto reemplaza a ChromaDB local.
  - **Por qué:** en App Runner el sistema de archivos del contenedor es
    **efímero** y puede haber **varias instancias**. Un store en disco local se
    perdería y no se compartiría. pgvector da persistencia y estado compartido
    con una sola fuente de datos.
  - **Embeddings:** se generan con la API de embeddings de Gemini
    (`text-embedding-004`, 768 dims), reutilizando el mismo cliente `genai`.
  - **Requisito Supabase:** habilitar la extensión una vez:
    `create extension if not exists vector;` (incluida en `schema.sql`).

---

## 6. Configuración y secretos

Toda la configuración entra por **variables de entorno** (cargadas con
`python-dotenv` en local, inyectadas por App Runner en producción).

| Variable | Obligatoria | Descripción |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Clave de Google Gemini (chat + embeddings). |
| `DATABASE_URL` | ✅ | Connection string de Supabase (Session pooler). |
| `EMAIL_SENDER` / `EMAIL_PASSWORD` | ❌ | Cuenta SMTP para reportes/alertas. |
| `EMAIL_SMTP_SERVER` / `EMAIL_SMTP_PORT` | ❌ | Servidor SMTP (Gmail por defecto). |
| `ALERT_EMAIL_TO` | ❌ | Destinatario de alertas automáticas. |
| `ALERT_CHECK_INTERVAL` | ❌ | Minutos entre revisiones de alertas. |
| `ENABLE_ALERT_MONITOR` | ❌ | `true` para arrancar el monitor de alertas en la web. |
| `PORT` | ❌ | Puerto de escucha (App Runner / contenedor). Por defecto 8000. |

> **Producción:** no se sube `.env`. Las credenciales se cargan en App Runner
> como *environment variables* o, mejor, referenciando **AWS Secrets Manager**.

---

## 7. Despliegue en AWS App Runner

### 7.1 Por qué App Runner
La app es un contenedor HTTP sin estado (el estado vive en Supabase). App Runner
aporta build/despliegue, HTTPS, escalado automático y red gestionada con mínimo
mantenimiento — el encaje natural para un FastAPI como este.

### 7.2 Empaquetado
- `Dockerfile` construye una imagen `python:3.12-slim` con el backend + frontend.
- Arranca con `uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}`.
- `.dockerignore` evita meter `.venv`, cachés, `.env` y `vector_store/` en la
  imagen.

### 7.3 Pasos (imagen en ECR → App Runner)
```bash
# 1. Construir la imagen
docker build -t inventario-retail .

# 2. Crear repositorio ECR y subir (ajusta REGION y ACCOUNT_ID)
aws ecr create-repository --repository-name inventario-retail
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker tag inventario-retail:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/inventario-retail:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/inventario-retail:latest

# 3. Crear el servicio App Runner desde esa imagen (consola o CLI):
#    - Puerto: 8000
#    - Variables de entorno: GEMINI_API_KEY, DATABASE_URL, EMAIL_*, etc.
#    - Health check path: /api/health
```

> Alternativa **sin Docker**: App Runner puede construir desde el código fuente
> usando `apprunner.yaml` (runtime Python gestionado). Útil para iterar rápido;
> el contenedor da más control y reproducibilidad.

### 7.4 Health check
App Runner debe apuntar a **`/api/health`**, que reporta el estado de la BD y de
Gemini. El arranque es tolerante: si la BD o Gemini fallan al iniciar, el
servicio sigue sirviendo el frontend y expone el error en ese endpoint.

---

## 8. Escalado y consideraciones operativas

- **Sin estado en el contenedor:** todo el estado persistente está en Supabase.
  Esto permite que App Runner escale a varias instancias sin problemas.
- **Historial de sesión del orquestador:** hoy vive **en memoria de proceso**
  (`_session_history`). Con varias instancias, una conversación podría caer en
  instancias distintas. La memoria de largo plazo (pgvector) sí es compartida; el
  historial de sesión inmediato es por proceso. *(Deuda técnica — ver §10.)*
- **Monitor de alertas (`tools/alert_monitor.py`):** corre en un hilo de fondo.
  Con varias instancias se enviarían **emails duplicados**. Por eso está detrás
  de `ENABLE_ALERT_MONITOR` (apagado por defecto). En producción, lo recomendable
  es sacarlo del servicio web y dispararlo con **EventBridge Scheduler** sobre
  una tarea dedicada. *(Ver §10.)*
- **Concurrencia del chat:** hay un `chat_lock` porque el orquestador guarda
  historial de sesión; serializa las peticiones de chat por instancia.

---

## 9. Seguridad

- Secretos solo por variables de entorno / Secrets Manager; `.env` está en
  `.gitignore`.
- Conexión a Postgres con `sslmode=require`.
- SSL de salida saneado por `fix_ssl.py` (certifi) en Windows; en Linux/contenedor
  es inocuo.
- *(Pendiente)* La API hoy es abierta. Antes de exponerla públicamente conviene
  añadir autenticación (API key / JWT) y CORS explícito.

---

## 10. Deuda técnica y roadmap

| Tema | Estado actual | Dirección propuesta |
|---|---|---|
| `db_path` (`"supabase"`) | Se pasa entre capas por compatibilidad histórica; se ignora. | Eliminarlo de las firmas cuando se toquen los `tools/`. |
| Historial de sesión | En memoria de proceso. | Persistir por sesión (tabla o Redis) si se escala horizontalmente. |
| Monitor de alertas | Hilo en el proceso web (opt-in). | Job externo con EventBridge Scheduler. |
| Autenticación | API abierta. | API key / JWT + CORS restringido. |
| Observabilidad | `print()`. | Logging estructurado + métricas (CloudWatch). |
| Tests | Solo smoke test de BD. | Tests de unidad para `tools/` y de integración para `api/`. |

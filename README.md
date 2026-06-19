# 🛒 Sistema Multiagente de Inventario Retail

Sistema de gestión de inventario retail basado en **múltiples agentes de IA**, con interfaz en lenguaje natural en español. Utiliza **Google Gemini** como LLM, **ChromaDB** para memoria semántica y **Supabase (PostgreSQL)** como base de datos.

---

## ✨ Características

- 🤖 **6 agentes especializados** coordinados por un orquestador central
- 💬 **Interfaz conversacional** en lenguaje natural (español)
- 🧠 **Memoria vectorial persistente** entre sesiones (ChromaDB)
- 📧 **Envío de reportes por email** (Gmail / SMTP)
- 📊 **Base de datos Supabase (PostgreSQL)** con 25 productos, 5 proveedores y 90 días de historial
- 🔄 **Historial de sesión** — el sistema recuerda el contexto de la conversación
- ⚡ **Manejo automático de errores** y reintentos ante fallos de API

---

## 🧠 Agentes disponibles

| Agente | Función |
|---|---|
| **Orquestador** | Coordina y enruta consultas a los agentes especializados |
| **Inventario** | Stock actual, alertas, productos sin stock, valor del inventario |
| **Ventas** | Análisis de ventas, ingresos, productos top, tendencias |
| **Demanda** | Pronósticos, días de stock restante, riesgo de desabasto |
| **Proveedores** | Evaluación comparativa, mejores precios, rendimiento |
| **Compras** | Creación de órdenes, reabastecimiento, seguimiento de pedidos |
| **Reportes** | Informes ejecutivos completos + envío por email |

---

## 🗂️ Estructura del proyecto

El proyecto está dividido en dos carpetas: **`backend/`** (la API y toda la
lógica de agentes) y **`frontend/`** (la interfaz web). Un solo servidor sirve
ambas cosas.

```
agente_automatizacion/
├── backend/                   # API + lógica (Python / FastAPI)
│   ├── app.py                 # Servidor web: API REST + sirve el frontend
│   ├── cli.py                 # Versión de terminal (la app original)
│   ├── agents/
│   │   ├── base.py            # Clase base con loop de herramientas Gemini
│   │   ├── orchestrator.py    # Orquestador central
│   │   ├── inventory.py       # Agente de inventario
│   │   ├── sales.py           # Agente de ventas
│   │   ├── demand.py          # Agente de pronóstico de demanda
│   │   ├── suppliers.py       # Agente de proveedores
│   │   ├── purchasing.py      # Agente de compras
│   │   └── reports.py         # Agente de reportes (+ email)
│   ├── tools/                 # Herramientas de datos de cada agente
│   ├── memory/                # Memoria semántica con ChromaDB
│   ├── database/              # Paquete de BD (Supabase / PostgreSQL)
│   ├── scripts/               # smoke_test_db.py
│   ├── config.py              # Configuración y variables de entorno
│   ├── fix_ssl.py             # Certificados SSL vía certifi (Windows)
│   └── requirements.txt
├── frontend/                  # Interfaz web (HTML/CSS/JS, sin build)
│   ├── index.html             # Dashboard + chat
│   └── static/
│       ├── styles.css         # Estilos (tema oscuro moderno)
│       └── app.js             # Lógica: vistas, gráficos (Chart.js) y chat
├── .env.example
└── .env                       # Secretos reales (no se sube al repo)
```

---

## 🚀 Instalación y uso

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/agente-inventario-retail.git
cd agente-inventario-retail
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate

pip install -r backend/requirements.txt
```

### 3. Configurar variables de entorno

Copia el archivo de ejemplo y edítalo:

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
# API de Google Gemini (gratis en aistudio.google.com)
GEMINI_API_KEY=AIzaSy-TU_CLAVE_AQUI

# Base de datos Supabase (PostgreSQL) — connection string URI
DATABASE_URL=postgresql://postgres.xxxx:TU_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres

# Email para envío de reportes (opcional)
EMAIL_SENDER=tu_correo@gmail.com
EMAIL_PASSWORD=tu_contraseña_de_aplicacion
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

> **Gemini API Key:** Obtén una gratis en [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
>
> **Supabase:** En tu proyecto, *Project Settings → Database → Connection string (URI)*. Usa el **Session pooler** (compatible con IPv4) y reemplaza `[YOUR-PASSWORD]`.
>
> **Email (Gmail):** Necesitas una *Contraseña de Aplicación*, no tu contraseña normal. Actívala en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### 4. Ejecutar

**Opción A — Aplicación web (recomendada)**

```bash
python backend/app.py
```

Luego abre **http://127.0.0.1:8000** en tu navegador. Verás el dashboard con
KPIs y gráficos, y el asistente conversacional con los 6 agentes.

> También puedes usar el modo recarga-en-caliente para desarrollo:
> `cd backend && uvicorn app:app --reload`

**Opción B — Modo terminal (CLI clásico)**

```bash
python backend/cli.py
```

---

## 🌐 Interfaz web

La web se sirve completa desde un único servidor (FastAPI) e incluye:

- **📊 Dashboard** — KPIs (ingresos, ganancia, valor de inventario, alertas) y
  gráficos en vivo: ingresos diarios, ventas por categoría, valor de inventario
  y productos más vendidos.
- **💬 Asistente IA** — chat en lenguaje natural conectado al orquestador y sus
  6 agentes, con sugerencias rápidas.
- **🔔 Alertas** — productos sin stock, stock bajo y alertas activas.
- **📦 Productos** y **🚚 Proveedores** — tablas con búsqueda.

### Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/chat` | Envía un mensaje al orquestador `{ "message": "..." }` |
| `GET` | `/api/dashboard` | KPIs y datos de los gráficos |
| `GET` | `/api/products` | Catálogo (opcional `?category=`) |
| `GET` | `/api/suppliers` | Lista de proveedores |
| `GET` | `/api/history` | Historial de conversaciones (memoria) |
| `GET` | `/api/search?q=` | Búsqueda semántica de productos |
| `GET` | `/api/health` | Estado del sistema (BD, Gemini) |

---

## 💬 Ejemplos de consultas

```
¿Qué productos están sin stock?
Muéstrame las ventas de los últimos 30 días
¿Qué productos están en riesgo de desabasto?
¿Cuál es el mejor proveedor para productos de electrónica?
Genera un reporte ejecutivo completo
Genera el reporte y envíalo a gerencia@empresa.com
Crea una orden de compra para reponer los audífonos
¿Cuáles son los productos más vendidos este mes?
```

---

## ⌨️ Comandos especiales

| Comando | Descripción |
|---|---|
| `/historial` | Ver las últimas 10 conversaciones guardadas |
| `/buscar <texto>` | Búsqueda semántica de productos |
| `/memoria` | Ver estadísticas de la memoria vectorial |
| `/limpiar` | Limpiar el historial de conversaciones |
| `salir` | Terminar la sesión |

---

## ⚙️ Configuración avanzada

En `config.py` puedes ajustar:

```python
ORCHESTRATOR_MODEL = "gemini-3.1-flash-lite"  # Modelo del orquestador
AGENT_MODEL        = "gemini-3.1-flash-lite"  # Modelo de los sub-agentes
MAX_ITERATIONS     = 10                        # Máximo de iteraciones por consulta
MAX_RETRIES        = 2                         # Reintentos ante errores de API
```

---

## 🗃️ Base de datos

La base de datos vive en **Supabase (PostgreSQL)**. Al iniciar, el sistema crea
las tablas (si no existen) y carga datos de ejemplo la primera vez — todo de
forma automática e idempotente, **no necesitas tocar Supabase manualmente**.

- **25 productos** en 5 categorías: Electrónica, Ropa, Alimentos, Hogar, Deportes
- **5 proveedores** con métricas de confiabilidad y lead time
- **90 días** de historial de ventas generado aleatoriamente
- **Alertas** de stock crítico y sin stock precargadas

El esquema es la fuente de verdad en [`backend/database/schema.sql`](backend/database/schema.sql);
el mismo archivo se puede pegar en el *SQL Editor* de Supabase si prefieres crear
las tablas a mano. Para verificar la conexión:

```bash
python backend/scripts/smoke_test_db.py
```

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|---|---|
| [Google Gemini](https://ai.google.dev/) | LLM principal (function calling) |
| [ChromaDB](https://www.trychroma.com/) | Memoria vectorial semántica |
| [Supabase](https://supabase.com/) (PostgreSQL) | Base de datos de inventario |
| psycopg2 | Driver de PostgreSQL |
| smtplib | Envío de reportes por email |
| python-dotenv | Gestión de variables de entorno |

---

## 📄 Licencia

MIT License — libre para usar, modificar y distribuir.

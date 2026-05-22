# 🛒 Sistema Multiagente de Inventario Retail

Sistema de gestión de inventario retail basado en **múltiples agentes de IA**, con interfaz en lenguaje natural en español. Utiliza **Google Gemini** como LLM, **ChromaDB** para memoria semántica y **SQLite** como base de datos.

---

## ✨ Características

- 🤖 **6 agentes especializados** coordinados por un orquestador central
- 💬 **Interfaz conversacional** en lenguaje natural (español)
- 🧠 **Memoria vectorial persistente** entre sesiones (ChromaDB)
- 📧 **Envío de reportes por email** (Gmail / SMTP)
- 📊 **Base de datos SQLite** con 25 productos, 5 proveedores y 90 días de historial
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

```
agente_automatizacion/
├── agents/
│   ├── base.py            # Clase base con loop de herramientas Gemini
│   ├── orchestrator.py    # Orquestador central
│   ├── inventory.py       # Agente de inventario
│   ├── sales.py           # Agente de ventas
│   ├── demand.py          # Agente de pronóstico de demanda
│   ├── suppliers.py       # Agente de proveedores
│   ├── purchasing.py      # Agente de compras
│   └── reports.py         # Agente de reportes (+ email)
├── tools/
│   ├── inventory_tools.py
│   ├── sales_tools.py
│   ├── demand_tools.py
│   ├── supplier_tools.py
│   ├── order_tools.py
│   └── email_tools.py     # Envío de reportes por correo
├── memory/
│   └── vector_memory.py   # Memoria semántica con ChromaDB
├── config.py              # Configuración y variables de entorno
├── database.py            # Setup y seed de SQLite
├── main.py                # Punto de entrada
├── fix_ssl.py             # Compatibilidad SSL en Windows
├── requirements.txt
└── .env.example
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

pip install -r requirements.txt
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

# Email para envío de reportes (opcional)
EMAIL_SENDER=tu_correo@gmail.com
EMAIL_PASSWORD=tu_contraseña_de_aplicacion
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

> **Gemini API Key:** Obtén una gratis en [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
>
> **Email (Gmail):** Necesitas una *Contraseña de Aplicación*, no tu contraseña normal. Actívala en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### 4. Ejecutar

```bash
python main.py
```

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

La base de datos SQLite se genera automáticamente al iniciar. Incluye datos de ejemplo:

- **25 productos** en 5 categorías: Electrónica, Ropa, Alimentos, Hogar, Deportes
- **5 proveedores** con métricas de confiabilidad y lead time
- **90 días** de historial de ventas generado aleatoriamente
- **Alertas** de stock crítico y sin stock precargadas

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|---|---|
| [Google Gemini](https://ai.google.dev/) | LLM principal (function calling) |
| [ChromaDB](https://www.trychroma.com/) | Memoria vectorial semántica |
| SQLite | Base de datos de inventario |
| smtplib | Envío de reportes por email |
| python-dotenv | Gestión de variables de entorno |

---

## 📄 Licencia

MIT License — libre para usar, modificar y distribuir.

-- Esquema de la base de datos (PostgreSQL / Supabase)
-- Fuente de verdad del modelo de datos.
-- Se ejecuta automáticamente desde Python (database/setup.py),
-- pero también puedes pegarlo tal cual en el SQL Editor de Supabase.

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL,
    cost_price DOUBLE PRECISION NOT NULL,
    unit_of_measure TEXT DEFAULT 'unidad',
    reorder_point INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 50,
    created_at TEXT DEFAULT to_char(now(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    warehouse_location TEXT,
    last_updated TEXT DEFAULT to_char(now(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    country TEXT DEFAULT 'Chile',
    lead_time_days INTEGER DEFAULT 7,
    reliability_score DOUBLE PRECISION DEFAULT 0.9,
    created_at TEXT DEFAULT to_char(now(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS product_suppliers (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    unit_cost DOUBLE PRECISION NOT NULL,
    min_order_quantity INTEGER DEFAULT 1,
    is_preferred INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL,
    total_amount DOUBLE PRECISION NOT NULL,
    sale_date TEXT NOT NULL,
    channel TEXT DEFAULT 'tienda'
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_cost DOUBLE PRECISION NOT NULL,
    total_cost DOUBLE PRECISION NOT NULL,
    status TEXT DEFAULT 'pendiente',
    order_date TEXT DEFAULT to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),
    expected_delivery TEXT,
    received_date TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS inventory_alerts (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_resolved INTEGER DEFAULT 0,
    notified BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT to_char(now(), 'YYYY-MM-DD HH24:MI:SS')
);

-- Migración: agrega la columna si la tabla ya existía sin ella
ALTER TABLE inventory_alerts ADD COLUMN IF NOT EXISTS notified BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- Memoria vectorial (pgvector)
-- Reemplaza a ChromaDB local: los embeddings viven en esta misma base, de modo
-- que la memoria es persistente y compartida entre instancias (necesario para
-- desplegar en AWS App Runner, donde el contenedor es efímero).
-- Embeddings de Gemini text-embedding-004 -> 768 dimensiones.
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_conversations (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    document TEXT NOT NULL,
    agents_used TEXT DEFAULT '[]',
    response_length INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    embedding vector(768)
);

CREATE TABLE IF NOT EXISTS memory_product_index (
    id TEXT PRIMARY KEY,
    document TEXT NOT NULL,
    sku TEXT,
    category TEXT,
    unit_price TEXT,
    quantity TEXT,
    embedding vector(768)
);

"""Datos de ejemplo (seed).

Se cargan una sola vez: si la tabla products ya tiene filas, no hace nada.
Vive en Python (no en SQL) porque genera 90 días de ventas y costos de
proveedor de forma aleatoria.
"""
import random
from datetime import datetime, timedelta


def seed_data(conn):
    existing = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if existing > 0:
        return

    products = [
        ("ELEC-001", "Televisor Smart TV 55\"", "Electrónica", 599990, 380000, "unidad", 3, 10),
        ("ELEC-002", "Laptop 15\" Core i5", "Electrónica", 499990, 320000, "unidad", 5, 10),
        ("ELEC-003", "Smartphone Android 128GB", "Electrónica", 299990, 190000, "unidad", 8, 20),
        ("ELEC-004", "Audífonos Bluetooth", "Electrónica", 49990, 28000, "unidad", 15, 50),
        ("ELEC-005", "Tablet 10\" WiFi", "Electrónica", 179990, 110000, "unidad", 5, 15),
        ("ROPA-001", "Polera Manga Corta Algodón", "Ropa", 9990, 4500, "unidad", 20, 100),
        ("ROPA-002", "Jeans Slim Fit", "Ropa", 29990, 15000, "unidad", 15, 60),
        ("ROPA-003", "Chaqueta Polar", "Ropa", 39990, 20000, "unidad", 10, 40),
        ("ROPA-004", "Vestido Casual", "Ropa", 24990, 12000, "unidad", 10, 50),
        ("ROPA-005", "Zapatillas Deportivas", "Ropa", 49990, 28000, "par", 12, 40),
        ("ALIM-001", "Arroz Grano Largo 5kg", "Alimentos", 4990, 2800, "bolsa", 30, 150),
        ("ALIM-002", "Aceite Vegetal 1L", "Alimentos", 2490, 1400, "botella", 25, 120),
        ("ALIM-003", "Leche Entera 1L", "Alimentos", 990, 550, "litro", 50, 200),
        ("ALIM-004", "Pan Integral 500g", "Alimentos", 1890, 950, "paquete", 40, 200),
        ("ALIM-005", "Pasta Espagueti 500g", "Alimentos", 1490, 750, "paquete", 35, 180),
        ("HOGAR-001", "Set Sábanas 2 Plazas", "Hogar", 19990, 10000, "set", 8, 30),
        ("HOGAR-002", "Olla Antiadherente 24cm", "Hogar", 14990, 7500, "unidad", 10, 40),
        ("HOGAR-003", "Aspiradora Ciclónica", "Hogar", 79990, 48000, "unidad", 4, 12),
        ("HOGAR-004", "Juego Cubiertos 24 pzas", "Hogar", 12990, 6500, "set", 8, 30),
        ("HOGAR-005", "Lampara LED Escritorio", "Hogar", 9990, 5000, "unidad", 12, 50),
        ("DEPO-001", "Bicicleta Mountain Bike", "Deportes", 249990, 155000, "unidad", 3, 8),
        ("DEPO-002", "Pelota Fútbol N°5", "Deportes", 14990, 7500, "unidad", 10, 40),
        ("DEPO-003", "Mancuernas Par 10kg", "Deportes", 24990, 13000, "par", 8, 25),
        ("DEPO-004", "Cuerda de Saltar Pro", "Deportes", 4990, 2200, "unidad", 15, 60),
        ("DEPO-005", "Colchoneta Yoga 6mm", "Deportes", 12990, 6500, "unidad", 10, 40),
    ]

    conn.executemany(
        "INSERT INTO products (sku, name, category, unit_price, cost_price, unit_of_measure, reorder_point, reorder_quantity) VALUES (?,?,?,?,?,?,?,?)",
        products
    )

    stock_levels = [
        (1, 12, "A1"), (2, 8, "A2"), (3, 25, "A3"), (4, 2, "A4"), (5, 0, "A5"),
        (6, 85, "B1"), (7, 42, "B2"), (8, 18, "B3"), (9, 35, "B4"), (10, 7, "B5"),
        (11, 120, "C1"), (12, 90, "C2"), (13, 5, "C3"), (14, 180, "C4"), (15, 95, "C5"),
        (16, 22, "D1"), (17, 0, "D2"), (18, 6, "D3"), (19, 28, "D4"), (20, 45, "D5"),
        (21, 4, "E1"), (22, 30, "E2"), (23, 12, "E3"), (24, 55, "E4"), (25, 18, "E5"),
    ]
    conn.executemany(
        "INSERT INTO inventory (product_id, quantity, warehouse_location) VALUES (?,?,?)",
        stock_levels
    )

    suppliers = [
        ("TechPro S.A.", "Carlos Mendoza", "cmendoza@techpro.cl", "+56 2 2345 6789", "Chile", 5, 0.95),
        ("ModaStyle Distribuidores", "Ana Rojas", "arojas@modastyle.cl", "+56 2 3456 7890", "Chile", 7, 0.88),
        ("AlimentosFresh Ltda.", "Pedro González", "pgonzalez@alimentosfresh.cl", "+56 2 4567 8901", "Chile", 3, 0.97),
        ("HogarPlus SpA", "María Torres", "mtorres@hogarplus.cl", "+56 2 5678 9012", "Chile", 6, 0.92),
        ("SportMax Distribuciones", "Jorge Vargas", "jvargas@sportmax.cl", "+56 2 6789 0123", "Chile", 8, 0.85),
    ]
    conn.executemany(
        "INSERT INTO suppliers (name, contact_name, email, phone, country, lead_time_days, reliability_score) VALUES (?,?,?,?,?,?,?)",
        suppliers
    )

    product_suppliers = []
    for prod_id in range(1, 6):
        product_suppliers.append((prod_id, 1, round(random.uniform(0.7, 0.85) * [380000, 320000, 190000, 28000, 110000][prod_id - 1]), 1, 1))
    for prod_id in range(6, 11):
        product_suppliers.append((prod_id, 2, round(random.uniform(0.75, 0.9) * [4500, 15000, 20000, 12000, 28000][prod_id - 6]), 5, 1))
    for prod_id in range(11, 16):
        product_suppliers.append((prod_id, 3, round(random.uniform(0.75, 0.9) * [2800, 1400, 550, 950, 750][prod_id - 11]), 10, 1))
    for prod_id in range(16, 21):
        product_suppliers.append((prod_id, 4, round(random.uniform(0.75, 0.9) * [10000, 7500, 48000, 6500, 5000][prod_id - 16]), 2, 1))
    for prod_id in range(21, 26):
        product_suppliers.append((prod_id, 5, round(random.uniform(0.75, 0.9) * [155000, 7500, 13000, 2200, 6500][prod_id - 21]), 1, 1))

    conn.executemany(
        "INSERT INTO product_suppliers (product_id, supplier_id, unit_cost, min_order_quantity, is_preferred) VALUES (?,?,?,?,?)",
        product_suppliers
    )

    random.seed(42)
    sales_data = []
    today = datetime.now()
    channels = ["tienda", "online", "telefono"]
    daily_demand = {
        1: 1, 2: 1, 3: 3, 4: 5, 5: 1,
        6: 12, 7: 6, 8: 3, 9: 5, 10: 4,
        11: 15, 12: 12, 13: 20, 14: 18, 15: 14,
        16: 2, 17: 4, 18: 1, 19: 3, 20: 5,
        21: 1, 22: 4, 23: 2, 24: 7, 25: 3,
    }
    prices = {i + 1: p[3] for i, p in enumerate(products)}

    for day_offset in range(90, 0, -1):
        sale_date = (today - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for prod_id, avg_demand in daily_demand.items():
            qty = max(0, int(random.gauss(avg_demand, avg_demand * 0.3)))
            if qty > 0:
                unit_price = prices[prod_id]
                sales_data.append((prod_id, qty, unit_price, qty * unit_price, sale_date, random.choice(channels)))

    conn.executemany(
        "INSERT INTO sales (product_id, quantity, unit_price, total_amount, sale_date, channel) VALUES (?,?,?,?,?,?)",
        sales_data
    )

    future_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
    purchase_orders = [
        (1, 4, 27000, 10, 270000, "en_transito", today.strftime("%Y-%m-%d"), future_date, None, "Reposición urgente"),
        (3, 13, 580, 100, 58000, "pendiente", today.strftime("%Y-%m-%d"), (today + timedelta(days=3)).strftime("%Y-%m-%d"), None, "Stock crítico leche"),
        (4, 17, 7500, 20, 150000, "pendiente", today.strftime("%Y-%m-%d"), (today + timedelta(days=7)).strftime("%Y-%m-%d"), None, "Reposición ollas"),
        (2, 10, 13000, 40, 520000, "pendiente", today.strftime("%Y-%m-%d"), (today + timedelta(days=8)).strftime("%Y-%m-%d"), None, "Reposición ropa"),
        (5, 21, 110000, 5, 550000, "aprobado", today.strftime("%Y-%m-%d"), (today + timedelta(days=6)).strftime("%Y-%m-%d"), None, "Tablets nuevas"),
    ]
    conn.executemany(
        "INSERT INTO purchase_orders (supplier_id, product_id, quantity, unit_cost, total_cost, status, order_date, expected_delivery, received_date, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        purchase_orders
    )

    alerts = [
        (5, "sin_stock", "Tablet 10\" WiFi - SIN STOCK. Requiere reposición inmediata."),
        (17, "sin_stock", "Olla Antiadherente 24cm - SIN STOCK. Requiere reposición inmediata."),
        (4, "stock_critico", "Audífonos Bluetooth - Stock crítico: 2 unidades (mínimo: 15)."),
        (13, "stock_bajo", "Leche Entera 1L - Stock bajo: 5 unidades (mínimo: 50)."),
        (18, "stock_bajo", "Aspiradora Ciclónica - Stock bajo: 6 unidades (mínimo: 4)."),
        (21, "stock_bajo", "Bicicleta Mountain Bike - Stock bajo: 4 unidades (mínimo: 3)."),
        (10, "stock_bajo", "Zapatillas Deportivas - Stock bajo: 7 unidades (mínimo: 12)."),
    ]
    conn.executemany(
        "INSERT INTO inventory_alerts (product_id, alert_type, message) VALUES (?,?,?)",
        alerts
    )

    conn.commit()

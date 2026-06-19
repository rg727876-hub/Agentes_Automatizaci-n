// ============================================================================
// RetailMind — frontend del sistema multiagente de inventario.
// Vanilla JS: navegación entre vistas, dashboard con Chart.js y chat con la API.
// ============================================================================

const CLP = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
const NUM = new Intl.NumberFormat("es-CL");

const VIEW_META = {
  dashboard: { title: "Dashboard", subtitle: "Visión general del negocio en tiempo real" },
  chat: { title: "Asistente IA", subtitle: "Conversa con los 6 agentes en lenguaje natural" },
  alerts: { title: "Alertas", subtitle: "Stock crítico y notificaciones del inventario" },
  products: { title: "Productos", subtitle: "Catálogo completo con stock actual" },
  suppliers: { title: "Proveedores", subtitle: "Red de abastecimiento y confiabilidad" },
};

const charts = {};
let productsCache = [];

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------
async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.toggle("err", isError);
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.hidden = true), 3500);
}

function el(tag, cls, html) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

// ---------------------------------------------------------------------------
// Navegación
// ---------------------------------------------------------------------------
function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== `view-${view}`));
  const meta = VIEW_META[view];
  document.getElementById("viewTitle").textContent = meta.title;
  document.getElementById("viewSubtitle").textContent = meta.subtitle;

  if (view === "products" && productsCache.length === 0) loadProducts();
  if (view === "suppliers") loadSuppliers();
}

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

// ---------------------------------------------------------------------------
// Health / estado del sistema
// ---------------------------------------------------------------------------
async function loadHealth() {
  const box = document.getElementById("systemStatus");
  try {
    const h = await api("/api/health");
    if (h.status === "ok") {
      box.className = "status ok";
      box.innerHTML = '<span class="status-dot"></span> Sistema en línea';
    } else {
      box.className = "status err";
      const msg = h.error ? "Base de datos sin conexión" : "Inicializando…";
      box.innerHTML = `<span class="status-dot"></span> ${msg}`;
      box.title = h.error || "";
    }
  } catch (_) {
    box.className = "status err";
    box.innerHTML = '<span class="status-dot"></span> Sin conexión';
  }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
const KPI_DEFS = [
  { key: "total_revenue", label: "Ingresos (30 días)", ico: "💰", fmt: CLP },
  { key: "gross_profit", label: "Ganancia bruta (30d)", ico: "📈", fmt: CLP },
  { key: "inventory_retail_value", label: "Valor de inventario", ico: "🏷️", fmt: CLP },
  { key: "inventory_units", label: "Unidades en stock", ico: "📦", fmt: NUM },
  { key: "total_units_sold", label: "Unidades vendidas (30d)", ico: "🛍️", fmt: NUM },
  { key: "active_alerts", label: "Alertas activas", ico: "🔔", fmt: NUM, warn: true },
  { key: "out_of_stock", label: "Productos sin stock", ico: "🚫", fmt: NUM, warn: true },
  { key: "pending_orders", label: "Órdenes pendientes", ico: "🧾", fmt: NUM },
];

function renderKpis(kpis) {
  const grid = document.getElementById("kpiGrid");
  grid.innerHTML = "";
  KPI_DEFS.forEach((def) => {
    const raw = kpis[def.key] ?? 0;
    const value = def.fmt === CLP ? CLP.format(raw) : NUM.format(raw);
    const warn = def.warn && raw > 0;
    grid.appendChild(
      el("div", `kpi${warn ? " warn" : ""}`,
        `<div class="kpi-ico">${def.ico}</div>
         <div class="kpi-label">${def.label}</div>
         <div class="kpi-value">${value}</div>`)
    );
  });
}

function gradient(ctx, area, c1, c2) {
  const g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  g.addColorStop(0, c1);
  g.addColorStop(1, c2);
  return g;
}

const baseOpts = (extra = {}) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { backgroundColor: "#1b2547", borderColor: "#243056", borderWidth: 1, padding: 10 } },
  scales: {
    x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#8b95b8", font: { size: 11 } } },
    y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#8b95b8", font: { size: 11 } } },
  },
  ...extra,
});

function makeChart(id, config) {
  const canvas = document.getElementById(id);
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(canvas, config);
}

function renderCharts(c) {
  // Ingresos diarios (línea con gradiente)
  makeChart("chartSales", {
    type: "line",
    data: {
      labels: c.sales_daily.labels,
      datasets: [{
        data: c.sales_daily.revenue,
        borderColor: "#6c8cff",
        borderWidth: 2.5,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        backgroundColor: (ctx) => {
          const { chart } = ctx;
          if (!chart.chartArea) return "rgba(108,140,255,0.1)";
          return gradient(chart.ctx, chart.chartArea, "rgba(108,140,255,0.35)", "rgba(108,140,255,0)");
        },
      }],
    },
    options: baseOpts(),
  });

  // Ventas por categoría (barras)
  makeChart("chartCategory", {
    type: "bar",
    data: {
      labels: c.sales_by_category.labels,
      datasets: [{ data: c.sales_by_category.revenue, backgroundColor: "#22d3ee", borderRadius: 6, maxBarThickness: 42 }],
    },
    options: baseOpts(),
  });

  // Valor de inventario por categoría (doughnut)
  makeChart("chartInventory", {
    type: "doughnut",
    data: {
      labels: c.inventory_by_category.labels,
      datasets: [{
        data: c.inventory_by_category.retail_value,
        backgroundColor: ["#6c8cff", "#8b5cf6", "#22d3ee", "#34d399", "#fb923c", "#f87171"],
        borderColor: "#151d38",
        borderWidth: 2,
      }],
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: "62%",
      plugins: { legend: { position: "bottom", labels: { color: "#8b95b8", font: { size: 11 }, padding: 12, boxWidth: 12 } } } },
  });

  // Top productos (barras horizontales)
  makeChart("chartTop", {
    type: "bar",
    data: {
      labels: c.top_products.labels,
      datasets: [{ data: c.top_products.units, backgroundColor: (ctx) => {
        const { chart } = ctx;
        if (!chart.chartArea) return "#8b5cf6";
        const g = chart.ctx.createLinearGradient(chart.chartArea.left, 0, chart.chartArea.right, 0);
        g.addColorStop(0, "#6c8cff"); g.addColorStop(1, "#22d3ee");
        return g;
      }, borderRadius: 6, maxBarThickness: 22 }],
    },
    options: baseOpts({ indexAxis: "y" }),
  });
}

function renderAlerts(d) {
  const oos = document.getElementById("outOfStockList");
  const low = document.getElementById("lowStockList");
  const al = document.getElementById("alertsList");

  oos.innerHTML = "";
  if (!d.out_of_stock.length) oos.appendChild(el("div", "empty", "Sin productos agotados. 🎉"));
  d.out_of_stock.forEach((p) => oos.appendChild(
    el("div", "list-item", `<div><div class="li-main">${p.name}</div><div class="li-sub">${p.sku} · ${p.category}</div></div><span class="tag tag-red">Sin stock</span>`)
  ));

  low.innerHTML = "";
  if (!d.low_stock.length) low.appendChild(el("div", "empty", "Ningún producto en stock bajo."));
  d.low_stock.forEach((p) => low.appendChild(
    el("div", "list-item", `<div><div class="li-main">${p.name}</div><div class="li-sub">${p.sku} · ${p.category}</div></div><span class="tag tag-orange">${p.quantity} uds · reorden ${p.reorder_point}</span>`)
  ));

  al.innerHTML = "";
  if (!d.alerts.length) al.appendChild(el("div", "empty", "Sin alertas activas."));
  d.alerts.forEach((a) => al.appendChild(
    el("div", "list-item", `<div><div class="li-main">${a.name}</div><div class="li-sub">${a.message || ""}</div></div><span class="tag tag-red">${a.alert_type}</span>`)
  ));

  // Badge en el sidebar
  const total = d.out_of_stock.length + d.alerts.length;
  const badge = document.getElementById("navAlertsBadge");
  badge.hidden = total === 0;
  badge.textContent = total;
}

async function loadDashboard() {
  try {
    const d = await api("/api/dashboard");
    renderKpis(d.kpis);
    renderCharts(d.charts);
    renderAlerts(d);
  } catch (e) {
    toast("No se pudo cargar el dashboard: " + e.message, true);
  }
}

// ---------------------------------------------------------------------------
// Productos / proveedores
// ---------------------------------------------------------------------------
function stockClass(p) {
  if (p.quantity === 0) return "stock-out";
  if (p.reorder_point != null && p.quantity <= p.reorder_point) return "stock-low";
  return "stock-ok";
}

function renderProducts(list) {
  const tb = document.querySelector("#productsTable tbody");
  tb.innerHTML = "";
  if (!list.length) { tb.appendChild(el("tr", "", `<td colspan="5" class="empty">Sin resultados.</td>`)); return; }
  list.forEach((p) => {
    const tr = el("tr", "", `
      <td><span class="pill">${p.sku}</span></td>
      <td>${p.name}</td>
      <td>${p.category}</td>
      <td>${CLP.format(p.unit_price)}</td>
      <td class="${stockClass(p)}">${NUM.format(p.quantity)}</td>`);
    tb.appendChild(tr);
  });
}

async function loadProducts() {
  try {
    const { products } = await api("/api/products");
    productsCache = products;
    renderProducts(products);
  } catch (e) {
    toast("Error cargando productos: " + e.message, true);
  }
}

document.getElementById("productSearch").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  renderProducts(productsCache.filter((p) =>
    p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)));
});

async function loadSuppliers() {
  try {
    const { suppliers } = await api("/api/suppliers");
    const tb = document.querySelector("#suppliersTable tbody");
    tb.innerHTML = "";
    if (!suppliers.length) { tb.appendChild(el("tr", "", `<td colspan="6" class="empty">Sin proveedores.</td>`)); return; }
    suppliers.forEach((s) => {
      const score = Math.round((s.reliability_score || 0) * 100);
      tb.appendChild(el("tr", "", `
        <td>${s.name}</td>
        <td>${s.contact_name || "—"}</td>
        <td>${s.country || "—"}</td>
        <td>${s.lead_time_days} días</td>
        <td><span class="pill">${score}%</span></td>
        <td>${s.products_supplied ?? 0}</td>`));
    });
  } catch (e) {
    toast("Error cargando proveedores: " + e.message, true);
  }
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
const chatMessages = document.getElementById("chatMessages");

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// Formato ligero: **negrita** y saltos de línea ya respetados por white-space.
function formatText(s) {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function addMessage(text, who) {
  const wrap = el("div", `msg msg-${who}`);
  wrap.appendChild(el("div", "msg-avatar", who === "user" ? "🧑" : "🤖"));
  wrap.appendChild(el("div", "msg-bubble", formatText(text)));
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

function addTyping() {
  const wrap = el("div", "msg msg-bot");
  wrap.appendChild(el("div", "msg-avatar", "🤖"));
  wrap.appendChild(el("div", "msg-bubble", '<span class="typing"><span></span><span></span><span></span></span>'));
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

async function sendMessage(text) {
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSend");
  addMessage(text, "user");
  input.value = "";
  input.disabled = sendBtn.disabled = true;
  const typing = addTyping();

  try {
    const { response } = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    typing.remove();
    addMessage(response, "bot");
    loadDashboard(); // los datos pueden haber cambiado (p.ej. una orden creada)
  } catch (e) {
    typing.remove();
    addMessage("⚠️ " + e.message, "bot");
  } finally {
    input.disabled = sendBtn.disabled = false;
    input.focus();
  }
}

document.getElementById("chatForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = document.getElementById("chatInput").value.trim();
  if (text) sendMessage(text);
});

document.getElementById("suggestions").addEventListener("click", (e) => {
  if (e.target.classList.contains("chip")) {
    switchView("chat");
    sendMessage(e.target.textContent.trim());
  }
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.getElementById("refreshBtn").addEventListener("click", () => {
  loadDashboard();
  loadHealth();
  toast("Datos actualizados");
});

loadHealth();
loadDashboard();
setInterval(loadHealth, 20000);

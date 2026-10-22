// ============================================================================
// GRANKHA · POST /api/create-checkout
//
// Recibe el carrito, recalcula TODO en servidor (precios, envío, IVA y la
// reserva para investigación), crea una sesión de Stripe Checkout y guarda el
// pedido en Supabase. Devuelve { url } para mandar al cliente a la pasarela.
//
// Variables de entorno (Vercel → Settings → Environment Variables):
//   STRIPE_SECRET_KEY            rk_live_... o sk_live_...
//   SUPABASE_URL                 https://xxxx.supabase.co
//   SUPABASE_SERVICE_ROLE_KEY    service_role (solo servidor)
//   SITE_URL                     https://grankha.roadshop.online  (para volver tras pagar)
//   ALLOWED_ORIGIN               opcional, por defecto cualquiera
// ============================================================================
const Stripe = require("stripe");
const { createClient } = require("@supabase/supabase-js");
const PRICES = require("./_lib/prices.json");
const { limitado } = require("./_lib/ratelimit");

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, { apiVersion: "2024-06-20" });
const supa = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

const SITE = process.env.SITE_URL || "https://grankha.roadshop.online";
const DONATION_RATE = 0.05;        // interno: nunca se muestra en la web
const VAT = 0.21;
const COSTS = PRICES.costs || {};

// zonas y tramos de envío (los mismos que enseña la web, aquí mandan estos)
const ZONES = {
  pen: { name: "España peninsular", tiers: [[0, 5.95], [20, 3.95], [39, 0]] },
  bal: { name: "Islas Baleares", tiers: [[0, 7.95], [49, 0]] },
  can: { name: "Canarias, Ceuta y Melilla", tiers: [[0, 14.95], [79, 0]] },
  prt: { name: "Portugal peninsular", tiers: [[0, 6.95], [49, 0]] },
  ue: { name: "Resto de la Unión Europea", tiers: [[0, 12.36], [79, 0]] },
};

const round = (n) => Math.round(n * 100) / 100;

const cors = (req) => ({
  "Access-Control-Allow-Origin": process.env.ALLOWED_ORIGIN || req.headers.origin || "*",
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
});

function shippingFor(zone, subtotalConIva) {
  const z = ZONES[zone] || ZONES.pen;
  let price = z.tiers[0][1];
  for (const [min, p] of z.tiers) if (subtotalConIva >= min) price = p;
  return { price, name: z.name };
}

function send(res, status, headers, body) {
  res.statusCode = status;
  for (const [k, v] of Object.entries(headers)) res.setHeader(k, v);
  res.end(body === undefined ? "" : JSON.stringify(body));
}

module.exports = async (req, res) => {
  const headers = cors(req);
  if (req.method === "OPTIONS") return send(res, 204, headers);
  if (req.method !== "POST") return send(res, 405, headers, { error: "Método no permitido" });

  // Crear una sesión de Stripe es gratis pero deja basura en el panel y permite
  // sondear el catálogo. 15 intentos por IP cada 10 min cubre de sobra una
  // compra real (incluidos los "volver y reintentar") y corta el abuso.
  if (limitado(req, "checkout", 15)) {
    return send(res, 429, headers, { error: "Demasiados intentos seguidos. Espera unos minutos." });
  }

  let order = req.body;
  if (typeof order === "string") {
    try { order = JSON.parse(order); } catch { return send(res, 400, headers, { error: "JSON inválido" }); }
  }
  if (!order || !Array.isArray(order.lines) || !order.lines.length) {
    return send(res, 400, headers, { error: "El carrito está vacío" });
  }
  const cust = order.customer || {};
  const email = String(cust.email || "").trim();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return send(res, 400, headers, { error: "Falta un email válido" });
  }
  if (!String(cust.name || "").trim() || !String(cust.address || "").trim() || !String(cust.city || "").trim()) {
    return send(res, 400, headers, { error: "Faltan datos de envío" });
  }

  // ---------------------------------------------------- precios oficiales ----
  let subtotal = 0, cogs = 0;
  const items = [];
  for (const l of order.lines) {
    const sku = String(l.sku || "");
    const official = PRICES[sku];
    if (!official) return send(res, 400, headers, { error: `Producto no disponible: ${sku}` });
    const qty = Math.max(1, Math.min(20, parseInt(l.qty, 10) || 1));
    subtotal = round(subtotal + official.price * qty);
    cogs = round(cogs + (COSTS[sku] || 0) * qty);
    items.push({
      sku, qty,
      slug: String(l.slug || ""),
      name: official.name,
      unit_price: official.price,
      line_total: round(official.price * qty),
      weight_g: parseInt(l.weight_g, 10) || 0,
    });
  }

  // --------------------------------------------------------- envío e IVA ----
  const zone = ZONES[order.zone] ? order.zone : "pen";
  const ship = shippingFor(zone, subtotal);
  const sinIva = zone === "can";                        // IGIC/IPSI en destino
  const shippingCharged = ship.price;
  const base = sinIva ? round(subtotal / (1 + VAT)) : subtotal;
  const vatIncluded = sinIva ? 0 : round(subtotal - subtotal / (1 + VAT));
  const total = round(base + shippingCharged);
  const grossBenefit = round(subtotal / (1 + VAT) - cogs);
  const donation = grossBenefit > 0 ? round(grossBenefit * DONATION_RATE) : 0;
  const reference = String(order.reference || "").match(/^GRK-[A-Z0-9-]{6,24}$/)
    ? order.reference
    : `GRK-${new Date().toISOString().slice(2, 10).replace(/-/g, "")}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;

  // ------------------------------------------------------ Stripe Checkout ---
  const line_items = items.map((l) => ({
    quantity: l.qty,
    price_data: {
      currency: "eur",
      unit_amount: Math.round(l.unit_price * 100),
      product_data: { name: l.name, metadata: { sku: l.sku } },
    },
  }));
  if (shippingCharged > 0) {
    line_items.push({
      quantity: 1,
      price_data: {
        currency: "eur",
        unit_amount: Math.round(shippingCharged * 100),
        product_data: { name: `Envío · ${ship.name}` },
      },
    });
  }

  let session;
  try {
    session = await stripe.checkout.sessions.create({
      mode: "payment",
      locale: "es",
      // siempre en euros: la tienda vende en EUR y el cliente paga EUR
      adaptive_pricing: { enabled: false },
      line_items,
      customer_email: email,
      client_reference_id: reference,
      metadata: { reference, donation: String(donation), cogs: String(cogs), zone },
      shipping_address_collection: {
        allowed_countries: ["ES", "PT", "FR", "DE", "IT", "NL", "BE", "IE", "AT", "LU"],
      },
      payment_intent_data: {
        description: `GRANKHA ${reference}`,
        receipt_email: email,          // Stripe manda el recibo de pago al cliente
        metadata: { reference },
      },
      success_url: `${SITE}/carrito?pedido=${reference}&estado=ok`,
      cancel_url: `${SITE}/carrito?estado=cancelado`,
    });
  } catch (e) {
    console.error("Stripe:", e.message);
    return send(res, 502, headers, { error: "No se pudo iniciar el pago", detail: e.message });
  }

  // ------------------------------------------------------- guardar pedido ---
  const { data: saved, error } = await supa.from("orders").insert({
    reference,
    status: "pending",
    stripe_session_id: session.id,
    currency: "EUR",
    subtotal: base,
    shipping_price: shippingCharged,
    vat_included: vatIncluded,
    total,
    donation,
    shipping_method: ship.name,
    customer: {
      name: cust.name, email, phone: cust.phone || "",
      address: cust.address, address2: cust.address2 || "",
      zip: cust.zip || "", city: cust.city, province: cust.province || "",
      country: cust.country || "ES", nif: cust.nif || "",
    },
    notes: order.notes || null,
    raw_payload: { zone, items, subtotal_con_iva: subtotal, cogs },
  }).select("id").single();

  if (error) {
    console.error("Supabase:", error.message);
    return send(res, 500, headers, { error: "No se pudo guardar el pedido" });
  }

  await supa.from("order_items").insert(items.map((l) => ({ ...l, order_id: saved.id })));

  return send(res, 200, headers, { url: session.url, reference, total });
};

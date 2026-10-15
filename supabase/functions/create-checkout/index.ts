// ============================================================================
// GRANKHA · Supabase Edge Function: create-checkout
// Recibe el pedido del carrito, crea una sesión de Stripe Checkout y guarda
// el pedido en Supabase. Devuelve { url } para redirigir al cliente.
//
// Despliegue:
//   supabase functions deploy create-checkout --no-verify-jwt
//
// Secretos necesarios:
//   supabase secrets set STRIPE_SECRET_KEY=sk_live_...
//   supabase secrets set SITE_URL=https://elexitodigital-eng.github.io/grankha
//   (SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY los inyecta Supabase)
//
// El carrito llama en POST con:
//   { reference, lines:[{sku, name, qty, unit_price, weight_g}], subtotal,
//     shipping_method, shipping_price, vat_included, total, customer, notes }
// y espera { url } para ir a la pasarela, o { message } si no hay pago online.
// ============================================================================

import Stripe from "https://esm.sh/stripe@16?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import PRICES from "./prices.json" assert { type: "json" };   // precios oficiales (se regeneran con tools/build.py)

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, { apiVersion: "2024-06-20" });
const supa = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const SITE_URL = Deno.env.get("SITE_URL") ?? "https://example.com";
const DONATION_RATE = 0.05;   // 5 % de los beneficios → investigación (ver docs/GRANKHA_Auditoria_Precios.xlsx)
const RETURNS_DAYS = 30;
const COSTS: Record<string, number> = (PRICES as any).costs ?? {};

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let order: any;
  try {
    order = await req.json();
  } catch {
    return json({ error: "JSON inválido" }, 400);
  }

  // ------------------------------------------------- validación mínima ----
  if (!order?.lines?.length || !order?.customer?.email) {
    return json({ error: "Pedido incompleto" }, 400);
  }

  // PRECIOS OFICIALES: el cliente no puede alterar importes ni el envío cobrado.
  const priceOf = (sku: string): number => {
    const entry = (PRICES as any)[sku];
    if (!entry) throw new Error(`SKU desconocido: ${sku}`);
    return Number(entry.price);
  };
  let subtotal = 0;
  let cogs = 0;
  for (const l of order.lines) {
    const official = priceOf(l.sku) * Number(l.qty);
    subtotal += official;
    l.unit_price = priceOf(l.sku);          // se sobreescribe con el precio oficial
    l.line_total = round(official);
    cogs += (COSTS[l.sku] ?? 0) * Number(l.qty);
  }
  subtotal = round(subtotal);
  const shippingCharged = Math.max(0, Number(order.shipping_price ?? 0));
  const allowedShipping = [0, 3.95, 5.95, 6.95, 7.95, 13.95, 14.95];
  if (!allowedShipping.includes(round(shippingCharged))) {
    return json({ error: "Gastos de envío no válidos" }, 400);
  }
  order.subtotal = subtotal;
  order.shipping_price = round(shippingCharged);
  order.total = round(subtotal + shippingCharged);
  order.vat_included = round(subtotal - subtotal / 1.21);
  // la donación es el 5 % del beneficio real del pedido (no del precio)
  const grossBenefit = round(subtotal / 1.21 - cogs);
  order.donation = grossBenefit > 0 ? round(grossBenefit * DONATION_RATE) : 0;
  order.cogs = round(cogs);
  order.reference = order.reference ?? `GRK-${Date.now().toString(36).toUpperCase()}`;

  // ------------------------------------------------------ Stripe Checkout -
  const line_items = order.lines.map((l: any) => ({
    quantity: l.qty,
    price_data: {
      currency: "eur",
      unit_amount: Math.round(l.unit_price * 100),   // precios con IVA incluido
      product_data: { name: l.name, metadata: { sku: l.sku } },
    },
  }));
  if (order.shipping_price > 0) {
    line_items.push({
      quantity: 1,
      price_data: {
        currency: "eur",
        unit_amount: Math.round(order.shipping_price * 100),
        product_data: { name: `Envío · ${order.shipping_method ?? "estándar"}` },
      },
    });
  }

  let session: Stripe.Checkout.Session;
  try {
    session = await stripe.checkout.sessions.create({
      mode: "payment",
      locale: "es",
      line_items,
      customer_email: order.customer.email,
      client_reference_id: order.reference,
      metadata: {
        reference: order.reference,
        donation: String(order.donation),
        cogs: String(order.cogs),
      },
      shipping_address_collection: { allowed_countries: ["ES", "PT", "FR", "DE", "IT", "NL", "BE", "IE", "AT", "LU"] },
      payment_intent_data: { description: `GRANKHA ${order.reference}` },
      success_url: `${SITE_URL}/carrito.html?pedido=${order.reference}&estado=ok`,
      cancel_url: `${SITE_URL}/carrito.html?estado=cancelado`,
    });
  } catch (e) {
    console.error("Stripe error", e);
    return json({ error: "No se pudo iniciar el pago" }, 502);
  }

  // --------------------------------------------------- guardar el pedido --
  const { data: saved, error } = await supa.from("orders").insert({
    reference: order.reference,
    status: "pending",
    stripe_session_id: session.id,
    currency: "EUR",
    subtotal: order.subtotal,
    shipping_price: order.shipping_price ?? 0,
    vat_included: order.vat_included,
    total: order.total,
    donation: order.donation,
    shipping_method: order.shipping_method ?? null,
    customer: order.customer,
    notes: order.notes ?? null,
    raw_payload: order,
  }).select("id").single();

  if (error) {
    console.error("Supabase error", error);
    return json({ error: "No se pudo guardar el pedido" }, 500);
  }

  await supa.from("order_items").insert(order.lines.map((l: any) => ({
    order_id: saved.id, sku: l.sku, slug: l.slug ?? "", name: l.name,
    qty: l.qty, unit_price: l.unit_price, line_total: round(l.unit_price * l.qty),
    weight_g: l.weight_g ?? 0,
  })));

  return json({ url: session.url, reference: order.reference }, 200);
});

function round(n: number) { return Math.round(n * 100) / 100; }
function json(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status, headers: { ...cors, "Content-Type": "application/json" },
  });
}

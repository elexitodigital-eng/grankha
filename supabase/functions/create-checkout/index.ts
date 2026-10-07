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

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, { apiVersion: "2024-06-20" });
const supa = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const SITE_URL = Deno.env.get("SITE_URL") ?? "https://example.com";
const DONATION_RATE = 0.05;   // % de los beneficios reservado a investigación

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
  const subtotal = round(order.lines.reduce(
    (s: number, l: any) => s + l.unit_price * l.qty, 0));
  // el cliente nunca fija el precio: lo recalculamos en servidor
  order.subtotal = subtotal;
  order.total = round(subtotal + (order.shipping_price ?? 0));
  order.vat_included = round(subtotal - subtotal / 1.21);
  order.donation = round(subtotal / 1.21 * DONATION_RATE);
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
      metadata: { reference: order.reference },
      shipping_address_collection: { allowed_countries: ["ES", "PT", "FR", "DE", "IT", "NL", "BE", "IE", "AT", "LU"] },
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

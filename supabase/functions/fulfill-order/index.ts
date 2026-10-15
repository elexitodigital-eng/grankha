// ============================================================================
// GRANKHA · Supabase Edge Function: fulfill-order
// Convierte un pedido pagado en un pedido real en AW Dropshipping (aiku) y
// guarda el número de seguimiento en Supabase.
//
// Flujo completo del pedido:
//   1. Cliente paga en Stripe            → stripe-webhook marca orders.status = 'paid'
//   2. Esta función crea el cliente en el proveedor (si no existe)
//   3. Crea el pedido con los SKU y la dirección de entrega
//   4. Lo envía al almacén (submit)
//   5. Guarda supplier_order_id y, cuando el proveedor devuelva el tracking,
//      lo escribe en orders.tracking_code para que llegue al cliente por email
//
// Despliegue:
//   supabase functions deploy fulfill-order --no-verify-jwt
//   supabase secrets set AIKU_TOKEN='690|xxxxxxxx'         (token del canal, NO en el repo)
//   supabase secrets set AIKU_API=https://api.aiku.io      (staging: https://api.aiku-sandbox.uk)
//
// IMPORTANTE: los nombres exactos de algunos campos del POST de pedidos dependen
// de la versión del panel del proveedor. Antes de usarlo en producción:
//   1) ejecuta la prueba con --dry-run (ver más abajo) y revisa la respuesta,
//   2) o crea un pedido manual en el panel y compara con data/channel_ids.json.
// El resto del flujo (validación, guardado de tracking, email) ya está resuelto.
// ============================================================================

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supa = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const AIKU = Deno.env.get("AIKU_API") ?? "https://api.aiku.io";
const TOKEN = Deno.env.get("AIKU_TOKEN")!;

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

async function aiku(path: string, init: RequestInit = {}) {
  const res = await fetch(`${AIKU}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init.headers ?? {}),
    },
  });
  const text = await res.text();
  let body: any = null;
  try { body = JSON.parse(text); } catch { body = text; }
  if (!res.ok) throw new Error(`aiku ${path} → ${res.status}: ${text.slice(0, 300)}`);
  return body;
}

// 1 · Cliente en el proveedor -------------------------------------------------
async function getOrCreateClient(order: any): Promise<number> {
  const email = order.customer.email;
  const list = await aiku(`/dropshipping/clients?search=${encodeURIComponent(email)}`);
  const found = (list?.data ?? []).find((c: any) => (c.email ?? "").toLowerCase() === email.toLowerCase());
  if (found) return found.id;

  const created = await aiku(`/dropshipping/clients`, {
    method: "POST",
    body: JSON.stringify({
      name: order.customer.name,
      email,
      phone: order.customer.phone,
      company_name: "",
      // dirección de entrega del cliente final
      address: order.customer.address,
      address_2: order.customer.address2 ?? "",
      zip: order.customer.zip,
      city: order.customer.city,
      province: order.customer.province ?? "",
      country: order.customer.country ?? "ES",
      nif: order.customer.nif ?? "",
    }),
  });
  return created?.data?.id ?? created?.id;
}

// 2 · Pedido en el proveedor --------------------------------------------------
async function createSupplierOrder(order: any, clientId: number) {
  // Los packs se piden por sus componentes (el proveedor factura por SKU).
  const items: { code: string; quantity: number }[] = [];
  for (const l of order.raw_payload?.lines ?? []) {
    if (Array.isArray(l.components) && l.components.length) {
      for (const c of l.components) {
        const prev = items.find((i) => i.code === c.sku);
        if (prev) prev.quantity += c.qty * l.qty;
        else items.push({ code: c.sku, quantity: c.qty * l.qty });
      }
    } else {
      const prev = items.find((i) => i.code === l.sku);
      if (prev) prev.quantity += l.qty;
      else items.push({ code: l.sku, quantity: l.qty });
    }
  }

  const body = {
    reference: order.reference,
    currency_code: "EUR",
    notes: `GRANKHA · ${order.notes ?? ""}`.trim(),
    customer_client_id: clientId,
    shipping: {
      name: order.customer.name,
      address: order.customer.address,
      address_2: order.customer.address2 ?? "",
      zip: order.customer.zip,
      city: order.customer.city,
      province: order.customer.province ?? "",
      country: order.customer.country ?? "ES",
      phone: order.customer.phone ?? "",
      email: order.customer.email,
    },
    items,
  };

  const created = await aiku(`/dropshipping/order/client/${clientId}/store`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  const orderId = created?.data?.id ?? created?.id;

  // 3 · enviar al almacén
  if (orderId) {
    await aiku(`/dropshipping/order/${orderId}/submit`, { method: "PATCH" });
  }
  return { orderId, body };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });

  let payload: any = {};
  try { payload = await req.json(); } catch { /* sin cuerpo */ }
  const dryRun = req.url.includes("dry_run=1") || payload?.dry_run === true;

  // Pedidos pagados (o una referencia concreta) pendientes de tramitar
  let q = supa.from("orders").select("*").is("supplier_order_id", null);
  q = payload?.reference ? q.eq("reference", payload.reference) : q.eq("status", "paid");
  const { data: orders, error } = await q.limit(20);
  if (error) return json({ error: error.message }, 500);
  if (!orders?.length) return json({ processed: 0, message: "Nada pendiente" }, 200);

  const results: any[] = [];
  for (const order of orders) {
    try {
      if (!order.customer?.address || !order.customer?.zip) {
        results.push({ reference: order.reference, error: "Dirección incompleta" });
        continue;
      }
      if (dryRun) {
        const items = (order.raw_payload?.lines ?? []).map((l: any) => `${l.sku} × ${l.qty}`);
        results.push({ reference: order.reference, dry_run: true, items, customer: order.customer.email });
        continue;
      }
      const clientId = await getOrCreateClient(order);
      const { orderId } = await createSupplierOrder(order, clientId);
      await supa.from("orders").update({
        supplier_order_id: orderId,
        status: "fulfilled",
      }).eq("id", order.id);
      results.push({ reference: order.reference, supplier_order_id: orderId, status: "fulfilled" });
    } catch (e) {
      console.error("fulfill error", order.reference, e);
      results.push({ reference: order.reference, error: String(e).slice(0, 200) });
    }
  }

  return json({ processed: results.length, results }, 200);
});

function json(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status, headers: { ...cors, "Content-Type": "application/json" },
  });
}

// ---------------------------------------------------------------------------
// GUARDAR EL SEGUIMIENTO
// Cuando el proveedor despacha, devuelve el número de seguimiento. Dos formas:
//
//   A) Manual (los primeros pedidos): en el panel de AW copias el tracking y
//      actualizas con esta consulta en Supabase →
//        update orders set tracking_code='XXXX', tracking_url='https://...',
//               shipped_at=now() where reference='GRK-XXXXXX-XXXX';
//
//   B) Automática: programa esta función cada 6 horas (Supabase → Edge Functions
//      → Schedules, o cron-job.org) con el cuerpo {"sync_tracking": true} y
//      rellena desde GET /dropshipping/order/{id}
//
// Con `orders.tracking_code` relleno, el email de "pedido enviado" (plantilla en
// docs/emails/pedido-enviado.html) se envía solo si tienes conectado Brevo/Resend.
// ---------------------------------------------------------------------------

// ============================================================================
// GRANKHA · Supabase Edge Function: notify-tracking
// Envía al cliente el correo 2: "tu pedido va de camino", con el número de
// seguimiento y el botón para ver dónde está.
//
// Tiene dos modos:
//
//  1) MANUAL (lo más rápido y lo que usarás al principio, sin Stripe del todo):
//     POST /notify-tracking
//     { "reference": "GRK-261015-4E7O", "tracking_code": "PQ123456789ES" }
//     Opcional: "tracking_url" si quieres apuntar a la web de la agencia.
//
//  2) AUTOMÁTICO (cuando tengas el flujo con Stripe funcionando):
//     POST /notify-tracking   { "poll": true }
//     Busca los pedidos pagados sin seguimiento enviado, pregunta a AW por su
//     estado y manda el correo en cuanto aparece el número de seguimiento.
//     Programable con pg_cron cada 30 minutos (instrucciones en
//     docs/COMO_VENDER_YA.md).
//
// Despliegue:
//   supabase functions deploy notify-tracking --no-verify-jwt
//   supabase secrets set EMAIL_PROVIDER=brevo BREVO_API_KEY=... EMAIL_FROM="GRANKHA <hola@...>"
//   supabase secrets set AW_TOKEN=... AW_CLIENT_ID=... AW_CHANNEL_ID=...
// ============================================================================

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { emailPedidoEnviado, sendEmail } from "../_shared/email.ts";

const supa = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

const AW_BASE = Deno.env.get("AW_BASE") ?? "https://api.aiku.io";
const AW_TOKEN = Deno.env.get("AW_TOKEN") ?? "";

const json = (b: unknown, status = 200) =>
  new Response(JSON.stringify(b), { status, headers: { "Content-Type": "application/json" } });

async function enviarCorreo2(order: any) {
  const email = order.customer?.email;
  if (!email) return { ok: false, motivo: "el pedido no tiene email" };
  const { subject, html } = emailPedidoEnviado({
    reference: order.reference,
    customer: order.customer,
    subtotal: Number(order.subtotal),
    shipping_price: Number(order.shipping_price),
    shipping_method: order.shipping_method,
    total: Number(order.total),
    tracking_code: order.tracking_code,
    tracking_url: order.tracking_url ?? undefined,
  });
  const ok = await sendEmail(email, subject, html);
  await supa.from("orders").update({
    tracking_code: order.tracking_code,
    status: "fulfilled",
    tracking_email_sent_at: new Date().toISOString(),
  }).eq("id", order.id);
  return { ok, reference: order.reference, para: email };
}

/** Pregunta a AW el estado del pedido y devuelve el número de seguimiento si ya existe. */
async function seguimientoDeAW(reference: string): Promise<{ code?: string; url?: string }> {
  if (!AW_TOKEN) return {};
  const q = new URLSearchParams({ reference, per_page: "5" });
  const r = await fetch(`${AW_BASE}/dropshipping/order?${q}`, {
    headers: { Authorization: `Bearer ${AW_TOKEN}`, Accept: "application/json" },
  });
  if (!r.ok) return {};
  const data = await r.json();
  const filas: any[] = Array.isArray(data) ? data : (data?.data ?? []);
  const pedido = filas.find((f) => (f.reference ?? f.client_reference ?? "") === reference) ?? filas[0];
  if (!pedido) return {};
  const code = pedido.tracking_number ?? pedido.tracking_code ?? pedido.tracking ?? "";
  const url = pedido.tracking_url ?? pedido.carrier_tracking_url ?? "";
  return code ? { code, url: url || undefined } : {};
}

Deno.serve(async (req) => {
  const body = await req.json().catch(() => ({}));

  // ---------------------------------------------------------- modo manual
  if (body.reference) {
    const { data: order } = await supa.from("orders").select("*").eq("reference", body.reference).maybeSingle();
    if (!order) return json({ error: "No existe ese pedido" }, 404);
    const res = await enviarCorreo2({ ...order, tracking_code: body.tracking_code ?? order.tracking_code,
                                      tracking_url: body.tracking_url ?? order.tracking_url });
    return json(res);
  }

  // -------------------------------------------------------- modo automático
  if (body.poll) {
    const { data: pendientes } = await supa.from("orders")
      .select("*").eq("status", "paid").is("tracking_email_sent_at", null).limit(50);
    const enviados = [];
    for (const o of pendientes ?? []) {
      const aw = await seguimientoDeAW(o.reference);
      if (aw.code) enviados.push(await enviarCorreo2({ ...o, tracking_code: aw.code, tracking_url: aw.url }));
    }
    return json({ revisados: pendientes?.length ?? 0, enviados });
  }

  return json({ error: "Pasa {reference, tracking_code} o {poll:true}" }, 400);
});

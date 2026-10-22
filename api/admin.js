// ============================================================================
// GRANKHA · /api/admin — panel privado para gestionar los pedidos
//
// Todo lo que hace exige el token (ADMIN_TOKEN). Sin él, 401. La página
// pedidos.html es solo la interfaz: no contiene ningún secreto.
//
//   GET  /api/admin?token=…                      → lista de pedidos
//   POST /api/admin { token, action, reference } →
//        action "shipped"        marca enviado + manda el email de seguimiento
//        action "resend-tracking" reenvía el email de seguimiento
//        action "resend-order"    reenvía la confirmación de pedido al cliente
//        action "resend-sale"     te reenvía a ti el aviso interno de venta
//
// Variables: ADMIN_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY y las de correo.
// ============================================================================
const { createClient } = require("@supabase/supabase-js");
const { sendEmail, mailReady } = require("./_lib/mail");
const { orderEmail, saleEmail, shippingEmail } = require("./_lib/emails");

const supa = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

const TOKEN = process.env.ADMIN_TOKEN || "";
const SELECT = `id, reference, created_at, status, currency, subtotal, shipping_price, vat_included,
                total, donation, shipping_method, customer, notes, tracking_code, tracking_url,
                tracking_carrier, tracking_eta, tracking_email_sent_at, shipped_at,
                order_email_sent_at, order_email_error, supplier_order_id,
                order_items(name, sku, qty, unit_price)`;

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(body === undefined ? "" : JSON.stringify(body));
}

// comparación en tiempo constante para no filtrar el token carácter a carácter
function tokenOk(dado) {
  const a = Buffer.from(String(dado || ""));
  const b = Buffer.from(TOKEN);
  if (!TOKEN || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

async function getOrder(reference) {
  const { data, error } = await supa.from("orders").select(SELECT).eq("reference", reference).maybeSingle();
  if (error) throw new Error(error.message);
  return data;
}

module.exports = async (req, res) => {
  if (!TOKEN) return send(res, 500, { error: "ADMIN_TOKEN no está configurado en Vercel" });

  // ------------------------------------------------------------ GET: listado
  if (req.method === "GET") {
    const u = new URL(req.url, "http://x");
    if (!tokenOk(u.searchParams.get("token"))) return send(res, 401, { error: "Token incorrecto" });
    const { data, error } = await supa.from("orders").select(SELECT)
      .order("created_at", { ascending: false }).limit(100);
    if (error) return send(res, 500, { error: error.message });
    return send(res, 200, {
      ok: true,
      correo: { configurado: mailReady(), from: process.env.EMAIL_FROM || "(por defecto)" },
      pedidos: data,
    });
  }

  if (req.method !== "POST") return send(res, 405, { error: "Método no permitido" });

  // ----------------------------------------------------------- POST: acciones
  // En Vercel el cuerpo ya viene parseado cuando Content-Type es application/json;
  // si llega como texto (otros clientes) se parsea aquí. Aceptamos ambos casos.
  let d = req.body;
  if (typeof d === "string" || Buffer.isBuffer(d)) {
    try { d = JSON.parse(Buffer.isBuffer(d) ? d.toString("utf8") : d); }
    catch { return send(res, 400, { error: "JSON inválido" }); }
  }
  if (!d || typeof d !== "object") return send(res, 400, { error: "JSON inválido" });
  if (!tokenOk(d.token)) return send(res, 401, { error: "Token incorrecto" });

  const action = String(d.action || "");
  const reference = String(d.reference || "").trim();
  if (!reference) return send(res, 400, { error: "Falta la referencia del pedido" });

  try {
    const o = await getOrder(reference);
    if (!o) return send(res, 404, { error: `No existe el pedido ${reference}` });
    const cliente = (o.customer && o.customer.email) || "";

    // ------------------------------------------- marcado como enviado + email
    if (action === "shipped") {
      const code = String(d.tracking_code || "").trim().slice(0, 80);
      const url = String(d.tracking_url || "").trim().slice(0, 400);
      const carrier = String(d.tracking_carrier || "").trim().slice(0, 80);
      const eta = String(d.tracking_eta || "").trim().slice(0, 160);
      if (!code) return send(res, 400, { error: "Falta el número de seguimiento" });
      if (url && !/^https?:\/\//i.test(url)) return send(res, 400, { error: "El enlace de seguimiento debe empezar por http(s)://" });
      if (!cliente) return send(res, 400, { error: "El pedido no tiene email de cliente" });

      const patch = {
        tracking_code: code,
        tracking_url: url || null,
        tracking_carrier: carrier || null,
        tracking_eta: eta || null,
        shipped_at: new Date().toISOString(),
        status: "shipped",
      };
      if (d.supplier_order_id) patch.supplier_order_id = String(d.supplier_order_id).slice(0, 80);

      const actualizado = { ...o, ...patch };
      const { subject, html } = shippingEmail(actualizado);
      const r = await sendEmail(cliente, subject, html);

      patch.tracking_email_sent_at = r.ok ? new Date().toISOString() : null;
      if (!r.ok) patch.notes = `email_seguimiento_fallo: ${r.error || "desconocido"}`;
      const { error } = await supa.from("orders").update(patch).eq("reference", reference);
      if (error) return send(res, 500, { error: error.message });

      return send(res, 200, {
        ok: r.ok, reference, enviado_a: cliente,
        email: r.ok ? { id: r.id } : { error: r.error },
        mensaje: r.ok ? "Pedido marcado como enviado y correo de seguimiento entregado a Resend."
                      : "Pedido marcado como enviado, pero el correo NO salió. Mira el error y reenvía.",
      });
    }

    // --------------------------------------------------------- reenvíos
    if (["resend-tracking", "resend-order", "resend-sale"].includes(action)) {
      let destino, msg;
      if (action === "resend-tracking") {
        if (!cliente) return send(res, 400, { error: "El pedido no tiene email de cliente" });
        if (!o.tracking_code) return send(res, 400, { error: "Este pedido aún no tiene número de seguimiento" });
        msg = shippingEmail(o); destino = cliente;
      } else if (action === "resend-order") {
        if (!cliente) return send(res, 400, { error: "El pedido no tiene email de cliente" });
        msg = orderEmail(o); destino = cliente;
      } else {
        if (!process.env.EMAIL_AVISO) return send(res, 400, { error: "EMAIL_AVISO no está configurado" });
        msg = saleEmail(o); destino = process.env.EMAIL_AVISO;
      }
      const r = await sendEmail(destino, msg.subject, msg.html);
      if (r.ok && action === "resend-order") {
        await supa.from("orders").update({
          order_email_sent_at: new Date().toISOString(), order_email_error: null,
        }).eq("reference", reference);
      }
      if (r.ok && action === "resend-tracking") {
        await supa.from("orders").update({ tracking_email_sent_at: new Date().toISOString() })
          .eq("reference", reference);
      }
      return send(res, r.ok ? 200 : 502, {
        ok: r.ok, reference, enviado_a: destino,
        email: r.ok ? { id: r.id } : { error: r.error },
      });
    }

    return send(res, 400, { error: `Acción no reconocida: ${action}` });
  } catch (e) {
    console.error("admin:", e && e.message ? e.message : e);
    return send(res, 500, { error: e && e.message ? e.message : "Error interno" });
  }
};

// ============================================================================
// GRANKHA · POST /api/stripe-webhook
//
// Stripe avisa aquí cuando se cobra un pedido. Marca el pedido como pagado en
// Supabase y manda al cliente el correo con los datos de la compra.
//
// Variables de entorno:
//   STRIPE_SECRET_KEY          (la misma que usa el checkout)
//   STRIPE_WEBHOOK_SECRET      whsec_...
//   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
//   EMAIL_PROVIDER = smtp | resend | brevo   (opcional; se deduce solo)
//     smtp   → SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS  (buzón de la empresa)
//     resend → RESEND_API_KEY
//     brevo  → BREVO_API_KEY
//   EMAIL_FROM = "GRANKHA <grankha@roadshop.online>"
//   EMAIL_AVISO = correo interno que recibe el aviso de cada venta
// ============================================================================
const Stripe = require("stripe");
const { createClient } = require("@supabase/supabase-js");

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, { apiVersion: "2024-06-20" });
const supa = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

// Vercel: hay que leer el cuerpo en crudo para poder verificar la firma.
const config = { api: { bodyParser: false } };

const eur = (n = 0) => Number(n).toFixed(2).replace(".", ",") + " €";
const esc = (s = "") => String(s).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

// Correo unificado (SMTP del buzón de la empresa, Resend o Brevo)
const { sendEmail } = require("./_lib/mail");

function orderEmail(o) {
  const lines = (o.order_items || []).map(
    (l) => `<tr><td style="padding:6px 0">${esc(l.qty)} × ${esc(l.name)}</td>
            <td align="right">${eur(Number(l.unit_price) * l.qty)}</td></tr>`
  ).join("");
  const c = o.customer || {};
  const html = `
  <div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111">
    <h2 style="letter-spacing:-.02em">Gracias por tu compra, ${esc((c.name || "").split(" ")[0])}.</h2>
    <p>Tu pedido <b>${esc(o.reference)}</b> ya está confirmado y pagado.</p>
    <table style="width:100%;border-collapse:collapse;border-top:1px solid #e5e5e3;border-bottom:1px solid #e5e5e3;margin:18px 0">
      ${lines}
      <tr><td style="padding:6px 0">Envío (${esc(o.shipping_method || "")})</td>
          <td align="right">${Number(o.shipping_price) === 0 ? "Gratis" : eur(o.shipping_price)}</td></tr>
      <tr><td style="padding:10px 0;border-top:1px solid #e5e5e3"><b>Total</b></td>
          <td align="right" style="padding:10px 0;border-top:1px solid #e5e5e3"><b>${eur(o.total)}</b></td></tr>
    </table>
    <p><b>Entrega en</b><br>${esc(c.name || "")}<br>${esc(c.address || "")} ${esc(c.address2 || "")}<br>
       ${esc(c.zip || "")} ${esc(c.city || "")}<br>${esc(c.province || "")} · ${esc(c.country || "")}</p>
    <p style="color:#555">Te escribiremos otra vez en cuanto el paquete salga, con el enlace de seguimiento.
       Devoluciones durante 30 días. Cualquier duda: respóndenos a este correo.</p>
    <p style="color:#555">GRANKHA · En memoria de Khalid · un porcentaje de los beneficios va destinado a la
       investigación del cáncer y las enfermedades raras en mascotas.</p>
  </div>`;
  return { subject: `Pedido ${o.reference} confirmado · GRANKHA`, html };
}

function send(res, status, body) {
  res.statusCode = status;
  if (body !== undefined) res.setHeader("Content-Type", "application/json");
  res.end(body === undefined ? "" : JSON.stringify(body));
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return send(res, 405);

  const sig = req.headers["stripe-signature"];
  const chunks = [];
  for await (const chunk of req) chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
  const body = Buffer.concat(chunks);

  let event;
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (e) {
    console.error("Firma inválida:", e.message);
    return send(res, 400, { error: e.message });
  }

  try {
    if (event.type === "checkout.session.completed") {
      const s = event.data.object;
      const { data: o } = await supa.from("orders")
        .update({ status: "paid", stripe_payment_intent: String(s.payment_intent || "") })
        .eq("stripe_session_id", s.id)
        .select("reference, customer, shipping_method, shipping_price, total, order_items(name, sku, qty, unit_price)")
        .maybeSingle();

      const email = (o && o.customer && o.customer.email) || (s.customer_details && s.customer_details.email);
      if (o && email) {
        const { subject, html } = orderEmail(o);
        await sendEmail(email, subject, html);
        if (process.env.EMAIL_AVISO) {
          await sendEmail(process.env.EMAIL_AVISO, `[VENTA] ${o.reference} · ${eur(o.total)}`, html);
        }
      }
    } else if (event.type === "charge.refunded") {
      const c = event.data.object;
      await supa.from("orders").update({ status: "refunded" })
        .eq("stripe_payment_intent", String(c.payment_intent || ""));
    }
  } catch (e) {
    console.error("webhook:", e.message);
    return send(res, 500, { received: false });
  }

  return send(res, 200, { received: true });
};

module.exports.config = config;

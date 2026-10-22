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


// Correo unificado (SMTP del buzón de la empresa, Resend o Brevo)
const { sendEmail } = require("./_lib/mail");

// --------------------------------------------------------------------------
// Plantillas de correo: pedido confirmado, aviso interno de venta y envío con
// seguimiento. Compartidas con api/tracking.js (mismo diseño, mismos datos).
// --------------------------------------------------------------------------
const { orderEmail, saleEmail } = require("./_lib/emails");

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
        .select(`reference, customer, shipping_method, shipping_price, subtotal, vat_included,
                 donation, total, currency, order_items(name, sku, qty, unit_price)`)
        .maybeSingle();

      const email = (o && o.customer && o.customer.email) || (s.customer_details && s.customer_details.email);
      if (o && email) {
        // al cliente: su confirmación de pedido
        const { subject, html } = orderEmail(o);
        const rCli = await sendEmail(email, subject, html);
        console.log(`[email cliente] ${o.reference} → ${email} · ${rCli.ok ? "OK " + (rCli.id || "") : "FALLO " + (rCli.error || "")}`);

        // a ti: el aviso interno con margen y los datos para pasar a AW (antes recibías
        // el mismo correo del cliente, sin coste, sin margen y sin dirección que copiar)
        if (process.env.EMAIL_AVISO) {
          const interno = saleEmail(o);
          const rInt = await sendEmail(process.env.EMAIL_AVISO, interno.subject, interno.html);
          console.log(`[aviso venta] ${o.reference} → ${process.env.EMAIL_AVISO} · ${rInt.ok ? "OK " + (rInt.id || "") : "FALLO " + (rInt.error || "")}`);
        }
        // si el correo al cliente no salió, se anota en el pedido para reenviarlo desde /pedidos
        if (!rCli.ok) {
          await supa.from("orders").update({ notes: `email_cliente_pendiente: ${rCli.error || "desconocido"}` })
            .eq("reference", o.reference);
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

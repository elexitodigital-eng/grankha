// ============================================================================
// GRANKHA · POST /api/contact
// Guarda el mensaje del formulario de contacto en Supabase (tabla
// contact_messages) y avisa por correo si hay proveedor configurado.
// ============================================================================
const { createClient } = require("@supabase/supabase-js");

const supa = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

const esc = (s = "") => String(s).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

async function notify(subject, html) {
  const provider = (process.env.EMAIL_PROVIDER || "").toLowerCase();
  const from = process.env.EMAIL_FROM || "GRANKHA <onboarding@resend.dev>";
  const to = process.env.EMAIL_AVISO;
  if (!to) return;
  try {
    if (provider === "resend" && process.env.RESEND_API_KEY) {
      await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({ from, to: [to], subject, html }),
      });
    } else if (provider === "brevo" && process.env.BREVO_API_KEY) {
      await fetch("https://api.brevo.com/v3/smtp/email", {
        method: "POST",
        headers: { "api-key": process.env.BREVO_API_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({
          sender: { name: "GRANKHA", email: from.replace(/.*<|>.*/g, "") },
          to: [{ email: to }], subject, htmlContent: html,
        }),
      });
    }
  } catch (e) {
    console.error("contacto email:", e.message);
  }
}

function send(res, status, headers, body) {
  res.statusCode = status;
  for (const [k, v] of Object.entries(headers)) res.setHeader(k, v);
  res.end(body === undefined ? "" : JSON.stringify(body));
}

module.exports = async (req, res) => {
  const headers = {
    "Access-Control-Allow-Origin": process.env.ALLOWED_ORIGIN || req.headers.origin || "*",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
  };
  if (req.method === "OPTIONS") return send(res, 204, headers);
  if (req.method !== "POST") return send(res, 405, headers, { error: "Método no permitido" });

  const d = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
  const nombre = String(d.nombre || "").slice(0, 120);
  const email = String(d.email || "").slice(0, 160);
  const mensaje = String(d.mensaje || d.message || "").slice(0, 4000);
  const pedido = String(d.pedido || d.order_ref || "").slice(0, 40);
  const mascota = String(d.mascota || "").slice(0, 120);

  if (!mensaje.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return send(res, 400, headers, { error: "Faltan el email o el mensaje" });
  }

  const { error } = await supa.from("contact_messages").insert({
    name: nombre, email, order_ref: pedido || null,
    message: mascota ? `${mensaje}\n\nMascota: ${mascota}` : mensaje,
  });
  if (error) {
    console.error("contacto:", error.message);
    return send(res, 500, headers, { error: "No se pudo guardar el mensaje" });
  }

  await notify(
    `Consulta web${pedido ? " · " + pedido : ""} · ${nombre || email}`,
    `<p><b>${esc(nombre)}</b> &lt;${esc(email)}&gt;</p>
     ${pedido ? `<p>Pedido: ${esc(pedido)}</p>` : ""}
     ${mascota ? `<p>Mascota: ${esc(mascota)}</p>` : ""}
     <p style="white-space:pre-wrap">${esc(mensaje)}</p>`
  );

  return send(res, 200, headers, { ok: true });
};

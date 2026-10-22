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

// El aviso interno siempre va al correo de la empresa
const { sendEmail } = require("./_lib/mail");

async function notify(subject, html) {
  const to = process.env.EMAIL_AVISO;
  if (!to) return;
  await sendEmail(to, subject, html);
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

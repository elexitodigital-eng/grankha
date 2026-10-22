// ============================================================================
// GRANKHA · POST /api/newsletter
//
// Recibe el email del formulario de la portada y lo entrega en el destino
// configurado. QUIEN HABLA CON ESE DESTINO ES ESTE FICHERO, EN EL SERVIDOR:
// el navegador solo ve /api/newsletter de esta misma web, así que nunca se
// expone ninguna URL, iframe ni redirección de un servicio de terceros.
//
// Variables de entorno (opcionales; si faltan se usa el valor por defecto):
//   GFORMS_NEWSLETTER_ID   id del formulario
//   GFORMS_NEWSLETTER_KEY  clave del campo de email
// ============================================================================
const { enviar } = require("./_lib/gforms");
const { limitado } = require("./_lib/ratelimit");

const FORM_ID = process.env.GFORMS_NEWSLETTER_ID ||
  "1FAIpQLSeRFRululS1q_8J4mr1ffdYRSKKS16omuh6z7thohCePzJltQ";
const ENTRY_EMAIL = process.env.GFORMS_NEWSLETTER_KEY || "entry.900045037";

// Máximo de suscripciones por IP y ventana de 10 min: corta el alta masiva.
const MAX_POR_IP = 6;

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
    "Cache-Control": "no-store",
  };
  if (req.method === "OPTIONS") return send(res, 204, headers);
  if (req.method !== "POST") return send(res, 405, headers, { error: "Método no permitido" });

  let d;
  try {
    d = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
  } catch {
    return send(res, 400, headers, { error: "Petición no válida" });
  }

  const email = String(d.email || "").trim().toLowerCase().slice(0, 160);
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
    return send(res, 400, headers, { error: "El email no es válido" });
  }
  // El consentimiento es obligatorio: sin él no se registra nada.
  if (d.consent !== true && d.consent !== "true" && d.consent !== "on") {
    return send(res, 400, headers, { error: "Falta el consentimiento" });
  }

  // El límite va aquí, no al principio: validar es gratis y una errata del
  // usuario no debe quemarle cupo. Lo que se protege es la llamada saliente.
  if (limitado(req, "news", MAX_POR_IP)) {
    return send(res, 429, headers, { error: "Demasiados intentos. Espera unos minutos." });
  }

  const r = await enviar(FORM_ID, { [ENTRY_EMAIL]: email });
  if (!r.ok) {
    console.error("newsletter: no se pudo entregar", r.status, r.error || "");
    return send(res, 502, headers, { error: "No se pudo completar la suscripción" });
  }

  console.log(`[newsletter] alta OK · ${email.replace(/^(.{2}).*(@.*)$/, "$1***$2")}`);
  return send(res, 200, headers, { ok: true });
};

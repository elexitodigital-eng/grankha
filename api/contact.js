// ============================================================================
// GRANKHA · POST /api/contact
//
// Recibe el formulario de contacto y lo entrega en el destino configurado.
// QUIEN HABLA CON ESE DESTINO ES ESTE FICHERO, EN EL SERVIDOR: el navegador
// solo ve /api/contact de esta misma web, así que nunca se expone ninguna URL,
// iframe ni redirección de un servicio de terceros.
//
// Variables de entorno (opcionales; si faltan se usa el valor por defecto):
//   GFORMS_CONTACT_ID   id del formulario
//   GFORMS_CONTACT_MAP  JSON {"nombre":"entry.X", ...} para cambiar el mapeo
// ============================================================================
const { enviar } = require("./_lib/gforms");
const { limitado } = require("./_lib/ratelimit");

const FORM_ID = process.env.GFORMS_CONTACT_ID ||
  "1FAIpQLSd7quYfl0_6CziwbW6JvT5fkJvX_-HcagEtnm197ST78AAL9A";

// Campos del formulario web → campos del destino.
const MAPA = Object.assign({
  nombre:  "entry.1610036456",
  email:   "entry.305793954",
  pedido:  "entry.783059237",
  mascota: "entry.604082290",
  mensaje: "entry.790312985",
}, (() => {
  try { return JSON.parse(process.env.GFORMS_CONTACT_MAP || "{}"); } catch { return {}; }
})());

// Máximo de mensajes por IP y ventana de 10 min: corta el spam automatizado.
const MAX_POR_IP = 4;

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

  const nombre  = String(d.nombre || "").trim().slice(0, 120);
  const email   = String(d.email || "").trim().slice(0, 160);
  const mensaje = String(d.mensaje || d.message || "").trim().slice(0, 4000);
  const pedido  = String(d.pedido || d.order_ref || "").trim().slice(0, 40);
  const mascota = String(d.mascota || "").trim().slice(0, 120);

  // Los tres campos obligatorios del formulario. Si falta alguno no se envía:
  // mejor un aviso claro al cliente que un mensaje a medias.
  if (!nombre) return send(res, 400, headers, { error: "Falta el nombre" });
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
    return send(res, 400, headers, { error: "El email no es válido" });
  }
  if (!mensaje) return send(res, 400, headers, { error: "Falta el mensaje" });
  // El consentimiento es obligatorio.
  if (d.consent === false || d.consent === "false") {
    return send(res, 400, headers, { error: "Falta el consentimiento" });
  }

  // Igual que en la newsletter: primero validar (gratis), luego limitar la
  // llamada saliente, que es lo que cuesta y lo que se puede abusar.
  if (limitado(req, "contacto", MAX_POR_IP)) {
    return send(res, 429, headers, { error: "Demasiados mensajes seguidos. Espera unos minutos." });
  }

  const r = await enviar(FORM_ID, {
    [MAPA.nombre]:  nombre,
    [MAPA.email]:   email,
    [MAPA.pedido]:  pedido,
    [MAPA.mascota]: mascota,
    [MAPA.mensaje]: mensaje,
  });

  if (!r.ok) {
    console.error("contacto: no se pudo entregar", r.status, r.error || "");
    return send(res, 502, headers, { error: "No se pudo enviar el mensaje" });
  }

  console.log(`[contacto] mensaje OK · ${email.replace(/^(.{2}).*(@.*)$/, "$1***$2")}` +
              (pedido ? ` · pedido ${pedido}` : ""));
  return send(res, 200, headers, { ok: true });
};

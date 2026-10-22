// ============================================================================
// GRANKHA · api/_lib/mail.js — envío de correo único para todas las funciones
//
// Tres proveedores, se elige con EMAIL_PROVIDER:
//
//   1) resend  → EMAIL_PROVIDER=resend + RESEND_API_KEY      ← el que usa GRANKHA
//   2) smtp    → el buzón de la propia empresa
//        EMAIL_PROVIDER = smtp
//        SMTP_HOST = smtp.ionos.es · SMTP_PORT = 587
//        SMTP_USER = grankha@roadshop.online · SMTP_PASS = contraseña
//   3) brevo   → EMAIL_PROVIDER=brevo  + BREVO_API_KEY
//
// Comunes a los tres:
//   EMAIL_FROM     remitente. Ej. "GRANKHA <pedidos@mail.roadshop.online>"
//   EMAIL_REPLY_TO dónde caen las respuestas. Ej. grankha@roadshop.online
//                  Imprescindible si se envía desde un subdominio verificado en
//                  Resend: el cliente responde y te llega al buzón de verdad.
//   EMAIL_AVISO    correo interno que recibe cada venta
//
// Si no hay proveedor configurado no se envía nada: se registra en el log de la
// función para poder revisarlo en Vercel. Nunca rompe un pedido ya cobrado.
// ============================================================================

const FROM_DEFAULT = "GRANKHA <grankha@roadshop.online>";

const fromAddress = () => process.env.EMAIL_FROM || FROM_DEFAULT;
const replyTo = () => (process.env.EMAIL_REPLY_TO || "").trim();
const bareEmail = (from = "") => String(from).replace(/.*<|>.*/g, "").trim();
const provider = () => (process.env.EMAIL_PROVIDER || "").toLowerCase();

// solo texto: para la alternativa multipart y para que los filtros antispam
// no vean únicamente HTML
const toText = (html = "") =>
  String(html)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|tr|h[1-6]|li|pre)>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

/** ¿Hay correo configurado de verdad? */
// Traduce el error crudo del proveedor a algo que se pueda leer y actuar.
// Lo usan el panel y los logs: un "502" o un JSON de Resend no le dicen nada a
// quien está gestionando pedidos.
function explainEmailError(err) {
  const raw = err == null ? "" : (typeof err === "string" ? err : JSON.stringify(err));
  const s = String(raw).toLowerCase();
  if (!s.trim()) return "Error desconocido del proveedor de correo.";
  if (s.includes("not verified"))
    return "El dominio del remitente aún no está verificado en Resend. Añádelo en " +
      "resend.com/domains y copia los registros DNS a IONOS (guía: docs/RESEND_Y_PANEL.md). " +
      "Ningún pedido se pierde: se guarda igual y puedes reenviarlo desde aquí cuando esté en verde.";
  if (s.includes("only send testing emails") || s.includes("onboarding"))
    return "Resend está en modo de pruebas: con el remitente por defecto solo puede escribir a la " +
      "dirección de tu propia cuenta. Se resuelve verificando el dominio.";
  if (s.includes("invalid api key") || s.includes("unauthorized") || s.includes("401"))
    return "La clave de Resend no es válida o no tiene permiso para enviar. Revísala en Vercel (RESEND_API_KEY).";
  if (s.includes("rate limit") || s.includes("429") || s.includes("too many"))
    return "Resend ha limitado los envíos por exceso de peticiones. Espera un par de minutos y reintenta.";
  if (s.includes("sin proveedor"))
    return "No hay proveedor de correo configurado en Vercel. Falta RESEND_API_KEY (o SMTP_HOST/USER/PASS).";
  return String(raw).slice(0, 400);
}

function mailReady() {
  const p = provider();
  if (p === "resend") return Boolean(process.env.RESEND_API_KEY);
  if (p === "smtp") return Boolean(process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS);
  if (p === "brevo") return Boolean(process.env.BREVO_API_KEY);
  // sin EMAIL_PROVIDER pero con credenciales: se deduce el proveedor
  if (process.env.RESEND_API_KEY) return true;
  if (process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS) return true;
  if (process.env.BREVO_API_KEY) return true;
  return false;
}

async function sendResend(to, subject, html) {
  const payload = { from: fromAddress(), to: [to], subject, html, text: toText(html) };
  if (replyTo()) payload.reply_to = replyTo();
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await r.text();
  if (!r.ok) {
    console.error("Resend", r.status, body.slice(0, 400));
    return { ok: false, error: body.slice(0, 300) };
  }
  let id = "";
  try { id = (JSON.parse(body) || {}).id || ""; } catch {}
  return { ok: true, id };
}

async function sendSmtp(to, subject, html) {
  // Con la configuración a medias (p. ej. host y usuario puestos pero sin contraseña)
  // no se intenta nada: así se pueden pre-rellenar las variables en Vercel sin riesgo.
  if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
    console.log("[smtp incompleto] faltan SMTP_HOST / SMTP_USER / SMTP_PASS ·", to, "·", subject);
    return { ok: false, error: "smtp incompleto" };
  }
  const nodemailer = require("nodemailer");
  const port = Number(process.env.SMTP_PORT || 587);
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port,
    secure: port === 465,
    auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
  });
  const msg = {
    from: process.env.EMAIL_FROM || `"GRANKHA" <${process.env.SMTP_USER}>`,
    to, subject, html, text: toText(html),
  };
  if (replyTo()) msg.replyTo = replyTo();
  const info = await transporter.sendMail(msg);
  return { ok: Boolean(info && (info.accepted || []).length), id: info && info.messageId };
}

async function sendBrevo(to, subject, html) {
  const msg = {
    sender: { name: "GRANKHA", email: bareEmail(fromAddress()) },
    to: [{ email: to }], subject, htmlContent: html, textContent: toText(html),
  };
  if (replyTo()) msg.replyTo = { email: replyTo() };
  const r = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": process.env.BREVO_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify(msg),
  });
  const body = await r.text();
  if (!r.ok) {
    console.error("Brevo", r.status, body.slice(0, 400));
    return { ok: false, error: body.slice(0, 300) };
  }
  return { ok: true };
}

/**
 * Envía un correo. Devuelve { ok, id?, error? }.
 * Nunca lanza: un fallo de correo no puede tirar abajo un pedido cobrado.
 */
async function sendEmail(to, subject, html) {
  if (!to) return { ok: false, error: "sin destinatario" };
  let p = provider();
  if (!p) {
    if (process.env.RESEND_API_KEY) p = "resend";
    else if (process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS) p = "smtp";
    else if (process.env.BREVO_API_KEY) p = "brevo";
  }
  try {
    if (p === "resend" && process.env.RESEND_API_KEY) return await sendResend(to, subject, html);
    if (p === "smtp") return await sendSmtp(to, subject, html);
    if (p === "brevo" && process.env.BREVO_API_KEY) return await sendBrevo(to, subject, html);
  } catch (e) {
    const msg = e && e.message ? e.message : String(e);
    console.error(`email (${p || "sin proveedor"}):`, msg);
    return { ok: false, error: msg.slice(0, 300) };
  }
  console.log("[email sin proveedor configurado]", to, "·", subject);
  return { ok: false, error: "sin proveedor configurado" };
}

module.exports = { sendEmail, mailReady, fromAddress, replyTo, bareEmail, toText, explainEmailError };

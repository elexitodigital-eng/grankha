// ============================================================================
// GRANKHA · api/_lib/mail.js — envío de correo único para todas las funciones
//
// Tres proveedores, se elige con EMAIL_PROVIDER:
//
//   1) smtp    → el buzón de la propia empresa (recomendado para GRANKHA)
//        EMAIL_PROVIDER = smtp
//        SMTP_HOST      = smtp.ionos.es        (el que use roadshop.online)
//        SMTP_PORT      = 587                  (465 también vale)
//        SMTP_USER      = grankha@roadshop.online
//        SMTP_PASS      = contraseña del buzón
//        EMAIL_FROM     = "GRANKHA <grankha@roadshop.online>"
//
//   2) resend  → EMAIL_PROVIDER=resend + RESEND_API_KEY
//   3) brevo   → EMAIL_PROVIDER=brevo  + BREVO_API_KEY
//
// Si no hay proveedor configurado no se envía nada: se registra en el log de
// la función para que se pueda revisar en Vercel. Nunca rompe el pedido.
// ============================================================================

const FROM_DEFAULT = "GRANKHA <grankha@roadshop.online>";

const fromAddress = () => process.env.EMAIL_FROM || FROM_DEFAULT;
const bareEmail = (from = "") => String(from).replace(/.*<|>.*/g, "").trim();
const provider = () => (process.env.EMAIL_PROVIDER || "").toLowerCase();

/** ¿Hay correo configurado de verdad? */
function mailReady() {
  const p = provider();
  if (p === "smtp") return Boolean(process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS);
  if (p === "resend") return Boolean(process.env.RESEND_API_KEY);
  if (p === "brevo") return Boolean(process.env.BREVO_API_KEY);
  // sin EMAIL_PROVIDER pero con credenciales: se deduce el proveedor
  if (process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS) return true;
  if (process.env.RESEND_API_KEY) return true;
  if (process.env.BREVO_API_KEY) return true;
  return false;
}

async function sendSmtp(to, subject, html) {
  // Con la configuración a medias (p. ej. host y usuario puestos pero sin contraseña)
  // no se intenta nada: así se pueden pre-rellenar las variables en Vercel sin riesgo.
  if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
    console.log("[smtp incompleto] faltan SMTP_HOST / SMTP_USER / SMTP_PASS ·", to, "·", subject);
    return false;
  }
  const nodemailer = require("nodemailer");
  const port = Number(process.env.SMTP_PORT || 587);
  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port,
    secure: port === 465,
    auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
  });
  const info = await transporter.sendMail({
    from: process.env.EMAIL_FROM || `"GRANKHA" <${process.env.SMTP_USER}>`,
    to,
    subject,
    html,
    text: String(html).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(),
  });
  return Boolean(info && (info.accepted || []).length);
}

async function sendResend(to, subject, html) {
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: fromAddress(), to: [to], subject, html }),
  });
  if (!r.ok) console.error("Resend", r.status, await r.text());
  return r.ok;
}

async function sendBrevo(to, subject, html) {
  const r = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": process.env.BREVO_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({
      sender: { name: "GRANKHA", email: bareEmail(fromAddress()) },
      to: [{ email: to }],
      subject,
      htmlContent: html,
    }),
  });
  if (!r.ok) console.error("Brevo", r.status, await r.text());
  return r.ok;
}

/**
 * Envía un correo. Devuelve true si salió, false si no hay proveedor o falló.
 * Nunca lanza: un fallo de correo no puede tirar abajo un pedido cobrado.
 */
async function sendEmail(to, subject, html) {
  if (!to) return false;
  let p = provider();
  if (!p) {
    if (process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS) p = "smtp";
    else if (process.env.RESEND_API_KEY) p = "resend";
    else if (process.env.BREVO_API_KEY) p = "brevo";
  }
  try {
    if (p === "smtp") return await sendSmtp(to, subject, html);
    if (p === "resend" && process.env.RESEND_API_KEY) return await sendResend(to, subject, html);
    if (p === "brevo" && process.env.BREVO_API_KEY) return await sendBrevo(to, subject, html);
  } catch (e) {
    console.error(`email (${p || "sin proveedor"}):`, e && e.message ? e.message : e);
  }
  console.log("[email sin proveedor configurado]", to, "·", subject);
  return false;
}

module.exports = { sendEmail, mailReady, fromAddress, bareEmail };

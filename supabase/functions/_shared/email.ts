// ============================================================================
// GRANKHA · _shared/email.ts
// Envío de correos al cliente. Funciona con Brevo (recomendado en España) o
// Resend: basta con definir las claves y elegir el proveedor por variable.
//
//   supabase secrets set EMAIL_PROVIDER=brevo
//   supabase secrets set BREVO_API_KEY=xkeysib-...
//   supabase secrets set EMAIL_FROM="GRANKHA <hola@grankha.com>"
//
//   ... o bien:
//   supabase secrets set EMAIL_PROVIDER=resend
//   supabase secrets set RESEND_API_KEY=re_...
//   supabase secrets set EMAIL_FROM="GRANKHA <hola@grankha.com>"
//
// Si no hay claves configuradas, no falla: escribe el correo en el log de la
// función (modo simulación), para que puedas probar todo el flujo hoy mismo.
// ============================================================================

const FROM = Deno.env.get("EMAIL_FROM") ?? "GRANKHA <onboarding@resend.dev>";
const PROVIDER = (Deno.env.get("EMAIL_PROVIDER") ?? "").toLowerCase();

export type Order = {
  reference: string;
  customer?: { name?: string; email?: string; address?: string; address2?: string; zip?: string; city?: string; phone?: string };
  lines?: Array<{ name?: string; sku?: string; qty?: number; price?: number }>;
  subtotal?: number;
  shipping_price?: number;
  shipping_method?: string;
  total?: number;
  tracking_code?: string;
  tracking_url?: string;
};

const eur = (n = 0) => n.toFixed(2).replace(".", ",") + " €";
const esc = (s = "") => String(s).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]!));

export async function sendEmail(to: string, subject: string, html: string): Promise<boolean> {
  if (!to) return false;
  if (PROVIDER === "brevo" && Deno.env.get("BREVO_API_KEY")) {
    const r = await fetch("https://api.brevo.com/v3/smtp/email", {
      method: "POST",
      headers: { "api-key": Deno.env.get("BREVO_API_KEY")!, "Content-Type": "application/json" },
      body: JSON.stringify({
        sender: { name: "GRANKHA", email: FROM.replace(/.*<|>.*/g, "") },
        to: [{ email: to }], subject, htmlContent: html,
      }),
    });
    if (!r.ok) console.error("Brevo", r.status, await r.text());
    return r.ok;
  }
  if (PROVIDER === "resend" && Deno.env.get("RESEND_API_KEY")) {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${Deno.env.get("RESEND_API_KEY")}`, "Content-Type": "application/json" },
      body: JSON.stringify({ from: FROM, to: [to], subject, html }),
    });
    if (!r.ok) console.error("Resend", r.status, await r.text());
    return r.ok;
  }
  console.log("[simulación de correo] para:", to, "·", subject);
  return false;
}

// ------------------------------------------------------------------ plantilla
function wrap(titulo: string, intro: string, cuerpo: string, pie: string) {
  return `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(titulo)}</title></head>
<body style="margin:0;background:#f4f3f1;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#111">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f3f1;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border:1px solid #e6e5e2">
  <tr><td style="padding:26px 30px 6px">
    <div style="letter-spacing:.34em;font-weight:700;font-size:14px">GRANKHA</div>
    <div style="height:1px;background:#e6e5e2;margin:16px 0 22px"></div>
    <h1 style="margin:0 0 10px;font-size:22px;font-weight:600;letter-spacing:-.01em">${esc(titulo)}</h1>
    <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#444">${intro}</p>
  </td></tr>
  <tr><td style="padding:0 30px">${cuerpo}</td></tr>
  <tr><td style="padding:22px 30px 30px">
    <p style="margin:0;font-size:12.5px;line-height:1.6;color:#777">${pie}</p>
  </td></tr>
</table>
<p style="max-width:600px;margin:14px auto 0;font-size:11.5px;color:#9b9b96;text-align:center;line-height:1.6">
  GRANKHA · Accesorios para perros y gatos · un porcentaje de los beneficios se destina a la investigación del cáncer y las enfermedades raras en mascotas.
</p>
</td></tr></table></body></html>`;
}

function tablaPedido(o: Order) {
  const filas = (o.lines ?? []).map((l) => `<tr>
    <td style="padding:10px 0;border-bottom:1px solid #efeeec;font-size:14px">${esc(l.name ?? "")}<br>
      <span style="color:#8a8a85;font-size:12.5px">${esc(l.sku ?? "")} · ${l.qty ?? 1} ud.</span></td>
    <td align="right" style="padding:10px 0;border-bottom:1px solid #efeeec;font-size:14px;white-space:nowrap">${eur((l.price ?? 0) * (l.qty ?? 1))}</td>
  </tr>`).join("");
  const sub = (o.subtotal ?? 0);
  const env = (o.shipping_price ?? 0);
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #efeeec">
  ${filas}
  <tr><td style="padding:12px 0 4px;font-size:13.5px;color:#555">Subtotal (IVA incluido)</td>
      <td align="right" style="padding:12px 0 4px;font-size:13.5px">${eur(sub)}</td></tr>
  <tr><td style="padding:2px 0;font-size:13.5px;color:#555">Envío${o.shipping_method ? " · " + esc(o.shipping_method) : ""}</td>
      <td align="right" style="padding:2px 0;font-size:13.5px">${env === 0 ? "Gratis" : eur(env)}</td></tr>
  <tr><td style="padding:12px 0 0;font-size:16px;font-weight:700;border-top:1px solid #111">TOTAL</td>
      <td align="right" style="padding:12px 0 0;font-size:16px;font-weight:700;border-top:1px solid #111">${eur(o.total ?? sub + env)}</td></tr>
</table>`;
}

function bloqueEnvio(o: Order) {
  const c = o.customer ?? {};
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f7f7f5;border:1px solid #e9e8e5;margin:18px 0">
  <tr><td style="padding:16px 18px;font-size:13.5px;line-height:1.7;color:#333">
    <b style="font-size:12px;letter-spacing:.12em;color:#777">DIRECCIÓN DE ENVÍO</b><br>
    ${esc(c.name ?? "")}<br>${esc(c.address ?? "")}${c.address2 ? "<br>" + esc(c.address2) : ""}<br>
    ${esc(c.zip ?? "")} ${esc(c.city ?? "")}<br>${c.phone ? "Tel. " + esc(c.phone) : ""}
  </td></tr></table>`;
}

/** Correo 1 · justo después del pago: todos los datos de la compra. */
export function emailPedidoRecibido(o: Order) {
  const cuerpo = `${tablaPedido(o)}${bloqueEnvio(o)}
  <p style="margin:20px 0 0;font-size:14px;line-height:1.7;color:#444">
    Hemos recibido tu pedido <b>${esc(o.reference)}</b> y ya lo estamos preparando con nuestro proveedor en España.
    Te enviaremos <b>otro correo con el número de seguimiento</b> en cuanto salga del almacén.</p>`;
  return {
    subject: `Tu pedido ${o.reference} ya está en marcha · GRANKHA`,
    html: wrap("Pedido recibido", "Gracias por confiar en GRANKHA. Aquí tienes el resumen de tu compra:", cuerpo,
      `¿Alguna duda? Responde a este correo y te contestamos nosotros mismos.<br>
       Devoluciones durante 30 días · Envío con seguimiento · Referencia ${esc(o.reference)}`),
  };
}

/** Correo 2 · cuando el paquete sale del almacén, con el enlace de seguimiento. */
export function emailPedidoEnviado(o: Order) {
  const track = o.tracking_url ?? (o.tracking_code
    ? `https://www.17track.net/es?nums=${encodeURIComponent(o.tracking_code)}`
    : "");
  const cuerpo = `
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#111;margin:0 0 18px">
    <tr><td style="padding:18px 20px;color:#fff">
      <div style="font-size:12px;letter-spacing:.14em;color:#bdbdb8">NÚMERO DE SEGUIMIENTO</div>
      <div style="font-size:20px;font-weight:700;letter-spacing:.04em;margin-top:6px">${esc(o.tracking_code ?? "—")}</div>
      ${track ? `<a href="${track}" style="display:inline-block;margin-top:12px;background:#fff;color:#111;
        text-decoration:none;padding:10px 18px;font-size:13.5px;font-weight:600">Ver dónde está mi pedido</a>` : ""}
    </td></tr></table>
  ${tablaPedido(o)}
  <p style="margin:18px 0 0;font-size:14px;line-height:1.7;color:#444">
    Tu pedido <b>${esc(o.reference)}</b> ya ha salido del almacén. Suele llegar en 1-3 días laborables a península.</p>`;
  return {
    subject: `Tu pedido ${o.reference} ya va de camino · GRANKHA`,
    html: wrap("Tu pedido va de camino", "Ya puedes seguir el envío con este número:", cuerpo,
      `El seguimiento puede tardar unas horas en mostrar movimiento desde que se genera la etiqueta.<br>
       Referencia ${esc(o.reference)} · GRANKHA`),
  };
}

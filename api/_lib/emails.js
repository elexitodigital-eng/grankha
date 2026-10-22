// ============================================================================
// GRANKHA · api/_lib/emails.js — las plantillas de correo de la tienda
//
// Las usan api/stripe-webhook.js (pedido confirmado + aviso de venta) y
// api/tracking.js (envío con seguimiento). Están aquí para que los dos
// endpoints compartan exactly el mismo diseño y los mismos datos.
//
//   orderEmail(o)    → al cliente cuando Stripe confirma el cobro
//   saleEmail(o)     → a ti: margen, reserva interna y datos para pasar a AW
//   shippingEmail(o) → al cliente cuando el paquete sale, con seguimiento
// ============================================================================

const PRICES = require("./prices.json");
const COSTS = PRICES.costs || {};
// Costes fijos por pedido: comisión de la pasarela y embalaje. Sin ellos el
// margen que se informa sería mayor que el dinero que realmente queda.
const META = PRICES.meta || {};
const STRIPE_PCT = Number(META.stripe_pct || 0.015);
const STRIPE_FIX = Number(META.stripe_fix || 0.25);
const PACKAGING = Number(META.packaging_per_order || 0);
const round2 = (n) => Math.round(Number(n || 0) * 100) / 100;
const SITE = process.env.SITE_URL || "https://grankha.roadshop.online";
const DELIVERY = process.env.DELIVERY_DAYS || "3-8";
const MAIL = process.env.EMAIL_REPLY_TO || process.env.EMAIL_AVISO || "grankha@roadshop.online";
const PROVEEDOR = process.env.SUPPLIER_NAME || "AW Dropshipping";
const MARCA = process.env.SITE_NAME || "GRANKHA";

const eur = (n = 0) => Number(n || 0).toFixed(2).replace(".", ",") + " €";
const esc = (s = "") => String(s == null ? "" : s).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

// cabecera y pie comunes: mismos colores que la web (#0B0B0B sobre #F5F5F4)
const wrap = (inner) => `
<div style="background:#F5F5F4;padding:26px 12px;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto">
    <tr><td style="background:#0B0B0B;padding:18px 26px">
      <span style="color:#fff;font-size:13px;letter-spacing:7px;font-weight:600">${esc(MARCA)}</span>
    </td></tr>
    <tr><td style="background:#fff;border:1px solid #E3E3E1;border-top:0;padding:28px 26px;color:#111">
      ${inner}
    </td></tr>
    <tr><td style="padding:16px 26px;color:#7a7a78;font-size:12px;line-height:1.6">
      ${esc(MARCA)} · <a href="${esc(SITE)}" style="color:#7a7a78">${esc(SITE.replace(/^https?:\/\//, ""))}</a><br>
      En memoria de Khalid · un porcentaje de los beneficios va destinado a la investigación del
      cáncer y las enfermedades raras en mascotas.
    </td></tr>
  </table>
</div>`;

const addressBlock = (c) =>
  `${esc(c.name || "")}<br>${esc([c.address, c.address2].filter(Boolean).join(", "))}<br>` +
  `${esc(c.zip || "")} ${esc(c.city || "")}<br>${esc(c.province || "")} · ${esc(c.country || "")}`;

// --------------------------------------------------------------------------
// EMAIL PARA EL CLIENTE · pedido confirmado y pagado
// --------------------------------------------------------------------------
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
    <p><b>Cuándo te llega:</b> estimamos la entrega en ${esc(DELIVERY)} días laborables. Trabajamos con envío
       directo junto a nuestro proveedor logístico, así que el paquete sale de su almacén hacia tu casa sin pasos
       intermedios. En cuanto salga te escribimos con el número de seguimiento y el enlace del transportista.</p>
    <p style="color:#555">Dispones de <b>30 días</b> para devolverlo sin justificar el motivo. Cualquier duda con
       el envío, la garantía o una devolución, escríbenos a
       <a href="mailto:${esc(MAIL)}" style="color:#111">${esc(MAIL)}</a> indicando tu número de pedido
       <b>${esc(o.reference)}</b>: GRANKHA es tu único interlocutor y lo gestionamos nosotros.</p>
    <p style="color:#555;font-size:13px">GRANKHA · <a href="${esc(SITE)}" style="color:#555">${esc(SITE.replace(/^https?:\/\//, ""))}</a><br>
       En memoria de Khalid · un porcentaje de los beneficios va destinado a la investigación del cáncer
       y las enfermedades raras en mascotas.</p>
  </div>`;
  return { subject: `Pedido ${o.reference} confirmado · GRANKHA`, html };
}

// --------------------------------------------------------------------------
// EMAIL INTERNO · aviso de venta para ti (NO es el correo del cliente)
// Incluye margen, reserva para investigación y el bloque listo para pasar a
// AW Dropshipping, porque hoy el envío al proveedor se hace a mano.
// --------------------------------------------------------------------------
function saleEmail(o) {
  const c = o.customer || {};
  const items = o.order_items || [];

  const filas = items.map((l) => {
    const unit = Number(l.unit_price) * l.qty;
    const cost = (COSTS[l.sku] || 0) * l.qty;
    return `<tr>
      <td style="padding:5px 0;font-family:monospace">${esc(l.sku || "—")}</td>
      <td style="padding:5px 0">${esc(l.qty)} × ${esc(l.name)}</td>
      <td align="right" style="padding:5px 0">${eur(unit)}</td>
      <td align="right" style="padding:5px 0;color:#8a2020">${eur(cost)}</td>
      <td align="right" style="padding:5px 0"><b>${eur(unit - cost)}</b></td>
    </tr>`;
  }).join("");

  const cogs = items.reduce((a, l) => a + (COSTS[l.sku] || 0) * l.qty, 0);
  const subtotal = Number(o.subtotal || 0);
  const iva = Number(o.vat_included || 0);
  const envio = Number(o.shipping_price || 0);
  const base = subtotal - iva;                    // venta sin IVA
  const bruto = base - cogs;                      // venta sin IVA − proveedor
  const reserva = Number(o.donation || 0);

  // La pasarela cobra sobre el total cargado (IVA y envío incluidos), no sobre
  // la base: calcularlo sobre `base` subestimaría la comisión.
  const stripeFee = round2(Number(o.total || 0) * STRIPE_PCT + STRIPE_FIX);
  const neto = round2(bruto - stripeFee - PACKAGING);

  // bloque para copiar y pegar en el panel del proveedor
  const aw = items.map((l) => `  ${l.qty} × ${l.sku || "—"}  ${l.name}`).join("\n");
  const awTexto = [
    `PEDIDO GRANKHA ${o.reference}`,
    `Destinatario: ${c.name || ""}`,
    `Dirección: ${[c.address, c.address2].filter(Boolean).join(" · ")}, ${c.zip || ""} ${c.city || ""}, ${c.province || ""} ${c.country || ""}`,
    `Teléfono: ${c.phone || "—"}`,
    `Email: ${c.email || "—"}`,
    `Artículos:`,
    aw,
    `Método de envío: ${o.shipping_method || "—"}`,
  ].join("\n");

  const html = `
  <div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:640px;margin:0 auto;color:#111">
    <h2 style="letter-spacing:-.02em;margin-bottom:4px">Venta nueva · ${esc(o.reference)}</h2>
    <p style="margin-top:0;color:#555">Cobrada por Stripe. Hay que pasarla a ${esc(PROVEEDOR)}.</p>

    <table style="width:100%;border-collapse:collapse;font-size:14px;margin:14px 0">
      <tr style="border-bottom:2px solid #111">
        <th align="left" style="padding:6px 0">SKU</th><th align="left" style="padding:6px 0">Artículo</th>
        <th align="right" style="padding:6px 0">Venta</th><th align="right" style="padding:6px 0">Coste</th>
        <th align="right" style="padding:6px 0">Margen</th>
      </tr>
      ${filas}
    </table>

    <table style="width:100%;border-collapse:collapse;font-size:14px;border-top:1px solid #e5e5e3;margin-bottom:18px">
      <tr><td style="padding:4px 0">Venta sin IVA</td><td align="right">${eur(base)}</td></tr>
      <tr><td style="padding:4px 0">IVA repercutido (21 %)</td><td align="right">${eur(iva)}</td></tr>
      <tr><td style="padding:4px 0">Coste del proveedor</td><td align="right" style="color:#8a2020">− ${eur(cogs)}</td></tr>
      <tr><td style="padding:4px 0">Envío cobrado al cliente</td><td align="right">${envio === 0 ? "Gratis" : eur(envio)}</td></tr>
      <tr><td style="padding:4px 0"><b>Beneficio bruto</b> (venta sin IVA − proveedor)</td><td align="right"><b>${eur(bruto)}</b></td></tr>
      <tr><td style="padding:4px 0">Comisión de Stripe (${(STRIPE_PCT * 100).toFixed(1).replace(".", ",")} % + ${eur(STRIPE_FIX)})</td>
          <td align="right" style="color:#8a2020">− ${eur(stripeFee)}</td></tr>
      <tr><td style="padding:4px 0">Embalaje</td><td align="right" style="color:#8a2020">− ${eur(PACKAGING)}</td></tr>
      <tr style="background:#f0f8f2"><td style="padding:6px 0"><b>Beneficio neto estimado</b></td>
          <td align="right" style="padding:6px 0"><b>${eur(neto)}</b></td></tr>
      <tr><td style="padding:4px 0">Reserva para investigación (interna)</td><td align="right">${eur(reserva)}</td></tr>
      <tr style="border-top:2px solid #111"><td style="padding:8px 0"><b>Total cobrado</b></td>
          <td align="right" style="padding:8px 0"><b>${eur(o.total)}</b></td></tr>
    </table>

    <p style="font-size:13px;color:#555"><b>El neto aún no descuenta el coste real del envío</b> cuando sale gratis
    (lo asume la tienda) ni las devoluciones. Es decir: es lo que queda del producto, no la caja final del mes.
    Importes de coste y comisiones en <code>api/_lib/prices.json</code>.</p>

    <h3 style="margin:22px 0 6px;font-size:15px">Datos para pasar a ${esc(PROVEEDOR)}</h3>
    <pre style="background:#f5f5f4;border:1px solid #e3e3e1;padding:14px;font-size:12.5px;line-height:1.55;overflow:auto;white-space:pre-wrap">${esc(awTexto)}</pre>

    <p style="color:#555;font-size:13px">Cliente: <b>${esc(c.name || "")}</b> · ${esc(c.email || "")}${c.phone ? " · " + esc(c.phone) : ""}<br>
    Cuando lo envíes, recuerda mandar el seguimiento al cliente: el correo de confirmación le promete
    el número de seguimiento en cuanto el paquete salga.</p>
  </div>`;
  return { subject: `[VENTA] ${o.reference} · ${eur(o.total)} · neto ${eur(neto)} · pasar a ${PROVEEDOR}`, html };
}

function send(res, status, body) {
  res.statusCode = status;
  if (body !== undefined) res.setHeader("Content-Type", "application/json");
  res.end(body === undefined ? "" : JSON.stringify(body));
}

// --------------------------------------------------------------------------
// EMAIL PARA EL CLIENTE · el paquete ya va camino de casa, con seguimiento
// --------------------------------------------------------------------------
function shippingEmail(o) {
  const c = o.customer || {};
  const code = o.tracking_code || "";
  const url = o.tracking_url || "";
  const carrier = o.tracking_carrier || "";

  const boton = url
    ? `<p style="margin:22px 0 6px"><a href="${esc(url)}"
         style="background:#0B0B0B;color:#fff;text-decoration:none;padding:13px 24px;
                display:inline-block;font-size:14.5px;letter-spacing:.02em">Seguir mi pedido</a></p>`
    : "";

  const seguimiento = code
    ? `<p style="margin:14px 0 0"><b>Número de seguimiento</b><br>
         <span style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:15px;
                      background:#F5F5F4;border:1px solid #E3E3E1;padding:6px 10px;
                      display:inline-block;margin-top:6px">${esc(code)}</span>
         ${carrier ? `<br><span style="color:#555;font-size:13px">Transportista: ${esc(carrier)}</span>` : ""}
       </p>`
    : "";

  const inner = `
    <p style="margin:0 0 6px;font-size:11px;letter-spacing:3px;color:#8A8A88;text-transform:uppercase">
      Pedido ${esc(o.reference)} · enviado</p>
    <h2 style="margin:0 0 14px;font-size:24px;font-weight:500;letter-spacing:-.4px;color:#0B0B0B">
      Tu pedido ya va camino de casa, ${esc((c.name || "").split(" ")[0])}.</h2>
    <p style="margin:0 0 4px;color:#5E5E5C;line-height:1.7;font-size:15px">
      Ha salido del almacén de nuestro proveedor logístico y va directo a tu dirección.
      ${esc(o.tracking_eta || `Llegará en unos ${DELIVERY} días laborables.`)}</p>
    ${seguimiento}
    ${boton}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border-top:1px solid #E3E3E1;border-bottom:1px solid #E3E3E1;margin:22px 0;font-size:14px">
      ${(o.order_items || []).map((l) => `<tr><td style="padding:6px 0">${esc(l.qty)} × ${esc(l.name)}</td></tr>`).join("")}
      <tr><td style="padding:10px 0;border-top:1px solid #E3E3E1"><b>Total pagado</b>
          <span style="float:right">${eur(o.total)}</span></td></tr>
    </table>
    <p style="margin:0;font-size:14px;color:#5E5E5C"><b>Se entrega en</b><br>${addressBlock(c)}</p>
    <p style="margin:18px 0 0;color:#555;font-size:13.5px;line-height:1.65">
      Si cuando llegue algo no encaja, tienes <b>30 días</b> para devolverlo sin dar explicaciones.
      Escríbenos a <a href="mailto:${esc(MAIL)}" style="color:#111">${esc(MAIL)}</a> indicando tu número
      de pedido <b>${esc(o.reference)}</b>. ${esc(MARCA)} es tu único interlocutor: lo gestionamos nosotros.</p>`;

  return { subject: `Tu pedido ${o.reference} ya está en camino · ${MARCA}`, html: wrap(inner) };
}

module.exports = { orderEmail, saleEmail, shippingEmail, wrap, addressBlock, eur, esc,
                   SITE, DELIVERY, MAIL, PROVEEDOR, MARCA, COSTS };

// ============================================================================
// GRANKHA · api/_lib/gforms.js — entrega de formularios desde el servidor
//
// El navegador habla SIEMPRE con /api/* de esta misma web. Quien contacta con
// el destino final es este módulo, en el servidor: el cliente no ve ninguna
// URL, iframe ni redirección de un servicio de terceros.
//
// DETALLE IMPORTANTE sobre cómo confirmar el éxito:
// Google responde de dos formas distintas según el formulario y la época:
//   · 302/303 a su página de confirmación  (comportamiento clásico)
//   · 200 con el HTML de confirmación      (comportamiento actual)
// Fiarse solo del 302 hace que un envío correcto se reporte como fallo, y al
// revés: un 200 puede ser también "te devuelvo el formulario porque falta un
// campo obligatorio". Por eso no se mira el código de estado, se mira el TEXTO:
// solo hay éxito si aparece el marcador de respuesta registrada.
// ============================================================================

const TIMEOUT_MS = 12000;

// Marcadores de éxito en los dos idiomas en que Google puede responder.
const EXITO = [
  /your response has been recorded/i,
  /tu respuesta se (ha )?registr/i,
  /respuesta registrada/i,
  /responseConfirmation/i,
];
// Marcadores de rechazo explícito.
const FALLO = [
  /this is a required question/i,
  /debes responder esta pregunta/i,
  /unusual traffic/i,
  /no es una página válida/i,
];

function registrada(html) {
  return EXITO.some((re) => re.test(html));
}
function rechazada(html) {
  return FALLO.some((re) => re.test(html));
}

async function enviar(formId, entradas) {
  const body = new URLSearchParams();
  for (const [k, v] of Object.entries(entradas)) {
    if (v !== undefined && v !== null && String(v).length) body.set(k, String(v));
  }
  // fvv/pageHistory/submit son los parámetros que añade el propio navegador de
  // Google al enviar; incluirlos evita rechazos por validación de contexto.
  body.set("fvv", "1");
  body.set("pageHistory", "0");
  body.set("submit", "Submit");

  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(`https://docs.google.com/forms/d/e/${formId}/formResponse`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (compatible; GRANKHA-web/1.0)",
      },
      body: body.toString(),
      redirect: "manual",   // el 302 ES un acuse: no hay que seguirlo
      signal: ctl.signal,
    });

    if (r.status === 302 || r.status === 303) return { ok: true, status: r.status };

    const html = await r.text();
    if (registrada(html)) return { ok: true, status: r.status };
    return {
      ok: false,
      status: r.status,
      error: rechazada(html) ? "campo obligatorio sin rellenar" : "el destino no confirmó la entrega",
    };
  } catch (e) {
    return { ok: false, status: 0, error: (e && e.message) || String(e) };
  } finally {
    clearTimeout(t);
  }
}

module.exports = { enviar, registrada, rechazada };

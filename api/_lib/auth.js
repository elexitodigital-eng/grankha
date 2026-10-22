// ============================================================================
// GRANKHA · api/_lib/auth.js — credencial del panel interno
//
// Compartida por /api/panel (la interfaz) y /api/admin (los datos).
//
// Cómo se entra:
//   1. Primera vez: /api/panel?token=<ADMIN_TOKEN>
//      → se fija una cookie HttpOnly y se redirige a /api/panel, para que el
//        token no quede en el historial, en la barra de direcciones ni en los
//        logs del navegador.
//   2. Después: la cookie sola. Nada de localStorage ni de token en el HTML.
//
// Sin credencial válida ambas rutas devuelven 404 con el mismo cuerpo que
// cualquier otra URL inexistente: desde fuera no se distingue que haya un
// panel, ni se puede sondear el token (no hay diferencia entre "falta" y
// "es incorrecto").
// ============================================================================

const TOKEN = process.env.ADMIN_TOKEN || "";
const COOKIE_NAME = "grankha_panel";
const COOKIE_MAX_AGE = 60 * 60 * 8; // 8 h de sesión

// Comparación en tiempo constante: no filtra el token carácter a carácter.
function tokenOk(dado) {
  const a = Buffer.from(String(dado == null ? "" : dado));
  const b = Buffer.from(TOKEN);
  if (!TOKEN || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

function cookieValue(req) {
  const raw = req && req.headers && req.headers.cookie;
  if (!raw) return "";
  for (const part of String(raw).split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    if (part.slice(0, i).trim() === COOKIE_NAME) {
      try { return decodeURIComponent(part.slice(i + 1).trim()); } catch { return ""; }
    }
  }
  return "";
}

// Acepta la credencial por cookie (uso normal), por ?token= (primer acceso)
// o por el cuerpo del POST (compatibilidad con llamadas manuales).
function autorizado(req, url, body) {
  if (tokenOk(cookieValue(req))) return { ok: true, via: "cookie" };
  const q = url && url.searchParams ? url.searchParams.get("token") : "";
  if (tokenOk(q)) return { ok: true, via: "query", token: q };
  if (body && tokenOk(body.token)) return { ok: true, via: "body" };
  return { ok: false };
}

// 404 byte a byte idéntico al que devuelve Vercel para una ruta /api/ que no
// existe: mismo content-type, mismo cuerpo en tres líneas con el id de
// petición, y ninguna cabecera extra. Si añadimos algo (un X-Robots-Tag, un
// JSON) la ruta se vuelve distinguible y delata que ahí hay un panel.
function noExiste(req, res) {
  const id = (req && req.headers && req.headers["x-vercel-id"]) || "";
  res.statusCode = 404;
  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(`The page could not be found\n\nNOT_FOUND\n\n${id}\n`);
}

function setCookie(value, maxAge) {
  return `${COOKIE_NAME}=${encodeURIComponent(value)}; Path=/api; HttpOnly; Secure; ` +
    `SameSite=Strict; Max-Age=${maxAge}`;
}

module.exports = { TOKEN, COOKIE_NAME, COOKIE_MAX_AGE, tokenOk, autorizado, setCookie, noExiste };

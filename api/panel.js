// ============================================================================
// GRANKHA · /api/panel — interfaz del panel interno de pedidos
//
// NO es una página pública. Sin credencial válida devuelve exactamente el
// mismo 404 que cualquier otra URL inexistente del proyecto, así que desde
// fuera no se puede distinguir que aquí haya un panel ni sondear el token.
//
//   /api/panel?token=<ADMIN_TOKEN>  → fija cookie HttpOnly y redirige a
//                                     /api/panel (el token no queda en la
//                                     barra, en el historial ni en logs)
//   /api/panel                      → sirve la interfaz si la cookie es válida
//   /api/panel?logout=1             → borra la cookie
//
// El HTML vive en api/_lib/panel-html.js, incrustado en el bundle: no hay
// ningún fichero .html suelto que Vercel pueda servir como estático.
// ============================================================================
const { autorizado, setCookie, noExiste, TOKEN, COOKIE_MAX_AGE } = require("./_lib/auth");
const HTML = require("./_lib/panel-html");

module.exports = (req, res) => {
  // Sin token configurado no hay panel que servir: 404, no un 500 que delate.
  if (!TOKEN) return noExiste(req, res);
  if (req.method !== "GET" && req.method !== "HEAD") return noExiste(req, res);

  const u = new URL(req.url, "http://x");

  if (u.searchParams.get("logout")) {
    res.setHeader("Set-Cookie", setCookie("", 0));
    return noExiste(req, res);
  }

  const auth = autorizado(req, u, null);
  if (!auth.ok) return noExiste(req, res);

  // Primer acceso con ?token=…: se fija la cookie y se limpia la URL.
  if (auth.via === "query") {
    res.setHeader("Set-Cookie", setCookie(auth.token, COOKIE_MAX_AGE));
    res.statusCode = 302;
    res.setHeader("Location", "/api/panel");
    res.setHeader("Cache-Control", "no-store");
    return res.end("");
  }

  res.statusCode = 200;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("X-Frame-Options", "DENY");
  res.end(req.method === "HEAD" ? "" : HTML);
};

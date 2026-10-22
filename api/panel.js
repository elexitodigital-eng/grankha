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

// Página de cierre de sesión. Mismas fuentes y paleta que el panel para que no
// parezca otra web. Solo la ve quien traía una sesión válida: si no, se sirve
// el 404 estándar y nadie aprende nada probando ?logout=1 a ciegas.
const SESION_CERRADA = `<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>Sesión cerrada · GRANKHA</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#F5F5F4;color:#0B0B0B;padding:24px;box-sizing:border-box;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.c{max-width:430px;width:100%;background:#fff;border:1px solid #E3E3E1;
border-radius:14px;padding:32px 28px;text-align:center;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.m{width:44px;height:44px;margin:0 auto 18px;border-radius:50%;background:#f0f8f2;
border:1px solid #bcd8c4;display:flex;align-items:center;justify-content:center}
.m svg{width:20px;height:20px;stroke:#1c6b3c;fill:none;stroke-width:2;
stroke-linecap:round;stroke-linejoin:round}
h1{margin:0 0 8px;font-size:19px;font-weight:600;letter-spacing:-.01em}
p{margin:0 0 22px;color:#6b6b68;font-size:14px}
a{display:inline-block;padding:10px 20px;border-radius:9px;background:#0B0B0B;
color:#fff;text-decoration:none;font-size:14px;font-weight:500}
a:hover{background:#1c6b3c}
</style></head>
<body><div class="c">
<div class="m"><svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg></div>
<h1>Sesión cerrada</h1>
<p>El panel se ha cerrado en este navegador. Para volver a entrar, abre de nuevo
el enlace con tu token.</p>
<a href="/">Ir a la tienda</a>
</div></body></html>`;

module.exports = (req, res) => {
  // Sin token configurado no hay panel que servir: 404, no un 500 que delate.
  if (!TOKEN) return noExiste(req, res);
  if (req.method !== "GET" && req.method !== "HEAD") return noExiste(req, res);

  const u = new URL(req.url, "http://x");

  if (u.searchParams.get("logout")) {
    const auth = autorizado(req, u, null);
    // Sin credencial válida, 404 pelado y SIN cabeceras. Si aquí enviáramos el
    // Set-Cookie que borra la sesión, el nombre "grankha_panel" en la respuesta
    // delataría que existe un panel justo en esta ruta, y se perdería todo el
    // trabajo de hacer el 404 indistinguible del de Vercel.
    // Quien no tiene sesión no tiene cookie que borrar: no se le envía nada.
    if (!auth.ok) return noExiste(req, res);
    res.setHeader("Set-Cookie", setCookie("", 0));
    res.statusCode = 200;
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet");
    res.setHeader("Referrer-Policy", "no-referrer");
    return res.end(req.method === "HEAD" ? "" : SESION_CERRADA);
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · build.py
Genera el sitio estático completo (HTML autocontenido) en la raíz del repo.

Páginas generadas:
  index.html · tienda.html · carrito.html · compromiso.html · envios.html
  contacto.html · legal.html · 404.html · producto.html (redirección)
  <slug>.html × 38 (una ficha por producto, con datos estructurados)
  sitemap.xml · robots.txt · .nojekyll

Las páginas son autocontenidas (CSS, JS e imágenes en línea) para que se vean
igual en GitHub Pages, en el navegador y en cualquier previsualización sin red.

Uso:  python3 tools/build.py
"""
import base64, html, io, json, re, shutil
from pathlib import Path
from datetime import date
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "assets" / "img"

PRODUCTS = json.loads((ROOT / "data" / "products.json").read_text())
SITE = json.loads((ROOT / "data" / "site.json").read_text())
CSS = (ROOT / "src" / "styles.css").read_text()
JS = (ROOT / "src" / "app.js").read_text().replace("</", "<\\/")

BASE = SITE["url"].rstrip("/")
CATS = [
    ("arneses", "Arneses", "Arneses de paso con malla reflectante"),
    ("correas", "Correas", "Correas retráctiles y de paseo"),
    ("camas", "Camas", "Camas y refugios para descansar"),
    ("comederos", "Comederos y fuentes", "Acero inoxidable, madera y fuentes"),
]
DESTACADOS = ["PAWH-01", "PAWH-03", "PawL-01", "PawL-05", "PawB-10", "PAWFB-04", "PAWFB-08", "PawB-07"]
TAG_BY_CAT = {"arneses": "Malla reflectante", "correas": "Uso diario", "camas": "Lavable",
              "comederos": "Acero inox."}
RETURNS = SITE.get("returns_days", 30)

# --------------------------------------------------------------------- utils
def esc(t):
    return html.escape(str(t if t is not None else ""), quote=True)

def eur(n):
    s = f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"

def data_uri(path: Path, max_w=1600, quality=82):
    im = Image.open(path)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if path.suffix.lower() in (".jpg", ".jpeg"):
        im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        im.save(buf, "WEBP", quality=quality, method=6)
        mime = "image/webp"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()

def webp_uri(path: Path):
    return "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode()

print("· cargando imágenes…")
THUMB = {p["slug"]: webp_uri(IMG_DIR / "thumbs" / f'{p["slug"]}.webp') for p in PRODUCTS}
PHOTO = {p["slug"]: webp_uri(IMG_DIR / "products" / p["img"]) for p in PRODUCTS}
HERO = data_uri(IMG_DIR / "hero.jpg", 1500, 80)
MEMORIAL = data_uri(IMG_DIR / "memorial.jpg", 1000, 80)

by_sku = {p["sku"]: p for p in PRODUCTS}
order_rank = {p["slug"]: i for i, p in enumerate(PRODUCTS)}
for i, sku in enumerate(DESTACADOS):
    order_rank[by_sku[sku]["slug"]] = -100 + i          # primero los destacados

LITE = [{"slug": p["slug"], "title": p["title"], "subtitle": p["subtitle"], "sku": p["sku"],
         "cat": p["cat"], "price": p["price"], "stock": p["stock"], "weight_g": p["weight_g"],
         "url": p["slug"] + ".html"} for p in PRODUCTS]
FULL = [dict(x, thumb=THUMB[x["slug"]], colorHex=by_sku[x["sku"]]["colorHex"]) for x in LITE]
CFG = {"name": SITE["name"], "contactEmail": SITE["contactEmail"], "shipping": SITE["shipping"],
       "checkout": {"endpoint": SITE["checkout"]["endpoint"]}, "currency": SITE["currency"],
       "returns": RETURNS}

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' fill='%230B0B0B'/%3E%3Ctext x='32' y='45' font-family="
           "'Helvetica,Arial,sans-serif' font-size='38' font-weight='600' fill='white' "
           "text-anchor='middle'%3EG%3C/text%3E%3C/svg%3E")

SVG = {
    "cart": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h2.2l2.1 10.3a2 2 0 0 0 2 1.7h7.9a2 2 0 0 0 2-1.6L21 8H6.2"/><circle cx="10" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h18M3 12h18M3 17h18"/></svg>',
    "truck": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h11v9H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="1.6"/><circle cx="17.5" cy="18" r="1.6"/></svg>',
    "return": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6z"/><path d="M9.2 12.2l2 2 3.6-3.9"/></svg>',
    "heart": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-9.3A4 4 0 0 1 12 8a4 4 0 0 1 7 2.7C19 15.6 12 20 12 20z"/></svg>',
    "ribbon": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c3.3 0 6 2.5 6 5.6 0 4-3.4 6.6-4.6 10.4h-2.8C9.4 15.2 6 12.6 6 8.6 6 5.5 8.7 3 12 3z"/><path d="M9.5 8.5l5 5M14.5 8.5l-5 5"/></svg>',
    "paw": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="7" cy="9" r="1.8"/><circle cx="12" cy="6.6" r="1.8"/><circle cx="17" cy="9" r="1.8"/><path d="M12 11.4c3 0 5.2 2 5.2 4.3 0 1.9-1.6 3.1-3.4 2.6-1.2-.3-2.4-.3-3.6 0-1.8.5-3.4-.7-3.4-2.6 0-2.3 2.2-4.3 5.2-4.3z"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10.5" width="14" height="9.5" rx="1.6"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/></svg>',
    "plus": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
}

def cat_count(cat):
    return sum(1 for p in PRODUCTS if p["cat"] == cat)

# ------------------------------------------------------------------ esqueleto
def head(title, desc, path, og="assets/img/hero.jpg", og_type="website", jsonld=None):
    img = og if og.startswith("http") else f"{BASE}/{og}"
    j = ""
    if jsonld:
        j = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + "</script>"
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#0B0B0B">
<script>document.documentElement.className+=" js";</script>
<link rel="canonical" href="{BASE}/{path}">
<link rel="icon" href="{FAVICON}">
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:locale" content="es_ES">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{BASE}/{path}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
{j}
<style>{CSS}</style>
</head>
<body>"""

def header(active=""):
    def a(href, txt, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur}>{txt}</a>'
    nav = "".join([
        a("tienda.html", "Tienda", "tienda"),
        a("tienda.html?cat=arneses", "Arneses", "arneses"),
        a("tienda.html?cat=correas", "Correas", "correas"),
        a("tienda.html?cat=camas", "Camas", "camas"),
        a("tienda.html?cat=comederos", "Comederos", "comederos"),
        a("compromiso.html", "Compromiso", "compromiso"),
    ])
    return f"""<div class="announce">Envío gratis en península desde {eur(SITE['shipping']['freeFromPeninsular'])} · Devoluciones {RETURNS} días · <a href="envios.html">Ver condiciones</a></div>
<header class="site-head">
  <div class="wrap site-head__in">
    <a class="wordmark" href="index.html" aria-label="GRANKHA, inicio">GRANKHA</a>
    <nav class="nav" aria-label="Navegación principal">{nav}</nav>
    <div class="head-actions">
      <a class="icon-btn" href="carrito.html" aria-label="Ver carrito">
        {SVG['cart']}<span class="cart-count hide" data-cart-count>0</span>
      </a>
      <button class="icon-btn menu-btn" id="menu-btn" aria-label="Abrir menú">{SVG['menu']}</button>
    </div>
  </div>
</header>"""

def footer():
    cats = "".join(f'<li><a href="tienda.html?cat={c}">{n}</a></li>' for c, n, _ in CATS)
    return f"""<footer class="footer">
  <div class="wrap">
    <div class="footer__cols">
      <div>
        <a class="wordmark" href="index.html" style="color:#fff">GRANKHA</a>
        <p class="footer__brand">Accesorios esenciales para mascotas, con una promesa: un porcentaje de cada compra financia la investigación del cáncer y las enfermedades raras en animales. En memoria de khalid.</p>
        <div class="pays"><span>Visa</span><span>Mastercard</span><span>Apple Pay</span><span>Google Pay</span><span>Pago seguro</span></div>
      </div>
      <div><h4>Tienda</h4><ul>{cats}<li><a href="tienda.html">Ver todo</a></li></ul></div>
      <div><h4>Ayuda</h4><ul>
        <li><a href="envios.html">Envíos y devoluciones</a></li>
        <li><a href="envios.html#faq">Preguntas frecuentes</a></li>
        <li><a href="contacto.html">Contacto</a></li>
        <li><a href="compromiso.html">Compromiso y corazón</a></li>
      </ul></div>
      <div><h4>Legal</h4><ul>
        <li><a href="legal.html#aviso">Aviso legal</a></li>
        <li><a href="legal.html#privacidad">Privacidad</a></li>
        <li><a href="legal.html#cookies">Cookies</a></li>
        <li><a href="legal.html#condiciones">Condiciones de venta</a></li>
      </ul></div>
    </div>
    <div class="footer__base">
      <span>© <span data-year>2026</span> {esc(SITE['name'])} · {esc(SITE['legal_name'])} · Todos los derechos reservados</span>
      <span>{esc(SITE['contactEmail'])} · Envíos desde 3 días laborables</span>
    </div>
  </div>
</footer>"""

def card(p, rank=None):
    href = p["slug"] + ".html"
    tag = TAG_BY_CAT[p["cat"]]
    if rank is not None and rank < 0:
        tag = "Más vendido"
    return f"""<article class="card" data-cat="{p['cat']}" data-price="{p['price']:.2f}" data-rank="{order_rank[p['slug']]}" data-search="{esc(p['title'] + ' ' + p['subtitle'] + ' ' + p['collection'] + ' ' + p['catName'])}">
  <a class="card__media" href="{href}" tabindex="-1" aria-hidden="true">
    <span class="card__tags"><span class="tag{' tag--dark' if rank is not None and rank < 0 else ''}">{tag}</span></span>
    <img src="{THUMB[p['slug']]}" alt="{esc(p['title'] + ' — ' + p['subtitle'])}" width="380" height="380" loading="lazy" decoding="async">
  </a>
  <div class="card__body">
    <span class="card__col">{esc(p['catName'])} · {esc(p['collection'])}</span>
    <a class="card__title" href="{href}">{esc(p['title'])}</a>
    <span class="card__sub"><span class="swatch" style="background:{p['colorHex']}"></span>{esc(p['subtitle'])}</span>
    <div class="card__foot">
      <span class="price">{eur(p['price'])}<small>IVA incl.</small></span>
      <button class="mini-add" data-add="{p['slug']}" aria-label="Añadir {esc(p['title'])} al carrito">{SVG['plus']}</button>
    </div>
  </div>
</article>"""

def products_grid(items, ranks=None):
    return '<div class="products">' + "".join(
        card(p, rank=(ranks or {}).get(p["slug"])) for p in items) + "</div>"

def tail(inject=("lite", "cfg"), full=False):
    cfg = json.dumps(CFG, ensure_ascii=False)
    lite = json.dumps(LITE, ensure_ascii=False)
    f = f"window.GRANKHA_CATALOG_FULL={json.dumps(FULL, ensure_ascii=False)};" if full else ""
    return f"""<div id="toast" class="toast" role="status" aria-live="polite"><span data-toast-msg></span><a data-toast-link href="#"></a></div>
<script>window.GRANKHA_CONFIG={cfg};window.GRANKHA_CATALOG={lite};{f}</script>
<script>{JS}</script>
</body></html>"""

def write(name, content):
    (ROOT / name).write_text(content, encoding="utf-8")
    size = len(content.encode()) / 1024
    print(f"  · {name:38s} {size:7.1f} KB")

# ------------------------------------------------------------------ index
def build_index():
    featured = [by_sku[s] for s in DESTACADOS]
    ranks = {p["slug"]: i for i, p in enumerate(featured)}
    tiles = ""
    for c, name, sub in CATS:
        rep = next(p for p in PRODUCTS if p["cat"] == c)
        tiles += f"""<a class="cat-tile" href="tienda.html?cat={c}">
  <img src="{THUMB[rep['slug']]}" alt="{esc(name)}" width="600" height="750" loading="lazy" decoding="async">
  <span class="cat-tile__cap"><b>{esc(name)}</b><span>{cat_count(c)} productos · {esc(sub)}</span></span>
</a>"""
    body = f"""{header("inicio")}
<main>
  <section class="hero">
    <div class="wrap hero__in">
      <div class="hero__copy">
        <p class="kicker">Colección PAW · Nueva temporada</p>
        <h1 class="h1">Accesorios con<br>propósito.</h1>
        <p class="lede">Arneses, correas, comederos y camas de diseño limpio para los que siempre están a tu lado. Y una promesa: <strong>un porcentaje de cada compra</strong> financia la investigación del cáncer y las enfermedades raras en mascotas.</p>
        <div class="hero__cta">
          <a class="btn" href="tienda.html">Ver la colección</a>
          <a class="btn btn--ghost" href="compromiso.html">En memoria de khalid</a>
        </div>
        <div class="hero__meta">
          <div>{SVG['truck']} Envío con seguimiento</div>
          <div>{SVG['return']} Devoluciones {RETURNS} días</div>
          <div>{SVG['lock']} Pago seguro</div>
        </div>
      </div>
      <div class="hero__media">
        <img src="{HERO}" alt="Perro con arnés de paso PAW Guardian" width="1500" height="838" fetchpriority="high">
      </div>
    </div>
  </section>

  <section class="strip">
    <div class="wrap strip__in">
      <div class="strip__i">{SVG['truck']}<div><b>Envío con seguimiento</b><span>Entrega en {SITE['delivery_days']} días laborables en España</span></div></div>
      <div class="strip__i">{SVG['return']}<div><b>Devoluciones {RETURNS} días</b><span>Cambios sencillos, sin complicaciones</span></div></div>
      <div class="strip__i">{SVG['shield']}<div><b>Pago seguro</b><span>Tarjeta y pagos móviles con cifrado</span></div></div>
      <div class="strip__i">{SVG['heart']}<div><b>GRANKHA por la salud animal</b><span>Un porcentaje de los beneficios a investigación</span></div></div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="section-head reveal">
        <div>
          <p class="kicker">Colecciones</p>
          <h2 class="h2">Todo lo que llevan puesto.</h2>
        </div>
        <a class="link-arrow" href="tienda.html">Ver toda la tienda</a>
      </div>
      <div class="cats reveal">{tiles}</div>
    </div>
  </section>

  <section class="section section--paper">
    <div class="wrap">
      <div class="section-head reveal">
        <div>
          <p class="kicker">Selección GRANKHA</p>
          <h2 class="h2">Lo más querido</h2>
        </div>
        <a class="link-arrow" href="tienda.html">Ver los {len(PRODUCTS)} productos</a>
      </div>
      <div class="reveal">{products_grid(featured, ranks)}</div>
    </div>
  </section>

  <section class="section memorial" id="compromiso">
    <div class="wrap memorial__in">
      <figure class="memorial__media reveal">
        <img src="{MEMORIAL}" alt="Mano de su dueño acariciando la pata de un perro tumbado" width="1000" height="1000" loading="lazy" decoding="async">
        <figcaption>In memoriam: khalid</figcaption>
      </figure>
      <div class="reveal">
        <p class="kicker kicker--light">Compromiso y corazón</p>
        <blockquote>«Perdí a mi gran amigo khalid por un cáncer de colon. Ningún dueño debería cargar con ese dolor solo, ni ninguna mascota debería padecerlo.»</blockquote>
        <p>Esta web no es solo un escaparate de productos: es un legado personal nacido del amor y la pérdida. Por eso, <strong>un porcentaje de los beneficios de GRANKHA</strong> va destinado directamente a la investigación del cáncer y las enfermedades raras en nuestras mascotas.</p>
        <div class="donate-note">{SVG['ribbon']}<div><b>GRANKHA por la salud animal</b><br>
        <span style="font-size:.88rem">khalid siempre estará en el ADN de esta marca, impulsándonos a cuidar de los tuyos como él cuidó de mí.</span></div></div>
        <p class="mt-m"><a class="link-arrow" href="compromiso.html" style="color:#fff;border-color:#fff">Leer nuestra historia completa</a></p>
      </div>
    </div>
  </section>

  <section class="section section--paper">
    <div class="wrap news">
      <div class="reveal">
        <p class="kicker">Comunidad</p>
        <h2 class="h2 ml">Únete a la familia GRANKHA.</h2>
        <p class="lede mt-s">Consejos de cuidado, novedades de producto y avances en investigación animal. Sin ruido, sin spam.</p>
      </div>
      <div class="reveal">
        <form data-news>
          <input type="email" required placeholder="tu@email.com" aria-label="Tu email">
          <button class="btn" type="submit">Suscribirme</button>
        </form>
        <p class="small mt-s">Al suscribirte aceptas la <a href="legal.html#privacidad" style="text-decoration:underline">política de privacidad</a>. Puedes darte de baja cuando quieras.</p>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    jsonld = [{
        "@context": "https://schema.org", "@type": "OnlineStore", "name": SITE["name"],
        "url": BASE, "logo": f"{BASE}/assets/img/hero.jpg", "email": SITE["contactEmail"],
        "currenciesAccepted": "EUR", "areaServed": "ES",
        "description": "Accesorios para mascotas con diseño minimalista. Un porcentaje de los beneficios financia la investigación del cáncer y enfermedades raras en animales. En memoria de khalid.",
    }, {
        "@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": BASE,
    }]
    desc = ("Arneses, correas, camas y comederos de diseño minimalista para perros y gatos. "
            f"Envío con seguimiento en {SITE['delivery_days']} días y devoluciones de {RETURNS} días. "
            "Un porcentaje de cada compra apoya la investigación del cáncer animal.")
    write("index.html", head(f"{SITE['name']} · {SITE['tagline']}", desc, "index.html", jsonld=jsonld)
          + body + tail())

# ------------------------------------------------------------------ tienda
def build_tienda():
    chips = '<button class="chip is-on" data-filter="todo">Todo</button>' + "".join(
        f'<button class="chip" data-filter="{c}">{n}</button>' for c, n, _ in CATS)
    body = f"""{header("tienda")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Tienda</p>
      <h1 class="h3" style="font-size:clamp(2rem,5vw,3.4rem)">La colección completa</h1>
      <p class="lede mt-s">{len(PRODUCTS)} productos pensados para el día a día. Precios con IVA incluido, envío gratis en península desde {eur(SITE['shipping']['freeFromPeninsular'])} y devoluciones durante {RETURNS} días.</p>
    </div>
  </section>
  <section class="section section--tight" style="padding-top:0">
    <div class="wrap">
      <div class="section-head" style="margin-bottom:22px;align-items:center">
        <div class="filters">{chips}</div>
        <div class="filters">
          <input class="chip" id="shop-search" type="search" placeholder="Buscar…" aria-label="Buscar productos" style="min-width:180px;text-transform:none;letter-spacing:0">
          <select class="chip" id="shop-sort" aria-label="Ordenar">
            <option value="destacados">Destacados</option>
            <option value="precio-asc">Precio: menor a mayor</option>
            <option value="precio-desc">Precio: mayor a menor</option>
            <option value="nombre">Nombre A-Z</option>
          </select>
        </div>
      </div>
      <p class="small mb-m" id="shop-count">{len(PRODUCTS)} productos</p>
      <div id="shop-grid">{products_grid(PRODUCTS)}</div>
      <div class="empty hide" id="shop-empty">
        <h3 class="h4">Sin resultados</h3>
        <p class="small mt-s">Prueba con otra búsqueda o revisa todas las categorías.</p>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    write("tienda.html", head(f"Tienda · {SITE['name']} — Accesorios para mascotas",
          "Todos los accesorios GRANKHA: arneses de paso, correas, camas y comederos. "
          "IVA incluido, envío gratis desde 49 € y devoluciones en 30 días.", "tienda.html")
          + body + tail())

# ------------------------------------------------------------------ ficha de producto
def build_product(p):
    sib = [q for q in PRODUCTS if q["title"] == p["title"] and q["slug"] != p["slug"]]
    rel = [q for q in PRODUCTS if q["cat"] == p["cat"] and q["slug"] != p["slug"]]
    rel.sort(key=lambda q: (q["collection"] == p["collection"], q["price"]))
    rel = rel[:4]
    specs = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in p["specs"])
    bullets = "".join(f"<li>{SVG['paw']}<span>{esc(b)}</span></li>" for b in p["bullets"])
    variants = ""
    if sib:
        links = "".join(
            f'<a class="chip" data-variant href="{q["slug"]}.html" style="display:inline-flex;align-items:center;gap:8px">'
            f'<span class="swatch" style="background:{q["colorHex"]}"></span>'
            f'{esc((q["size"] + " · " if q["size"] not in ("", "—", "Único", "Única", q["dims"]) else "") + q["color"])}</a>'
            for q in sib[:10])
        variants = f'<div class="mt-m"><p class="small mb-m">Otras variantes de <b>{esc(p["title"])}</b></p><div class="filters">{links}</div></div>'
    stock = p["stock"]
    avail = "https://schema.org/InStock" if stock > 5 else ("https://schema.org/LimitedAvailability" if stock > 0 else "https://schema.org/OutOfStock")
    body = f"""{header(p['cat'])}
<main>
  <div class="wrap crumbs">
    <a href="index.html">Inicio</a><span>/</span><a href="tienda.html">Tienda</a><span>/</span>
    <a href="tienda.html?cat={p['cat']}">{esc(p['catName'])}</a><span>/</span><span>{esc(p['title'])}</span>
  </div>
  <section class="wrap pd" id="pd" data-slug="{p['slug']}">
    <div class="pd__media reveal">
      <img src="{PHOTO[p['slug']]}" alt="{esc(p['title'] + ' — ' + p['subtitle'])}" width="900" height="900" fetchpriority="high">
    </div>
    <div>
      <p class="kicker">{esc(p['catName'])} · Colección {esc(p['collection'])}</p>
      <h1 class="h2 pd__title">{esc(p['title'])}</h1>
      <p class="lede">{esc(p['subtitle'])}</p>
      <div class="pd__price">
        <span class="now mono">{eur(p['price'])}</span>
        <span class="tax">IVA incluido · Envío gratis desde {eur(SITE['shipping']['freeFromPeninsular'])}</span>
      </div>
      <p class="small" data-stock="{stock}">Disponible · envío en {SITE['delivery_days']} días laborables</p>
      <div class="pd__buy">
        <div class="qty" data-pdqty data-max="{stock}">
          <button type="button" data-step="-1" aria-label="Menos">−</button>
          <input type="number" value="1" min="1" max="{stock}" aria-label="Cantidad">
          <button type="button" data-step="1" aria-label="Más">+</button>
        </div>
        <button class="btn btn--ghost" data-add="{p['slug']}" data-qty-from="pd">Añadir a la cesta</button>
        <button class="btn" data-buy="{p['slug']}">Comprar ahora</button>
      </div>
      <ul class="usp">
        <li>{SVG['truck']}<span><b>Envío con seguimiento</b> en {SITE['delivery_days']} días laborables</span></li>
        <li>{SVG['return']}<span><b>Devoluciones fáciles</b> durante {RETURNS} días</span></li>
        <li>{SVG['lock']}<span><b>Pago seguro</b> con cifrado · tarjeta y pagos móviles</span></li>
        <li>{SVG['heart']}<span><b>Un porcentaje de esta compra</b> apoya la investigación animal</span></li>
      </ul>
      <div class="acc">
        <details open><summary>Descripción</summary><div class="acc__body">{esc(p['desc'])}</div></details>
        <details><summary>Características</summary><div class="acc__body"><ul style="padding-left:18px;margin:0">{''.join(f'<li>{esc(b)}</li>' for b in p['bullets'])}</ul></div></details>
        <details><summary>Detalles y medidas</summary><div class="acc__body"><table class="spec-table">{specs}</table></div></details>
        <details><summary>Envío y devoluciones</summary><div class="acc__body">
          <p>Preparamos tu pedido en 24-48 h y lo enviamos con seguimiento. Entrega estimada en {SITE['delivery_days']} días laborables en España peninsular. Envío gratis a partir de {eur(SITE['shipping']['freeFromPeninsular'])}; por debajo, {eur(SITE['shipping']['options'][0]['price'])}.</p>
          <p>Si algo no encaja, tienes {RETURNS} días para devolverlo. <a href="envios.html">Ver política completa</a>.</p>
        </div></details>
        <details><summary>Garantía y cuidado</summary><div class="acc__body">
          <p>Garantía legal de conformidad de 3 años en España. Ante cualquier defecto de fabricación, escríbenos a <a href="mailto:{SITE['contactEmail']}">{SITE['contactEmail']}</a> y lo solucionamos.</p>
          <p>Cuidado: limpiar con un paño húmedo o lavado suave en frío según el material. No usar lejía ni secadora.</p>
        </div></details>
      </div>
      {variants}
    </div>
  </section>

  <section class="memorial" style="padding-block:clamp(40px,6vw,72px)">
    <div class="wrap pledge">
      <div class="donate-note" style="margin:0">{SVG['ribbon']}<div><b>GRANKHA por la salud animal</b><br>
        <span style="font-size:.88rem">Un porcentaje de los beneficios financia la investigación del cáncer y las enfermedades raras en mascotas.</span></div></div>
      <div>
        <h3 class="h3" style="margin-bottom:10px;color:#fff">Un porcentaje de esta compra va a investigación.</h3>
        <p>Investigar el cáncer y las enfermedades raras en mascotas evita sufrimiento a los animales y a sus familias. Gracias por formar parte de esto. <a href="compromiso.html" style="color:#fff;text-decoration:underline">Nuestra historia</a>.</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="section-head">
        <div><p class="kicker">También te puede gustar</p><h2 class="h3">Completa el conjunto</h2></div>
        <a class="link-arrow" href="tienda.html?cat={p['cat']}">Ver {esc(p['catName'].lower())}</a>
      </div>
      {products_grid(rel)}
    </div>
  </section>
</main>
{footer()}"""
    og = f"assets/img/og/{p['slug']}.jpg"
    jsonld = [{
        "@context": "https://schema.org", "@type": "Product",
        "name": f"{p['title']} · {p['subtitle']}",
        "description": p["desc"][:400],
        "sku": p["sku"], "brand": {"@type": "Brand", "name": "PAW"},
        "image": [f"{BASE}/{og}"], "color": p["color"],
        "offers": {
            "@type": "Offer", "url": f"{BASE}/{p['slug']}.html", "price": f"{p['price']:.2f}",
            "priceCurrency": "EUR", "availability": avail,
            "itemCondition": "https://schema.org/NewCondition",
            "shippingDetails": {"@type": "OfferShippingDetails",
                "shippingRate": {"@type": "MonetaryAmount", "value": f"{SITE['shipping']['options'][0]['price']:.2f}", "currency": "EUR"},
                "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "ES"}},
            "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy", "applicableCountry": "ES",
                "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                "merchantReturnDays": RETURNS, "returnMethod": "https://schema.org/ReturnByMail",
                "returnFees": "https://schema.org/FreeReturn"},
        },
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{BASE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "Tienda", "item": f"{BASE}/tienda.html"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": f"{BASE}/{p['slug']}.html"},
        ],
    }]
    title = f"{p['title']} · {p['subtitle']} — GRANKHA"
    desc = f"{p['title']} ({p['subtitle']}). {p['desc'][:120]}… Compra en GRANKHA con IVA incluido, envío en {SITE['delivery_days']} días y devoluciones en {RETURNS} días."
    write(p["slug"] + ".html", head(title, desc, p["slug"] + ".html", og=og,
          og_type="product", jsonld=jsonld) + body + tail())

# ------------------------------------------------------------------ carrito
def build_carrito():
    countries = ["España", "Portugal", "Francia", "Alemania", "Italia", "Países Bajos",
                 "Bélgica", "Irlanda", "Austria", "Luxemburgo"]
    opts = "".join(f'<option value="{c}">{c}</option>' for c in countries)
    body = f"""{header("")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Carrito</p>
      <h1 class="h3" style="font-size:clamp(2rem,5vw,3.2rem)">Tu cesta</h1>
    </div>
  </section>
  <section class="section" style="padding-top:0">
    <div class="wrap">
      <div id="cart-empty" class="empty hide">
        <h3 class="h4">Tu carrito está vacío</h3>
        <p class="small mt-s">Descubre la colección y encuentra el detalle que le falta a tu compañero.</p>
        <p class="mt-m"><a class="btn" href="tienda.html">Ver la colección</a></p>
      </div>

      <div class="cart" id="cart-root">
        <div>
          <div id="cart-lines"></div>
          <p class="small mt-m">Los gastos de envío y los impuestos se calculan antes de finalizar la compra. Precios con IVA incluido.</p>
        </div>
        <aside>
          <div id="cart-shipping" class="mb-m"></div>
          <div class="summary" id="cart-summary"></div>
        </aside>
      </div>

      <div id="checkout" class="section" style="padding-block:clamp(30px,5vw,60px) 0">
        <div class="section-head">
          <div><p class="kicker">Paso 2</p><h2 class="h3">Finalizar compra</h2></div>
        </div>
        <form class="form" id="checkout-form" novalidate style="max-width:640px">
          <div class="f2">
            <div class="field"><label for="f-name">Nombre y apellidos *</label><input id="f-name" name="name" required autocomplete="name"></div>
            <div class="field"><label for="f-email">Email *</label><input id="f-email" name="email" type="email" required autocomplete="email"></div>
          </div>
          <div class="f2">
            <div class="field"><label for="f-phone">Teléfono *</label><input id="f-phone" name="phone" required autocomplete="tel" placeholder="Para avisos de entrega"></div>
            <div class="field"><label for="f-nif">NIF / CIF (opcional)</label><input id="f-nif" name="nif" placeholder="Si necesitas factura"></div>
          </div>
          <div class="field"><label for="f-address">Dirección *</label><input id="f-address" name="address" required autocomplete="street-address"></div>
          <div class="field"><label for="f-address2">Piso, puerta, escalera (opcional)</label><input id="f-address2" name="address2"></div>
          <div class="f2">
            <div class="field"><label for="f-zip">Código postal *</label><input id="f-zip" name="zip" required inputmode="numeric" pattern="[0-9]{{5}}" autocomplete="postal-code"></div>
            <div class="field"><label for="f-city">Ciudad *</label><input id="f-city" name="city" required autocomplete="address-level2"></div>
          </div>
          <div class="f2">
            <div class="field"><label for="f-province">Provincia</label><input id="f-province" name="province" autocomplete="address-level1"></div>
            <div class="field"><label for="f-country">País *</label><select id="f-country" name="country" required>{opts}</select></div>
          </div>
          <div class="field"><label for="f-notes">Notas para la entrega (opcional)</label><textarea id="f-notes" name="notes" rows="3" placeholder="Portero, horarios, indicaciones…"></textarea></div>
          <label class="check"><input type="checkbox" name="terms" required>
            <span>He leído y acepto las <a href="legal.html#condiciones" style="text-decoration:underline">condiciones de venta</a> y la <a href="legal.html#privacidad" style="text-decoration:underline">política de privacidad</a>. *</span></label>
          <button class="btn btn--block" type="submit">Confirmar pedido</button>
          <div id="checkout-pay" class="hide"></div>
          <p class="small">{SVG['lock']} El pago con tarjeta se realiza en un entorno seguro. GRANKHA no almacena datos de tarjeta. Cuando Stripe esté activo, este botón te llevará a su pasarela segura; mientras tanto, recibirás el enlace de pago por email.</p>
        </form>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    write("carrito.html", head(f"Carrito · {SITE['name']}",
          "Revisa tu cesta y finaliza tu pedido. Envío gratis en península desde 49 € y devoluciones en 30 días.",
          "carrito.html", jsonld={"@context": "https://schema.org", "@type": "WebPage",
                                  "name": "Carrito de la compra", "url": f"{BASE}/carrito.html",
                                  "isPartOf": {"@type": "WebSite", "name": SITE["name"], "url": BASE}})
          + body + tail(full=True))

# ------------------------------------------------------------------ compromiso
def build_compromiso():
    body = f"""{header("compromiso")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Compromiso y corazón</p>
      <h1 class="h2" style="font-size:clamp(2.2rem,6vw,4.4rem)">In memoriam: khalid.</h1>
      <p class="lede mt-m">En GRANKHA creemos que la tecnología y el diseño solo tienen sentido si sirven para proteger aquello que amamos.</p>
    </div>
  </section>

  <section class="section" style="padding-top:0">
    <div class="wrap split">
      <figure class="memorial__media reveal" style="margin:0">
        <img src="{MEMORIAL}" alt="Mano acariciando la pata de un perro tumbado, en blanco y negro" width="1000" height="1000">
        <figcaption style="color:var(--muted)">khalid</figcaption>
      </figure>
      <div class="prose reveal">
        <p><b>En GRANKHA, creemos que la tecnología solo tiene sentido si sirve para proteger aquello que amamos.</b> Esta web no es solo un escaparate de productos, es un legado personal nacido del amor y la pérdida.</p>
        <p>Hace poco perdí a mi gran amigo khalid debido a un cáncer de colon. No hay día que pase sin que su recuerdo me acompañe. Verle sufrir, ver cómo su luz se apagaba lentamente y tener que tomar la dolorosa decisión de dejarle marchar cuando ya no había solución, es un dolor que ningún dueño debería cargar solo ni ninguna mascota debería padecer.</p>
        <p>Por eso, <b>un porcentaje de los beneficios de GRANKHA</b> irá destinado directamente a la investigación del cáncer y enfermedades raras en nuestras mascotas. Queremos contribuir a que el desconocimiento no sea la causa de más sufrimiento. Queremos evitar ese dolor tanto al animal como a sus familias. khalid siempre estará en el ADN de esta marca, impulsándonos a cuidar de los tuyos como él cuidó de mí.</p>
        <blockquote class="mt-m" style="margin:34px 0 0;padding-left:20px;border-left:2px solid var(--ink);font-size:clamp(1.1rem,1.9vw,1.5rem);letter-spacing:-.02em"><b>GRANKHA por la salud animal</b></blockquote>
      </div>
    </div>
  </section>

  <section class="section memorial">
    <div class="wrap">
      <div class="section-head">
        <div>
          <p class="kicker kicker--light">Cómo se traduce en acción</p>
          <h2 class="h2" style="color:#fff">Del carrito a la investigación.</h2>
        </div>
      </div>
      <div class="grid g3">
        <div class="donate-note" style="border-color:rgba(255,255,255,.22);margin:0">{SVG['heart']}<div><b>Un porcentaje de cada compra</b><br><span style="font-size:.88rem">Se calcula sobre los beneficios de GRANKHA y se reserva cada mes para proyectos de investigación veterinaria.</span></div></div>
        <div class="donate-note" style="border-color:rgba(255,255,255,.22);margin:0">{SVG['shield']}<div><b>Entidades verificadas</b><br><span style="font-size:.88rem">Buscamos organizaciones y grupos de investigación con programas en oncología y enfermedades raras veterinarias.</span></div></div>
        <div class="donate-note" style="border-color:rgba(255,255,255,.22);margin:0">{SVG['ribbon']}<div><b>Transparencia</b><br><span style="font-size:.88rem">Publicaremos un resumen anual con los importes donados y los proyectos apoyados, con nombre y apellidos.</span></div></div>
      </div>
      <div class="notice notice--light mt-l">
        <b>¿Quieres proponer un proyecto?</b><br>
        Si conoces una entidad o un equipo de investigación que trabaje en cáncer o enfermedades raras en animales,
        escríbenos a <a href="mailto:{SITE['contactEmail']}" style="color:#fff">{SITE['contactEmail']}</a>. Leemos todo.
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap prose">
      <h2 style="margin-top:0">Preguntas sobre el compromiso</h2>
      <h3>¿Qué porcentaje de los beneficios se dona?</h3>
      <p>Un porcentaje fijo de los beneficios netos de GRANKHA. El importe exacto se revisa cada año y se comunica en el resumen anual de donaciones. Nuestro objetivo es que sea cada vez mayor a medida que la marca crece.</p>
      <h3>¿Cuándo se hace la donación?</h3>
      <p>La reserva se hace de forma continua y la aportación se materializa al cierre de cada ejercicio o cuando el importe acumulado permite una aportación útil al proyecto elegido.</p>
      <h3>¿Esto sube el precio de los productos?</h3>
      <p>No. Los precios se fijan según el coste de producto, envío y gestión. La donación sale del margen de GRANKHA, no de un recargo añadido a cada pedido.</p>
      <h3>Mi mascota está enferma, ¿podéis ayudarme?</h3>
      <p>No somos veterinarios ni podemos dar diagnóstico. Si tu mascota está enferma, acude a un profesional. Podemos orientarte sobre a qué entidades o asociaciones acudir: escríbenos y te ayudamos en lo que esté en nuestra mano.</p>
    </div>
  </section>
</main>
{footer()}"""
    write("compromiso.html", head(f"Compromiso y corazón · {SITE['name']}",
          "En memoria de khalid: un porcentaje de los beneficios de GRANKHA financia la investigación del cáncer y las enfermedades raras en mascotas.",
          "compromiso.html", og="assets/img/memorial.jpg")
          + body + tail())

# ------------------------------------------------------------------ envíos
def build_envios():
    rows = "".join(
        f"<tr><td>{esc(o['name'])}</td><td>{'Gratis desde ' + eur(o['free_from']) if o.get('free_from') else '—'}</td>"
        f"<td>{eur(o['price'])}</td><td>{esc(o['eta'])}</td></tr>"
        for o in SITE["shipping"]["options"])
    body = f"""{header("")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Envíos y devoluciones</p>
      <h1 class="h2" style="font-size:clamp(2rem,5vw,3.6rem)">Llega rápido, vuelve fácil.</h1>
      <p class="lede mt-m">Trabajamos con envío con seguimiento y plazos realistas. Si algo no encaja, tienes {RETURNS} días para cambiarlo o devolverlo.</p>
    </div>
  </section>
  <section class="section" style="padding-top:0">
    <div class="wrap">
      <h2 class="h3">Tarifas de envío</h2>
      <table class="table mt-m">
        <thead><tr><th>Destino</th><th>Envío gratis</th><th>Coste</th><th>Plazo estimado</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p class="small mt-s">Precios con impuestos incluidos. {esc(SITE['shipping']['note'])}</p>

      <h2 class="h3 mt-l">Cómo funciona</h2>
      <div class="grid g3 mt-m">
        <div class="notice"><b>1 · Preparación</b><br>Preparamos y verificamos tu pedido en 24-48 horas laborables.</div>
        <div class="notice"><b>2 · Envío</b><br>Recibes un email con el número de seguimiento en cuanto sale del almacén.</div>
        <div class="notice"><b>3 · Entrega</b><br>Entrega en {SITE['delivery_days']} días laborables con aviso del transportista.</div>
      </div>

      <h2 class="h3 mt-l" id="devoluciones">Devoluciones y cambios</h2>
      <div class="prose">
        <p>Puedes devolver cualquier producto en los <b>{RETURNS} días</b> siguientes a la entrega, sin necesidad de justificar el motivo (muy por encima de los 14 días naturales que exige la ley). Condiciones:</p>
        <ul>
          <li>El producto debe estar sin usar, con su embalaje y, si procede, con las etiquetas originales.</li>
          <li>Por higiene no se admiten devoluciones de productos usados o con restos de pelo, salvo defecto de fabricación.</li>
          <li>Escríbenos a <a href="mailto:{SITE['contactEmail']}">{SITE['contactEmail']}</a> con el número de pedido e indícanos qué quieres devolver.</li>
          <li>Te enviamos instrucciones de devolución y, una vez recibido y revisado el producto, reembolsamos el importe por el mismo método de pago en un plazo máximo de 14 días.</li>
          <li>Si el producto llega defectuoso o incorrecto, asumimos nosotros el coste de la devolución.</li>
        </ul>
        <h2 id="faq">Preguntas frecuentes</h2>
        <h3>¿Puedo cambiar el tamaño de un arnés?</h3>
        <p>Sí. Si la talla no queda bien, escríbenos dentro de los {RETURNS} días y gestionamos el cambio por la talla superior o inferior. Consulta la guía de tallas en la ficha del producto: XS para 2-4 kg y S para 4-8 kg en los artículos que las ofrecen.</p>
        <h3>¿Puedo modificar mi pedido después de comprarlo?</h3>
        <p>Si aún no lo hemos preparado, sí. Escríbenos lo antes posible y lo actualizamos.</p>
        <h3>¿Enviáis a Canarias, Ceuta y Melilla?</h3>
        <p>Sí. Estas entregas pueden requerir el despacho de aduanas y el pago de IGIC/IPSI en destino, que corre por cuenta del cliente.</p>
        <h3>¿Necesito registrarme para comprar?</h3>
        <p>No. Puedes comprar como invitado. Solo pedimos los datos imprescindibles para entregar el pedido.</p>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    write("envios.html", head(f"Envíos y devoluciones · {SITE['name']}",
          "Tarifas de envío con seguimiento en España, plazos de entrega y política de devoluciones de 30 días.",
          "envios.html") + body + tail())

# ------------------------------------------------------------------ contacto
def build_contacto():
    body = f"""{header("")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Contacto</p>
      <h1 class="h2" style="font-size:clamp(2rem,5vw,3.4rem)">Hablemos.</h1>
      <p class="lede mt-m">¿Dudas sobre una talla, un pedido o una devolución? Escríbenos: contestamos en menos de 24 horas laborables.</p>
    </div>
  </section>
  <section class="section" style="padding-top:0">
    <div class="wrap split">
      <div>
        <ul class="usp" style="margin-top:0">
          <li>{SVG['lock']}<span><b>Email</b><br><a href="mailto:{SITE['contactEmail']}" style="text-decoration:underline">{SITE['contactEmail']}</a></span></li>
          <li>{SVG['truck']}<span><b>Pedidos y envíos</b><br>Incluye tu número de pedido (GRK-…) para que podamos ayudarte más rápido.</span></li>
          <li>{SVG['return']}<span><b>Devoluciones</b><br>Indica qué producto quieres devolver y el motivo (opcional).</span></li>
          <li>{SVG['heart']}<span><b>Propuestas de investigación</b><br>Entidades y equipos que trabajen en cáncer o enfermedades raras en mascotas.</span></li>
        </ul>
        <p class="small mt-m">GRANKHA · {esc(SITE['legal_name'])} · {esc(SITE['contactEmail'])}</p>
      </div>
      <form class="form" data-contact>
        <div class="f2">
          <div class="field"><label for="c-name">Nombre *</label><input id="c-name" name="nombre" required></div>
          <div class="field"><label for="c-email">Email *</label><input id="c-email" name="email" type="email" required></div>
        </div>
        <div class="field"><label for="c-ref">Nº de pedido (opcional)</label><input id="c-ref" name="pedido" placeholder="GRK-XXXXXX-XXXX"></div>
        <div class="field"><label for="c-msg">Mensaje *</label><textarea id="c-msg" name="mensaje" rows="6" required></textarea></div>
        <label class="check"><input type="checkbox" required><span>Acepto la <a href="legal.html#privacidad" style="text-decoration:underline">política de privacidad</a>.</span></label>
        <button class="btn" type="submit">Enviar mensaje</button>
        <p class="small">El mensaje se abrirá en tu programa de correo con todo rellenado, listo para enviar.</p>
      </form>
    </div>
  </section>
</main>
{footer()}"""
    write("contacto.html", head(f"Contacto · {SITE['name']}",
          "Atención al cliente de GRANKHA: dudas sobre tallas, pedidos, envíos y devoluciones.",
          "contacto.html") + body + tail())

# ------------------------------------------------------------------ legal
def build_legal():
    body = f"""{header("")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Información legal</p>
      <h1 class="h2" style="font-size:clamp(2rem,5vw,3.4rem)">Legal</h1>
      <p class="small mt-m">Última actualización: {date.today().strftime('%d/%m/%Y')}</p>
    </div>
  </section>
  <section class="section" style="padding-top:0">
    <div class="wrap prose">
      <div class="notice"><b>Pendiente de completar antes de vender:</b> razón social, NIF, domicilio fiscal y teléfono de contacto del titular. Sustituye los campos marcados con [ ] en esta página. Ver docs/PENDIENTES.md.</div>

      <h2 id="aviso">Aviso legal</h2>
      <p>En cumplimiento del artículo 10 de la Ley 34/2002 de Servicios de la Sociedad de la Información y de Comercio Electrónico (LSSI-CE), se informa:</p>
      <ul>
        <li><b>Titular:</b> [RAZÓN SOCIAL / NOMBRE Y APELLIDOS]</li>
        <li><b>Nombre comercial:</b> GRANKHA · {esc(SITE['legal_name'])}</li>
        <li><b>NIF:</b> [NIF]</li>
        <li><b>Domicilio:</b> [DIRECCIÓN COMPLETA, CP, LOCALIDAD, MADRID, ESPAÑA]</li>
        <li><b>Email:</b> {esc(SITE['contactEmail'])}</li>
        <li><b>Actividad:</b> comercio electrónico de accesorios para mascotas.</li>
      </ul>
      <p>El acceso y uso de este sitio atribuye la condición de usuario e implica la aceptación de este aviso legal. Los contenidos, marcas y diseños son propiedad de su titular o se utilizan con autorización; no se permite su reproducción sin consentimiento.</p>

      <h2 id="condiciones">Condiciones generales de venta</h2>
      <h3>1. Proceso de compra</h3>
      <p>El pedido se formaliza cuando el usuario completa el formulario de finalizar compra y recibe la confirmación por email. GRANKHA se reserva el derecho de cancelar pedidos con errores evidentes de precio o disponibilidad, reembolsando el importe íntegro.</p>
      <h3>2. Precios e impuestos</h3>
      <p>Todos los precios se muestran en euros <b>con el IVA español (21 %) incluido</b> para envíos a la España peninsular y Baleares. En Canarias, Ceuta y Melilla no se aplica el IVA: el impuesto indirecto correspondiente (IGIC/IPSI) y los posibles gastos aduaneros se liquidan en destino a cargo del cliente. {esc(SITE['shipping']['note'])}</p>
      <h3>3. Gastos de envío</h3>
      <p>Los gastos de envío se muestran antes de finalizar la compra: {esc(' / '.join(f"{o['name']}: {eur(o['price'])}" for o in SITE['shipping']['options']))}. El envío es gratuito en España peninsular a partir de {eur(SITE['shipping']['freeFromPeninsular'])}.</p>
      <h3>4. Entrega</h3>
      <p>Plazo estimado de entrega: {SITE['delivery_days']} días laborables desde la confirmación del pedido. Son plazos orientativos; los retrasos por causas ajenas (aduanas, transporte, fuerza mayor) no generan derecho a indemnización, sin perjuicio del derecho de desistimiento.</p>
      <h3>5. Desistimiento y devoluciones</h3>
      <p>Dispones de <b>{RETURNS} días</b> desde la recepción para devolver el producto sin justificar el motivo, muy por encima de los 14 días naturales que establece la normativa. Procedimiento y condiciones en la página de <a href="envios.html#devoluciones">Envíos y devoluciones</a>.</p>
      <h3>6. Garantía legal</h3>
      <p>Todos los productos cuentan con la garantía legal de conformidad de <b>3 años</b> desde la entrega (Real Decreto Legislativo 1/2007). Si el producto presenta un defecto de origen, GRANKHA asume la reparación, sustitución, rebaja o reembolso.</p>
      <h3>7. Atención al cliente y resolución de conflictos</h3>
      <p>Para cualquier reclamación, escribe a {esc(SITE['contactEmail'])}. También puedes acudir a la Junta Arbitral de Consumo de tu provincia o a la plataforma europea de resolución de litigios en línea. No estamos adheridos a ningún sistema arbitral de consumo.</p>

      <h2 id="privacidad">Política de privacidad</h2>
      <p>De acuerdo con el RGPD (UE 2016/679) y la LOPDGDD:</p>
      <ul>
        <li><b>Responsable:</b> [RAZÓN SOCIAL], NIF [NIF], correo {esc(SITE['contactEmail'])}.</li>
        <li><b>Finalidades:</b> gestionar tu pedido y su envío, atender consultas y devoluciones, y —si lo autorizas— enviarte novedades de GRANKHA.</li>
        <li><b>Base jurídica:</b> ejecución del contrato (pedido), consentimiento (newsletter), interés legítimo (atención al cliente) y obligación legal (facturación y garantías).</li>
        <li><b>Destinatarios:</b> proveedor logístico y empresa de transporte que entrega tu pedido, pasarela de pago (Stripe) y proveedores técnicos de hosting y correo. No se realizan transferencias internacionales sin garantías adecuadas ni se venden datos a terceros.</li>
        <li><b>Conservación:</b> datos de pedido durante los plazos legales (facturación: 4 años; garantías: 3 años); datos de newsletter hasta que te des de baja.</li>
        <li><b>Derechos:</b> acceder, rectificar, suprimir, oponerte, limitar el tratamiento y solicitar la portabilidad escribiendo a {esc(SITE['contactEmail'])}. Puedes reclamar ante la Agencia Española de Protección de Datos.</li>
      </ul>
      <p>Los datos de pago se introducen directamente en la pasarela del proveedor de pagos; GRANKHA no almacena números de tarjeta. El carrito de compra se guarda únicamente en tu propio navegador (almacenamiento local).</p>

      <h2 id="cookies">Política de cookies</h2>
      <p>Esta web <b>no utiliza cookies publicitarias ni de seguimiento</b>. Solo emplea almacenamiento local del navegador (localStorage) para recordar tu carrito y tus preferencias: es información que permanece en tu dispositivo y puedes borrar desde los ajustes de tu navegador. Si en el futuro se incorporan herramientas de analítica, se informará y se pedirá consentimiento previo.</p>

      <h2 id="devoluciones-legales">Productos y responsabilidad</h2>
      <p>Las imágenes son orientativas; pueden existir ligeras variaciones de tono entre lotes. La información de esta web no sustituye el consejo veterinario. En caso de ingestión de piezas pequeñas o reacción adversa, acude a tu veterinario.</p>
    </div>
  </section>
</main>
{footer()}"""
    write("legal.html", head(f"Legal · {SITE['name']}",
          "Aviso legal, condiciones de venta, privacidad y cookies de GRANKHA.", "legal.html")
          + body + tail())

# ------------------------------------------------------------------ 404
def build_404():
    body = f"""{header("")}
<main>
  <section class="section" style="padding-block:clamp(70px,12vw,150px)">
    <div class="wrap" style="max-width:640px">
      <p class="kicker">Error 404</p>
      <h1 class="h2">Esta página se perdió de paseo.</h1>
      <p class="lede mt-m">No encontramos lo que buscabas, pero tu compañero sigue esperando su accesorio.</p>
      <p class="mt-l"><a class="btn" href="tienda.html">Ver la colección</a></p>
    </div>
  </section>
</main>
{footer()}"""
    write("404.html", head(f"Página no encontrada · {SITE['name']}", "Página no encontrada.",
          "404.html") + body + tail())

# ------------------------------------------------------------------ extras
def build_extras():
    # redirección amable: producto.html?p=slug -> slug.html
    write("producto.html", """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>GRANKHA</title><meta name="robots" content="noindex">
<script>(function(){var m=location.search.match(/[?&]p=([^&]+)/);
location.replace(m?decodeURIComponent(m[1]).replace(/[^a-z0-9-]/gi,"")+".html":"tienda.html");})();</script>
<meta http-equiv="refresh" content="1;url=tienda.html">
</head><body style="font-family:system-ui;padding:40px">Redirigiendo… <a href="tienda.html">Ir a la tienda</a></body></html>""")

    urls = ["index.html", "tienda.html", "compromiso.html", "envios.html", "contacto.html", "legal.html", "carrito.html"] \
           + [p["slug"] + ".html" for p in PRODUCTS]
    today = date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        pri = "1.0" if u == "index.html" else ("0.9" if u == "tienda.html" else "0.7")
        sm.append(f"  <url><loc>{BASE}/{u}</loc><lastmod>{today}</lastmod><priority>{pri}</priority></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    (ROOT / ".nojekyll").write_text("")
    print("  · .nojekyll")

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    print("· generando páginas…")
    build_index()
    build_tienda()
    for p in PRODUCTS:
        build_product(p)
    build_carrito()
    build_compromiso()
    build_envios()
    build_contacto()
    build_legal()
    build_404()
    build_extras()
    total = sum(f.stat().st_size for f in ROOT.glob("*.html"))
    print(f"✓ sitio generado · {len(list(ROOT.glob('*.html')))} páginas · {total/1024/1024:.1f} MB")

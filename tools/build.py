#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · build.py — genera el sitio estático completo (HTML autocontenido).

  index.html · tienda.html · carrito.html · compromiso.html · envios.html
  contacto.html · legal.html · 404.html · producto.html (redirección)
  <slug>.html × 44 (38 productos + 6 packs) · sitemap.xml · robots.txt
  supabase/functions/create-checkout/prices.json (validación de precios en servidor)

Uso: python3 tools/build.py
"""
import base64, html, io, json, re
from pathlib import Path
from datetime import date
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "assets" / "img"

PRODUCTS = json.loads((ROOT / "data" / "products.json").read_text())
SITE = json.loads((ROOT / "data" / "site.json").read_text())
ANALYSIS = json.loads((ROOT / "data" / "pricing_analysis.json").read_text())
CSS = (ROOT / "src" / "styles.css").read_text()
JS = (ROOT / "src" / "app.js").read_text().replace("</", "<\\/")
# sello de versión: invalida la caché del navegador solo cuando el archivo cambia
ASSET_V = str(abs(hash(CSS + JS)) % 10 ** 8)

BASE = SITE["url"].rstrip("/")
SHIP_OPTS = SITE["shipping"]["options"]
FREE_FROM = SITE["shipping"]["freeFromPeninsular"]
DON_TEXT = SITE["donation"].get("public_text", "un porcentaje de los beneficios")
RETURNS = SITE.get("returns_days", 30)
DELIVERY = SITE.get("delivery_days", "3-8")

PROD = [p for p in PRODUCTS if p["kind"] == "product"]
PACKS = [p for p in PRODUCTS if p["kind"] == "pack"]
CATS = [
    ("arneses", "Arneses", "Arneses de paso con malla reflectante"),
    ("correas", "Correas", "Correas de paseo y retráctiles"),
    ("camas", "Camas", "Camas y refugios para descansar"),
    ("comederos", "Comederos y fuentes", "Acero, madera y fuentes de agua"),
    ("packs", "Packs", "Conjuntos coordinados"),
]
DESTACADOS_SKU = ["PAWH-01", "PawL-01", "PawB-10", "PAWFB-08", "PAWH-06", "PawB-07",
                  "PAWFB-04", "PawL-05"]
TAG_BY_CAT = {"arneses": "Malla reflectante", "correas": "Uso diario", "camas": "Lavable",
              "comederos": "Acero inox.", "packs": "Pack"}

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
# Las imágenes se sirven como archivos (se cachean entre páginas y se cargan
# en diferido). Antes iban incrustadas en base64 y engordaban ~400 KB cada página.
THUMB = {p["slug"]: f'assets/img/thumbs/{p["slug"]}.webp' for p in PRODUCTS}
PHOTO = {p["slug"]: f'assets/img/products/{p["img"]}' for p in PRODUCTS}
HERO = data_uri(IMG_DIR / "hero.jpg", 1500, 80)
KHALID = data_uri(IMG_DIR / "khalid.jpg", 1000, 80)

by_slug = {p["slug"]: p for p in PRODUCTS}
by_sku = {p["sku"]: p for p in PRODUCTS}
order_rank = {p["slug"]: i for i, p in enumerate(PRODUCTS)}
for i, sku in enumerate(DESTACADOS_SKU):
    if sku in by_sku:
        order_rank[by_sku[sku]["slug"]] = -100 + i

def pack_of(p):
    """Texto con el contenido del pack (para carrito y fichas)."""
    if p["kind"] != "pack":
        return ""
    return " + ".join(f'{c["qty"]}× {c["name"]}' if c["qty"] > 1 else c["name"] for c in p["components"])

LITE = [{"slug": p["slug"], "title": p["name"], "subtitle": p["subtitle"], "sku": p["sku"],
         "cat": p["cat"], "price": p["price"], "stock": p["stock"], "weight_g": p["weight_g"],
         "kind": p["kind"], "url": p["slug"] + ".html",
         "packOf": pack_of(p) or None} for p in PRODUCTS]
FULL = [dict(x, thumb=THUMB[x["slug"]], colorHex=by_sku[x["sku"]]["colorHex"],
             components=(by_sku[x["sku"]].get("components") if x["kind"] == "pack" else None))
        for x in LITE]
# Configuración que se incrusta en el navegador: SOLO datos públicos.
# (el porcentaje interno de donación no se publica nunca)
CFG = {
    "name": SITE["name"],
    "contactEmail": SITE["contactEmail"],
    "shipping": {k: v for k, v in SITE["shipping"].items()
                 if k in ("default", "freeFromPeninsular", "vat", "note", "options")},
    "checkout": {"endpoint": SITE["checkout"]["endpoint"]},
    # si algún día hay proyecto Supabase, la newsletter se guarda de verdad
    "supabase": SITE.get("supabase", {}),
    "currency": SITE["currency"],
    "returns": RETURNS,
    "delivery": DELIVERY,
    "donation": {"public_text": DON_TEXT},   # solo la frase genérica
}

# Favicon e iconos: los genera tools/logo.py a partir del logo de la marca
def favicon_tags():
    return (
        '<link rel="icon" href="favicon.ico" sizes="any">\n'
        '<link rel="icon" type="image/png" sizes="32x32" href="assets/img/favicon-32.png">\n'
        '<link rel="icon" type="image/png" sizes="64x64" href="assets/img/favicon.png">\n'
        '<link rel="apple-touch-icon" sizes="180x180" href="assets/img/apple-touch-icon.png">'
    )

SVG = {
    "cart": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h2.2l2.1 10.3a2 2 0 0 0 2 1.7h7.9a2 2 0 0 0 2-1.6L21 8H6.2"/><circle cx="10" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h18M3 12h18M3 17h18"/></svg>',
    "truck": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h11v9H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="1.6"/><circle cx="17.5" cy="18" r="1.6"/></svg>',
    "return": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6z"/><path d="M9.2 12.2l2 2 3.6-3.9"/></svg>',
    "heart": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-9.3A4 4 0 0 1 12 8a4 4 0 0 1 7 2.7C19 15.6 12 20 12 20z"/></svg>',
    "ribbon": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c3.3 0 6 2.5 6 5.6 0 4-3.4 6.6-4.6 10.4h-2.8C9.4 15.2 6 12.6 6 8.6 6 5.5 8.7 3 12 3z"/><path d="M9.5 8.5l5 5M14.5 8.5l-5 5"/></svg>',
    "paw": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="7" cy="9" r="1.8"/><circle cx="12" cy="6.6" r="1.8"/><circle cx="17" cy="9" r="1.8"/><path d="M12 11.4c3 0 5.2 2 5.2 4.3 0 1.9-1.6 3.1-3.4 2.6-1.2-.3-2.4-.3-3.6 0-1.8.5-3.4-.7-3.4-2.6 0-2.3 2.2-4.3 5.2-4.3z"/></svg>',
    "cat": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 10V5l4 2.4h6L19 5v5a7 7 0 0 1-7 7 7 7 0 0 1-7-7z"/><path d="M9.5 12h.01M14.5 12h.01"/></svg>',
    "dog": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8l1.2-4L9 6.4h6L18.8 4 20 8a8 8 0 0 1-8 9 8 8 0 0 1-8-9z"/><circle cx="9.5" cy="12" r=".6"/><circle cx="14.5" cy="12" r=".6"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10.5" width="14" height="9.5" rx="1.6"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/></svg>',
    "plus": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
    "box": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 8l9-5 9 5v8l-9 5-9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>',
}

def cat_count(cat):
    return sum(1 for p in PRODUCTS if p["cat"] == cat)

def price_block(p, big=False):
    """Precio. En packs nunca mostramos ahorro ni precio tachado; en productos,
    solo si la diferencia con el precio anterior es relevante (>= 15 %)."""
    strike = ""
    prev = p.get("prevPrice")
    if p.get("kind") != "pack" and prev and p["price"] > 0 and prev > p["price"] * 1.15:
        strike = f'<span class="was">{eur(prev)}</span>'
    cls = "now mono" + (" now--big" if big else "")
    return f'<span class="{cls}">{eur(p["price"])}</span>{strike}'

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
{favicon_tags()}
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:locale" content="es_ES">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{BASE}/{path}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
{j}
<link rel="stylesheet" href="styles.css?v={ASSET_V}">
</head>
<body>"""

def header(active=""):
    def a(href, txt, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur}>{txt}</a>'
    nav = "".join([
        a("tienda.html", "Tienda", "tienda"),
        a("tienda.html?cat=packs", "Packs", "packs"),
        a("tienda.html?aud=perro", "Perros", "perro"),
        a("tienda.html?aud=gato", "Gatos", "gato"),
        a("compromiso.html", "Compromiso", "compromiso"),
    ])
    return f"""<div class="announce">Envío gratis en península desde {eur(FREE_FROM)} · Devoluciones {RETURNS} días · <a href="compromiso.html">GRANKHA por la salud animal</a></div>
<header class="site-head">
  <div class="wrap site-head__in">
    <a class="wordmark" href="index.html" aria-label="GRANKHA, inicio"><img class="wordmark__logo" src="assets/img/logo.png" srcset="assets/img/logo.png 1x, assets/img/logo@2x.png 2x" alt="" width="34" height="34" fetchpriority="high" decoding="async"><span>GRANKHA</span></a>
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
        <a class="wordmark" href="index.html" style="color:#fff"><img class="wordmark__logo" src="assets/img/logo.png" alt="" width="30" height="30" loading="lazy" decoding="async"><span>GRANKHA</span></a>
        <p class="footer__brand">Accesorios de diseño para perros y gatos, con una promesa: un porcentaje de los beneficios irá destinado a la investigación del cáncer y las enfermedades raras en mascotas. En memoria de Khalid, un gato blanco inolvidable.</p>
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
      <span>{esc(SITE['contactEmail'])} · Envío en {DELIVERY} días laborables</span>
    </div>
  </div>
</footer>"""

def card(p, rank=None):
    href = p["slug"] + ".html"
    tag = TAG_BY_CAT[p["cat"]]
    dark = ""
    if rank is not None and rank < 0:
        tag, dark = "Más vendido", " tag--dark"
    if p["kind"] == "pack":
        tag, dark = "Pack", " tag--dark"
    aud_icon = "" if p["audience"] == "ambos" else (SVG["cat"] if p["audience"] == "gato" else SVG["dog"])
    sub = p["subtitle"]
    if p["kind"] == "pack":
        sub = pack_of(p)
    # en los packs la categoría y la colección coinciden: no repetir el rótulo
    col_label = p["catName"] if p["catName"] == p["collection"] else f"{p['catName']} · {p['collection']}"
    return f"""<article class="card" data-cat="{p['cat']}" data-aud="{p['audience']}" data-price="{p['price']:.2f}" data-rank="{order_rank[p['slug']]}" data-search="{esc(p['name'] + ' ' + p['subtitle'] + ' ' + p['collection'] + ' ' + p['catName'] + ' ' + ' '.join(p.get('tags', [])))}">
  <a class="card__media" href="{href}" tabindex="-1" aria-hidden="true">
    <span class="card__tags"><span class="tag{dark}">{tag}</span></span>
    <img src="{THUMB[p['slug']]}" alt="{esc(p['name'] + ' — ' + p['subtitle'])}" width="380" height="380" loading="lazy" decoding="async">
  </a>
  <div class="card__body">
    <span class="card__col">{esc(col_label)}</span>
    <a class="card__title" href="{href}">{esc(p['name'])}</a>
    <span class="card__sub">{aud_icon}<span class="swatch" style="background:{p['colorHex']}"></span>{esc(sub)}</span>
    <div class="card__foot">
      <span class="price">{price_block(p)}<small>IVA incl.</small></span>
      <button class="mini-add" data-add="{p['slug']}" aria-label="Añadir {esc(p['name'])} al carrito">{SVG['plus']}</button>
    </div>
  </div>
</article>"""

def products_grid(items, ranks=None):
    return '<div class="products">' + "".join(
        card(p, rank=(ranks or {}).get(p["slug"])) for p in items) + "</div>"

def tail(full=False):
    cfg = json.dumps(CFG, ensure_ascii=False)
    lite = json.dumps(LITE, ensure_ascii=False)
    # al navegador solo van los datos públicos de cada pack (sin importes de ahorro)
    packs = json.dumps([{k: v for k, v in p.items() if k in ("slug", "name", "price", "components")} for p in PACKS], ensure_ascii=False)
    f = f"window.GRANKHA_CATALOG_FULL={json.dumps(FULL, ensure_ascii=False)};" if full else ""
    return f"""<div id="toast" class="toast" role="status" aria-live="polite"><span data-toast-msg></span><a data-toast-link href="#"></a></div>
<script>window.GRANKHA_CONFIG={cfg};window.GRANKHA_CATALOG={lite};window.GRANKHA_PACKS={packs};{f}</script>
<script src="app.js?v={ASSET_V}" defer></script>
</body></html>"""

def write(name, content):
    (ROOT / name).write_text(content, encoding="utf-8")

# ------------------------------------------------------------------- index
def build_index():
    featured = [by_sku[s] for s in DESTACADOS_SKU if s in by_sku]
    ranks = {p["slug"]: i for i, p in enumerate(featured)}
    tiles = ""
    for c, name, sub in CATS[:4]:
        rep = next(p for p in PRODUCTS if p["cat"] == c and p["kind"] == "product")
        tiles += f"""<a class="cat-tile" href="tienda.html?cat={c}">
  <img src="{THUMB[rep['slug']]}" alt="{esc(name)}" width="600" height="750" loading="lazy" decoding="async">
  <span class="cat-tile__cap"><b>{esc(name)}</b><span>{cat_count(c)} referencias · {esc(sub)}</span></span>
</a>"""
    packs_home = [p for p in PACKS][:3]
    body = f"""{header("inicio")}
<main>
  <section class="hero">
    <div class="wrap hero__in">
      <div class="hero__copy">
        <p class="kicker">Colección PAW · Perros y gatos</p>
        <h1 class="h1">Accesorios con<br>propósito.</h1>
        <p class="lede">Arneses, correas, camas, comederos y fuentes de diseño limpio para los que siempre están a tu lado —sean de cuatro patas y ladren, o de cuatro patas y ronroneen—. Y una promesa: <strong>un porcentaje de los beneficios irá destinado a la investigación del cáncer y las enfermedades raras en mascotas</strong>.</p>
        <div class="hero__cta">
          <a class="btn" href="tienda.html">Ver la colección</a>
          <a class="btn btn--ghost" href="tienda.html?cat=packs">Ver packs con descuento</a>
        </div>
        <div class="hero__meta">
          <div>{SVG['truck']} Envío gratis desde {eur(FREE_FROM)}</div>
          <div>{SVG['return']} Devoluciones {RETURNS} días</div>
          <div>{SVG['heart']} Un porcentaje a investigación</div>
        </div>
      </div>
      <div class="hero__media">
        <picture>
          <source media="(max-width:980px)" srcset="assets/img/hero-movil.jpg">
          <img src="{HERO}" alt="Un perro y un gato juntos sobre fondo blanco" width="1080" height="1926" fetchpriority="high" decoding="async">
        </picture>
      </div>
    </div>
  </section>

  <section class="strip">
    <div class="wrap strip__in">
      <div class="strip__i">{SVG['truck']}<div><b>Envío gratis desde {eur(FREE_FROM)}</b><span>Entrega en {DELIVERY} días laborables en España</span></div></div>
      <div class="strip__i">{SVG['return']}<div><b>Devoluciones {RETURNS} días</b><span>Cambios sencillos, sin preguntas incómodas</span></div></div>
      <div class="strip__i">{SVG['shield']}<div><b>Pago seguro</b><span>Tarjeta y pagos móviles con cifrado</span></div></div>
      <div class="strip__i">{SVG['heart']}<div><b>Un porcentaje a investigación</b><span>Cáncer y enfermedades raras en mascotas</span></div></div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="section-head reveal">
        <div>
          <p class="kicker">Colecciones</p>
          <h2 class="h2">Todo lo que llevan puesto (y lo que usan en casa).</h2>
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
        <a class="link-arrow" href="tienda.html">Ver las {len(PRODUCTS)} referencias</a>
      </div>
      <div class="reveal">{products_grid(featured, ranks)}</div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="section-head reveal">
        <div>
          <p class="kicker">Compra mejor, compra en conjunto</p>
          <h2 class="h2">Packs con descuento</h2>
          <p class="lede mt-s">Conjuntos pensados para resolver el paseo completo o un rincón de la casa, coordinados en color y con envío gratis incluido.</p>
        </div>
        <div class="packs-cta reveal">
          <a class="btn btn--lg" href="tienda.html?cat=packs">
            Ver los {len(PACKS)} packs <span class="btn__arrow" aria-hidden="true">→</span>
          </a>
          <span class="packs-cta__note">Envío gratis incluido · desde {eur(min(pk['price'] for pk in PACKS))}</span>
        </div>
      </div>
      <div class="reveal">{products_grid(packs_home)}</div>
    </div>
  </section>

  <section class="section memorial" id="compromiso">
    <div class="wrap memorial__in">
      <figure class="memorial__media reveal">
        <img src="{KHALID}" alt="Khalid, un gato blanco de ojos claros, sentado junto a una ventana" width="1000" height="1000" loading="lazy" decoding="async">
        <figcaption>Khalid</figcaption>
      </figure>
      <div class="reveal">
        <p class="kicker kicker--light">Compromiso y corazón</p>
        <blockquote>«Khalid, mi gatito blanco. Sordo de nacimiento pero mi amigo inseparable y el compañero más cariñoso que he tenido. Perderle por un cáncer de colon me rompió; nadie debería cargar con ese dolor ni ninguna mascota debería padecerlo»</blockquote>
        <p>Esta web no es solo un escaparate de productos: es un legado personal nacido del amor y la pérdida. Por eso, <strong>un porcentaje de los beneficios de GRANKHA</strong> irá destinado directamente a la investigación del cáncer y las enfermedades raras en nuestras mascotas.</p>
        <div class="donate-note">{SVG['ribbon']}<div><b>GRANKHA por la salud animal</b><br>
        <span style="font-size:.88rem">Khalid sigue en el ADN de esta marca, impulsándonos a cuidar de los tuyos como él cuidó de mí.</span></div></div>
        <p class="mt-m"><a class="link-arrow" href="compromiso.html" style="color:#fff;border-color:#fff">Leer nuestra historia completa</a></p>
      </div>
    </div>
  </section>

  <section class="section section--paper">
    <div class="wrap news">
      <div class="reveal">
        <p class="kicker">Comunidad</p>
        <h2 class="h2">Únete a la familia GRANKHA.</h2>
        <p class="lede mt-s">Consejos de cuidado para perros y gatos, novedades de producto y avances en investigación animal. Sin ruido, sin spam.</p>
      </div>
      <div class="reveal">
        <form data-news>
          <input type="email" required placeholder="tu@email.com" aria-label="Tu email">
          <button class="btn" type="submit">Suscribirme</button>
          <label class="consent small"><input type="checkbox" required>
            Acepto recibir novedades de GRANKHA y he leído la
            <a href="legal.html#privacidad" style="text-decoration:underline">política de privacidad</a>.</label>
        </form>
        <p class="small mt-s">Puedes darte de baja en cualquier momento con un clic.</p>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    jsonld = [{
        "@context": "https://schema.org", "@type": "OnlineStore", "name": SITE["name"], "url": BASE,
        "logo": f"{BASE}/assets/img/hero.jpg", "email": SITE["contactEmail"],
        "currenciesAccepted": "EUR", "areaServed": "ES",
        "description": ("Accesorios de diseño para perros y gatos. Un porcentaje de los beneficios financia "
                        "la investigación del cáncer y enfermedades raras en mascotas. En memoria de Khalid."),
    }, {"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": BASE}]
    desc = (f"Arneses, correas, camas, comederos y fuentes para perros y gatos. Envío gratis desde {eur(FREE_FROM)}, "
            f"devoluciones de {RETURNS} días y {DON_TEXT.lower()} de los beneficios a investigación animal.")
    write("index.html", head(f"{SITE['name']} · {SITE['tagline']}", desc, "index.html", jsonld=jsonld)
          + body + tail())

# ------------------------------------------------------------------ tienda
def build_tienda():
    chips = '<button class="chip is-on" data-filter="todo">Todo</button>' + "".join(
        f'<button class="chip" data-filter="{c}">{n}</button>' for c, n, _ in CATS)
    auds = ('<button class="chip is-on" data-aud="todos">Perros y gatos</button>'
            f'<button class="chip" data-aud="perro">{SVG["dog"]} Perros</button>'
            f'<button class="chip" data-aud="gato">{SVG["cat"]} Gatos</button>')
    body = f"""{header("tienda")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Tienda</p>
      <h1 class="h3" style="font-size:clamp(2rem,5vw,3.4rem)">La colección completa</h1>
      <p class="lede mt-s">{len(PRODUCTS)} referencias para perros y gatos: {len(PROD)} productos y {len(PACKS)} packs con descuento. Precios con IVA incluido, envío gratis en península desde {eur(FREE_FROM)} y devoluciones durante {RETURNS} días.</p>
    </div>
  </section>
  <section class="section section--tight" style="padding-top:0">
    <div class="wrap">
      <div class="section-head" style="margin-bottom:22px;align-items:center">
        <div class="filters">{chips}</div>
        <div class="filters">
          <input class="chip" id="shop-search" type="search" placeholder="Buscar…" aria-label="Buscar productos" style="min-width:160px;text-transform:none;letter-spacing:0">
          <select class="chip" id="shop-sort" aria-label="Ordenar">
            <option value="destacados">Destacados</option>
            <option value="precio-asc">Precio: menor a mayor</option>
            <option value="precio-desc">Precio: mayor a menor</option>
            <option value="nombre">Nombre A-Z</option>
          </select>
        </div>
      </div>
      <div class="section-head" style="margin-bottom:18px;align-items:center">
        <div class="filters">{auds}</div>
        <p class="small mb-0" id="shop-count">{len(PRODUCTS)} referencias</p>
      </div>
      <div id="shop-grid">{products_grid(PRODUCTS)}</div>
      <div class="empty hide" id="shop-empty">
        <h3 class="h4">Sin resultados</h3>
        <p class="small mt-s">Prueba con otra búsqueda o revisa todas las categorías.</p>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    write("tienda.html", head(f"Tienda · {SITE['name']} — Accesorios para perros y gatos",
          f"Todos los accesorios GRANKHA para perros y gatos: arneses, correas, camas, comederos y fuentes. "
          f"IVA incluido, envío gratis desde {eur(FREE_FROM)} y packs con descuento.", "tienda.html")
          + body + tail())

# ------------------------------------------------------------------ ficha
def build_product(p):
    is_pack = p["kind"] == "pack"
    rel = [q for q in PRODUCTS if q["cat"] == p["cat"] and q["slug"] != p["slug"]]
    rel.sort(key=lambda q: (q["kind"] != p["kind"], q["price"]))
    rel = rel[:4]
    specs = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in p["specs"])
    bullets = "".join(f"<li>{SVG['paw']}<span>{esc(b)}</span></li>" for b in p["bullets"])
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in p.get("tags", []))

    variants = ""
    if not is_pack:
        sib = [q for q in PROD if q["name"] == p["name"] and q["slug"] != p["slug"]]
        if sib:
            links = "".join(
                f'<a class="chip" data-variant href="{q["slug"]}.html" style="display:inline-flex;align-items:center;gap:8px">'
                f'<span class="swatch" style="background:{q["colorHex"]}"></span>'
                f'{esc(q["subtitle"].split("·")[0].strip() + " · " + q["color"])}</a>' for q in sib[:10])
            variants = (f'<div class="mt-m"><p class="small mb-m">Otras variantes de '
                        f'<b>{esc(p["name"])}</b></p><div class="filters">{links}</div></div>')
    else:
        rows = "".join(
            f'<li>{SVG["box"]}<span><a href="{c["slug"]}.html" style="text-decoration:underline">{esc(c["name"])}</a>'
            f'{" × " + str(c["qty"]) if c["qty"] > 1 else ""}</span></li>' for c in p["components"])
        variants = f"""<div class="notice mt-m"><b>Este pack incluye {len(p["components"])} piezas:</b>
          <ul class="usp" style="border:0;margin-top:8px">{rows}</ul>
          </div>"""

    # galería: los packs muestran sus piezas una a una en un deslizador
    if is_pack:
        slides = ""
        for i, c in enumerate(p["components"]):
            comp = by_sku[c["sku"]]
            qty = f'{c["qty"]}× ' if c["qty"] > 1 else ""
            slides += f"""<figure class="gallery__slide">
        <img src="{PHOTO[comp['slug']]}" alt="{esc(comp['name'] + ' — ' + comp['subtitle'])}" width="900" height="900"{' fetchpriority="high"' if i == 0 else ''} loading="{'eager' if i == 0 else 'lazy'}" decoding="async">
        <figcaption><b>{qty}{esc(comp['name'])}</b><span>{esc(comp['subtitle'])}</span></figcaption>
      </figure>"""
        media = f"""<div class="gallery" data-gallery>
        <div class="gallery__viewport">
          <div class="gallery__track">{slides}</div>
          <button class="gallery__nav gallery__nav--prev" type="button" data-gprev aria-label="Ver pieza anterior">‹</button>
          <button class="gallery__nav gallery__nav--next" type="button" data-gnext aria-label="Ver pieza siguiente">›</button>
        </div>
        <div class="gallery__bar">
          <span class="small">Desliza para ver las {len(p['components'])} piezas del pack</span>
          <span class="gallery__dots" data-gdots></span>
          <span class="gallery__pos mono" data-gpos>1 / {len(p['components'])}</span>
        </div>
      </div>"""
    else:
        media = (f'<img src="{PHOTO[p["slug"]]}" alt="{esc(p["name"] + " — " + p["subtitle"])}" '
                 f'width="900" height="900" fetchpriority="high">')

    stock = p["stock"]
    avail = ("https://schema.org/InStock" if stock > 5 else
             ("https://schema.org/LimitedAvailability" if stock > 0 else "https://schema.org/OutOfStock"))
    why = f'<div class="notice mt-m"><b>Por qué lo tenemos</b><br>{esc(p["why"])}</div>' if p.get("why") else ""
    pledge = ""
    if (not is_pack and p.get("prevPrice") and p["price"] > 0
            and p["prevPrice"] > p["price"] * 1.15):
        pledge = (f'<p class="small mt-s">Precio anterior {eur(p["prevPrice"])} · ajustado para estar en línea '
                  f'con el mercado real.</p>')

    body = f"""{header(p['cat'])}
<main>
  <div class="wrap crumbs">
    <a href="index.html">Inicio</a><span>/</span><a href="tienda.html">Tienda</a><span>/</span>
    <a href="tienda.html?cat={p['cat']}">{esc(p['catName'])}</a><span>/</span><span>{esc(p['name'])}</span>
  </div>
  <section class="wrap pd" id="pd" data-slug="{p['slug']}" data-sku="{p['sku']}">
    <div class="pd__media reveal">
      {media}
    </div>
    <div>
      <p class="kicker">{esc(p['audienceLabel'] or p['catName'])} · {esc(p['collection'])}</p>
      <h1 class="h2 pd__title">{esc(p['name'])}</h1>
      <p class="lede">{esc(p['subtitle'] if not is_pack else pack_of(p))}</p>
      <div class="pd__price">
        {price_block(p, big=True)}
        <span class="tax">IVA incluido · Envío gratis desde {eur(FREE_FROM)}</span>
      </div>
      {pledge}
      <p class="small" data-stock="{stock}">Disponible · envío en {DELIVERY} días laborables</p>
      <div class="pd__buy">
        <div class="qty" data-pdqty data-max="{max(1, min(stock, 20))}">
          <button type="button" data-step="-1" aria-label="Menos">−</button>
          <input type="number" value="1" min="1" max="{max(1, min(stock, 20))}" aria-label="Cantidad">
          <button type="button" data-step="1" aria-label="Más">+</button>
        </div>
        <button class="btn btn--ghost" data-add="{p['slug']}">Añadir a la cesta</button>
        <button class="btn" data-buy="{p['slug']}">Comprar ahora</button>
      </div>
      <div class="filters" style="margin-top:4px">{tags}</div>
      {why}
      <ul class="usp">
        <li>{SVG['truck']}<span><b>Envío gratis</b> desde {eur(FREE_FROM)} · entrega en {DELIVERY} días laborables</span></li>
        <li>{SVG['return']}<span><b>Devoluciones fáciles</b> durante {RETURNS} días</span></li>
        <li>{SVG['lock']}<span><b>Pago seguro</b> con cifrado · tarjeta y pagos móviles</span></li>
        <li>{SVG['heart']}<span><b>Un porcentaje de los beneficios</b> se destina a investigación animal</span></li>
      </ul>
      <div class="acc">
        <details open><summary>Descripción</summary><div class="acc__body">{esc(p['desc'])}</div></details>
        <details><summary>Características</summary><div class="acc__body"><ul style="padding-left:18px;margin:0">{''.join(f'<li>{esc(b)}</li>' for b in p['bullets'])}</ul></div></details>
        <details><summary>Detalles y medidas</summary><div class="acc__body"><table class="spec-table">{specs}</table></div></details>
        <details><summary>Envío y devoluciones</summary><div class="acc__body">
          <p>Preparamos tu pedido en 24-48 h y lo enviamos con seguimiento. Entrega estimada en {DELIVERY} días laborables en España peninsular. Envío gratis a partir de {eur(FREE_FROM)}; por debajo, desde {eur(5.95)}. Tarifas completas en <a href="envios.html">Envíos y devoluciones</a>.</p>
          <p>Si algo no encaja, tienes {RETURNS} días para devolverlo.</p>
        </div></details>
        <details><summary>Garantía y cuidado</summary><div class="acc__body">
          <p>Garantía legal de conformidad de 3 años en España. Ante cualquier defecto de fabricación, escríbenos a <a href="mailto:{SITE['contactEmail']}">{SITE['contactEmail']}</a> y lo solucionamos.</p>
        </div></details>
      </div>
      {variants}
      <div id="pd-pack"></div>
    </div>
  </section>

  <section class="memorial" style="padding-block:clamp(40px,6vw,72px)">
    <div class="wrap pledge">
      <div class="donate-note" style="margin:0">{SVG['ribbon']}<div><b>GRANKHA por la salud animal</b><br>
        <span style="font-size:.88rem">Un porcentaje de los beneficios irá destinado a la investigación del cáncer y las enfermedades raras en mascotas.</span></div></div>
      <div>
        <h3 class="h3" style="margin-bottom:10px;color:#fff">Esta compra también investiga.</h3>
        <p>Cada pedido reserva una parte del beneficio para proyectos de investigación veterinaria. Khalid, un gato blanco que perdimos por un cáncer de colon, es la razón. <a href="compromiso.html" style="color:#fff;text-decoration:underline">Nuestra historia</a>.</p>
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
        "name": f"{p['name']} · {p['subtitle']}", "description": p["desc"][:400],
        "sku": p["sku"], "brand": {"@type": "Brand", "name": "GRANKHA"},
        "image": [f"{BASE}/{og}"], "color": p.get("color", ""),
        "audience": {"@type": "PeopleAudience", "suggestedMinAge": 0},
        "offers": {
            "@type": "Offer", "url": f"{BASE}/{p['slug']}.html", "price": f"{p['price']:.2f}",
            "priceCurrency": "EUR", "availability": avail,
            "itemCondition": "https://schema.org/NewCondition",
            "shippingDetails": {"@type": "OfferShippingDetails",
                "shippingRate": {"@type": "MonetaryAmount", "value": "0", "currency": "EUR"},
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
            {"@type": "ListItem", "position": 3, "name": p["name"], "item": f"{BASE}/{p['slug']}.html"},
        ],
    }]
    title = f"{p['name']} · {p['subtitle']} — GRANKHA"
    desc = f"{p['name']} ({p['subtitle']}). {p['desc'][:120]}… IVA incluido, envío gratis desde {eur(FREE_FROM)}."
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
        <p class="mt-m"><a class="btn" href="tienda.html">Ver la colección</a>
        <a class="btn btn--ghost" href="tienda.html?cat=packs">Ver packs con descuento</a></p>
      </div>

      <div class="cart" id="cart-root">
        <div>
          <div id="cart-lines"></div>
          <p class="small mt-m">Precios con IVA incluido. Gastos de envío calculados por zona y tramo de cesta:
          menos de 20 € → {eur(5.95)}; de 20 € a {eur(FREE_FROM - 0.01)} → {eur(3.95)}; desde {eur(FREE_FROM)} → gratis (península).</p>
        </div>
        <aside>
          <div id="cart-shipping" class="mb-m"></div>
          <div class="summary" id="cart-summary"></div>
        </aside>
      </div>

      <div id="checkout" class="section hide" style="padding-block:clamp(30px,5vw,60px) 0">
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
          <p class="small">{SVG['lock']} Pago con tarjeta en entorno seguro (Stripe). GRANKHA no almacena datos de tarjeta.
          Con cada pedido reservamos un porcentaje del beneficio para investigación veterinaria.</p>
        </form>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    write("carrito.html", head(f"Carrito · {SITE['name']}",
          f"Revisa tu cesta y finaliza tu pedido. Envío gratis en península desde {eur(FREE_FROM)} y devoluciones en {RETURNS} días.",
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
      <h1 class="h2" style="font-size:clamp(2.2rem,6vw,4.4rem)">In memoriam: Khalid.</h1>
      <p class="lede mt-m">Khalid, mi gatito blanco. Sordo de nacimiento pero mi amigo inseparable y el compañero más cariñoso que he tenido. Perderle por un cáncer de colon me rompió; nadie debería cargar con ese dolor ni ninguna mascota debería padecerlo.</p>
      <p class="lede mt-s">En GRANKHA creemos que el diseño solo tiene sentido si sirve para proteger aquello que amamos.</p>
    </div>
  </section>

  <section class="section" style="padding-top:0">
    <div class="wrap split">
      <figure class="memorial__media reveal" style="margin:0">
        <img src="{KHALID}" alt="Khalid, un gato blanco de ojos claros, sentado junto a una ventana" width="1000" height="1000">
        <figcaption style="color:var(--muted)">Khalid</figcaption>
      </figure>
      <div class="prose reveal">
        <p><b>En GRANKHA, creemos que la tecnología solo tiene sentido si sirve para proteger aquello que amamos.</b> Esta web no es solo un escaparate de productos, es un legado personal nacido del amor y la pérdida.</p>
        <p>Hace poco perdí a mi gran amigo Khalid debido a un cáncer de colon. No hay día que pase sin que su recuerdo me acompañe. Verle sufrir, ver cómo su luz se apagaba lentamente y tener que tomar la dolorosa decisión de dejarle marchar cuando ya no había solución, es un dolor que ningún dueño debería cargar solo ni ninguna mascota debería padecer.</p>
        <p>Por eso, <b>un porcentaje de los beneficios de GRANKHA</b> irá destinado directamente a la investigación del cáncer y enfermedades raras en nuestras mascotas. Queremos contribuir a que el desconocimiento no sea la causa de más sufrimiento. Queremos evitar ese dolor tanto al animal como a sus familias. Khalid siempre estará en el ADN de esta marca, impulsándonos a cuidar de los tuyos como él cuidó de mí.</p>
        <blockquote class="mt-m" style="margin:34px 0 0;padding-left:20px;border-left:2px solid var(--ink);font-size:clamp(1.1rem,1.9vw,1.5rem);letter-spacing:-.02em"><b>GRANKHA por la salud animal</b></blockquote>
        <p class="small mt-m">Khalid era un gato: la tienda nace de él, y por eso aquí encontrarás accesorios para gatos y para perros,
        sin favoritismos. Los gatos también salen a pasear, también necesitan beber, también duermen en coronas.</p>
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
        <div class="donate-note" style="margin:0">{SVG['heart']}<div><b>Un porcentaje de los beneficios</b><br><span style="font-size:.88rem">Se reserva cada mes de forma continua, no solo en campañas puntuales.</span></div></div>
        <div class="donate-note" style="margin:0">{SVG['shield']}<div><b>Entidades verificadas</b><br><span style="font-size:.88rem">Buscamos grupos de investigación con programas en oncología y enfermedades raras veterinarias.</span></div></div>
        <div class="donate-note" style="margin:0">{SVG['ribbon']}<div><b>Transparencia</b><br><span style="font-size:.88rem">Publicaremos un resumen anual con importes donados y proyectos apoyados, con nombre y apellidos.</span></div></div>
      </div>
      <div class="notice notice--light mt-l">
        <b>¿Quieres proponer un proyecto?</b><br>
        Si conoces una entidad o un equipo que trabaje en cáncer o enfermedades raras en animales, escríbenos a
        <a href="mailto:{SITE['contactEmail']}" style="color:#fff">{SITE['contactEmail']}</a>. Leemos todo.
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap prose">
      <h2 style="margin-top:0">Preguntas sobre el compromiso</h2>
      <h3>¿Qué porcentaje de los beneficios se dona?</h3>
      <p><b>Un porcentaje de los beneficios.</b> Sale del margen de GRANKHA (no es un recargo en el pedido) y se reserva pedido a pedido desde el primer día. El importe exacto se revisa cada ejercicio y se comunica en el resumen anual de donaciones.</p>
      <h3>¿Cuándo se hace la donación?</h3>
      <p>La reserva es continua y la aportación se materializa al cierre del ejercicio o cuando el importe acumulado permite una aportación útil al proyecto elegido.</p>
      <h3>¿Esto sube el precio de los productos?</h3>
      <p>No. Los precios se fijan según el coste del producto, el envío y la gestión. La donación sale del beneficio, no de un recargo que pagues tú.</p>
      <h3>¿Por qué la tienda es de perros y gatos?</h3>
      <p>Porque Khalid era un gato, y porque en casa conviven los dos. Los arneses, camas y comederos están pensados para perros pequeños y gatos; las correas y fuentes, para ambos. Si dudas de si un producto encaja con tu mascota, pregúntanos antes de comprar.</p>
      <h3>Mi mascota está enferma, ¿podéis ayudarme?</h3>
      <p>No somos veterinarios ni podemos dar diagnóstico. Si tu mascota está enferma, acude a un profesional. Podemos orientarte sobre a qué entidades o asociaciones acudir: escríbenos y te ayudamos en lo que esté en nuestra mano.</p>
    </div>
  </section>
</main>
{footer()}"""
    write("compromiso.html", head(f"Compromiso y corazón · {SITE['name']}",
          f"En memoria de Khalid, un gato blanco: {DON_TEXT.lower()} de los beneficios de GRANKHA financia "
          "la investigación del cáncer y las enfermedades raras en mascotas.",
          "compromiso.html", og="assets/img/khalid.jpg") + body + tail())

# ------------------------------------------------------------------ envíos
def build_envios():
    rows = ""
    for o in SHIP_OPTS:
        tiers = " · ".join(
            (f"desde {eur(t['min'])}: gratis" if t["price"] == 0 else f"de {eur(t['min'])} a {eur(t['price'])}"
             if t["min"] > 0 else f"hasta {eur(o['tiers'][1]['min'] - 0.01)}: {eur(t['price'])}")
            for t in o["tiers"])
        rows += f"<tr><td>{esc(o['name'])}</td><td>{tiers}</td><td>{esc(o['eta'])}</td></tr>"
    body = f"""{header("")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Envíos y devoluciones</p>
      <h1 class="h2" style="font-size:clamp(2rem,5vw,3.6rem)">Llega rápido, vuelve fácil.</h1>
      <p class="lede mt-m">Enviamos con seguimiento y plazos realistas. El envío es gratis en península desde {eur(FREE_FROM)},
      y si algo no encaja tienes {RETURNS} días para cambiarlo o devolverlo.</p>
    </div>
  </section>
  <section class="section" style="padding-top:0">
    <div class="wrap">
      <h2 class="h3">Tarifas de envío por tramos</h2>
      <table class="table mt-m">
        <thead><tr><th>Destino</th><th>Tramo de cesta</th><th>Plazo estimado</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p class="small mt-s">Precios con impuestos incluidos. {esc(SITE['shipping']['note'])}
      ¿Por qué por tramos? Porque el envío tiene un coste real: en pedidos pequeños lo cubrimos casi íntegro y,
      a partir de {eur(FREE_FROM)}, lo asumimos nosotros. Así los precios de los productos se mantienen justos.</p>

      <h2 class="h3 mt-l">Cómo funciona</h2>
      <div class="grid g3 mt-m">
        <div class="notice"><b>1 · Preparación</b><br>Verificamos y preparamos tu pedido en 24-48 horas laborables.</div>
        <div class="notice"><b>2 · Envío con seguimiento</b><br>Recibes un email con el número de seguimiento en cuanto sale del almacén; puedes consultar el estado del envío en la web del transportista.</div>
        <div class="notice"><b>3 · Entrega</b><br>Entrega en {DELIVERY} días laborables con aviso del transportista. Si no estás, se reintenta o se deja en punto de recogida.</div>
      </div>

      <h2 class="h3 mt-l" id="seguimiento">Seguimiento del pedido</h2>
      <div class="prose">
        <p>Cuando tu pedido sale del almacén recibes un email con:</p>
        <ul>
          <li><b>Número de pedido</b> (formato GRK-XXXXXX-XXXX) para cualquier consulta.</li>
          <li><b>Número de seguimiento</b> y enlace del transportista para ver dónde está tu paquete.</li>
          <li>La fecha estimada de entrega.</li>
        </ul>
        <p>¿No lo encuentras? Escríbenos a <a href="mailto:{SITE['contactEmail']}">{SITE['contactEmail']}</a> con tu
        número de pedido y lo comprobamos nosotros por ti.</p>
      </div>

      <h2 class="h3 mt-l" id="devoluciones">Devoluciones y cambios</h2>
      <div class="prose">
        <p>Puedes devolver cualquier producto en los <b>{RETURNS} días</b> siguientes a la entrega sin justificar el motivo
        (muy por encima de los 14 días naturales que exige la ley). Condiciones:</p>
        <ul>
          <li>El producto debe estar sin usar, con su embalaje original.</li>
          <li>Por higiene no se admiten devoluciones de productos usados o con pelo, salvo defecto de fabricación.</li>
          <li>Escríbenos con el número de pedido e indícanos qué quieres devolver.</li>
          <li>Reembolso por el mismo método de pago en un máximo de 14 días desde la recepción.</li>
          <li>Si el producto llega defectuoso o incorrecto, el coste de la devolución corre de nuestra cuenta.</li>
        </ul>
        <h2 id="faq">Preguntas frecuentes</h2>
        <h3>¿Puedo cambiar la talla de un arnés?</h3>
        <p>Sí. Los arneses Guardian van de 2-4 kg (XS) y 4-8 kg (S). Si la talla no queda bien, escríbenos dentro de los {RETURNS} días y gestionamos el cambio.</p>
        <h3>¿Los productos sirven para gatos?</h3>
        <p>Las correas, camas, comederos y fuentes están pensados para perros pequeños y gatos. En cada ficha indicamos para quién es. Si tu gato es grande o muy nervioso, pregúntanos antes.</p>
        <h3>¿Enviáis a Canarias, Ceuta y Melilla?</h3>
        <p>Sí. Estas entregas pueden requerir despacho de aduanas y el pago de IGIC/IPSI en destino, que corre por cuenta del cliente.</p>
        <h3>¿Puedo modificar mi pedido después de comprarlo?</h3>
        <p>Si aún no lo hemos preparado, sí. Escríbenos lo antes posible.</p>
        <h3>¿Necesito registrarme para comprar?</h3>
        <p>No. Puedes comprar como invitado con los datos imprescindibles para entregar el pedido.</p>
      </div>
    </div>
  </section>
</main>
{footer()}"""
    write("envios.html", head(f"Envíos, seguimiento y devoluciones · {SITE['name']}",
          f"Tarifas de envío por tramos, seguimiento del pedido y devoluciones de {RETURNS} días.", "envios.html")
          + body + tail())

# ------------------------------------------------------------------ contacto
def build_contacto():
    body = f"""{header("")}
<main>
  <section class="section section--tight">
    <div class="wrap">
      <p class="kicker">Contacto</p>
      <h1 class="h2" style="font-size:clamp(2rem,5vw,3.4rem)">Hablemos.</h1>
      <p class="lede mt-m">¿Dudas sobre si un producto encaja con tu perro o tu gato, sobre una talla, un pedido
      o una devolución? Escríbenos: contestamos en menos de 24 horas laborables.</p>
    </div>
  </section>
  <section class="section" style="padding-top:0">
    <div class="wrap split">
      <div>
        <ul class="usp" style="margin-top:0">
          <li>{SVG['lock']}<span><b>Email</b><br><a href="mailto:{SITE['contactEmail']}" style="text-decoration:underline">{SITE['contactEmail']}</a></span></li>
          <li>{SVG['truck']}<span><b>Pedidos y envíos</b><br>Incluye tu número de pedido (GRK-…) para que te ayudemos más rápido.</span></li>
          <li>{SVG['return']}<span><b>Devoluciones</b><br>Indica qué producto quieres devolver; el motivo es opcional.</span></li>
          <li>{SVG['heart']}<span><b>Propuestas de investigación</b><br>Entidades y equipos que trabajen en cáncer o enfermedades raras en mascotas.</span></li>
        </ul>
        <p class="small mt-m">GRANKHA · {esc(SITE['legal_name'])} · {esc(SITE['contactEmail'])}</p>
      </div>
      <form class="form" data-contact>
        <div class="f2">
          <div class="field"><label for="c-name">Nombre *</label><input id="c-name" name="nombre" required></div>
          <div class="field"><label for="c-email">Email *</label><input id="c-email" name="email" type="email" required></div>
        </div>
        <div class="f2">
          <div class="field"><label for="c-ref">Nº de pedido (opcional)</label><input id="c-ref" name="pedido" placeholder="GRK-XXXXXX-XXXX"></div>
          <div class="field"><label for="c-pet">Mi mascota es…</label>
            <select id="c-pet" name="mascota"><option>Perro</option><option>Gato</option><option>Perro y gato</option><option>Otro</option></select></div>
        </div>
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
          "Atención al cliente de GRANKHA: dudas sobre tallas, productos para perros y gatos, pedidos y devoluciones.",
          "contacto.html") + body + tail())

# ------------------------------------------------------------------ legal
def build_legal():
    tier_pen = SHIP_OPTS[0]["tiers"]
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
      <!-- HUECOS PENDIENTES (invisibles para el cliente): razón social, NIF, domicilio fiscal y teléfono.
           Se sustituyen en cuanto el titular facilite los datos. Ver docs/PENDIENTES.md -->

      <h2 id="aviso">Aviso legal</h2>
      <p>En cumplimiento del artículo 10 de la Ley 34/2002 (LSSI-CE), se informa:</p>
      <ul>
        <li><b>Titular:</b> [RAZÓN SOCIAL / NOMBRE Y APELLIDOS]</li>
        <li><b>Nombre comercial:</b> GRANKHA · {esc(SITE['legal_name'])}</li>
        <li><b>NIF:</b> [NIF]</li>
        <li><b>Domicilio:</b> [DIRECCIÓN COMPLETA, CP, LOCALIDAD, MADRID, ESPAÑA]</li>
        <li><b>Email:</b> {esc(SITE['contactEmail'])}</li>
        <li><b>Actividad:</b> comercio electrónico de accesorios para mascotas.</li>
      </ul>
      <p>El acceso y uso de este sitio atribuye la condición de usuario e implica la aceptación de este aviso legal.
      Los contenidos, marcas y diseños son propiedad de su titular o se utilizan con autorización.</p>

      <h2 id="condiciones">Condiciones generales de venta</h2>
      <h3>1. Proceso de compra</h3>
      <p>El pedido se formaliza cuando el usuario completa el formulario y recibe la confirmación por email.
      GRANKHA puede cancelar pedidos con errores evidentes de precio o disponibilidad, reembolsando el importe íntegro.</p>
      <h3>2. Precios e impuestos</h3>
      <p>Los precios se muestran en euros <b>con el IVA español (21 %) incluido</b> para envíos a la España peninsular y Baleares.
      En Canarias, Ceuta y Melilla no se aplica el IVA: el impuesto correspondiente (IGIC/IPSI) y los posibles gastos
      aduaneros se liquidan en destino a cargo del cliente.</p>
      <h3>3. Gastos de envío</h3>
      <p>Los gastos de envío se calculan por zona y tramo de cesta y se muestran antes de finalizar la compra.
      España peninsular: {eur(tier_pen[0]['price'])} hasta {eur(20 - 0.01)}, {eur(tier_pen[1]['price'])} de {eur(20)} a {eur(FREE_FROM - 0.01)}
      y <b>gratis desde {eur(FREE_FROM)}</b>. Resto de zonas, en <a href="envios.html">Envíos y devoluciones</a>.</p>
      <h3>4. Entrega y seguimiento</h3>
      <p>Plazo estimado: {DELIVERY} días laborables desde la confirmación. Enviamos con número de seguimiento que
      recibirás por email. Los retrasos por causas ajenas (aduanas, transporte, fuerza mayor) no generan derecho a
      indemnización, sin perjuicio del derecho de desistimiento.</p>
      <h3>5. Desistimiento y devoluciones</h3>
      <p>Dispones de <b>{RETURNS} días</b> desde la recepción para devolver el producto sin justificar el motivo,
      muy por encima de los 14 días naturales legales. Condiciones en <a href="envios.html#devoluciones">Envíos y devoluciones</a>.</p>
      <h3>6. Garantía legal</h3>
      <p>Garantía legal de conformidad de <b>3 años</b> desde la entrega (RDL 1/2007). Ante un defecto de origen,
      GRANKHA asume reparación, sustitución, rebaja o reembolso.</p>
      <h3>7. Compromiso de donación</h3>
      <p>Un porcentaje de los beneficios de GRANKHA se reserva para la investigación del cáncer y las
      enfermedades raras en mascotas. Es un compromiso de marca, no una condición del contrato de compraventa: si en algún
      ejercicio no hubiera beneficios, no habría aportación, y se informará en el resumen anual de donaciones.</p>
      <h3>8. Atención al cliente y resolución de conflictos</h3>
      <p>Para cualquier reclamación, escribe a {esc(SITE['contactEmail'])}. También puedes acudir a la Junta Arbitral
      de Consumo de tu provincia o a la plataforma europea de resolución de litigios en línea (<a href="https://ec.europa.eu/consumers/odr" rel="noopener" target="_blank">ec.europa.eu/consumers/odr</a>). No estamos adheridos a
      ningún sistema arbitral de consumo.</p>

      <h2 id="privacidad">Política de privacidad</h2>
      <p>De acuerdo con el RGPD (UE 2016/679) y la LOPDGDD:</p>
      <ul>
        <li><b>Responsable:</b> [RAZÓN SOCIAL], NIF [NIF], correo {esc(SITE['contactEmail'])}.</li>
        <li><b>Finalidades:</b> gestionar tu pedido y su envío, atender consultas y devoluciones y —si lo autorizas— enviarte novedades.</li>
        <li><b>Base jurídica:</b> ejecución del contrato, consentimiento (newsletter), interés legítimo y obligación legal.</li>
        <li><b>Destinatarios:</b> proveedor logístico y transportista que entrega el pedido, pasarela de pago (Stripe) y
        proveedores técnicos de hosting y correo. No se venden datos a terceros.</li>
        <li><b>Conservación:</b> datos de pedido durante los plazos legales (facturación: 4 años; garantías: 3 años);
        newsletter hasta que te des de baja.</li>
        <li><b>Derechos:</b> acceder, rectificar, suprimir, oponerte, limitar y portar tus datos escribiendo a
        {esc(SITE['contactEmail'])}. Puedes reclamar ante la Agencia Española de Protección de Datos.</li>
      </ul>
      <p>Los datos de pago se introducen directamente en la pasarela del proveedor de pagos; GRANKHA no almacena números de tarjeta.
      El carrito se guarda únicamente en tu navegador (almacenamiento local).</p>

      <h2 id="cookies">Política de cookies</h2>
      <p>Esta web <b>no utiliza cookies publicitarias ni de seguimiento</b>. Solo emplea almacenamiento local del navegador
      para recordar tu carrito y tus preferencias: la información permanece en tu dispositivo y puedes borrarla desde los
      ajustes de tu navegador. Si en el futuro se incorporan herramientas de analítica o píxeles publicitarios, se pedirá
      consentimiento previo.</p>

      <h2>Productos y responsabilidad</h2>
      <p>Las imágenes son orientativas; pueden existir ligeras variaciones de tono entre lotes. La información de esta web
      no sustituye el consejo veterinario. Ante ingestión de piezas pequeñas o reacción adversa, acude a tu veterinario.</p>
    </div>
  </section>
</main>
{footer()}"""
    write("legal.html", head(f"Legal · {SITE['name']}",
          "Aviso legal, condiciones de venta, envíos por tramos, privacidad y cookies de GRANKHA.", "legal.html")
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
      <p class="mt-l"><a class="btn" href="tienda.html">Ver la colección</a>
      <a class="btn btn--ghost" href="index.html">Volver al inicio</a></p>
    </div>
  </section>
</main>
{footer()}"""
    write("404.html", head(f"Página no encontrada · {SITE['name']}", "Página no encontrada.", "404.html")
          + body + tail())

# ------------------------------------------------------------------ extras
def build_extras():
    # precios en servidor para la función de Stripe (evita que nadie manipule importes)
    prices = {p["sku"]: {"price": p["price"], "name": f"{p['name']} · {p['subtitle']}"} for p in PRODUCTS}
    costs = {p["sku"]: p.get("cost", 0) for p in PRODUCTS}
    fn_dir = ROOT / "supabase" / "functions" / "create-checkout"
    fn_dir.mkdir(parents=True, exist_ok=True)
    (fn_dir / "prices.json").write_text(json.dumps({**prices, "costs": costs}, ensure_ascii=False, indent=1))
    print(f"  · supabase/.../prices.json ({len(prices)} referencias)")

    # redirecciones desde los slugs anteriores (SEO)
    OLD = {
        "arnes-guardian-xs-rosa-suave-cuarzo": "arnes-de-paso-guardian-xs-rosa-suave",
        "arnes-guardian-xs-lavanda-amatista": "arnes-de-paso-guardian-xs-lavanda",
        "arnes-guardian-xs-rock-grey-obsidiana": "arnes-de-paso-guardian-xs-rock-grey",
        "arnes-guardian-s-rosa-suave-cuarzo": "arnes-de-paso-guardian-s-rosa-suave",
        "arnes-guardian-s-lavanda-amatista": "arnes-de-paso-guardian-s-lavanda",
        "arnes-guardian-s-gris-roca-obsidiana": "arnes-de-paso-guardian-s-gris-roca",
        "comedero-cobre-18-cm": "comedero-estilo-cobre-18-cm",
        "comedero-cobre-22-cm": "comedero-estilo-cobre-22-cm",
        "comedero-acero-soporte-de-madera-12-cm": "comedero-acero-soporte-madera-12-cm",
        "comedero-doble-acero-soporte-de-madera": "comedero-doble-soporte-madera",
        "comedero-doble-grande-soporte-de-madera": "comedero-doble-grande-soporte-madera",
        "comedero-ceramica-soporte-de-madera": "comedero-ceramica-soporte-madera",
        "comedero-gato-con-soporte": "comedero-gatos-soporte",
        "fuente-de-agua-electrica-2-5-l-usb": "fuente-de-agua-2-5-l",
        "filtros-de-repuesto-para-fuente-pack-4": "filtros-repuesto-fuente-pack-4",
        "cama-teddy-pequena-marron": "cama-teddy-pequena",
        "cama-teddy-mediana-marron": "cama-teddy-mediana",
        "cama-classic-pequena-verde-caqui": "cama-acolchada-pequena-verde",
        "cama-classic-mediana-caqui-beige": "cama-acolchada-mediana-caqui",
        "cama-lucky-elephant-unica-rojo": "cama-lucky-elephant-roja",
        "cama-lucky-elephant-unica-verde": "cama-lucky-elephant-verde",
        "cama-corona-real-mediana-arena-y-gris": "cama-corona-real-mediana",
        "cama-corona-real-grande-negro-y-gris": "cama-corona-real-grande",
        "cama-sofa-pequena-rayas-marrones": "cama-sofa-pequena",
        "cama-sofa-mediana-rayas-marrones": "cama-sofa-mediana",
        "cama-patita-mediana-beige": "cama-patita-mediana",
        "cama-patita-grande-beige": "cama-patita-grande",
        "cama-tienda-48-48-40-cm-verde-y-naranja": "cama-tienda-48-verde",
        "cama-tienda-58-58-48-cm-beige-y-naranja": "cama-tienda-58-beige",
        "correa-elefante-azul": "correa-elephant-azul",
        "correa-elefante-gris": "correa-elephant-gris",
        "correa-elefante-marron": "correa-elephant-marrón",    }
    for old, new in OLD.items():
        if (ROOT / f"{new}.html").exists():
            write(old + ".html", f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>GRANKHA</title><link rel="canonical" href="{BASE}/{new}.html"><meta name="robots" content="noindex">
<script>location.replace("{new}.html"+location.hash);</script>
<meta http-equiv="refresh" content="0;url={new}.html"></head>
<body><p>Redirigiendo a <a href="{new}.html">la ficha actual</a>…</p></body></html>""")

    write("producto.html", """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>GRANKHA</title><meta name="robots" content="noindex">
<script>(function(){var m=location.search.match(/[?&]p=([^&]+)/);
location.replace(m?decodeURIComponent(m[1]).replace(/[^a-z0-9-]/gi,"")+".html":"tienda.html");})();</script>
<meta http-equiv="refresh" content="1;url=tienda.html">
</head><body style="font-family:system-ui;padding:40px">Redirigiendo… <a href="tienda.html">Ir a la tienda</a></body></html>""")

    urls = ["index.html", "tienda.html", "compromiso.html", "envios.html", "contacto.html", "legal.html",
            "carrito.html"] + [p["slug"] + ".html" for p in PRODUCTS]
    today = date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        pri = "1.0" if u == "index.html" else ("0.9" if u in ("tienda.html", "compromiso.html") else "0.7")
        sm.append(f"  <url><loc>{BASE}/{u}</loc><lastmod>{today}</lastmod><priority>{pri}</priority></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    (ROOT / ".nojekyll").write_text("")

# --------------------------------------------------------------------- main
if __name__ == "__main__":
    print("· generando páginas…")
    # CSS y JS como archivos (se cachean entre páginas; el sello ?v= los refresca)
    (ROOT / "styles.css").write_text(CSS, encoding="utf-8")
    (ROOT / "app.js").write_text(JS.replace("<\\/", "</"), encoding="utf-8")
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
    # vista previa autocontenida: un solo archivo con todo incrustado, para
    # revisar el diseño abriéndolo directamente (el sitio publicado usa archivos)
    try:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        html = html.replace(f'<link rel="stylesheet" href="styles.css?v={ASSET_V}">', f"<style>{CSS}</style>")
        html = html.replace(f'<script src="app.js?v={ASSET_V}" defer></script>', f"<script>{JS}</script>")
        for slug, ruta in THUMB.items():
            if ruta in html:
                html = html.replace(ruta, webp_uri(ROOT / ruta))
        (ROOT / "preview.html").write_text(html, encoding="utf-8")
        print("  · preview.html (vista previa autocontenida)")
    except Exception as e:  # pragma: no cover
        print("  · no se pudo generar preview.html:", e)

    print(f"✓ sitio generado · {len(list(ROOT.glob('*.html'))) - 1} páginas · {total/1024/1024:.1f} MB")

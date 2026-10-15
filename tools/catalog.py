#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · catalog.py
Construye data/products.json (catálogo normalizado para la web) uniendo:

  · data/feed.json      -> coste, stock, imágenes y descripciones del proveedor
  · data/pricing.json   -> tabla comercial: nombre, precio recomendado, audiencia, copy…
  · data/pricing_analysis.json -> contribución calculada por tools/pricing.py

Incluye los PACKS como productos con su propia ficha, imagen compuesta y
componentes (para poder pedirlos al proveedor).

Imágenes que genera:
  assets/img/products/<slug>.webp  -> 900 px, calidad 82   (foto de ficha)
  assets/img/thumbs/<slug>.webp    -> 380 px, calidad 68   (miniaturas a incrustar)
  assets/img/og/<slug>.jpg         -> 1200×630             (imagen para redes)
  assets/img/packs/<code>.webp     -> 1200 px              (imagen compuesta del pack)

Uso: python3 tools/catalog.py --raw data/raw
"""
import argparse, json, re, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

# categoría de tienda por colección
FAMILY_CAT = {
    "Guardian": ("arneses", "Arneses"),
    "Pocket Pod": ("correas", "Correas"),
    "Mini Mango": ("correas", "Correas"),
    "Elephant": ("correas", "Correas"),
    "Descanso": ("camas", "Camas"),
    "Hogar": ("comederos", "Comederos y fuentes"),
    "Hidratación": ("comederos", "Comederos y fuentes"),
}
CAT_ORDER = {"arneses": 0, "correas": 1, "camas": 2, "comederos": 3, "packs": 4}
SIZE_HINT = ["XS", "S", "M", "L", "XL"]


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).lower()
    return re.sub(r"-{2,}", "-", s).strip("-")


def specs_for(sku, p, commercial):
    """Tabla de especificaciones de la ficha de producto."""
    out = []
    sub = commercial["subtitle"]
    if commercial.get("audience") == "gato":
        out.append(["Para", "Gatos"])
    elif commercial.get("audience") == "perro":
        out.append(["Para", "Perros pequeños (2-8 kg)"])
    else:
        out.append(["Para", "Perros y gatos"])
    parts = [x.strip() for x in sub.split("·")]
    for part in parts:
        if re.match(r"^(XS|S|M|L|XL)\b", part) or "cm" in part or "L ·" in part or part.endswith("L"):
            out.append(["Medida / talla", part])
            break
    out.append(["Color", commercial["color"]])
    out.append(["Material", commercial["material"]])
    out.append(["Peso del paquete", f'{p["weight_g"]} g'])
    out.append(["Referencia", sku])
    return out


def pack_image(code, components, raw_dir: Path, dest: Path):
    """Compone la imagen de un pack: componentes en fila sobre fondo blanco."""
    imgs = []
    for sku, qty in components:
        f = raw_dir / f"{sku}.webp"
        if f.exists():
            imgs.append((Image.open(f).convert("RGB"), qty))
    if not imgs:
        return False
    n = len(imgs)
    W = H = 1200
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    cell_w = int(W / max(n, 1))
    pad = 60
    for i, (im, qty) in enumerate(imgs):
        im = im.copy()
        im.thumbnail((cell_w - pad, H - 2 * pad), Image.LANCZOS)
        x = int(i * cell_w + (cell_w - im.width) / 2)
        y = int((H - im.height) / 2)
        canvas.paste(im, (x, y))
        if qty > 1:
            d = ImageDraw.Draw(canvas)
            try:
                f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except Exception:
                f = ImageFont.load_default()
            label = f"×{qty}"
            lw = d.textlength(label, font=f)
            d.rectangle([x + 8, y + 8, x + 8 + lw + 24, y + 68], fill=(11, 11, 11))
            d.text((x + 20, y + 18), label, fill=(255, 255, 255), font=f)
    if n > 1:
        d = ImageDraw.Draw(canvas)
        for i in range(1, n):
            x = int(i * cell_w)
            d.line([(x, 140), (x, H - 140)], fill=(230, 230, 228), width=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, "WEBP", quality=84, method=6)
    return True


def process_image(src: Path, dst: Path, thumb: Path, og_dir: Path, label: str = ""):
    dst.parent.mkdir(parents=True, exist_ok=True)
    thumb.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    full = im.copy()
    full.thumbnail((900, 900), Image.LANCZOS)
    full.save(dst, "WEBP", quality=82, method=6)
    th = im.copy()
    th.thumbnail((380, 380), Image.LANCZOS)
    th.save(thumb, "WEBP", quality=68, method=6)
    # OG 1200×630
    og = Image.new("RGB", (1200, 630), (255, 255, 255))
    sq = im.copy()
    sq.thumbnail((520, 520), Image.LANCZOS)
    og.paste(sq, ((1200 - sq.width) // 2, (630 - sq.height) // 2 - 18))
    d = ImageDraw.Draw(og)
    try:
        f_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        f_reg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        f_bold = f_reg = ImageFont.load_default()
    x = 56
    for ch in "GRANKHA":
        d.text((x, 552), ch, fill=(11, 11, 11), font=f_bold)
        x += d.textlength(ch, font=f_bold) + 7
    d.text((56, 588), "Accesorios para perros y gatos  ·  GRANKHA por la salud animal",
           fill=(138, 138, 136), font=f_reg)
    og_dir.mkdir(parents=True, exist_ok=True)
    og.save(og_dir / (dst.stem + ".jpg"), "JPEG", quality=82, optimize=True)


def build(raw_dir: Path, out_path: Path, thumbs_dir: Path, og_dir: Path, packs_dir: Path):
    feed = json.loads((ROOT / "data" / "feed.json").read_text())
    pricing = json.loads((ROOT / "data" / "pricing.json").read_text())
    analysis = json.loads((ROOT / "data" / "pricing_analysis.json").read_text())
    commercial_all = pricing["products"]
    rows = {r[1]: r for r in feed["data"]}

    products, missing, skipped = [], [], []
    for sku, c in commercial_all.items():
        row = rows.get(sku)
        if not row:
            skipped.append(sku)
            continue
        cost = float(row[9])
        stock = int(row[22] or 0)
        weight_g = int(row[13] or row[12] or 0) or int(c.get("weight_g_default", 0)) or 400
        cat, cat_name = FAMILY_CAT.get(c["collection"], ("otros", "Otros"))
        slug = c["slug"]
        price = float(c["price"])
        an = analysis["products"].get(sku, {})
        products.append({
            "sku": sku, "slug": slug, "kind": "product",
            "name": c["name"], "subtitle": c["subtitle"], "collection": c["collection"],
            "cat": cat, "catName": cat_name,
            "audience": c["audience"], "audienceLabel": c.get("audience_label", ""),
            "price": round(price, 2), "prevPrice": round(float(c["prev_price"]), 2),
            "cost": round(cost, 2), "stock": stock, "weight_g": weight_g,
            "color": c["color"], "colorHex": c["colorHex"],
            "tags": c.get("tags", []), "material": c["material"],
            "desc": c["desc"], "bullets": c["bullets"], "why": c.get("why"),
            "market_lo": c["market_lo"], "market_hi": c["market_hi"],
            "market_note": c["market_note"], "vs_market": c.get("vs_market", ""),
            "rationale": c.get("rationale", ""),
            "contrib_1u": an.get("contrib_1u"), "contrib_2u": an.get("contrib_2u"),
            "img": f"{slug}.webp", "feedName": row[10],
            "specs": specs_for(sku, {"weight_g": weight_g}, c),
        })
        src = raw_dir / f"{sku}.webp"
        if src.exists():
            process_image(src, ROOT / "assets" / "img" / "products" / f"{slug}.webp",
                          thumbs_dir / f"{slug}.webp", og_dir)
        else:
            missing.append(sku)

    # ------------------------------------------------------------------ packs
    for code, pk in pricing["packs"].items():
        an = analysis["packs"].get(code, {})
        comps = [(s, q) for s, q in pk["components"]]
        names = []
        weight = 0
        stock = 999
        for s, q in comps:
            c = commercial_all[s]
            names.append(f'{q}× {c["name"]} ({c["subtitle"]})' if q > 1 else f'{c["name"]} ({c["subtitle"]})')
            prod = next((p for p in products if p["sku"] == s), None)
            if prod:
                weight += prod["weight_g"] * q
                stock = min(stock, prod["stock"] // q)
        slug = pk["slug"]
        price = float(an["price"])
        saving = float(an["saving"])
        disc = float(an["discount"])
        dest = ROOT / "assets" / "img" / "packs" / f"{slug}.webp"
        ok = pack_image(code, comps, raw_dir, dest)
        if ok:
            process_image(dest, ROOT / "assets" / "img" / "products" / f"{slug}.webp",
                          thumbs_dir / f"{slug}.webp", og_dir)
        products.append({
            "sku": code, "slug": slug, "kind": "pack",
            "name": pk["name"], "subtitle": f'{len(comps)} piezas · ahorras {saving:.2f} €'.replace(".", ","),
            "collection": "Packs", "cat": "packs", "catName": "Packs",
            "audience": pk["audience"],
            "audienceLabel": {"perro": "Pack para perros", "gato": "Pack para gatos",
                              "ambos": "Para perros y gatos"}[pk["audience"]],
            "price": round(price, 2), "prevPrice": round(float(an["component_sum"]), 2),
            "cost": round(an.get("component_cost", 0), 2),
            "stock": stock, "weight_g": weight,
            "color": "Varios", "colorHex": "#0B0B0B",
            "tags": ["Pack", f'Ahorras {saving:.2f} €'.replace(".", ",")],
            "material": "", "desc": pk["desc"], "bullets": pk["bullets"], "why": None,
            "components": [{"sku": s, "qty": q, "slug": commercial_all[s]["slug"],
                            "name": commercial_all[s]["name"]} for s, q in comps],
            "saving": round(saving, 2), "componentSum": round(float(an["component_sum"]), 2),
            "discount": round(disc, 4),
            "img": f"{slug}.webp", "feedName": pk["name"],
            "specs": [["Contenido", n] for n in names] + [
                ["Peso del paquete", f"{weight} g"], ["Referencia", code]],
        })

    products.sort(key=lambda p: (CAT_ORDER.get(p["cat"], 9), p["collection"], p["price"]))
    out_path.write_text(json.dumps(products, ensure_ascii=False, indent=1))
    print(f"✓ {len(products)} fichas ({sum(1 for p in products if p['kind']=='pack')} packs) -> {out_path}")
    if missing:
        print("  ⚠ sin imagen:", ", ".join(missing))
    if skipped:
        print("  ⚠ SKUs del pricing sin datos en el feed:", ", ".join(skipped))
    tot = sum(f.stat().st_size for f in Path(thumbs_dir).glob("*.webp"))
    print(f"  miniaturas: {len(list(Path(thumbs_dir).glob('*.webp')))} archivos, {tot/1024:.0f} KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out", default=str(ROOT / "data" / "products.json"))
    ap.add_argument("--thumbs", default=str(ROOT / "assets" / "img" / "thumbs"))
    ap.add_argument("--og", default=str(ROOT / "assets" / "img" / "og"))
    ap.add_argument("--packs", default=str(ROOT / "assets" / "img" / "packs"))
    a = ap.parse_args()
    build(Path(a.raw), Path(a.out), Path(a.thumbs), Path(a.og), Path(a.packs))

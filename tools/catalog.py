#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · catalog.py
Construye data/products.json (catálogo normalizado) a partir del data feed del
proveedor (data/feed.json) + la tabla de especificaciones SPECS.

También procesa las imágenes de producto (JPG/WebP originales) a:
  assets/img/products/<slug>.webp   -> 900 px, calidad 82   (foto de ficha)
  assets/img/thumbs/<slug>.webp     -> 380 px, calidad 68   (miniaturas a incrustar)
  assets/img/og/<slug>.jpg          -> 1200×630, calidad 82 (imagen para redes)

Uso:
  python3 tools/catalog.py --raw /tmp/full --out data/products.json
"""
import argparse, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Especificaciones por SKU (título comercial, atributos y datos de envío).
# Editables: si el proveedor cambia algo, ajusta aquí y vuelve a construir.
# weight_g = peso del paquete en gramos (para cálculo de envíos).
# ---------------------------------------------------------------------------
SPECS = {
    # --- ARNESES GUARDIAN ---------------------------------------------------
    "PAWH-01": dict(cat="arneses", col="Guardian", title="Arnés de paso Guardian",
                    size="XS", size_range="2-4 kg", color="Rosa suave", color_hex="#E3C3C7",
                    accent="Colgante de cuarzo rosa", material="Poliéster con malla reflectante",
                    weight_g=140),
    "PAWH-02": dict(cat="arneses", col="Guardian", title="Arnés de paso Guardian",
                    size="XS", size_range="2-4 kg", color="Lavanda", color_hex="#CBC3E3",
                    accent="Colgante de amatista", material="Poliéster con malla reflectante",
                    weight_g=140),
    "PAWH-03": dict(cat="arneses", col="Guardian", title="Arnés de paso Guardian",
                    size="XS", size_range="2-4 kg", color="Rock Grey", color_hex="#8E8E8E",
                    accent="Colgante de obsidiana negra", material="Poliéster con malla reflectante",
                    weight_g=140),
    "PAWH-04": dict(cat="arneses", col="Guardian", title="Arnés de paso Guardian",
                    size="S", size_range="4-8 kg", color="Rosa suave", color_hex="#E3C3C7",
                    accent="Colgante de cuarzo rosa", material="Poliéster con malla reflectante",
                    weight_g=165),
    "PAWH-05": dict(cat="arneses", col="Guardian", title="Arnés de paso Guardian",
                    size="S", size_range="4-8 kg", color="Lavanda", color_hex="#CBC3E3",
                    accent="Colgante de amatista", material="Poliéster con malla reflectante",
                    weight_g=165),
    "PAWH-06": dict(cat="arneses", col="Guardian", title="Arnés de paso Guardian",
                    size="S", size_range="4-8 kg", color="Gris roca", color_hex="#8E8E8E",
                    accent="Colgante de obsidiana negra", material="Poliéster con malla reflectante",
                    weight_g=165),

    # --- CORREAS ------------------------------------------------------------
    "PawL-01": dict(cat="correas", col="Pocket Pod", title="Correa Pocket Pod",
                    size="—", color="Rosa", color_hex="#E3A7B4", accent="1,5 m",
                    material="Cinta de nailon + ABS", weight_g=112),
    "PawL-02": dict(cat="correas", col="Pocket Pod", title="Correa Pocket Pod",
                    size="—", color="Verde", color_hex="#5C8A6A", accent="1,5 m",
                    material="Cinta de nailon + ABS", weight_g=112),
    "PawL-03": dict(cat="correas", col="Pocket Pod", title="Correa Pocket Pod",
                    size="—", color="Blanco", color_hex="#F2F2F0", accent="1,5 m",
                    material="Cinta de nailon + ABS", weight_g=112),
    "PawL-04": dict(cat="correas", col="Mini Mango", title="Correa Mini Mango",
                    size="3 m", color="Amarillo", color_hex="#E5C13F", accent="Retráctil 3 m",
                    material="ABS reforzado + nailon", weight_g=122),
    "PawL-05": dict(cat="correas", col="Mini Mango", title="Correa Mini Mango",
                    size="3 m", color="Ciruela", color_hex="#6E3B5E", accent="Retráctil 3 m",
                    material="ABS reforzado + nailon", weight_g=122),
    "PawL-06": dict(cat="correas", col="Mini Mango", title="Correa Mini Mango",
                    size="3 m", color="Durazno", color_hex="#EFB398", accent="Retráctil 3 m",
                    material="ABS reforzado + nailon", weight_g=122),
    "PawL-07": dict(cat="correas", col="Elefante", title="Correa Elephant Strap",
                    size="2 m", color="Azul", color_hex="#3F6E9E", accent="Retráctil 2 m",
                    material="ABS reforzado + nailon", weight_g=189),
    "PawL-08": dict(cat="correas", col="Elefante", title="Correa Elephant Strap",
                    size="2 m", color="Marrón", color_hex="#6B4A33", accent="Retráctil 2 m",
                    material="ABS reforzado + nailon", weight_g=189),
    "PawL-09": dict(cat="correas", col="Elefante", title="Correa Elephant Strap",
                    size="2 m", color="Gris", color_hex="#9A9A9A", accent="Retráctil 2 m",
                    material="ABS reforzado + nailon", weight_g=189),

    # --- COMEDEROS Y FUENTES ------------------------------------------------
    "PAWFB-01": dict(cat="comederos", col="Copper", title="Comedero cobre 18 cm",
                     size="18 cm", color="Cobre", color_hex="#B87333", accent="Acero inox. 304",
                     material="Acero inoxidable 304", weight_g=103),
    "PAWFB-02": dict(cat="comederos", col="Copper", title="Comedero cobre 22 cm",
                     size="22 cm", color="Cobre", color_hex="#B87333", accent="Acero inox. 304",
                     material="Acero inoxidable 304", weight_g=141),
    "PAWFB-03": dict(cat="comederos", col="Wood", title="Comedero acero + soporte de madera 12 cm",
                     size="12 cm", color="Madera / Acero", color_hex="#C7A97D", accent="Acero inox. 201",
                     material="Acero inoxidable 201 + madera natural", weight_g=243),
    "PAWFB-04": dict(cat="comederos", col="Wood", title="Comedero doble acero + soporte de madera",
                     size="2 × 12 cm", color="Madera / Acero", color_hex="#C7A97D", accent="Acero inox. 201",
                     material="Acero inoxidable 201 + madera natural", weight_g=450),
    "PAWFB-05": dict(cat="comederos", col="Wood", title="Comedero doble grande + soporte de madera",
                     size="2 × 13 cm", color="Madera / Acero", color_hex="#C7A97D", accent="Acero inox. 201",
                     material="Acero inoxidable 201 + madera natural", weight_g=1020),
    "PAWFB-06": dict(cat="comederos", col="Wood", title="Comedero cerámica + soporte de madera",
                     size="14 cm", color="Crema / Madera", color_hex="#E2D6BE", accent="Cerámica vidriada",
                     material="Cerámica + madera natural", weight_g=799),
    "PAWFB-07": dict(cat="comederos", col="Cat", title="Comedero gato con soporte",
                     size="Único", color="Acero", color_hex="#B9BCC0", accent="Acero inox. 304",
                     material="Acero inoxidable 304", weight_g=196),
    "PAWFB-08": dict(cat="comederos", col="Fountain", title="Fuente de agua eléctrica 2,5 L USB",
                     size="2,5 L", color="Acero", color_hex="#B9BCC0", accent="Alimentación USB",
                     material="Acero inoxidable 304 + ABS", weight_g=690),
    "PAWFB-09": dict(cat="comederos", col="Fountain", title="Filtros de repuesto para fuente (pack 4)",
                     size="Pack 4", color="Blanco", color_hex="#F2F2F0", accent="Recambio original",
                     material="Carbón activado + fibra", weight_g=160),

    # --- CAMAS --------------------------------------------------------------
    "PawB-01": dict(cat="camas", col="Teddy", title="Cama Teddy peluche",
                    size="Pequeña", dims="60 × 45 × 17 cm", color="Marrón", color_hex="#7A5638",
                    accent="Peluche texturizado", material="Poliéster", weight_g=760),
    "PawB-02": dict(cat="camas", col="Teddy", title="Cama Teddy peluche",
                    size="Mediana", dims="70 × 55 × 18 cm", color="Marrón", color_hex="#7A5638",
                    accent="Peluche texturizado", material="Poliéster", weight_g=1000),
    "PawB-03": dict(cat="camas", col="Classic", title="Cama acolchada caqui",
                    size="Pequeña", dims="60 × 50 × 15 cm", color="Verde caqui", color_hex="#A8A17C",
                    accent="Bordes elevados", material="Poliéster", weight_g=1330),
    "PawB-04": dict(cat="camas", col="Classic", title="Cama acolchada caqui",
                    size="Mediana", dims="70 × 60 × 15 cm", color="Caqui beige", color_hex="#D8CBB2",
                    accent="Bordes elevados", material="Poliéster", weight_g=1600),
    "PawB-05": dict(cat="camas", col="Lucky Elephant", title="Cama Lucky Elephant",
                    size="Única", dims="60 × 50 × 14 cm", color="Rojo", color_hex="#A8322C",
                    accent="Estampado elefantes", material="Poliéster", weight_g=960),
    "PawB-06": dict(cat="camas", col="Lucky Elephant", title="Cama Lucky Elephant",
                    size="Única", dims="60 × 50 × 14 cm", color="Verde", color_hex="#4E7A5C",
                    accent="Estampado elefantes", material="Poliéster", weight_g=960),
    "PawB-07": dict(cat="camas", col="Sofá", title="Cama sofá",
                    size="Pequeña", dims="50 × 50 × 26 cm", color="Rayas marrones", color_hex="#8A6B4F",
                    accent="Respaldo alto + cojín", material="Poliéster", weight_g=1250),
    "PawB-08": dict(cat="camas", col="Sofá", title="Cama sofá",
                    size="Mediana", dims="60 × 60 × 28 cm", color="Rayas marrones", color_hex="#8A6B4F",
                    accent="Respaldo alto + cojín", material="Poliéster", weight_g=1570),
    "PawB-09": dict(cat="camas", col="Corona Real", title="Cama Corona Real",
                    size="Mediana", dims="50 × 50 × 26 cm", color="Arena y gris", color_hex="#D3C6AF",
                    accent="Forma de corona", material="Poliéster", weight_g=840),
    "PawB-10": dict(cat="camas", col="Corona Real", title="Cama Corona Real",
                    size="Grande", dims="50 × 50 × 26 cm", color="Negro y gris", color_hex="#2B2B2B",
                    accent="Forma de corona", material="Poliéster", weight_g=1000),
    "PawB-11": dict(cat="camas", col="Patita", title="Cama Patita",
                    size="Mediana", dims="60 cm", color="Beige", color_hex="#D9C7AC",
                    accent="Forma de huella", material="Felpa larga", weight_g=1000),
    "PawB-12": dict(cat="camas", col="Patita", title="Cama Patita",
                    size="Grande", dims="70 cm", color="Beige", color_hex="#D9C7AC",
                    accent="Forma de huella", material="Felpa larga", weight_g=1360),
    "PawB-13": dict(cat="camas", col="Tienda", title="Cama tienda iglú",
                    size="48 × 48 × 40 cm", dims="48 × 48 × 40 cm", color="Verde y naranja", color_hex="#4E7A5C",
                    accent="Refugio cerrado", material="Poliéster", weight_g=500),
    "PawB-14": dict(cat="camas", col="Tienda", title="Cama tienda iglú",
                    size="58 × 58 × 48 cm", dims="58 × 58 × 48 cm", color="Beige y naranja", color_hex="#D9C7AC",
                    accent="Refugio cerrado", material="Poliéster", weight_g=650),
}

CAT_NAMES = {"arneses": "Arneses", "correas": "Correas",
             "comederos": "Comederos y fuentes", "camas": "Camas"}

# Bullets por categoría (se muestran en las fichas de producto)
BULLETS = {
    "arneses": ["Malla reflectante para paseos con poca luz",
                "Diseño de paso: se coloca en segundos, sin pasar por la cabeza",
                "Correas ajustables y cierres de clip seguros",
                "Colgante decorativo con gema natural",
                "Interior acolchado, sin roces en la piel"],
    "correas": ["Cinta resistente y ligera para el uso diario",
                "Ergonomía pensada para un agarre cómodo",
                "Mosquetón metálico giratorio 360°",
                "Diseño PAW original, fácil de limpiar"],
    "comederos": ["Acero inoxidable apto para contacto con alimentos",
                  "Base estable que no se desplaza",
                  "Diseño pensado para tu interior, no solo para tu mascota",
                  "Fácil de limpiar a mano"],
    "camas": ["Relleno mullido que mantiene la forma",
              "Laterales elevados: sensación de refugio y seguridad",
              "Base antideslizante",
              "Lavable a mano o a máquina en frío"],
}

FEATURES_BY_SKU = {
    "PAWFB-08": ["Circulación constante: el agua se mantiene en movimiento",
                 "2,5 litros de capacidad para varios días",
                 "Alimentación por USB",
                 "Acero inoxidable 304 apto para contacto con alimentos",
                 "Bomba silenciosa, apta para gatos y perros"],
    "PAWFB-09": ["Pack de 4 filtros + recambio de bomba",
                 "Compatible con la fuente PAW de 2,5 L",
                 "Mantiene el agua limpia y fresca",
                 "Sustitución sencilla, sin herramientas"],
    "PAWFB-07": ["Revela una cara de gato a medida que baja la comida",
                 "Acero inoxidable 304 apto para contacto con alimentos",
                 "Soporte estable que evita vuelcos",
                 "Apto para agua o pienso"],
}


def clean_text(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", t).strip()


def build(raw_dir: Path, out_path: Path, thumbs_dir: Path):
    feed = json.loads((ROOT / "data" / "feed.json").read_text())
    rows = feed["data"]
    products = []
    missing = []
    for r in rows:
        sku = r[1]
        spec = SPECS.get(sku)
        if not spec:
            print(f"  ⚠ SKU sin especificación, se omite: {sku}")
            continue
        price = float(r[11] or r[9])                       # PVP (con IVA)
        cost = float(r[9])                                 # coste proveedor
        stock = int(r[22] or 0)
        desc = clean_text(r[17]) or clean_text(r[16])
        name_feed = r[10]
        # peso: feed (col. 13 = peso paquete en g) > tabla SPECS
        w_feed = r[13] or r[12]
        weight_g = int(w_feed) if w_feed else int(spec.get("weight_g") or 500)

        slug_base = f"{spec['title'].lower()}"
        slug = slugify(f"{spec['col']}-{spec.get('size','')}-{spec.get('color','')}-{sku}")
        if spec["cat"] == "arneses":
            gem = re.sub(r"^Colgante de\s+", "", spec["accent"]).split()[0]
            slug = slugify(f"arnes-guardian-{spec['size']}-{spec['color']}-{gem}")
        elif spec["cat"] == "correas":
            slug = slugify(f"correa-{spec['col']}-{spec['color']}")
        elif spec["cat"] == "comederos":
            slug = slugify(spec["title"])
        elif spec["cat"] == "camas":
            slug = slugify(f"cama-{spec['col']}-{spec['size']}-{spec['color']}")
        slug = slug[:70].strip("-")

        subtitle_bits = []
        if spec.get("size") and spec["cat"] == "arneses":
            subtitle_bits.append(f"{spec['size']} ({spec['size_range']})")
        elif spec.get("size") and spec["cat"] != "arneses":
            subtitle_bits.append(spec["size"])
        if spec.get("color"):
            subtitle_bits.append(spec["color"])
        if spec.get("accent") and spec["cat"] == "arneses":
            subtitle_bits.append(spec["accent"])
        subtitle = " · ".join(subtitle_bits)

        specs = []
        if spec["cat"] == "arneses":
            specs.append(["Talla", f"{spec['size']} · {spec['size_range']}"])
            specs.append(["Tipo", "Arnés de paso (step-in)"])
            specs.append(["Extras", spec["accent"]])
        else:
            if spec.get("size"):
                specs.append(["Medida", spec["size"]])
            if spec.get("dims") and spec["dims"] != spec.get("size"):
                specs.append(["Dimensiones", spec["dims"]])
        specs.append(["Color", spec["color"]])
        specs.append(["Material", spec["material"]])
        specs.append(["Peso del paquete", f"{weight_g} g"])
        specs.append(["Referencia", sku])

        products.append({
            "sku": sku, "slug": slug, "cat": spec["cat"], "catName": CAT_NAMES[spec["cat"]],
            "collection": spec["col"], "title": spec["title"], "subtitle": subtitle,
            "size": spec.get("size", ""), "dims": spec.get("dims", ""),
            "color": spec["color"], "colorHex": spec["color_hex"],
            "price": round(price, 2), "cost": round(cost, 2), "stock": stock,
            "weight_g": weight_g, "img": f"{slug}.webp", "feedName": name_feed,
            "bullets": FEATURES_BY_SKU.get(sku, BULLETS[spec["cat"]]),
            "desc": desc, "specs": specs,
        })

        # imagen
        src = raw_dir / f"{sku}.webp"
        if src.exists():
            process_image(src, ROOT / "assets" / "img" / "products" / f"{slug}.webp",
                          thumbs_dir / f"{slug}.webp")
        else:
            missing.append(sku)

    products.sort(key=lambda p: ({"arneses": 0, "correas": 1, "camas": 2, "comederos": 3}[p["cat"]],
                                 p["collection"], p["sku"]))
    out_path.write_text(json.dumps(products, ensure_ascii=False, indent=1))
    print(f"✓ {len(products)} productos -> {out_path}")
    if missing:
        print("  ⚠ sin imagen:", ", ".join(missing))


def slugify(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).lower()
    return re.sub(r"-{2,}", "-", s).strip("-")


def process_image(src: Path, dst: Path, thumb: Path):
    from PIL import Image
    dst.parent.mkdir(parents=True, exist_ok=True)
    thumb.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    full = im.copy()
    full.thumbnail((900, 900), Image.LANCZOS)
    full.save(dst, "WEBP", quality=82, method=6)
    th = im.copy()
    th.thumbnail((380, 380), Image.LANCZOS)
    th.save(thumb, "WEBP", quality=68, method=6)
    # imagen OG 1200x630 sobre lienzo blanco (para compartir en redes)
    og = Image.new("RGB", (1200, 630), (255, 255, 255))
    sq = im.copy()
    sq.thumbnail((520, 520), Image.LANCZOS)
    og.paste(sq, ((1200 - sq.width) // 2, (630 - sq.height) // 2 - 18))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(og)
    try:
        f_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        f_reg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        f_bold = f_reg = ImageFont.load_default()
    x = 56
    for ch in "GRANKHA":                      # wordmark con tracking
        d.text((x, 552), ch, fill=(11, 11, 11), font=f_bold)
        x += d.textlength(ch, font=f_bold) + 7
    d.text((56, 588), "Accesorios para mascotas  ·  GRANKHA por la salud animal",
           fill=(138, 138, 136), font=f_reg)
    og_path = ROOT / "assets" / "img" / "og" / (dst.stem + ".jpg")
    og_path.parent.mkdir(parents=True, exist_ok=True)
    og.save(og_path, "JPEG", quality=82, optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="/tmp/full")
    ap.add_argument("--out", default=str(ROOT / "data" / "products.json"))
    ap.add_argument("--thumbs", default=str(ROOT / "assets" / "img" / "thumbs"))
    a = ap.parse_args()
    build(Path(a.raw), Path(a.out), Path(a.thumbs))
    # resumen de tamaño de miniaturas (para decidir incrustación en HTML)
    tot = sum(f.stat().st_size for f in Path(a.thumbs).glob("*.webp"))
    print(f"  miniaturas: {len(list(Path(a.thumbs).glob('*.webp')))} archivos, "
          f"{tot/1024:.0f} KB total (≈{tot*1.34/1024:.0f} KB en base64)")

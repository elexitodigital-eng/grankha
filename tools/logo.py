#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · logo.py
Convierte tu logo en el set que usa la web: marco circular con fondo blanco.

Genera:
  assets/img/logo.png            256 px  · cabecera (círculo, fondo blanco)
  assets/img/logo@2x.png         512 px  · pantallas retina
  assets/img/favicon-32.png       32 px
  assets/img/favicon.png          64 px
  assets/img/apple-touch-icon.png 180 px
  favicon.ico                    multi-tamaño para navegadores antiguos

Uso:
  python3 tools/logo.py                      # usa assets/src/logo-src.<ext> si existe
  python3 tools/logo.py ruta/a/mi-logo.png    # o la imagen que le pases
Si no encuentra ninguna imagen, dibuja un monograma provisional de GRANKHA.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets/img"
CANDIDATOS = ["logo-src.png", "logo-src.jpg", "logo-src.jpeg", "logo-src.webp", "logo-src.svg.png"]


def monograma(size=512):
    """Provisional: círculo negro con la G de GRANKHA, estilo de la marca."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], outline=(17, 17, 17, 255), width=int(s * 0.055))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(s * 0.46))
    except Exception:  # pragma: no cover
        f = ImageFont.load_default()
    txt = "G"
    box = d.textbbox((0, 0), txt, font=f)
    d.text(((s - (box[2] - box[0])) / 2 - box[0], (s - (box[3] - box[1])) / 2 - box[1]),
           txt, font=f, fill=(17, 17, 17, 255))
    # pequeña huella bajo la letra
    r = int(s * 0.035)
    cx, cy = s // 2, int(s * 0.72)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(17, 17, 17, 255))
    for dx in (-r * 2.1, -r * 0.75, r * 0.75, r * 2.1):
        rr = r * 0.62
        d.ellipse([cx + dx - rr, cy - r * 2.1 - rr, cx + dx + rr, cy - r * 2.1 + rr], fill=(17, 17, 17, 255))
    return im.resize((size, size), Image.LANCZOS)


def limpiar(src: Image.Image) -> Image.Image:
    """Deja solo el dibujo en negro sobre transparencia.

    Muchos PNG llevan el tablero de transparencia 'pintado' como píxeles blancos
    y gris claro: aquí se convierte en transparencia real (por tabla de niveles,
    rápido incluso con imágenes de 4000 px) y el trazo negro se conserva con sus
    bordes suavizados."""
    from PIL import ImageChops
    src = src.convert("RGBA")
    lut = []
    for lum in range(256):
        if lum <= 140:
            k = 1.0
        elif lum >= 238:
            k = 0.0
        else:
            k = (238 - lum) / 98.0
        a = int(round(255 * k))
        lut.append(0 if a < 28 else a)      # el damero (243 y 253) desaparece
    alfa = ImageChops.multiply(src.convert("L").point(lut), src.getchannel("A"))
    out = Image.new("RGBA", src.size, (17, 17, 17, 255))
    out.putalpha(alfa)
    caja = out.getbbox()
    return out.crop(caja) if caja else out


def circular(src: Image.Image, size: int, margen=0.07) -> Image.Image:
    """Centra, recorta en cuadrado, pone fondo blanco y aplica el marco circular."""
    src = limpiar(src)
    if margen:
        # caja cuadrada alrededor del dibujo + aire para que el círculo no lo corte
        lado = max(src.size)
        aire = int(lado * margen)
        lienzo = Image.new("RGBA", (lado + 2 * aire, lado + 2 * aire), (0, 0, 0, 0))
        lienzo.alpha_composite(src, ((lienzo.width - src.width) // 2, (lienzo.height - src.height) // 2))
        src = lienzo

    # fondo blanco detrás (el marco circular es blanco, como pediste)
    base = Image.new("RGBA", src.size, (255, 255, 255, 255))
    base.alpha_composite(src)

    base = base.resize((size * 4, size * 4), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    out = Image.new("RGBA", (size * 4, size * 4), (255, 255, 255, 0))
    out.paste(base, (0, 0), mask)
    return out.resize((size, size), Image.LANCZOS)


def main():
    ruta = None
    if len(sys.argv) > 1:
        ruta = Path(sys.argv[1])
    else:
        for c in CANDIDATOS:
            if (IMG / c).exists():
                ruta = IMG / c
                break

    if ruta and ruta.exists():
        src = Image.open(ruta)
        print(f"· usando {ruta}")
        icon = lambda s: circular(src, s)  # noqa: E731
    else:
        print("· no hay imagen de origen: genero un monograma provisional "
              "(pásame tu logo con: python3 tools/logo.py ruta/a/tu-logo.png)")
        icon = lambda s: monograma(s)  # noqa: E731

    IMG.mkdir(parents=True, exist_ok=True)
    salidas = [("logo.png", 256), ("logo@2x.png", 512), ("favicon-32.png", 32),
               ("favicon.png", 64), ("apple-touch-icon.png", 180)]
    for nombre, size in salidas:
        icon(size).save(IMG / nombre, "PNG", optimize=True)
        print(f"  ✓ assets/img/{nombre} ({size} px)")

    icon(64).save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("  ✓ favicon.ico")


if __name__ == "__main__":
    main()

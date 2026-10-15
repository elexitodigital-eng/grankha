#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · hero.py
Recompone la foto de portada para que salgan SIEMPRE el perro y el gato.

La foto original (1376×768) trae a los dos animales a la derecha del encuadre,
pero el marco de la portada es vertical en escritorio, así que el recorte
automático se comía al gato. Aquí se genera:

  assets/img/hero.jpg        formato vertical (mismo hueco que ocupa ahora)
  assets/img/hero-movil.jpg  formato apaisado para móvil y tablet

La foto de origen es assets/src/hero-fuente.jpg y no se toca, así que se puede
volver a ejecutar tantas veces como haga falta sin degradar la imagen.

Los dos salen de la misma foto: se amplía el fondo de estudio (un degradado
suave) repitiendo su borde superior e inferior y difuminando la unión, sin
tocar a los animales.

Uso: python3 tools/hero.py     (o con la ruta de otra foto: python3 tools/hero.py foto.jpg)
"""
import sys
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets/img"

# encuadre de escritorio (proporción medida del marco: 543×962)
VERTICAL = (1080, 1926)
# encuadre de móvil / tablet (marco 707×430 y 354×218)
APAISADO = (1600, 988)


def extender_vertical(img: Image.Image, alto: int) -> Image.Image:
    """Coloca la foto en el centro y prolonga el fondo repitiendo sus bordes."""
    w, h = img.size
    if h == alto:
        return img
    canvas = Image.new("RGB", (w, alto), (250, 250, 250))
    if h < alto:
        arriba = int((alto - h) * 0.66)
        canvas.paste(img, (0, arriba))
        # fondo continuado: se estira la primera y la última fila de la foto.
        # Se promedia en horizontal (bajar y volver a subir) para que el degradado
        # del estudio no arrastre bandas verticales al estirarlo.
        def banda(y, alto_banda):
            b = img.crop((0, y, w, y + 1)).resize((w, alto_banda), Image.LANCZOS)
            prom = b.resize((max(1, w // 12), alto_banda), Image.LANCZOS)
            return prom.resize((w, alto_banda), Image.LANCZOS)

        fila_top = banda(0, arriba + 1)
        fila_bot = banda(h - 1, alto - arriba - h + 1)
        canvas.paste(fila_top, (0, 0))
        canvas.paste(fila_bot, (0, arriba + h - 1))
        # se difumina la unión para que no se note la costura
        union = 70
        for y0 in (arriba, arriba + h - union):
            tira = canvas.crop((0, max(0, y0 - union // 2), w, min(alto, y0 + union // 2)))
            canvas.paste(tira.filter(ImageFilter.GaussianBlur(14)), (0, max(0, y0 - union // 2)))
        return canvas
    return img.crop((0, (h - alto) // 2, w, (h - alto) // 2 + alto))


def main():
    # la foto original de estudio (nunca se sobrescribe)
    origen = Path(sys.argv[1]) if len(sys.argv) > 1 else IMG / "hero-fuente.jpg"
    src = Image.open(origen).convert("RGB")
    print(f"· foto de origen: {origen.name} {src.size}")

    # la pareja (perro + gato) ocupa, en la foto original, de x≈760 a x≈1330
    pareja_izq, pareja_der = 780, 1345
    ancho_pareja = pareja_der - pareja_izq

    # ---------------------------------------------------- 1) versión vertical
    escala = (VERTICAL[0] * 0.72) / ancho_pareja        # la pareja al 72 % del ancho
    grande = src.resize((round(src.width * escala), round(src.height * escala)), Image.LANCZOS)
    # ventana horizontal: la pareja queda a la derecha, con aire a la izquierda
    x0 = round(pareja_der * escala) - int(VERTICAL[0] * 0.79)
    x0 = max(0, min(x0, grande.width - VERTICAL[0]))
    recorte = grande.crop((x0, 0, x0 + VERTICAL[0], grande.height))
    vertical = extender_vertical(recorte, VERTICAL[1])
    vertical.save(IMG / "hero.jpg", "JPEG", quality=88, optimize=True, progressive=True)
    print(f"  ✓ assets/img/hero.jpg {vertical.size}  (perro + gato, alineados a la derecha)")

    # ---------------------------------------------------- 2) versión apaisada
    # Mismo encuadre que la foto original, recortado un poco por abajo: los dos
    # animales se ven grandes y juntos, sin ampliar nada.
    ancho, alto = src.size
    corte_abajo = 120
    apaisado = src.crop((0, 0, ancho, alto - corte_abajo))
    apaisado.save(IMG / "hero-movil.jpg", "JPEG", quality=88, optimize=True, progressive=True)
    print(f"  ✓ assets/img/hero-movil.jpg {apaisado.size}  (para móvil y tablet)")


if __name__ == "__main__":
    main()

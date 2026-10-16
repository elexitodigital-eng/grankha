"""Reencuadra y unifica las fotos de producto (utilidad, NO en uso).

OJO: ahora mismo la web publica los ORIGINALES del proveedor, tal cual salen
de AW. Este script está aquí por si algun dia se quiere normalizar el fondo y
el tamano de los productos en la rejilla, pero no forma parte del build: si se
ejecuta, sobreescribe las fotos de assets/img/products y assets/img/thumbs.
Los originales sin tocar estan en assets/src/products-original/ y en data/raw.

Uso:
    python3 tools/reencuadre.py --probar    # hoja de control, sin escribir
    python3 tools/reencuadre.py             # aplica a todas las fotos
"""
from pathlib import Path
import json
import sys

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
IMG = RAIZ / "assets" / "img"
PRODUCTS = IMG / "products"
THUMBS = IMG / "thumbs"
CATALOGO = RAIZ / "data" / "products.json"

FICHA = 900                 # lado de la ficha
MINI = 380                  # lado de la miniatura de la rejilla
TONO = 250                  # tono de fondo de la rejilla (#FAFAF9)
TONO_MIN = 200              # por debajo, el fondo no es claro: solo se reencuadra
AIRE = 0.07                 # aire alrededor del producto en fotos con textura
OBJETIVO = 0.86             # lado mayor del producto dentro de la ficha


def modelo_fondo(img, anillo=22):
    """Tono de fondo estimado: plano inclinado + viñeta radial."""
    h, w, _ = img.shape
    borde = np.zeros((h, w), bool)
    borde[:anillo, :] = borde[-anillo:, :] = True
    borde[:, :anillo] = borde[:, -anillo:] = True
    ys, xs = np.where(borde)

    def base(x, y):
        X, Y = x / w, y / h
        r = np.sqrt((X - .5) ** 2 + (Y - .5) ** 2)
        return np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y,
                         X ** 3, X * X * Y, X * Y * Y, Y ** 3, r * r, r ** 4], -1)

    A = base(xs.astype(np.float32), ys.astype(np.float32))
    coef, *_ = np.linalg.lstsq(A, img[ys, xs].astype(np.float32), rcond=None)
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    B = (base(gx.ravel(), gy.ravel()) @ coef).reshape(h, w, 3)
    return B, borde


def rellenar_huecos(m):
    """Rellena los huecos interiores de una máscara (el producto macizo)."""
    h, w = m.shape
    inv = (1 - m).astype(np.uint8)
    for esquina in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if inv[esquina[1], esquina[0]]:
            cv2.floodFill(inv, np.zeros((h + 2, w + 2), np.uint8), esquina, 2)
    return (m | (inv == 1).astype(np.uint8))


def caja_producto(img, B, tol):
    """Caja del producto: lo que no es fondo liso.

    Se pide además que tenga borde (gradiente): así un foco o un halo suave
    de la propia foto no cuenta como producto y el recorte sigue siendo justo.
    """
    dif = np.linalg.norm(img.astype(np.float32) - B, axis=2)
    L = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32),
                         (0, 0), 1.2)
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    G = np.sqrt(gx * gx + gy * gy)
    m = ((dif > tol) & (G > 3.0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] > 0.0015 * m.size:
            keep[lab == i] = 1
    keep = rellenar_huecos(keep)
    ys, xs = np.where(keep > 0)
    if len(ys) < 500:
        return None, keep
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1), keep


def aplanar(img, B, borde, keep, tol):
    """Deja el fondo de estudio liso y del mismo tono claro en todas las fotos.

    Solo actúa si el fondo es claro (fotos de estudio). En fotos de exterior,
    con césped o fondo oscuro, se deja intacta: solo se reencuadra.
    El producto no se toca: el fondo se lleva al tono de la rejilla y la
    transición se hace corta para que no aparezca halo.
    Devuelve (imagen, tono_de_fondo).
    """
    med = np.median(B[borde].reshape(-1, 3), axis=0).astype(np.float32)
    if float(med.mean()) < TONO_MIN:
        return img, med
    objetivo = np.array([TONO, TONO, TONO - 1], np.float32)
    plano = img.astype(np.float32) * (med / np.clip(B, 8, 255))
    # el fondo sube entero y el producto (silueta rellena) no se toca
    m = (keep > 0).astype(np.uint8)
    m = cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)).astype(np.float32),
                         (0, 0), 2.5)
    plano = plano + (objetivo - med) * (1 - m)[..., None]
    return np.clip(plano, 0, 255).astype(np.uint8), objetivo


def montar(plano, caja, tono, lado, uniforme, aire=AIRE):
    """Producto centrado y al mismo tamaño en todas las fichas.

    Con el fondo liso (fotos de estudio) se escala al tamaño objetivo y lo que
    sobra se rellena con el propio tono del fondo, así todos los productos
    ocupan lo mismo. En fotos con fondo de color solo se recorta, para no
    inventarse texturas.
    """
    x0, y0, x1, y1 = caja
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    caja_lado = max(x1 - x0, y1 - y0)
    if uniforme:
        esc = min(max((OBJETIVO * lado) / caja_lado, 0.35), 1.6)
        color = tuple(int(round(v)) for v in np.clip(tono, 0, 255))
        M = np.array([[esc, 0, lado / 2.0 - esc * cx],
                      [0, esc, lado / 2.0 - esc * cy]], np.float32)
        return cv2.warpAffine(plano, M, (lado, lado), flags=cv2.INTER_AREA,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=color)
    h, w, _ = plano.shape
    ventana = max(60, min(int(round(caja_lado * (1 + 2 * aire))), min(h, w)))
    rx = int(round(min(max(cx - ventana / 2.0, 0), w - ventana)))
    ry = int(round(min(max(cy - ventana / 2.0, 0), h - ventana)))
    return cv2.resize(plano[ry:ry + ventana, rx:rx + ventana], (lado, lado),
                      interpolation=cv2.INTER_AREA)


def normalizar(img, lado=FICHA, aire=AIRE):
    """Ficha cuadrada normalizada. Devuelve (imagen, cambia)."""
    B, borde = modelo_fondo(img)
    res = np.linalg.norm(img.astype(np.float32) - B, axis=2)[borde]
    sig = float(np.median(np.abs(res - np.median(res))) * 1.4826)
    tol = max(5.0, 5 * sig)
    caja, keep = caja_producto(img, B, tol)
    vacio = np.zeros(img.shape[:2], np.uint8)
    plano, tono = aplanar(img, B, borde, keep if caja is not None else vacio, tol)
    uniforme = float(tono.mean()) >= TONO_MIN     # fondo liso → se puede igualar tamaño
    if caja is None:
        return cv2.resize(plano, (lado, lado), interpolation=cv2.INTER_AREA), False
    return montar(plano, caja, tono, lado, uniforme, aire), True


def fotos():
    """Fotos de producto del catálogo (los packs van aparte)."""
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    salida = []
    for p in datos:
        if p.get("kind") == "pack":
            continue
        f = PRODUCTS / f"{p['img']}"
        if f.exists():
            salida.append((p["sku"], p["slug"], f))
    return salida


def hoja(pares, destino, cols=6, cell=200):
    filas = (len(pares) + cols - 1) // cols
    hoja = np.full((filas * cell, cols * cell * 2, 3), 255, np.uint8)
    for i, (_, antes, despues) in enumerate(pares):
        f, c = divmod(i, cols)
        a = cv2.resize(antes, (cell - 8, cell - 8), interpolation=cv2.INTER_AREA)
        d = cv2.resize(despues, (cell - 8, cell - 8), interpolation=cv2.INTER_AREA)
        hoja[f * cell + 4:f * cell + cell - 4, c * cell + 4:c * cell + cell - 4] = a
        hoja[f * cell + 4:f * cell + cell - 4,
             cols * cell + c * cell + 4:cols * cell + c * cell + cell - 4] = d
    cv2.imwrite(str(destino), hoja)
    return destino


def main():
    args = sys.argv[1:]
    probar = "--probar" in args
    aire = float(args[args.index("--aire") + 1]) if "--aire" in args else AIRE
    pares, hechas, iguales = [], 0, []
    for sku, slug, ruta in fotos():
        img = cv2.imread(str(ruta))
        if img is None:
            print(f"  ! no se puede leer {ruta}")
            continue
        final, cambia = normalizar(img, FICHA, aire)
        pares.append((slug, img, final))
        if not cambia:
            iguales.append(slug)
        if probar:
            continue
        mini, _ = normalizar(img, MINI, aire)
        cv2.imwrite(str(PRODUCTS / ruta.name), final, [cv2.IMWRITE_WEBP_QUALITY, 82])
        cv2.imwrite(str(THUMBS / ruta.name), mini, [cv2.IMWRITE_WEBP_QUALITY, 72])
        hechas += 1
    if probar:
        print("hoja de control →", hoja(pares, RAIZ.parent / "reencuadre-control.png"))
    if iguales:
        print(f"sin cambios ({len(iguales)}): " + ", ".join(iguales))
    print(f"✓ {hechas} foto(s) normalizadas")


if __name__ == "__main__":
    main()

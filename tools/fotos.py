"""Limpieza y montaje de las fotos de producto de GRANKHA.

Coge las fotos originales del proveedor (data/raw), les quita la marca, la
tarjeta y las sombras, las pone sobre el fondo del estudio y escribe la ficha,
la miniatura y la imagen de redes. También rehace las fotos de los packs.

Uso:
    python3 tools/fotos.py                 # las 44 fotos y los packs
    python3 tools/fotos.py PAWH-01         # solo un producto (por SKU o slug)
    python3 tools/fotos.py --sin-fondo     # solo limpia, sin cambiar el fondo
"""
from pathlib import Path
import json
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
IMG = RAIZ / "assets" / "img"
RAW = RAIZ / "data" / "raw"
PRODUCTS_JSON = RAIZ / "data" / "products.json"

# caja (y0, y1, x0, x1) donde va serigrafiada la marca sobre la tela del arnés
CAJA_ARnes = (645, 785, 530, 680)

# rango del color piel, para la etiqueta de las camas
COLOR_PIEL = {"h": (0, 25), "s": (40, 255), "v": (60, 255)}


def limpiar_marca_clara(img, alfa=None):
    """Borra la impresión clara (el logo) sobre el cuerpo del producto.

    La impresión es más clara que el material que tiene alrededor, así que se
    compara cada píxel con el color local del propio producto y se rellena.
    """
    if alfa is None:
        alfa = alpha_producto(img)
    cuerpo = (alfa > 0.5).astype(np.uint8)
    if cuerpo.sum() < 2000:
        return img
    interior = cv2.erode(cuerpo * 255, np.ones((3, 3), np.uint8), iterations=4) > 0
    area = float(interior.sum())
    base = interior.astype(np.float32)
    num = cv2.GaussianBlur(img.astype(np.float32) * base[:, :, None], (0, 0), 16)
    den = cv2.GaussianBlur(base, (0, 0), 16)[:, :, None]
    local = np.clip(num / np.maximum(den, 1e-3), 0, 255).astype(np.uint8)
    dif = (cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) -
           cv2.cvtColor(local, cv2.COLOR_BGR2GRAY).astype(np.float32))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    S, V = hsv[:, :, 1].astype(np.float32), hsv[:, :, 2].astype(np.float32)
    marca = ((dif > 9) & (V > 170) & (S < 95) & interior).astype(np.uint8)
    marca = cv2.morphologyEx(marca, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(marca, 8)
    keep = np.zeros_like(marca)
    for i in range(1, n):
        a = st[i, 4]
        if 40 < a < 0.10 * area:
            keep[lab == i] = 1
    if keep.sum() == 0 or keep.sum() > 0.10 * area:
        return img
    if keep.sum() < 0.035 * area:      # manchita compacta: se cierra por dentro
        n2, lab2 = cv2.connectedComponents((1 - keep).astype(np.uint8), 8)
        borde = set(lab2[0, :]) | set(lab2[-1, :]) | set(lab2[:, 0]) | set(lab2[:, -1])
        for i in range(1, n2):
            if i in borde:
                continue
            g = (lab2 == i)
            if g.sum() < 9000:
                keep[g] = 1
    return _relleno(img, cv2.dilate(keep, np.ones((9, 9), np.uint8)), 16)


def _relleno(img, mask, sigma):
    """Rellena la máscara con lo de alrededor (convolución normalizada: sin costuras)."""
    mm = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
    base = 1.0 - mask.astype(np.float32)
    out = np.zeros_like(img, np.float32)
    for c in range(3):
        num = cv2.GaussianBlur(img[:, :, c].astype(np.float32) * base, (0, 0), sigma)
        den = cv2.GaussianBlur(base, (0, 0), sigma)
        out[:, :, c] = num / np.maximum(den, 1e-3)
    f = mm[:, :, None]
    return np.clip(out * f + img.astype(np.float32) * (1 - f), 0, 255).astype(np.uint8)


def _card_mask(img, semilla=(300, 600), huecos=True):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    claro = cv2.morphologyEx((g > 231).astype(np.uint8), cv2.MORPH_CLOSE,
                             np.ones((31, 31), np.uint8))
    n, lab = cv2.connectedComponents(claro, 8)
    cual = lab[semilla[0], semilla[1]]
    if cual == 0:
        return None
    card = (lab == cual).astype(np.uint8)
    if not huecos:
        return card
    comp = (1 - card).astype(np.uint8)
    n2, lab2, _, _ = cv2.connectedComponentsWithStats(comp, 8)
    borde = set(lab2[0, :]) | set(lab2[-1, :]) | set(lab2[:, 0]) | set(lab2[:, -1])
    for i in range(1, n2):
        if i in borde:
            continue
        m = (lab2 == i)
        if m.sum() > 50:
            card[m] = 1
    return card


def _producto_mask(img, card):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    osc = cv2.morphologyEx((g < 200).astype(np.uint8), cv2.MORPH_CLOSE,
                           np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(osc, 8)
    prot = np.zeros_like(osc)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        comp = (lab == i)
        fuera = float((comp & (card == 0)).sum()) / max(1, a)
        if a > 2200 and fuera > 0.15:
            prot[comp] = 1
    return cv2.dilate(prot, np.ones((9, 9), np.uint8))


# ------------------------------------------------------------------- limpieza
def limpiar_tarjeta(img, card, src):
    """Quita textos y logo de la tarjeta y la deja blanca."""
    bg = np.median(np.concatenate([src[0:25, :].reshape(-1, 3),
                                   src[-25:, :].reshape(-1, 3)]), axis=0)
    prot = _producto_mask(src, card)
    salida = img.copy()
    interior = cv2.erode((card > 0).astype(np.uint8), np.ones((11, 11), np.uint8)) > 0
    for _ in range(4):
        V = cv2.cvtColor(salida, cv2.COLOR_BGR2HSV)[:, :, 2].astype(np.float32)
        fv = cv2.GaussianBlur(V, (0, 0), 26)
        tinta = interior & (prot == 0) & ((fv - V) > 1.0)
        tinta = cv2.morphologyEx(tinta.astype(np.uint8), cv2.MORPH_CLOSE,
                                 np.ones((7, 7), np.uint8))
        nn, lb, _, _ = cv2.connectedComponentsWithStats(tinta, 8)
        quitar = np.zeros_like(tinta)
        for i in range(1, nn):
            mm = (lb == i)
            if mm.sum() < 60:
                continue
            # el hueco del colgador tiene el color del fondo: se conserva
            if np.linalg.norm(np.median(src[mm], axis=0) - bg) < 45:
                quitar |= mm
        salida = _relleno(salida, tinta & (~quitar), 16)
    # el cartón se va al blanco: no queda ni rastro de la tinta
    suave = cv2.GaussianBlur(((card > 0) & (prot == 0)).astype(np.float32), (0, 0), 5.0)
    return np.clip(255 - (255 - salida.astype(np.float32)) * (1 - 0.95 * suave[:, :, None]),
                   0, 255).astype(np.uint8)


def limpiar_marca_tejido(img, caja, card):
    """Borra la marca serigrafiada sobre el tejido, conservando su grano.

    Se marca solo el trazo (unas gotas más claro que el propio tejido) y se
    rellena a poca distancia, para no dejar una mancha lisa.
    """
    y0, y1, x0, x1 = caja
    marca = np.zeros(img.shape[:2], np.uint8)
    marca[y0:y1, x0:x1] = 255
    zona = (marca > 0) & ((card is None) | (card == 0))
    if zona.sum() < 200:
        return img
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    base = float(np.median(g[zona]))
    if base > 205:                     # ahí no hay tejido, es la tarjeta clara
        return img
    for umbral, sigma, dil in ((11, 4, 3), (6, 5, 4)):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        letras = (zona & (g > base + umbral)).astype(np.uint8)
        letras = cv2.morphologyEx(letras, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        if letras.sum() == 0:
            continue
        img = _relleno(img, cv2.dilate(letras, np.ones((dil, dil), np.uint8)), sigma)
    return img


def detectar_etiqueta_piel(img, card=None):
    """Localiza la etiqueta de piel con el logo en las fotos de camas."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    m = ((h >= COLOR_PIEL["h"][0]) & (h <= COLOR_PIEL["h"][1]) &
         (s >= COLOR_PIEL["s"][0]) & (s <= COLOR_PIEL["s"][1]) &
         (v >= COLOR_PIEL["v"][0]) & (v <= COLOR_PIEL["v"][1])).astype(np.uint8)
    if card is not None:
        m[card > 0] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    cajas = []
    H = img.shape[0]
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if not (COLOR_PIEL["area"][0] <= a <= COLOR_PIEL["area"][1]):
            continue
        rel = w / max(1, hh)
        if not (0.9 <= rel <= 2.4):
            continue
        relleno_bbox = a / max(1, w * hh)
        if relleno_bbox < 0.55:
            continue
        if y < H * 0.35:            # la etiqueta va en la parte baja de la cama
            continue
        cajas.append((max(0, y - 8), min(H, y + hh + 8), max(0, x - 8), min(img.shape[1], x + w + 8), a))
    cajas.sort(key=lambda c: -c[4])
    return cajas[0][:4] if cajas else None


def limpiar_cama(img, card=None):
    caja = detectar_etiqueta_piel(img, card)
    if not caja:
        return img, None
    y0, y1, x0, x1 = caja
    return limpiar_marca_tejido(img, (y0, y1, x0, x1), card), caja


def _cuerpo_claro(img, alfa=None):
    """¿El producto es blanco o muy clarito? (decide qué limpieza del logo toca)"""
    if alfa is None:
        alfa = alpha_producto(img)
    mm = cv2.erode(((alfa > 0.5).astype(np.uint8)) * 255, np.ones((3, 3), np.uint8), iterations=2) > 0
    if mm.sum() < 2000:
        return False
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    S = hsv[:, :, 1].astype(np.float32)[mm]
    V = hsv[:, :, 2].astype(np.float32)[mm]
    return float(np.median(S)) < 50 and float(np.median(V)) > 170


def limpiar_marca_saturada(img, alfa=None):
    """Borra las impresiones de color (el óvalo naranja del logo) sobre cuerpos claros."""
    if alfa is None:
        alfa = alpha_producto(img)
    mm = cv2.erode(((alfa > 0.5).astype(np.uint8)) * 255, np.ones((3, 3), np.uint8), iterations=2) > 0
    if mm.sum() < 2000:
        return img
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    S, V = hsv[:, :, 1].astype(np.float32), hsv[:, :, 2].astype(np.float32)
    if np.median(S[mm]) > 50 or np.median(V[mm]) < 170:
        return img                                  # el cuerpo ya es de color u oscuro
    mancha = ((S > 70) & (V > 100) & mm).astype(np.uint8)
    mancha = cv2.morphologyEx(mancha, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(mancha, 8)
    keep = np.zeros_like(mancha)
    for i in range(1, n):
        if st[i, 4] > 300:
            keep[lab == i] = 1
    if keep.sum() == 0 or keep.sum() > 0.12 * mm.sum():
        return img
    return _relleno(img, cv2.dilate(keep, np.ones((21, 21), np.uint8)), 24)


def limpiar_marca_clara(img, alfa=None):
    """Borra cualquier impresión clara (el logo) sobre el cuerpo del producto.

    Se calcula el color propio del producto alrededor de cada píxel y se marcan
    los que son claramente más claros: eso es la serigrafía. Después se rellena
    con el propio material, así que vale para el plástico y para el tejido.
    """
    if alfa is None:
        alfa = alpha_producto(img)
    m = ((alfa > 0.5).astype(np.uint8)) * 255
    m = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=6)      # fuera los bordes
    if m.sum() == 0:
        return img
    base = m.astype(np.float32) / 255.0
    num = cv2.GaussianBlur(img.astype(np.float32) * base[:, :, None], (0, 0), 18)
    den = cv2.GaussianBlur(base, (0, 0), 18)[:, :, None]
    local = num / np.maximum(den, 1e-3)
    dif = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) - \
        cv2.cvtColor(np.clip(local, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    marca = ((dif > 8) & (m > 0)).astype(np.uint8)
    marca = cv2.morphologyEx(marca, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    # los huecos interiores de la mancha (el relleno de las letras) también cuentan
    n, lab = cv2.connectedComponents((1 - marca).astype(np.uint8), 8)
    borde = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    for i in range(1, n):
        if i in borde:
            continue
        g = (lab == i)
        if g.sum() < 12000:
            marca[g] = 1
    if marca.sum() < 40:
        return img
    return _relleno(img, cv2.dilate(marca, np.ones((9, 9), np.uint8)), 16)


# --------------------------------------------------------------------- recorte
def _alpha_rembg(img):
    try:
        from rembg import remove, new_session
    except Exception:
        return None
    sesion = getattr(_alpha_rembg, "_sesion", None) or new_session("u2net")
    _alpha_rembg._sesion = sesion
    cut = remove(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)),
                 session=sesion, alpha_matting=False)
    return (np.array(cut)[:, :, 3] > 100).astype(np.uint8)


def _fondo_4bordes(img):
    """Estimación del fondo de la foto (degradado suave) a partir de sus bordes."""
    h, w, _ = img.shape
    up = np.median(img[:20, :].astype(np.float32), axis=0)
    dn = np.median(img[-20:, :].astype(np.float32), axis=0)
    lf = np.median(img[:, :20].astype(np.float32), axis=1)
    rt = np.median(img[:, -20:].astype(np.float32), axis=1)
    ty = (np.arange(h, dtype=np.float32) / (h - 1))[:, None, None]
    tx = (np.arange(w, dtype=np.float32) / (w - 1))[None, :, None]
    return (up[None, :, :] * (1 - ty) + dn[None, :, :] * ty +
            lf[:, None, :] * (1 - tx) + rt[:, None, :] * tx) / 2.0


def alpha_umbral(img, k=3.0):
    """Máscara por diferencia de color con el fondo (funciona con piezas claras)."""
    B = _fondo_4bordes(img)
    d = np.linalg.norm(img.astype(np.float32) - B, axis=2)
    d = cv2.GaussianBlur(d, (0, 0), 2.0)
    d8 = np.clip(d * k, 0, 255).astype(np.uint8)
    t, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    fuerte = (d8 > t).astype(np.uint8)
    n, lab = cv2.connectedComponents((1 - fuerte).astype(np.uint8), 8)
    borde = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    fondo = np.zeros_like(fuerte)
    for i in borde:
        if i:
            fondo[lab == i] = 1
    m = (1 - fondo).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return m.astype(bool)


def _fondo_ajustado(img, prot, grado=2):
    """Modelo suave del fondo (superficie) ajustado SOLO con los píxeles que no son
    producto. Mucho más fiable que interpolar los bordes cuando hay sombras."""
    h, w, _ = img.shape
    lejos = (prot == 0)
    ys, xs = np.where(lejos)
    if len(ys) < 5000:
        return _fondo_4bordes(img)
    paso = max(1, len(ys) // 40000)
    ys, xs = ys[::paso], xs[::paso]
    X = xs / w
    Y = ys / h
    A = [np.ones_like(X)]
    for i in range(1, grado + 1):
        for j in range(i + 1):
            A.append((X ** (i - j)) * (Y ** j))
    A = np.stack(A, axis=1)
    cols = img[ys, xs].astype(np.float32)
    coef, *_ = np.linalg.lstsq(A, cols, rcond=None)
    gy, gx = np.mgrid[0:h, 0:w]
    GX = gx / w
    GY = gy / h
    G = [np.ones_like(GX)]
    for i in range(1, grado + 1):
        for j in range(i + 1):
            G.append((GX ** (i - j)) * (GY ** j))
    G = np.stack(G, axis=-1)
    return (G.reshape(-1, len(G[0, 0])) @ coef).reshape(h, w, 3)


def _tiene_cesped(img):
    """Fotos hechas en exterior (las casetas): mejor conservarlas como están."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    verde = ((h > 30) & (h < 90) & (s > 55) & (v > 55))
    return verde.mean() > 0.02


def recorte_fiable(a, img=None, cobertura_min=0.12, borde_max=0.25):
    """¿Merece la pena cambiar el fondo? Evita recortes rotos o con césped."""
    if img is not None and _tiene_cesped(img):
        return False
    m = a > 0.5
    cob = m.mean()
    if cob < cobertura_min or cob > 0.80:
        return False
    h, w = m.shape
    b = np.concatenate([m[0, :], m[-1, :], m[:, 0], m[:, -1]])
    if b.mean() > borde_max:          # la foto está llena por el sujeto/fondo
        return False
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    grande = max((st[i, 4] for i in range(1, n)), default=0)
    if grande / max(1, m.sum()) < 0.85:   # trozos sueltos = recorte sucio
        return False
    return True


def alpha_producto(img):
    """Máscara del producto a partir de la IA, con la morfología justa.

    No se rellenan los huecos: en estas fotos el hueco interior (el lazo del
    arnés, el asa de la correa…) es fondo de verdad y debe quedarse fuera.
    """
    ia = _alpha_rembg(img)
    if ia is None:
        ia = (alpha_basico(img, umbral=10.0) > 0.5).astype(np.uint8)
    m = (ia > 0).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    # fuera las motas y los flecos del césped: piezas sueltas muy pequeñas
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] > 1200:
            keep[lab == i] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    a = cv2.GaussianBlur(keep.astype(np.float32) * 255.0, (0, 0), 1.2) / 255.0
    # bordes duros donde no hay duda, suaves en la transición
    return np.clip((a - 0.12) / 0.76, 0, 1)


def alpha_basico(img, umbral=12.0):
    """Recorte sin IA: el fondo de estas fotos es un degradado claro sin sombras."""
    h, w, _ = img.shape
    izq = np.median(img[:, :30].astype(np.float32), axis=1)
    der = np.median(img[:, -30:].astype(np.float32), axis=1)
    t = (np.arange(w, dtype=np.float32) / (w - 1))[None, :, None]
    fondo = izq[:, None, :] * (1 - t) + der[:, None, :] * t
    d = np.linalg.norm(img.astype(np.float32) - fondo, axis=2)
    m = (d > umbral).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] > 900:
            keep[lab == i] = 1
    keep = cv2.dilate(keep, np.ones((3, 3), np.uint8))
    return cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 1.2)


def fondo_estudio(h=1200, w=1200, arriba=(243, 243, 241), abajo=(226, 226, 224)):
    y = np.linspace(0, 1, h)[:, None, None]
    gr = (np.array(arriba, np.float32)[None, None, :] * (1 - y) +
          np.array(abajo, np.float32)[None, None, :] * y)
    return np.repeat(gr, w, axis=1)


def montar(img, alpha, ancho=900):
    """Coloca el producto sobre el fondo nuevo: color real + sombra suave."""
    a3 = np.clip(alpha, 1e-3, 1.0)[:,:,None]
    # separa el color real del blanco del fondo original
    color = np.clip((img.astype(np.float32) - (1 - a3) * 255.0) / a3, 0, 255)
    base = fondo_estudio()
    sombra = np.roll(cv2.GaussianBlur(alpha, (0, 0), 26), 18, axis=0) * 0.2
    base = (base * (1 - sombra[:, :, None]) +
            np.array([168, 168, 166], np.float32) * sombra[:, :, None])
    out = base * (1 - a3) + color * a3
    out = np.clip(out, 0, 255).astype(np.uint8)
    return cv2.resize(out, (ancho, ancho), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------- salida
def escribir(slug: str, final: np.ndarray, dir_og=True):
    (IMG / "products").mkdir(parents=True, exist_ok=True)
    (IMG / "thumbs").mkdir(parents=True, exist_ok=True)
    (IMG / "og").mkdir(parents=True, exist_ok=True)
    im = Image.fromarray(cv2.cvtColor(final, cv2.COLOR_BGR2RGB))
    im.save(IMG / "products" / f"{slug}.webp", "WEBP", quality=82, method=6)
    th = im.copy(); th.thumbnail((380, 380), Image.LANCZOS)
    th.save(IMG / "thumbs" / f"{slug}.webp", "WEBP", quality=68, method=6)
    if dir_og:
        og = Image.new("RGB", (1200, 630), (255, 255, 255))
        sq = im.copy(); sq.thumbnail((520, 520), Image.LANCZOS)
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
        og.save(IMG / "og" / f"{slug}.jpg", "JPEG", quality=82, optimize=True)


# ----------------------------------------------------------------- catalogo
def catalogo():
    return json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))


def packs():
    return [p for p in catalogo() if p.get("kind") == "pack"]


def limpiar_foto(path: Path, slug: str, aviso=None):
    """Limpia una foto según la familia de producto a la que pertenece."""
    src = cv2.imread(str(path))
    if src is None:
        return None
    card = _card_mask(src)
    img = src.copy()
    # la tarjeta de cartón solo la llevan las fotos de los arneses
    if card is not None and slug.startswith("arnes"):
        img = limpiar_tarjeta(img, card, src)
    else:
        card = None
    if slug.startswith("arnes"):
        # la impresión del pecho ("Paw AW") es de muy bajo contraste sobre el
        # propio tejido: se deja tal cual, borrarla dejaba una mancha lisa
        pass
    elif slug.startswith("correa"):
        if _cuerpo_claro(img):
            img = limpiar_marca_saturada(img)   # la placa de color
            img = limpiar_marca_clara(img)      # y la impresión que lleva encima
        else:
            img = limpiar_marca_clara(img)
    # las camas llevan una etiqueta de piel con el logo bordado: es muy pequeña y
    # va en perspectiva en cada foto, así que se deja tal cual (pendiente)
    return img


def proceso(sku: str, slug: str, con_fondo=True, guardar=True, avisos=None):
    path = RAW / f"{sku}.webp"
    if not path.exists():
        return False
    img = limpiar_foto(path, slug, avisos)
    if img is None:
        return False
    if con_fondo:
        a = alpha_producto(img)
        if slug.startswith("arnes"):
            # la tarjeta de cartón con la que el proveedor presenta el arnés no
            # debe salir en la foto: se quita de la máscara (el producto no)
            src = cv2.imread(str(path))
            card = _card_mask(src, huecos=False)
            if card is not None:
                fuera = cv2.dilate(card, np.ones((7, 7), np.uint8))
                a = a * (1.0 - fuera)
        if recorte_fiable(a, img):
            final = montar(img, a)
        else:
            # el recorte no es fiable (pieza casi del color del fondo o foto con
            # césped): se conserva la foto original, ya limpia de marcas
            final = cv2.resize(img, (900, 900), interpolation=cv2.INTER_AREA)
    else:
        final = cv2.resize(img, (900, 900), interpolation=cv2.INTER_AREA)
    if guardar:
        escribir(slug, final)
    return True


def componer_pack(pack, dir_tmp: Path):
    """Rehace la foto del pack con las fotos ya limpias de sus piezas."""
    dir_tmp.mkdir(parents=True, exist_ok=True)
    piezas = []
    for c in pack["components"]:
        prod = next((p for p in catalogo() if p["sku"] == c["sku"]), None)
        if not prod:
            continue
        f = IMG / "products" / f"{prod['slug']}.webp"
        if not f.exists():
            continue
        piezas.append((c["sku"], Image.open(f).convert("RGB"), c["qty"]))
        (dir_tmp / f"{c['sku']}.webp").write_bytes(f.read_bytes())
    if not piezas:
        return None
    W = H = 1200
    GAP, MARGIN = 26, 46
    canvas = Image.new("RGB", (W, H), (250, 250, 249))
    n = len(piezas)

    def encajar(im, bw, bh):
        im = im.copy(); im.thumbnail((bw, bh), Image.LANCZOS); return im

    if n == 1:
        zonas = [(0, 0, W, H)]
    elif n == 2:
        mit = W // 2
        zonas = [(0, 0, mit, H), (mit, 0, W, H)]
    elif n == 3:
        mit = W // 2
        zonas = [(0, 0, mit, H), (mit, 0, W, H // 2), (mit, H // 2, W, H)]
    else:
        zonas = [(0, 0, W // 2, H // 2), (W // 2, 0, W, H // 2),
                 (0, H // 2, W // 2, H), (W // 2, H // 2, W, H)]
    for i, (sku, im, qty) in enumerate(piezas[:len(zonas)]):
        x0, y0, x1, y1 = zonas[i]
        im = encajar(im, x1 - x0 - 2 * GAP, y1 - y0 - 2 * GAP)
        canvas.paste(im, (x0 + (x1 - x0 - im.width) // 2, y0 + (y1 - y0 - im.height) // 2))
    return canvas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    con_fondo = "--sin-fondo" not in sys.argv
    avisos = []
    hechos = 0
    for p in catalogo():
        if p.get("kind") == "pack":
            continue
        if args and p["sku"] not in args and p["slug"] not in args:
            continue
        if proceso(p["sku"], p["slug"], con_fondo=con_fondo, guardar=not args, avisos=avisos):
            print(f"  ✓ {p['sku']} → {p['slug']}")
            hechos += 1
    # packs: se recomponen con las piezas limpias
    if not args:
        import tempfile
        for pk in packs():
            canvas = componer_pack(pk, Path(tempfile.mkdtemp()))
            if canvas is None:
                continue
            (IMG / "packs").mkdir(parents=True, exist_ok=True)
            canvas.save(IMG / "packs" / f"{pk['slug']}.webp", "WEBP", quality=82, method=6)
            escribir(pk["slug"], cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR))
            print(f"  ✓ pack {pk['slug']}")
            hechos += 1
    print(f"✓ {hechos} imagen(es)")
    if avisos:
        sin = [s for s, c in avisos if c is None]
        con = [(s, c) for s, c in avisos if c]
        if con:
            print("· etiquetas detectadas:", ", ".join(f"{s}{c}" for s, c in con))
        if sin:
            print("· camas sin etiqueta detectada:", ", ".join(sin))


if __name__ == "__main__":
    main()

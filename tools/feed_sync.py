#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · feed_sync.py
Sincroniza el catálogo con la API de AW Dropshipping (ZENQA LIFE).

Descarga:
  · data/feed.json              -> data feed JSON de "mis productos"
  · data/raw/<SKU>.webp         -> imagen principal de cada producto a 1200 px

Después reconstruye el catálogo y el sitio:
  1) python3 tools/feed_sync.py
  2) python3 tools/catalog.py --raw data/raw
  3) python3 tools/build.py

El token NUNCA se guarda en el repositorio: se lee de la variable de entorno
AIKU_TOKEN (o del archivo ~/.config/grankha/token, con permisos 600).

API: https://api.aiku.io  (staging: https://api.aiku-sandbox.uk)
Doc: https://documenter.getpostman.com/view/28816137/2sB34Zrjrp

Uso:
  AIKU_TOKEN='xxx|yyy' python3 tools/feed_sync.py
  python3 tools/feed_sync.py --api https://api.aiku-sandbox.uk   # staging
"""
import argparse, json, os, sys, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = Path.home() / ".config" / "grankha" / "token"
UA = "GRANKHA-catalog-sync/1.0 (+https://grankha.example)"


def token():
    t = os.environ.get("AIKU_TOKEN", "").strip()
    if not t and TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text().strip()
    if not t:
        sys.exit("✗ Falta el token. Exporta AIKU_TOKEN='...' o guárdalo en ~/.config/grankha/token")
    return t


def api_get(url, tok, timeout=60):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download(url, dest: Path, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        dest.write_bytes(r.read())
    return dest.stat().st_size


def pick_image(images: dict) -> str:
    for k in ("webp_2x", "original_2x", "webp", "original", "png_2x"):
        if images.get(k):
            return images[k]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="https://api.aiku.io",
                    help="Base URL (staging: https://api.aiku-sandbox.uk)")
    ap.add_argument("--skip-images", action="store_true")
    a = ap.parse_args()
    tok = token()

    # --- comprobación de credenciales -------------------------------------
    try:
        prof = json.loads(api_get(f"{a.api}/user-profile", tok))
        name = prof.get("data", {}).get("name", "?")
        print(f"✓ Token válido · canal: {name}")
    except urllib.error.HTTPError as e:
        sys.exit(f"✗ Token rechazado por la API ({e.code}). En staging el token se resetea "
                 f"cada domingo 03:00 UTC: genera uno nuevo y reinténtalo.")

    # --- data feed de productos -------------------------------------------
    print("· descargando data feed de productos…")
    raw = api_get(f"{a.api}/dropshipping/my-products-data-feed-json", tok)
    feed = json.loads(raw)
    if not isinstance(feed, dict) or "data" not in feed:
        sys.exit("✗ Formato inesperado del data feed")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "feed.json").write_bytes(raw)
    rows = feed["data"]
    print(f"  {len(rows)} productos en el feed")

    # --- imágenes ----------------------------------------------------------
    if not a.skip_images:
        raw_dir = ROOT / "data" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        tasks = []
        for r in rows:
            sku, img = r[1], pick_image(r[23] or {})
            if sku and img:
                tasks.append((sku, img, raw_dir / f"{sku}.webp"))
        print(f"· descargando {len(tasks)} imágenes…")

        def job(t):
            sku, url, dest = t
            try:
                size = download(url, dest)
                return sku, f"{size/1024:.0f} KB"
            except Exception as e:
                return sku, f"ERROR {e}"

        with ThreadPoolExecutor(max_workers=8) as ex:
            for sku, res in ex.map(job, tasks):
                if "ERROR" in res:
                    print(f"  ⚠ {sku}: {res}")

    # --- utilidad: listado de IDs de canal (para galerías) -----------------
    try:
        print("· IDs de canal (por si necesitas /dropshipping/images):")
        listing = json.loads(api_get(f"{a.api}/dropshipping/products/my-products?per_page=100", tok))
        ids = {p["code"]: p["id"] for p in listing.get("data", [])}
        (ROOT / "data" / "channel_ids.json").write_text(json.dumps(ids, indent=1, ensure_ascii=False))
        print(f"  guardados {len(ids)} IDs en data/channel_ids.json")
    except Exception as e:
        print(f"  (aviso) no se pudo obtener el listado de IDs: {e}")

    print("\n✓ Sincronización terminada. Ahora ejecuta:\n"
          "    python3 tools/catalog.py --raw data/raw\n"
          "    python3 tools/build.py")


if __name__ == "__main__":
    main()

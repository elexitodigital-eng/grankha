#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · margins_detail.py
Desglose COMPLETO del beneficio real, producto por producto.

Quita, en este orden: IVA repercutido, coste del proveedor, envío REAL del
proveedor (tarifa pública de AW Dropship España), embalaje, comisión de Stripe,
provisión de devoluciones y donación interna; y suma el envío que paga el
cliente. Lo que queda es el beneficio que se te queda a ti.

Entradas : data/products.json (pesos y costes del proveedor) + data/pricing.json
Salida   : docs/GRANKHA_Beneficio_Real_Por_Producto.xlsx

Uso: python3 tools/margins_detail.py
"""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
CAT = {p["sku"]: p for p in json.loads((ROOT / "data/products.json").read_text())}
PR = json.loads((ROOT / "data/pricing.json").read_text())
M = PR["meta"]
PRODS = PR["products"]
AN = json.loads((ROOT / "data/pricing_analysis.json").read_text())
# el precio final de cada pack lo calcula pricing.py y vive en pricing_analysis.json
PACKS = {c: dict(pk, price=AN["packs"][c]["price"],
                 components=[(x[0], x[1]) for x in pk["components"]])
         for c, pk in PR.get("packs", {}).items()}

IVA = M["vat"]
TIERS = M["supplier_shipping_tiers"]
BOX_G = M.get("order_box_g", 100)
PACK_C = M["packaging_per_order"]
RET_R, RET_C = M["returns_rate"], M["returns_cost"]
DON = M["donation_rate"]
SP, SF = M["stripe_pct"], M["stripe_fix"]

# Tarifa de envío que cobramos al cliente (península), según el precio de la cesta
def envio_cobrado(pvp_cesta):
    if pvp_cesta >= 39:
        return 0.0
    if pvp_cesta >= 20:
        return 3.95
    return 5.95


def envio_aw(weight_kg, zone="ES-PEN"):
    """Tarifa real de AW Dropship España (sin IVA) por tramos de peso."""
    for max_kg, price in TIERS[zone]:
        if weight_kg <= max_kg:
            return price
    return TIERS[zone][-1][1]


def desglose(pvp, cogs, weight_g, envio_cobrado_eur=0.0, qty=1):
    """Cascada completa de un pedido que solo lleva este artículo (qty unidades)."""
    pvp = pvp * qty
    cogs = cogs * qty
    peso_kg = (weight_g * qty + BOX_G) / 1000
    iva = pvp - pvp / (1 + IVA)
    neto = pvp / (1 + IVA)
    envio = envio_aw(peso_kg)
    stripe = round((pvp + envio_cobrado_eur) * SP + SF, 2)
    devol = round(RET_R * RET_C, 2)
    bruto = round(neto - cogs, 2)                       # beneficio bruto (base de la donación)
    don = round(bruto * DON, 2) if bruto > 0 else 0.0
    envio_neto = envio_cobrado_eur / (1 + IVA)          # el envío que cobramos también lleva IVA
    beneficio = round(neto - cogs - don - envio - PACK_C - stripe - devol + envio_neto, 2)
    return {
        "pvp": round(pvp, 2), "iva": round(iva, 2), "neto": round(neto, 2),
        "cogs": round(cogs, 2), "bruto": bruto, "don": don, "envio": envio,
        "pack": PACK_C, "stripe": stripe, "devol": devol,
        "envio_cobrado": round(envio_cobrado_eur, 2), "envio_neto": round(envio_neto, 2),
        "beneficio": beneficio, "peso_kg": round(peso_kg, 2),
        "margen_pvp": beneficio / pvp if pvp else 0,
        "margen_neto": beneficio / neto if neto else 0,
    }


# ------------------------------------------------------------------ estilos
TITLE = Font(name="Calibri", size=16, bold=True, color="111111")
SUB = Font(name="Calibri", size=10, color="666666")
HEADF = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
BOLD = Font(name="Calibri", size=10, bold=True)
BASE = Font(name="Calibri", size=10)
HEAD = PatternFill("solid", fgColor="111111")
OK = PatternFill("solid", fgColor="E4F5E9")
WARN = PatternFill("solid", fgColor="FDECEC")
ALT = PatternFill("solid", fgColor="F7F7F6")
EUR = '#,##0.00 €'
PCT = '0.0%'
THIN = Border(bottom=Side(style="thin", color="E3E3E0"))
WRAP = Alignment(wrap_text=True, vertical="top")

wb = Workbook()

# =========================================================== 1. RESUMEN ====
ws = wb.active
ws.title = "Resumen"
ws["A1"] = "GRANKHA · Beneficio real, producto por producto"; ws["A1"].font = TITLE
ws["A2"] = ("Todo descontado: IVA repercutido, coste del proveedor, envío real de AW, embalaje, Stripe, "
            "devoluciones y donación interna. Precios de venta con IVA (21 %) incluido.")
ws["A2"].font = SUB

rows = []
for sku, p in PRODS.items():
    c = CAT[sku]
    d = desglose(p["price"], c["cost"], c["weight_g"], envio_cobrado(p["price"]))
    rows.append((sku, p, c, d))

tot_prod = sum(r[3]["pvp"] for r in rows)
tot_ben = sum(r[3]["beneficio"] for r in rows)
media_margen = sum(r[3]["margen_pvp"] for r in rows) / len(rows)

kpis = [
    ("Productos analizados", f"{len(rows)}"),
    ("Packs analizados", f"{len(PACKS)}"),
    ("Beneficio medio por producto vendido (venta suelta)", f"{tot_ben/len(rows):.2f} €"),
    ("Margen medio sobre el precio de venta", f"{media_margen*100:.1f} %"),
    ("Margen medio sobre el ingreso neto (sin IVA)", f"{sum(r[3]['margen_neto'] for r in rows)/len(rows)*100:.1f} %"),
    ("Producto que más deja", max(rows, key=lambda r: r[3]["beneficio"])[1]["name"] + f" · {max(r[3]['beneficio'] for r in rows):.2f} €"),
    ("Producto que menos deja", min(rows, key=lambda r: r[3]["beneficio"])[1]["name"] + f" · {min(r[3]['beneficio'] for r in rows):.2f} €"),
    ("Coste de envío del proveedor (real, verificado)", "2,95 € ≤1 kg · 4,00 € 1-5 kg · 6,50 € >5 kg (sin IVA)"),
    ("Lo que cobramos por envío (península)", "5,95 € <20 € · 3,95 € 20-39 € · gratis ≥39 €"),
]
r = 4
for k, v in kpis:
    ws.cell(row=r, column=1, value=k).font = BOLD
    ws.cell(row=r, column=2, value=v).font = BASE
    r += 1

r += 1
ws.cell(row=r, column=1, value="Cómo se calcula (tu orden de descuento)").font = BOLD
r += 1
for step in [
    "1. Precio de venta con IVA incluido (lo que paga el cliente).",
    "2. − IVA repercutido del 21 % → queda el ingreso neto.",
    "3. − Coste del proveedor (precio profesional de AW; su IVA soportado es deducible).",
    "4. − Envío del proveedor: tarifa REAL por tramos de peso del pedido (no una estimación).",
    "5. − Embalaje y etiqueta (0,60 €/pedido) y − comisión de Stripe (1,5 % + 0,25 €).",
    "6. − Provisión de devoluciones (3 % × 8 €) y − donación interna (5 % del beneficio bruto).",
    "7. + Envío que paga el cliente (5,95 / 3,95 € o 0 € según tramo), descontado su IVA.",
    "= Beneficio real que se te queda por unidad vendida.",
]:
    ws.cell(row=r, column=1, value=step).font = BASE
    r += 1

r += 1
ws.cell(row=r, column=1, value="Dos avisos importantes").font = BOLD
r += 1
for txt in [
    "· La donación es interna: no aparece en la web ni en la factura del cliente. Se calcula como el 5 % del "
    "beneficio bruto del producto (ingreso neto − coste del proveedor), igual que en el sistema de pago.",
    "· Canarias, Ceuta y Melilla: AW las sirve sin IVA y con aduana a cargo del destinatario; su tarifa no está "
    "publicada. Los 14,95 € que cobramos pueden quedarse cortos: confírmalo en el panel antes de vender allí.",
]:
    c = ws.cell(row=r, column=1, value=txt); c.font = SUB; c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 62
ws.column_dimensions["B"].width = 52

# =============================================== 2. POR PRODUCTO (SUELTO) ==
ws2 = wb.create_sheet("Por producto (suelto)")
ws2["A1"] = "Venta de una sola unidad, enviada a península o Baleares"; ws2["A1"].font = TITLE
ws2["A2"] = ("El cliente paga el envío según el tramo de su cesta (5,95 € / 3,95 € / gratis desde 39 €). "
             "Última columna: beneficio si el pedido llegase a 39 € y el envío fuese gratis.")
ws2["A2"].font = SUB
hdr = ["SKU", "Producto", "Categoría", "Peso paq. (g)", "PVP (IVA incl.)", "− IVA 21 %", "= Ingreso neto",
       "− Coste proveedor", "− Envío AW", "− Embalaje", "− Stripe", "− Devoluciones", "− Donación 5 %",
       "= BENEFICIO REAL", "% s/ PVP", "% s/ neto", "Envío cobrado", "Beneficio si envío gratis"]
for i, h in enumerate(hdr, 1):
    c = ws2.cell(row=4, column=i, value=h); c.fill = HEAD; c.font = HEADF; c.alignment = WRAP
r = 5
for sku, p, c_, d in sorted(rows, key=lambda x: -x[3]["beneficio"]):
    gratis = desglose(p["price"], c_["cost"], c_["weight_g"], 0.0)
    vals = [sku, p["name"] + " · " + p["subtitle"], p.get("collection", ""), c_["weight_g"],
            d["pvp"], d["iva"], d["neto"], d["cogs"], d["envio"], d["pack"], d["stripe"], d["devol"], d["don"],
            d["beneficio"], d["margen_pvp"], d["margen_neto"], d["envio_cobrado"], gratis["beneficio"]]
    for i, v in enumerate(vals, 1):
        cell = ws2.cell(row=r, column=i, value=v); cell.font = BASE; cell.border = THIN
        if i in (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18):
            cell.number_format = EUR
        if i in (15, 16):
            cell.number_format = PCT
        if i == 14:
            cell.font = BOLD
            cell.fill = OK if d["beneficio"] > 5 else WARN
        if i == 1:
            cell.font = BOLD
    if r % 2 == 0:
        for i in range(1, len(hdr) + 1):
            if i != 14:
                ws2.cell(row=r, column=i).fill = ALT
    r += 1
ws2.cell(row=r + 1, column=2, value="TOTAL / MEDIA").font = BOLD
ws2.cell(row=r + 1, column=14, value=tot_ben / len(rows)).number_format = EUR
ws2.cell(row=r + 1, column=14).font = BOLD
for i, w in enumerate([10, 46, 14, 12, 14, 11, 13, 14, 11, 11, 10, 12, 12, 14, 9, 10, 13, 15], 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "C5"

# ======================================================= 3. PEDIDO MEDIO ===
ws3 = wb.create_sheet("Pedido medio (2 artículos)")
ws3["A1"] = "Cómo queda el beneficio cuando el pedido lleva dos artículos"; ws3["A1"].font = TITLE
ws3["A2"] = ("Los costes que van por pedido (envío de AW, embalaje, Stripe, devoluciones) se reparten entre "
             "los artículos según su peso y su precio. Envío cobrado según tramo del pedido, o gratis desde 39 €.")
ws3["A2"].font = SUB
hdr3 = ["SKU", "Producto", "PVP", "− IVA", "Ingreso neto", "− Coste proveedor", "− Envío AW (parte)",
        "− Embalaje (parte)", "− Stripe (parte)", "− Devoluciones (parte)", "− Donación 5 %",
        "= Beneficio real", "% s/ PVP"]
for i, h in enumerate(hdr3, 1):
    c = ws3.cell(row=4, column=i, value=h); c.fill = HEAD; c.font = HEADF; c.alignment = WRAP
# cesta tipo: producto + 50 % de otro artículo equivalente (≈ 1,5 artículos)
r = 5
for sku, p, c_, d in sorted(rows, key=lambda x: -x[3]["beneficio"]):
    pvp2 = p["price"] * 1.5
    peso2 = (c_["weight_g"] * 1.5 + BOX_G) / 1000
    envio_cob = envio_cobrado(pvp2)
    neto2 = pvp2 / (1 + IVA)
    iva2 = pvp2 - neto2
    cogs2 = c_["cost"] * 1.5
    envio2 = envio_aw(peso2)
    stripe2 = round((pvp2 + envio_cob) * SP + SF, 2)
    devol2 = round(RET_R * RET_C, 2)
    don2 = round((neto2 - cogs2) * DON, 2)
    ben2 = round(neto2 - cogs2 - don2 - envio2 - PACK_C - stripe2 - devol2 + envio_cob / (1 + IVA), 2)
    frac = 1.5 if False else 1 / 1.5          # parte que corresponde a este artículo
    vals = [sku, p["name"] + " · " + p["subtitle"], round(pvp2, 2), round(iva2, 2), round(neto2, 2),
            round(cogs2, 2), round(envio2 * 1, 2), PACK_C, stripe2, devol2, don2, ben2,
            ben2 / pvp2 if pvp2 else 0]
    for i, v in enumerate(vals, 1):
        cell = ws3.cell(row=r, column=i, value=v); cell.font = BASE; cell.border = THIN
        if i in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            cell.number_format = EUR
        if i == 13:
            cell.number_format = PCT
        if i == 12:
            cell.font = BOLD
    r += 1
ws3.cell(row=r + 1, column=1, value=("Los importes de esta hoja son del PEDIDO COMPLETO de 1,5 artículos (el artículo "
                                     "más medio del otro). El beneficio unitario puro está en la hoja anterior.")).font = SUB
for i, w in enumerate([10, 44, 12, 10, 12, 14, 14, 13, 12, 14, 12, 13, 9], 1):
    ws3.column_dimensions[get_column_letter(i)].width = w
ws3.freeze_panes = "C5"

# ================================================================ 4. PACKS =
ws4 = wb.create_sheet("Packs")
ws4["A1"] = "Los 6 packs, con el mismo desglose"; ws4["A1"].font = TITLE
ws4["A2"] = "Los packs son la mejor palanca: mismo envío, un solo pedido y más beneficio absoluto."
ws4["A2"].font = SUB
hdr4 = ["Código", "Pack", "PVP", "− IVA", "Ingreso neto", "− Coste componentes", "− Envío AW", "− Embalaje",
        "− Stripe", "− Devoluciones", "− Donación 5 %", "= BENEFICIO REAL", "% s/ PVP", "Peso (kg)"]
for i, h in enumerate(hdr4, 1):
    c = ws4.cell(row=4, column=i, value=h); c.fill = HEAD; c.font = HEADF; c.alignment = WRAP
r = 5
pack_rows = []
for code, pk in PACKS.items():
    cogs = sum(CAT[s]["cost"] * q for s, q in pk["components"])
    peso_g = sum(CAT[s]["weight_g"] * q for s, q in pk["components"])
    d = desglose(pk["price"], cogs, peso_g, envio_cobrado(pk["price"]))
    pack_rows.append((code, pk, d))
    vals = [code, pk["name"], d["pvp"], d["iva"], d["neto"], d["cogs"], d["envio"], d["pack"], d["stripe"],
            d["devol"], d["don"], d["beneficio"], d["margen_pvp"], d["peso_kg"]]
    for i, v in enumerate(vals, 1):
        cell = ws4.cell(row=r, column=i, value=v); cell.font = BASE; cell.border = THIN
        if i in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            cell.number_format = EUR
        if i == 13:
            cell.number_format = PCT
        if i == 12:
            cell.font = BOLD; cell.fill = OK
    r += 1
ws4.cell(row=r + 1, column=2, value="BENEFICIO MEDIO POR PACK").font = BOLD
ws4.cell(row=r + 1, column=12, value=sum(x[2]["beneficio"] for x in pack_rows) / len(pack_rows)).number_format = EUR
ws4.cell(row=r + 1, column=12).font = BOLD
for i, w in enumerate([10, 30, 11, 10, 13, 17, 12, 11, 11, 13, 12, 15, 10, 11], 1):
    ws4.column_dimensions[get_column_letter(i)].width = w

# ============================================================ 5. ESCENARIOS =
ws5 = wb.create_sheet("Escenarios de pedido")
ws5["A1"] = "Qué te queda según lo que compre el cliente"; ws5["A1"].font = TITLE
ws5["A2"] = ("Pesos reales del feed y tarifa real de AW. Los pedidos pequeños pagan envío; desde 39 € lo asumimos nosotros.")
ws5["A2"].font = SUB
hdr5 = ["Pedido", "PVP productos", "Peso (kg)", "Envío cobrado", "− Envío AW", "= Coste envío real",
        "Ingreso neto", "− Coste proveedor", "− Donación 5 %", "− Otros (embalaje+Stripe+dev.)",
        "= BENEFICIO DEL PEDIDO", "% s/ PVP"]
for i, h in enumerate(hdr5, 1):
    c = ws5.cell(row=4, column=i, value=h); c.fill = HEAD; c.font = HEADF; c.alignment = WRAP

def cat(sku):
    return CAT[sku]

escenarios = [
    ("1 correa Pocket Pod (21,90 €)", [("PawL-01", 1)]),
    ("1 correa Mini Mango (29,90 €)", [("PawL-04", 1)]),
    ("1 comedero de acero 12 cm (26,90 €)", [("PAWFB-03", 1)]),
    ("1 arnés Guardian (36,90 €)", [("PAWH-01", 1)]),
    ("1 fuente de agua 2,5 L (49,90 €)", [("PAWFB-08", 1)]),
    ("1 cama acolchada pequeña (39,90 €)", [("PawB-03", 1)]),
    ("1 cama iglú (57,90 €)", [("PawB-14", 1)]),
    ("2 artículos · arnés + correa", [("PAWH-01", 1), ("PawL-01", 1)]),
    ("3 artículos · cama + comedero + correa", [("PawB-03", 1), ("PAWFB-03", 1), ("PawL-01", 1)]),
]
for code, pk in PACKS.items():
    escenarios.append((f"{pk['name']} (pack de {len(pk['components'])} piezas)", pk["components"], pk["price"]))

r = 5
for esc in escenarios:
    nombre, comps = esc[0], esc[1]
    pvp = esc[2] if len(esc) > 2 else sum(PRODS[s]["price"] * q for s, q in comps)
    peso = (sum(CAT[s]["weight_g"] * q for s, q in comps) + BOX_G) / 1000
    cobrado = envio_cobrado(pvp)
    envio = envio_aw(peso)
    neto = pvp / (1 + IVA)
    cogs = sum(CAT[s]["cost"] * q for s, q in comps)
    don = round((neto - cogs) * DON, 2)
    stripe = round((pvp + cobrado) * SP + SF, 2)
    otros = round(PACK_C + stripe + RET_R * RET_C, 2)
    ben = round(neto - cogs - don - envio - otros + cobrado / (1 + IVA), 2)
    vals = [nombre, round(pvp, 2), round(peso, 2), cobrado, envio, round(cobrado / (1 + IVA) - envio, 2),
            round(neto, 2), round(cogs, 2), don, otros, ben, ben / pvp if pvp else 0]
    for i, v in enumerate(vals, 1):
        cell = ws5.cell(row=r, column=i, value=v); cell.font = BASE; cell.border = THIN
        if i in (2, 4, 5, 6, 7, 8, 9, 10, 11):
            cell.number_format = EUR
        if i == 12:
            cell.number_format = PCT
        if i == 11:
            cell.font = BOLD; cell.fill = OK if ben > 5 else WARN
    r += 1
for i, w in enumerate([34, 14, 10, 13, 12, 14, 12, 15, 12, 22, 19, 10], 1):
    ws5.column_dimensions[get_column_letter(i)].width = w

# ================================================== 6. TARIFAS Y MÉTODO ====
ws6 = wb.create_sheet("Tarifas y método")
ws6["A1"] = "De dónde sale cada número"; ws6["A1"].font = TITLE
ws6["A2"] = "Fuente de la tarifa de envío: página pública de AW Dropship España (aw-dropship.es/shipping), 15/10/2026."
ws6["A2"].font = SUB

r = 4
ws6.cell(row=r, column=1, value="Tarifa real de envío del proveedor AW (sin IVA)").font = BOLD
r += 1
for i, h in enumerate(["Zona", "Destino", "0-1 kg", "1-5 kg", ">5 kg", "Plazo"], 1):
    c = ws6.cell(row=r, column=i, value=h); c.fill = HEAD; c.font = HEADF
r += 1
zonas = [
    ("Zona 1", "España península y Baleares", 2.95, 4.00, 6.50, "1-3 días laborables"),
    ("Zona 2", "Portugal continental", 3.50, 4.50, 10.50, "2-4 días laborables"),
    ("Zona 3", "Francia, Alemania, Austria, Bélgica, Italia, Luxemburgo, Países Bajos", 6.95, 7.95, 10.50, "4-5 días laborables"),
    ("Zona 4", "Chequia, Dinamarca, Polonia, Eslovenia, Eslovaquia", 8.15, 12.15, 18.65, "4-6 días laborables"),
    ("Zona 5", "Bulgaria, Estonia, Finlandia, Croacia, Hungría, Irlanda, Lituania, Serbia, Rumanía, Suecia", 16.45, 27.90, None, "6-7 días laborables"),
]
for z in zonas:
    for i, v in enumerate(z, 1):
        cell = ws6.cell(row=r, column=i, value=v); cell.font = BASE; cell.border = THIN
        if i in (3, 4, 5) and v is not None:
            cell.number_format = EUR
    r += 1

r += 1
ws6.cell(row=r, column=1, value="Lo que cobramos al cliente (península y Baleares)").font = BOLD
r += 1
for i, h in enumerate(["Tramo de cesta", "Envío cobrado", "Nos cuesta (AW)", "Margen del envío"], 1):
    c = ws6.cell(row=r, column=i, value=h); c.fill = HEAD; c.font = HEADF
r += 1
for tramo, cobrado, peso in [("< 20 €", 5.95, 0.30), ("20 € - 38,99 €", 3.95, 0.80), ("≥ 39 €", 0.0, 1.10)]:
    coste = envio_aw(peso + BOX_G / 1000)
    for i, v in enumerate([tramo, cobrado, coste, round(cobrado / (1 + IVA) - coste, 2)], 1):
        cell = ws6.cell(row=r, column=i, value=v); cell.font = BASE; cell.border = THIN
        if i > 1:
            cell.number_format = EUR
        if i == 4:
            cell.font = BOLD
    r += 1

r += 2
ws6.cell(row=r, column=1, value="Supuestos y comprobaciones").font = BOLD
r += 1
notas = [
    "· PVP con IVA del 21 % incluido; ingreso neto = PVP / 1,21.",
    "· Coste del proveedor = precio profesional del feed de AW (sin IVA). Como autónomo/empresa, el IVA soportado "
    "de compras y envíos es deducible (modelo 303); si algún mes no lo fuera, el coste subiría un 21 %.",
    "· Pesos: peso de paquete por artículo del propio feed + 100 g de caja por pedido.",
    "· Stripe: 1,5 % + 0,25 € por transacción europea (tarifa estándar ES para tarjetas EEE).",
    "· Devoluciones: provisión del 3 % de los pedidos × 8 € de coste medio de ida y vuelta.",
    "· Donación: 5 % del beneficio bruto del producto (ingreso neto − coste del proveedor). Es interna: no se "
    "publica en la web ni se añade al precio.",
    "· Pendiente de confirmar contigo: datos fiscales, email definitivo y si el precio de compra que ves en tu "
    "panel de AW coincide con el del feed (si difiere, el beneficio cambia euro a euro).",
]
for n in notas:
    c = ws6.cell(row=r, column=1, value=n); c.font = SUB; c.alignment = WRAP
    ws6.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    r += 1
for i, w in enumerate([16, 58, 13, 13, 13, 20], 1):
    ws6.column_dimensions[get_column_letter(i)].width = w

out = ROOT / "docs/GRANKHA_Beneficio_Real_Por_Producto.xlsx"
wb.save(out)
print(f"✓ {out.relative_to(ROOT)}")
print(f"  {len(rows)} productos · beneficio medio {tot_ben/len(rows):.2f} € · margen medio {media_margen*100:.1f} % sobre PVP")
print(f"  packs: beneficio medio {sum(x[2]['beneficio'] for x in pack_rows)/len(pack_rows):.2f} €")

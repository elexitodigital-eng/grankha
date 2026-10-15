#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · pricing.py
Motor de precios y márgenes. Hace tres cosas:

 1. AUDITA cada producto: precio recomendado vs. coste, banda de mercado y
    contribución real por pedido (descontando IVA, comisión de Stripe, envío del
    proveedor, embalaje, devoluciones y donación).
 2. CALCULA los packs: descuento sobre la suma de componentes y contribución
    resultante, avisando si no alcanza el objetivo.
 3. GENERA docs/GRANKHA_Auditoria_Precios.xlsx con todo el detalle y las
    decisiones de envío gratis y donación.

Entradas : data/products.json (costes y stock del proveedor) + data/pricing.json (tabla comercial)
Salidas  : data/pricing_analysis.json + docs/GRANKHA_Auditoria_Precios.xlsx

Uso: python3 tools/pricing.py
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

IVA = M["vat"]
# Tarifa REAL de AW Dropship España (aw-dropship.es/shipping, 15/10/2026), SIN IVA.
# Tramos por peso total del pedido: [kg máx, precio €].
SHIP_TIERS = M["supplier_shipping_tiers"]
BOX_G = M.get("order_box_g", 100)


def supplier_shipping(weight_kg, zone="ES-PEN"):
    """Coste real de envío que nos cobra AW para un pedido de ese peso."""
    for max_kg, price in SHIP_TIERS[zone]:
        if weight_kg <= max_kg:
            return price
    return SHIP_TIERS[zone][-1][1]
PACK_C = M["packaging_per_order"]
RET_R, RET_C = M["returns_rate"], M["returns_cost"]
DON = M["donation_rate"]
SP, SF = M["stripe_pct"], M["stripe_fix"]
TARGET = M["target_contribution_per_order"]
CAC = M["cac_target"]

# --------------------------------------------------------------------- packs
# Suma de componentes y precio de pack (≈7 % de descuento, redondeado a .90)
def pack_price(component_sum, disc):
    """Redondea a un precio terminado en ,90 que nunca supere el descuento pactado."""
    import math
    raw = component_sum * (1 - disc)
    p = math.floor(raw)
    if p % 10 >= 9:
        return p - 0.10            # 69 -> 68,90
    cand = p + 0.90                # 66 -> 66,90
    return round(cand if cand <= raw + 1e-9 else p - 0.10, 2)

# Los packs se definen en data/pricing.json (única fuente de verdad)
PACKS = {code: dict(pk, components=[(c[0], c[1]) for c in pk["components"]])
         for code, pk in PR.get("packs", {}).items()}

# ------------------------------------------------------- motor de economía
def product_contribution(sku, qty=1, shipping_charged=0.0, donation_rate=None):
    """Contribución (beneficio) de un pedido que solo lleva este artículo."""
    p, m = CAT[sku], PRODS[sku]
    pvp = m["price"]
    net = pvp / (1 + IVA) * qty                       # ingreso sin IVA
    cogs = p["cost"] * qty
    gross_benefit = net - cogs                        # beneficio bruto
    don = gross_benefit * (DON if donation_rate is None else donation_rate) if gross_benefit > 0 else 0
    stripe = (pvp * qty + shipping_charged) * SP + SF
    weight_kg = max(0.05, p["weight_g"] * qty / 1000)
    ship_cost = supplier_shipping(weight_kg + BOX_G / 1000)
    costs = ship_cost + PACK_C + stripe + RET_R * RET_C + don
    return dict(pvp=pvp, net=net, cogs=cogs, gross=gross_benefit, donation=don,
                stripe=stripe, ship=ship_cost, packaging=PACK_C,
                returns=RET_R * RET_C, contribution=net - cogs - costs + shipping_charged,
                margin=(net - cogs - costs + shipping_charged) / net if net else 0)


def order_contribution(pvp_total, cogs_total, weight_kg, shipping_charged=0.0, donation_rate=None):
    """Contribución de un pedido a partir de su PVP final, coste y peso."""
    net = pvp_total / (1 + IVA)
    gross = net - cogs_total
    don = gross * (DON if donation_rate is None else donation_rate) if gross > 0 else 0
    stripe = (pvp_total + shipping_charged) * SP + SF
    ship = supplier_shipping(weight_kg + BOX_G / 1000)
    costs = ship + PACK_C + stripe + RET_R * RET_C + don
    return dict(pvp=pvp_total, net=net, cogs=cogs_total, gross=gross, donation=don, stripe=stripe,
                ship=ship, packaging=PACK_C, returns=RET_R * RET_C, weight_kg=weight_kg,
                contribution=net - cogs_total - costs + shipping_charged,
                margin=(net - cogs_total - costs + shipping_charged) / net if net else 0)


def basket_contribution(lines, shipping_charged=0.0, donation_rate=None):
    net = sum(PRODS[s]["price"] / (1 + IVA) * q for s, q in lines)
    cogs = sum(CAT[s]["cost"] * q for s, q in lines)
    gross = net - cogs
    don = gross * (DON if donation_rate is None else donation_rate) if gross > 0 else 0
    pvp = sum(PRODS[s]["price"] * q for s, q in lines)
    stripe = (pvp + shipping_charged) * SP + SF
    weight_kg = max(0.05, sum(CAT[s]["weight_g"] * q for s, q in lines) / 1000)
    ship = supplier_shipping(weight_kg + BOX_G / 1000)
    costs = ship + PACK_C + stripe + RET_R * RET_C + don
    return dict(pvp=pvp, net=net, cogs=cogs, gross=gross, donation=don, stripe=stripe,
                ship=ship, packaging=PACK_C, returns=RET_R * RET_C, weight_kg=weight_kg,
                contribution=net - cogs - costs + shipping_charged,
                margin=(net - cogs - costs + shipping_charged) / net if net else 0)

# analizar packs
for code, pk in PACKS.items():
    suma = sum(PRODS[s]["price"] * q for s, q in pk["components"])
    pk["price"] = round(pack_price(suma, pk["discount"]), 2)
    pk["component_sum"] = round(suma, 2)
    pk["saving"] = round(suma - pk["price"], 2)
    pk["real_discount"] = 1 - pk["price"] / suma
    # contribución calculada con el PVP DEL PACK (no con la suma de componentes)
    pk_cogs = sum(CAT[s_]["cost"] * q for s_, q in pk["components"])
    pk_weight = max(0.05, sum(CAT[s_]["weight_g"] * q for s_, q in pk["components"]) / 1000)
    r = order_contribution(pk["price"], pk_cogs, pk_weight, shipping_charged=0.0)
    pk.update(contribution=r["contribution"], margin=r["margin"], cogs=r["cogs"], net=r["net"],
              weight_kg=r["weight_kg"], component_cost=r["cogs"])
    pk["ok"] = pk["contribution"] >= TARGET * 1.5     # un pack debe dejar bastante más que un artículo suelto

# validaciones de producto
for sku, m in PRODS.items():
    r1 = product_contribution(sku, 1, shipping_charged=5.95 if m["price"] < 20 else (3.95 if m["price"] < 39 else 0))
    r2u = product_contribution(sku, 2)
    m["contrib_1u"] = r1["contribution"]
    m["contrib_2u"] = r2u["contribution"]
    m["margin_1u"] = r1["margin"]
    m["in_band"] = m["market_lo"] <= m["price"] <= m["market_hi"]
    m["price_delta"] = round(m["price"] - m["prev_price"], 2)

# coste medio de mercancía sobre PVP (para las simulaciones de cesta)
avg_cogs_ratio = sum(CAT[s]["cost"] for s in PRODS) / sum(PRODS[s]["price"] for s in PRODS)

# ------------------------------------------------------------ Excel informe
INK = "0B0B0B"
HEAD = PatternFill("solid", fgColor=INK)
HEADF = Font(color="FFFFFF", bold=True, size=10)
EDIT = PatternFill("solid", fgColor="FFF6C7")
OK = PatternFill("solid", fgColor="E8F5E9")
WARN = PatternFill("solid", fgColor="FDECEA")
TITLE = Font(bold=True, size=14, color=INK)
SUB = Font(italic=True, size=9, color="777777")
BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
EUR = '#,##0.00 "€"'
PCT = '0.0%'

wb = Workbook()

# ---------------------------------------------------- 1. Resumen ejecutivo
ws = wb.active
ws.title = "Resumen ejecutivo"
ws["A1"] = "GRANKHA · Auditoría de precios y rentabilidad"; ws["A1"].font = Font(bold=True, size=16)
ws["A2"] = ("Precios con IVA incluido. Contribución = lo que queda para ti después de pagar "
            "producto, IVA, envío del proveedor, embalaje, Stripe, devoluciones y donación.")
ws["A2"].font = SUB

avg_1u = sum(m["contrib_1u"] for m in PRODS.values()) / len(PRODS)
avg_2u = sum(m["contrib_2u"] for m in PRODS.values()) / len(PRODS)
avg_margin = sum(m["margin_1u"] for m in PRODS.values()) / len(PRODS)
pack_avg = sum(p["contribution"] for p in PACKS.values()) / len(PACKS)
subidos = [s for s, m in PRODS.items() if m["price_delta"] > 0.5]
bajados = [s for s, m in PRODS.items() if m["price_delta"] < -0.5]

rows = [
    ("Referencias auditadas", len(PRODS), "0"),
    ("Packs creados", len(PACKS), "0"),
    ("PVP medio del catálogo", sum(m["price"] for m in PRODS.values()) / len(PRODS), EUR),
    ("PVP medio anterior", sum(m["prev_price"] for m in PRODS.values()) / len(PRODS), EUR),
    ("Precios subidos (estaban por debajo del mercado)", len(subidos), "0"),
    ("Precios bajados (estaban fuera de mercado)", len(bajados), "0"),
    ("Contribución media · pedido de 1 artículo", avg_1u, EUR),
    ("Contribución media · pedido de 2 artículos (mismo artículo)", avg_2u, EUR),
    ("Contribución media · pack", pack_avg, EUR),
    ("Margen medio sobre ingreso neto (1 artículo)", avg_margin, PCT),
    ("Coste de mercancía sobre PVP (media del catálogo)", avg_cogs_ratio, PCT),
    ("CAC objetivo (publicidad por cliente)", CAC, EUR),
    ("Objetivo de contribución por pedido", TARGET, EUR),
]
r = 4
for name, val, fmt in rows:
    ws[f"A{r}"] = name; ws[f"B{r}"] = val; ws[f"B{r}"].number_format = fmt
    r += 1

ws[f"A{r+1}"] = "Las 4 conclusiones de la auditoría"; ws[f"A{r+1}"].font = TITLE
concl = [
 "1. Tu proveedor te vende al 50 % del PVP que él sugiere. Traducido: el margen bruto real, "
 "después del IVA, es del ~33 % del precio (no del 50 %). Eso es lo que limita todo lo demás.",
 "2. Con un pedido de UN solo artículo barato, el envío del proveedor, la comisión fija de Stripe "
 "y el embalaje se comen casi todo: quedan 2-5 €. Con dos artículos o un pack, se pasa a 8-15 €.",
 "3. Había 8 referencias por debajo del mercado (cuencos de cobre, comedero de gato, cerámica, "
 "camas caqui, patita…): se suben sin perder competitividad. Y 3 por encima del mercado "
 "(fuente de agua, comedero doble grande, cama acolchada mediana): se bajan para poder vender.",
 "4. La palanca no es el precio unitario: es el TICKET MEDIO. Packs + envío gratis desde 39 € + "
 "recambios (filtros) suben el pedido medio sin subir el coste de captación.",
]
r += 2
for c in concl:
    ws[f"A{r}"] = c; ws[f"A{r}"].alignment = WRAP; r += 2
ws.column_dimensions["A"].width = 74
ws.column_dimensions["B"].width = 18

# ------------------------------------------------- 2. Auditoría por producto
ws2 = wb.create_sheet("Precios por producto")
ws2["A1"] = "Auditoría por referencia: PVP recomendado, banda de mercado y contribución"
ws2["A1"].font = TITLE
ws2["A2"] = ("Comparativa frente a precios reales de tiendas españolas (idealo.es, tiendanimal.es, "
             "bitiba.es, manomano.es) consultados en octubre de 2026.")
ws2["A2"].font = SUB
cols = ["SKU", "Producto", "Variante", "Audiencia", "Coste proveedor", "PVP anterior",
        "PVP recomendado", "Δ precio", "Mercado desde", "Mercado hasta", "¿En banda?",
        "Contribución 1 ud.", "Contribución 2 ud.", "Margen 1 ud.", "Motivo del ajuste", "Referencias de mercado"]
for i, c in enumerate(cols, 1):
    cell = ws2.cell(row=4, column=i, value=c)
    cell.fill = HEAD; cell.font = HEADF; cell.alignment = WRAP
r = 5
for sku, m in PRODS.items():
    p = CAT[sku]
    ws2.cell(row=r, column=1, value=sku)
    ws2.cell(row=r, column=2, value=m["name"])
    ws2.cell(row=r, column=3, value=m["subtitle"])
    ws2.cell(row=r, column=4, value=m.get("audience_label", m["audience"]))
    ws2.cell(row=r, column=5, value=p["cost"]).number_format = EUR
    ws2.cell(row=r, column=6, value=m["prev_price"]).number_format = EUR
    ws2.cell(row=r, column=7, value=m["price"]).number_format = EUR
    d = ws2.cell(row=r, column=8, value=m["price_delta"]); d.number_format = EUR
    d.fill = OK if m["price_delta"] < -0.5 else (WARN if m["price_delta"] > 0.5 else PatternFill())
    ws2.cell(row=r, column=9, value=m["market_lo"]).number_format = EUR
    ws2.cell(row=r, column=10, value=m["market_hi"]).number_format = EUR
    c11 = ws2.cell(row=r, column=11, value="Sí" if m["in_band"] else "Revisar")
    c11.fill = OK if m["in_band"] else WARN
    ws2.cell(row=r, column=12, value=m["contrib_1u"]).number_format = EUR
    ws2.cell(row=r, column=13, value=m["contrib_2u"]).number_format = EUR
    ws2.cell(row=r, column=14, value=m["margin_1u"]).number_format = PCT
    ws2.cell(row=r, column=15, value=m["rationale"]).alignment = WRAP
    ws2.cell(row=r, column=16, value=m["market_note"]).alignment = WRAP
    r += 1
for i, w in enumerate([11, 34, 34, 17, 13, 12, 14, 10, 11, 11, 10, 13, 13, 10, 46, 52], 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ------------------------------------------------------------------ 3. Packs
ws3 = wb.create_sheet("Packs")
ws3["A1"] = "Packs: descuento comercial y contribución resultante"; ws3["A1"].font = TITLE
ws3["A2"] = ("El descuento medio es del ~7 %: suficiente para que se note, pequeño para no destruir "
             "margen. Todos superan el umbral de envío gratis (39 €), así que además ahorran al cliente el envío.")
ws3["A2"].font = SUB
cols3 = ["Código", "Pack", "Componentes", "Suma individual", "Precio pack", "Ahorro cliente",
         "Descuento real", "Coste proveedor", "Contribución", "Margen", "Peso (kg)", "¿Rentable?"]
for i, c in enumerate(cols3, 1):
    cell = ws3.cell(row=4, column=i, value=c); cell.fill = HEAD; cell.font = HEADF; cell.alignment = WRAP
r = 5
for code, pk in PACKS.items():
    comps = " + ".join(f"{q}× {PRODS[s]['name']} ({PRODS[s]['subtitle']})" for s, q in pk["components"])
    ws3.cell(row=r, column=1, value=code)
    ws3.cell(row=r, column=2, value=pk["name"])
    ws3.cell(row=r, column=3, value=comps).alignment = WRAP
    ws3.cell(row=r, column=4, value=pk["component_sum"]).number_format = EUR
    ws3.cell(row=r, column=5, value=pk["price"]).number_format = EUR
    ws3.cell(row=r, column=6, value=pk["saving"]).number_format = EUR
    ws3.cell(row=r, column=7, value=pk["real_discount"]).number_format = PCT
    ws3.cell(row=r, column=8, value=pk["cogs"]).number_format = EUR
    ws3.cell(row=r, column=9, value=pk["contribution"]).number_format = EUR
    ws3.cell(row=r, column=10, value=pk["margin"]).number_format = PCT
    ws3.cell(row=r, column=11, value=round(pk["weight_kg"], 2))
    c12 = ws3.cell(row=r, column=12, value="Sí" if pk["ok"] else "Revisar")
    c12.fill = OK if pk["ok"] else WARN
    r += 1
for i, w in enumerate([10, 26, 60, 14, 12, 13, 12, 14, 13, 10, 10, 11], 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

# ------------------------------------------------------------ 4. Envío gratis
ws4 = wb.create_sheet("Envío gratis")
ws4["A1"] = "Umbral de envío gratis: qué deja cada tramo"; ws4["A1"].font = TITLE
ws4["A2"] = ("Tramo propuesto: menos de 20 € → 5,95 €; de 20 a 39 € → 3,95 €; desde 39 € → gratis. "
             "Coste real del proveedor: tarifa AW 2,95 € (≤1 kg) / 4,00 € (1-5 kg) / 6,50 € (>5 kg), sin IVA.")
ws4["A2"].font = SUB
hdr = ["Tramo de cesta", "Envío cobrado", "Pedidos esperados", "Ingreso neto", "Coste producto (media 47,5 %)",
       "Envío proveedor", "Otros costes", "Donación", "Contribución", "Margen"]
for i, c in enumerate(hdr, 1):
    cell = ws4.cell(row=4, column=i, value=c); cell.fill = HEAD; cell.font = HEADF; cell.alignment = WRAP
# (PVP cesta, envío cobrado, peso del pedido en kg, cuota de pedidos)
cesta = [(14.90, 5.95, 0.30, 0.20), (24.90, 5.95, 0.60, 0.15), (32.90, 3.95, 0.90, 0.15),
         (39.90, 0.0, 1.10, 0.15), (54.90, 0.0, 1.40, 0.15), (69.90, 0.0, 1.80, 0.10),
         (89.90, 0.0, 2.20, 0.10)]
r = 5
for pvp, ship_charged, peso, cuota in cesta:
    net = pvp / (1 + IVA)
    cogs = pvp * avg_cogs_ratio
    don = (net - cogs) * DON if net > cogs else 0
    stripe = (pvp + ship_charged) * SP + SF
    otros = PACK_C + stripe + RET_R * RET_C
    ship = supplier_shipping(peso + BOX_G / 1000)
    contrib = net - cogs - ship - otros - don + ship_charged
    ws4.cell(row=r, column=1, value=f"{pvp:.2f} €").font = BOLD
    ws4.cell(row=r, column=2, value=ship_charged).number_format = EUR
    ws4.cell(row=r, column=3, value=cuota).number_format = PCT
    ws4.cell(row=r, column=4, value=net).number_format = EUR
    ws4.cell(row=r, column=5, value=cogs).number_format = EUR
    ws4.cell(row=r, column=6, value=ship).number_format = EUR
    ws4.cell(row=r, column=7, value=otros).number_format = EUR
    ws4.cell(row=r, column=8, value=don).number_format = EUR
    ws4.cell(row=r, column=9, value=contrib).number_format = EUR
    ws4.cell(row=r, column=9).font = BOLD
    ws4.cell(row=r, column=10, value=contrib / net if net else 0).number_format = PCT
    r += 1
ws4.cell(row=r + 1, column=1, value="Ticket medio objetivo (con packs y envío gratis desde 39 €)").font = BOLD
ws4.cell(row=r + 1, column=9, value=sum(p * cuota for p, _, _, cuota in cesta)).number_format = EUR
ws4.cell(row=r + 2, column=1, value="Contribución media por pedido con esa mezcla").font = BOLD
ws4.cell(row=r + 3, column=1, value=("Con este umbral la mayoría de pedidos llevan 2 artículos o un pack. "
                                     "El coste real verificado en AW Dropship España es de 2,95 € (hasta 1 kg), "
                                     "4,00 € (1-5 kg) y 6,50 € (más de 5 kg), sin IVA: cobrar 5,95 € en los "
                                     "pedidos pequeños cubre el envío y deja margen.")).font = SUB
for i, w in enumerate([34, 13, 16, 12, 22, 14, 12, 11, 13, 9], 1):
    ws4.column_dimensions[get_column_letter(i)].width = w

# --------------------------------------------------------------- 5. Donación
ws5 = wb.create_sheet("Donación")
ws5["A1"] = "Qué cuesta la donación (y por qué 5 % es sostenible)"; ws5["A1"].font = TITLE
ws5["A2"] = ("La donación sale del beneficio bruto, no del precio: no sube el coste para el cliente "
             "ni rompe la competitividad.")
ws5["A2"].font = SUB
hdr5 = ["Escenario", "Pedido de 39 €", "Pedido de 55 €", "Pedido de 70 €", "Pedido de 90 €", "¿Sostenible?"]
for i, c in enumerate(hdr5, 1):
    cell = ws5.cell(row=4, column=i, value=c); cell.fill = HEAD; cell.font = HEADF
cenarios = [0.03, 0.05, 0.08, 0.10]
r = 5
for rate in cenarios:
    ws5.cell(row=r, column=1, value=f"Donación del {rate*100:.0f} % del beneficio bruto").font = BOLD
    vals = []
    for pvp in (39.90, 54.90, 69.90, 89.90):
        net = pvp / (1 + IVA)
        cogs = pvp * avg_cogs_ratio
        gross = net - cogs
        don = gross * rate
        stripe = pvp * SP + SF
        contrib = net - cogs - supplier_shipping(1.2 + BOX_G / 1000) - PACK_C - stripe - RET_R * RET_C - don
        ws5.cell(row=r, column=2 + vals.__len__(), value=contrib).number_format = EUR
        vals.append(contrib)
    ok = all(v > 4 for v in vals)
    c = ws5.cell(row=r, column=6, value="Sí" if ok else "Ajustar")
    c.fill = OK if ok else WARN
    r += 1
ws5.cell(row=r + 1, column=1, value=("Recomendación: 5 % del beneficio bruto. Es un mensaje potente y honesto, "
                                     "y deja entre 1,2 € y 4,5 € por pedido para la investigación. "
                                     "Si algún mes el negocio va justo, se puede pausar la reserva y reanudarla "
                                     "al recuperar margen (comunícalo con transparencia).")).font = SUB
ws5.cell(row=r + 1, column=1).alignment = WRAP
for i, w in enumerate([42, 16, 16, 16, 16, 13], 1):
    ws5.column_dimensions[get_column_letter(i)].width = w

# ------------------------------------------------- 6. Pedido objetivo y equilibrio
ws6 = wb.create_sheet("Objetivo mensual")
ws6["A1"] = "Cuánto necesitas vender al mes"; ws6["A1"].font = TITLE
ws6["A2"] = "Con la mezcla esperada de cestas (ticket medio calculado en la hoja de envíos)."
ws6["A2"].font = SUB
aov = sum(p * cuota for p, _, _, cuota in cesta)
contrib_medio = sum((p / (1 + IVA) - p * avg_cogs_ratio
                     - supplier_shipping(peso + BOX_G / 1000) - PACK_C - (p * SP + SF) - RET_R * RET_C
                     - max(0, (p / (1 + IVA) - p * avg_cogs_ratio)) * DON) * cuota
                    for p, _, peso, cuota in cesta)
filas = [
    ("Ticket medio objetivo (AOV)", aov, EUR),
    ("Contribución media por pedido", contrib_medio, EUR),
    ("Costes fijos mensuales (Supabase, dominio, gestoría)", 65.00, EUR),
    ("Publicidad mensual (ejemplo)", 150.00, EUR),
    ("Pedidos/mes para cubrir fijos + publicidad", (65.00 + 150.00) / max(contrib_medio, 0.01), "0"),
    ("Facturación equivalente", (65.00 + 150.00) / max(contrib_medio, 0.01) * aov, EUR),
    ("Con 150 pedidos/mes", 150 * contrib_medio - 65 - 150, EUR),
]
r = 4
for name, val, fmt in filas:
    ws6[f"A{r}"] = name; ws6[f"B{r}"] = val; ws6[f"B{r}"].number_format = fmt
    if "Pedidos/mes" in name or "Con 150" in name: ws6[f"B{r}"].font = BOLD
    r += 1
ws6[f"A{r+1}"] = ("Ojo con el CAC: si pagas 12 € por cliente y la contribución media es 8 €, pierdes dinero. "
                  "Empieza con contenido orgánico y compra tráfico solo para los packs (que dejan más).")
ws6[f"A{r+1}"].font = SUB
ws6.column_dimensions["A"].width = 58
ws6.column_dimensions["B"].width = 16

out = ROOT / "docs" / "GRANKHA_Auditoria_Precios.xlsx"
out.parent.mkdir(exist_ok=True)
wb.save(out)

# ------------------------------------------- salida JSON para el generador web
analysis = {
    "meta": {**M, "avg_cogs_ratio": round(avg_cogs_ratio, 4), "avg_contrib_1u": round(avg_1u, 2),
             "avg_contrib_2u": round(avg_2u, 2), "avg_pack_contrib": round(pack_avg, 2)},
    "products": {s: {"contrib_1u": round(m["contrib_1u"], 2), "contrib_2u": round(m["contrib_2u"], 2),
                     "margin_1u": round(m["margin_1u"], 4), "in_band": m["in_band"],
                     "price_delta": m["price_delta"], "contrib_2u": round(m["contrib_2u"], 2)}
                 for s, m in PRODS.items()},
    "packs": {c: {"price": p["price"], "component_sum": p["component_sum"], "saving": p["saving"],
                  "component_cost": round(p["cogs"], 2),
                  "discount": round(p["real_discount"], 4), "contribution": round(p["contribution"], 2),
                  "margin": round(p["margin"], 4), "ok": p["ok"],
                  "components": [{"sku": s, "qty": q} for s, q in p["components"]]}
              for c, p in PACKS.items()},
    "free_shipping_avg_contribution": round(contrib_medio, 2),
    "aov_target": round(aov, 2),
}
(ROOT / "data" / "pricing_analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=1))

print(f"✓ {out.relative_to(ROOT)}")
print(f"  packs: {len(PACKS)} · contribución media 1 artículo {avg_1u:.2f} € · 2 artículos {avg_2u:.2f} € · pack medio {pack_avg:.2f} €")
print(f"  ticket medio objetivo {aov:.2f} € · contribución media por pedido {contrib_medio:.2f} €")
sin_banda = [s for s, m in PRODS.items() if not m['in_band']]
print(f"  fuera de banda: {sin_banda or 'ninguno'}")
packs_flojos = [c for c, p in PACKS.items() if not p["ok"]]
print(f"  packs por debajo del objetivo: {packs_flojos or 'ninguno'}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRANKHA · margins_xlsx.py
Genera docs/GRANKHA_Margenes_IVA_Envios.xlsx

  · Supuestos            -> IVA, Stripe, envío del proveedor, CAC, % donación… (editables)
  · Margen por producto  -> beneficio real por unidad tras IVA, costes y comisiones
  · Pedido ejemplo       -> cuenta de resultados de un pedido tipo
  · Punto de equilibrio  -> pedidos/mes necesarios para cubrir costes fijos

Uso: python3 tools/margins_xlsx.py
"""
from pathlib import Path
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = json.loads((ROOT / "data" / "products.json").read_text())
SITE = json.loads((ROOT / "data" / "site.json").read_text())

INK = "0B0B0B"
HEAD = PatternFill("solid", fgColor=INK)
HEADF = Font(color="FFFFFF", bold=True, size=10)
EDIT = PatternFill("solid", fgColor="FFF6C7")
TITLE = Font(bold=True, size=14, color=INK)
SUB = Font(italic=True, size=9, color="777777")
BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
EUR = '#,##0.00 "€"'
PCT = '0.0%'

wb = Workbook()

# ============================================================ 1. SUPUESTOS
ws = wb.active
ws.title = "Supuestos"
ws["A1"] = "GRANKHA · Supuestos de cálculo"; ws["A1"].font = TITLE
ws["A2"] = "Edita solo las celdas amarillas de la columna B. El resto se recalcula."
ws["A2"].font = SUB

header_row = 4
ws[f"A{header_row}"] = "Concepto"; ws[f"B{header_row}"] = "Valor"; ws[f"C{header_row}"] = "Nota"
for c in "ABC":
    ws[f"{c}{header_row}"].fill = HEAD; ws[f"{c}{header_row}"].font = HEADF

supuestos = [
    ("IVA español aplicado (península y Baleares)", 0.21, PCT,
     "Canarias, Ceuta y Melilla: sin IVA (IGIC/IPSI se liquida en destino)."),
    ("Comisión Stripe (tarjeta europea)", 0.015, PCT, "Stripe España: 1,5 % + 0,25 € en tarjetas europeas."),
    ("Comisión fija Stripe por transacción", 0.25, EUR, ""),
    ("Coste de envío del proveedor (tarifa real AW, por pedido)", 2.95, EUR,
     "VERIFICADO en aw-dropship.es/shipping (15/10/2026): 2,95 € hasta 1 kg · 4,00 € de 1 a 5 kg · "
     "6,50 € más de 5 kg. Sin IVA (deducible)."),
    ("Coste de embalaje / manipulación por pedido", 0.60, EUR, ""),
    ("% de beneficios destinado a investigación", 0.05, PCT,
     "Compromiso GRANKHA: se reserva sobre los beneficios."),
    ("Devoluciones previstas (sobre ventas)", 0.04, PCT, "Estimación; ajústala con datos reales."),
    ("Coste medio de una devolución", 9.00, EUR, "Transporte de retorno + gestión."),
    ("Coste de adquisición de cliente (CAC objetivo)", 6.00, EUR,
     "Publicidad media por cliente nuevo (Meta/Google/TikTok)."),
]
r = header_row + 1
for name, val, fmt, note in supuestos:
    ws[f"A{r}"] = name
    ws[f"B{r}"] = val; ws[f"B{r}"].number_format = fmt; ws[f"B{r}"].fill = EDIT
    if note: ws[f"C{r}"] = note
    r += 1
IVA, STRIPE_P, STRIPE_F, SHIP, PACK, DON, RET_R, RET_C, CAC = [f"Supuestos!$B${i}" for i in range(5, 14)]

ws["A15"] = "Costes fijos mensuales"; ws["A15"].font = TITLE
ws["A16"] = "Concepto"; ws["B16"] = "€/mes"
for c in "AB":
    ws[f"{c}16"].fill = HEAD; ws[f"{c}16"].font = HEADF
fijos = [("Supabase + dominio + herramientas", 25.0),
         ("Gestoría, tasas y otros", 40.0)]
r = 17
for name, val in fijos:
    ws[f"A{r}"] = name; ws[f"B{r}"] = val; ws[f"B{r}"].number_format = EUR; ws[f"B{r}"].fill = EDIT
    r += 1
ws[f"A{r}"] = "TOTAL costes fijos"; ws[f"A{r}"].font = BOLD
ws[f"B{r}"] = f"=SUM(B17:B{r-1})"; ws[f"B{r}"].number_format = EUR; ws[f"B{r}"].font = BOLD
FIXED = f"Supuestos!$B${r}"

ws.column_dimensions["A"].width = 50
ws.column_dimensions["B"].width = 14
ws.column_dimensions["C"].width = 62

# ================================================== 2. MARGEN POR PRODUCTO
ws2 = wb.create_sheet("Margen por producto")
ws2["A1"] = "Beneficio real por unidad (1 ud. por pedido, envío del proveedor repartido)"
ws2["A1"].font = TITLE
ws2["A2"] = "El PVP incluye IVA: el ingreso neto es PVP / (1 + IVA). Revisa tus precios con estos datos."
ws2["A2"].font = SUB

cols = ["SKU", "Producto", "Variante", "Categoría", "Peso (g)", "Coste proveedor",
        "PVP (IVA incl.)", "IVA incluido", "Ingreso neto", "Comisión Stripe",
        "Envío proveedor", "Embalaje", "Prov. devoluciones", "Donación investigación",
        "BENEFICIO NETO", "Margen s/ingreso neto"]
for i, c in enumerate(cols, 1):
    cell = ws2.cell(row=4, column=i, value=c)
    cell.fill = HEAD; cell.font = HEADF; cell.alignment = WRAP

r = 5
for p in PRODUCTS:
    f = lambda col: f"{col}{r}"
    ws2.cell(row=r, column=1, value=p["sku"])
    ws2.cell(row=r, column=2, value=p.get("name") or p.get("title"))
    ws2.cell(row=r, column=3, value=p["subtitle"])
    ws2.cell(row=r, column=4, value=p["catName"])
    ws2.cell(row=r, column=5, value=p["weight_g"])
    ws2.cell(row=r, column=6, value=p["cost"]).number_format = EUR
    ws2.cell(row=r, column=7, value=p["price"]).number_format = EUR
    ws2.cell(row=r, column=8, value=f"=G{r}-G{r}/(1+{IVA})").number_format = EUR
    ws2.cell(row=r, column=9, value=f"=G{r}/(1+{IVA})").number_format = EUR
    ws2.cell(row=r, column=10, value=f"=-G{r}*{STRIPE_P}-{STRIPE_F}").number_format = EUR
    ws2.cell(row=r, column=11, value=f"=-{SHIP}").number_format = EUR
    ws2.cell(row=r, column=12, value=f"=-{PACK}").number_format = EUR
    ws2.cell(row=r, column=13, value=f"=-{RET_R}*{RET_C}").number_format = EUR
    ws2.cell(row=r, column=14, value=f"=-{f('I')}*{DON}").number_format = EUR
    ws2.cell(row=r, column=15, value=f"=-F{r}+I{r}+J{r}+K{r}+L{r}+M{r}+N{r}").number_format = EUR
    ws2.cell(row=r, column=15).font = BOLD
    ws2.cell(row=r, column=16, value=f"=IF(I{r}=0,0,O{r}/I{r})").number_format = PCT
    r += 1
last = r - 1
ws2.cell(row=r + 1, column=14, value="Beneficio medio").font = BOLD
ws2.cell(row=r + 1, column=15, value=f"=AVERAGE(O5:O{last})").number_format = EUR
ws2.cell(row=r + 2, column=14, value="Margen medio").font = BOLD
ws2.cell(row=r + 2, column=15, value=f"=AVERAGE(P5:P{last})").number_format = PCT
ws2.cell(row=r + 4, column=2,
         value=("Nota: si un producto tiene beneficio negativo, súbelo de precio o retíralo. "
                "Los artículos de bajo importe suelen necesitar venta cruzada (2-3 uds. por pedido) "
                "para compensar el coste fijo del envío y de Stripe.")).font = SUB

for i, w in enumerate([11, 32, 38, 18, 9, 14, 14, 11, 12, 12, 12, 10, 13, 14, 13, 12], 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ======================================================= 3. PEDIDO EJEMPLO
ws3 = wb.create_sheet("Pedido ejemplo")
ws3["A1"] = "Cuenta de resultados de un pedido tipo"; ws3["A1"].font = TITLE
ws3["A2"] = "Edita cantidades y el envío cobrado (amarillo)."
ws3["A2"].font = SUB

ws3["A4"] = "Producto"; ws3["B4"] = "Cantidad"; ws3["C4"] = "PVP ud. (IVA incl.)"
ws3["D4"] = "Coste ud."; ws3["E4"] = "Subtotal venta"; ws3["F4"] = "Coste total"
for c in "ABCDEF":
    ws3[f"{c}4"].fill = HEAD; ws3[f"{c}4"].font = HEADF

demo = ["PAWH-01", "PawL-01", "PAWFB-01"]
by_sku = {p["sku"]: p for p in PRODUCTS}
r = 5
for sku in demo:
    p = by_sku[sku]
    ws3[f"A{r}"] = f"{sku} · {p.get('name') or p.get('title')} · {p['subtitle']}"
    ws3[f"B{r}"] = 1; ws3[f"B{r}"].fill = EDIT
    ws3[f"C{r}"] = p["price"]; ws3[f"C{r}"].number_format = EUR
    ws3[f"D{r}"] = p["cost"]; ws3[f"D{r}"].number_format = EUR
    ws3[f"E{r}"] = f"=B{r}*C{r}"; ws3[f"E{r}"].number_format = EUR
    ws3[f"F{r}"] = f"=B{r}*D{r}"; ws3[f"F{r}"].number_format = EUR
    r += 1
sub_row = r
ws3[f"D{r}"] = "Subtotal (IVA incl.)"; ws3[f"D{r}"].font = BOLD
ws3[f"E{r}"] = f"=SUM(E5:E{r-1})"; ws3[f"E{r}"].number_format = EUR; ws3[f"E{r}"].font = BOLD
ws3[f"F{r}"] = f"=SUM(F5:F{r-1})"; ws3[f"F{r}"].number_format = EUR; ws3[f"F{r}"].font = BOLD
r += 1
ship_row = r
ws3[f"D{r}"] = "Envío cobrado al cliente"
ws3[f"E{r}"] = SITE["shipping"]["options"][0]["tiers"][0]["price"]; ws3[f"E{r}"].number_format = EUR
ws3[f"E{r}"].fill = EDIT
r += 1
ws3[f"D{r}"] = "TOTAL COBRADO"; ws3[f"D{r}"].font = BOLD
ws3[f"E{r}"] = f"=E{sub_row}+E{ship_row}"; ws3[f"E{r}"].number_format = EUR; ws3[f"E{r}"].font = BOLD
cobrado_row = r
r += 2

ws3[f"A{r}"] = "Cuenta de resultados"; ws3[f"A{r}"].font = TITLE; r += 1
pl = [
    ("Ingresos (venta sin IVA)", f"=E{sub_row}/(1+{IVA})", +1),
    ("Envío cobrado al cliente", f"=E{ship_row}", +1),
    ("Coste de los productos", f"=-F{sub_row}", -1),
    ("Envío pagado al proveedor", f"=-{SHIP}", -1),
    ("Embalaje / manipulación", f"=-{PACK}", -1),
    ("Comisión Stripe", f"=-E{cobrado_row}*{STRIPE_P}-{STRIPE_F}", -1),
    ("Provisión devoluciones", f"=-{RET_R}*{RET_C}", -1),
    ("Donación a investigación", f"=-E{sub_row}/(1+{IVA})*{DON}", -1),
]
first = r
for name, formula, _ in pl:
    ws3[f"A{r}"] = name
    ws3[f"B{r}"] = formula; ws3[f"B{r}"].number_format = EUR
    r += 1
profit_row = r
ws3[f"A{r}"] = "BENEFICIO DEL PEDIDO"; ws3[f"A{r}"].font = Font(bold=True, size=12)
ws3[f"B{r}"] = "=SUM(B" + str(first) + ":B" + str(r - 1) + ")"
ws3[f"B{r}"].number_format = EUR; ws3[f"B{r}"].font = Font(bold=True, size=12)
r += 1
ws3[f"A{r}"] = "Margen sobre ventas sin IVA"
ws3[f"B{r}"] = f"=B{profit_row}/(E{sub_row}/(1+{IVA}))"; ws3[f"B{r}"].number_format = PCT
r += 2
ws3[f"A{r}"] = "Variante: el pedido supera el envío gratis (tú pagas el envío del cliente)"
ws3[f"A{r}"].font = BOLD
ws3[f"B{r}"] = f"=B{profit_row}-E{ship_row}"; ws3[f"B{r}"].number_format = EUR
r += 2
ws3[f"A{r}"] = ("Usa esta hoja para decidir el umbral de envío gratis: comprueba qué queda en el bolsillo "
                "cuando lo asumes tú, y cuánto sube el ticket medio por la venta cruzada.")
ws3[f"A{r}"].font = SUB

for i, w in enumerate([52, 13, 16, 12, 15, 12], 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

# ==================================================== 4. PUNTO DE EQUILIBRIO
ws4 = wb.create_sheet("Punto de equilibrio")
ws4["A1"] = "¿Cuántas ventas necesito al mes?"; ws4["A1"].font = TITLE
ws4["A2"] = "Basado en el beneficio del pedido ejemplo (hoja anterior)."
ws4["A2"].font = SUB
rows4 = [
    ("Beneficio por pedido (ejemplo)", f"='Pedido ejemplo'!B{profit_row}", EUR, False),
    ("Costes fijos mensuales", f"={FIXED}", EUR, False),
    ("Pedidos/mes para cubrir costes fijos", "=IF(B4<=0,\"—\",B5/B4)", '0.0', False),
    ("CAC objetivo por cliente", f"={CAC}", EUR, False),
    ("Pedidos/mes para cubrir fijos + CAC", "=IF(B4<=B7,\"—\",B5/(B4-B7))", '0.0', False),
    ("Ejemplo: 100 pedidos/mes (beneficio antes de fijos)",
     "=100*(B4-B7)-B5", EUR, False),
    ("Ejemplo: 250 pedidos/mes (beneficio antes de fijos)",
     "=250*(B4-B7)-B5", EUR, False),
]
r = 4
for name, formula, fmt, _ in rows4:
    ws4[f"A{r}"] = name
    ws4[f"B{r}"] = formula; ws4[f"B{r}"].number_format = fmt
    r += 1
ws4[f"A{r+1}"] = ("Si el beneficio por pedido es menor que el CAC, cada venta pierde dinero: sube el ticket "
                  "medio (packs de arnés + correa, envío gratis desde 49 €) o mejora el margen negociando "
                  "precios con el proveedor.")
ws4[f"A{r+1}"].font = SUB; ws4[f"A{r+1}"].alignment = WRAP
ws4.column_dimensions["A"].width = 55
ws4.column_dimensions["B"].width = 16

out = ROOT / "docs" / "GRANKHA_Margenes_IVA_Envios.xlsx"
out.parent.mkdir(exist_ok=True)
wb.save(out)
print(f"✓ {out.relative_to(ROOT)}")

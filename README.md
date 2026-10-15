# GRANKHA · Accesorios para mascotas

Ecommerce estático (HTML/CSS/JS, sin dependencias) generado a partir del catálogo real del
proveedor **AW Dropshipping** (canal *ZENQA LIFE*). Estética blanco y negro, limpia y
minimalista. Incluye el compromiso de marca: **un porcentaje de los beneficios se destina a
la investigación del cáncer y las enfermedades raras en mascotas** (en memoria de khalid).

**Web publicada:** https://elexitodigital-eng.github.io/grankha

---

## Qué incluye

| Página | Contenido |
|---|---|
| `index.html` | Hero, categorías, destacados, sección «Compromiso y corazón», newsletter |
| `tienda.html` | 44 referencias (38 productos + 6 packs) con filtros por categoría, por mascota (perro/gato), búsqueda y ordenación |
| `<slug>.html` × 44 | Ficha de producto o pack: foto, características, medidas, variantes, packs sugeridos, schema.org |
| `carrito.html` | Carrito con cantidades, método de envío, IVA y checkout |
| `compromiso.html` | La historia completa (texto original, khalid como gato blanco) y preguntas sobre la donación |
| `envios.html` | Tarifas, plazos, devoluciones 30 días y FAQ |
| `contacto.html` | Formulario (abre el correo con todo rellenado) |
| `legal.html` | Aviso legal, condiciones de venta, privacidad y cookies |
| `404.html` | Página de error |

**Funciona sin servidor ni build en el navegador.** Cada página es autocontenida (CSS, JS e
imágenes en línea), así que se ve igual en GitHub Pages, abriendo el archivo en local o
dentro de una previsualización sin red. No usa CDN, ni fuentes externas, ni cookies.

---

## Fiscalidad y envíos (España)

- Precios mostrados **con IVA (21 %) incluido**; el carrito desglosa el IVA.
- Canarias, Ceuta y Melilla: sin IVA (IGIC/IPSI en destino), con su propia tarifa de envío.
- **Envío por tramos** (península): hasta 20 € → 5,95 € · de 20 € a 39 € → 3,95 € · **desde 39 € → gratis**.
- **Donación**: 5 % de los beneficios a investigación del cáncer y enfermedades raras en mascotas.
- Precios auditados contra el mercado real (idealo, Tiendanimal, Bitiba, ManoMano) y
  contribución por pedido calculada en **`docs/GRANKHA_Auditoria_Precios.xlsx`**.
- 6 **packs** con 5,8-9 % de descuento que elevan el ticket medio y la rentabilidad.

---

## Estructura del repositorio

```
grankha/
├─ index.html, tienda.html, carrito.html…   ← sitio generado (lo que se publica)
├─ data/
│  ├─ feed.json            ← data feed original del proveedor
│  ├─ products.json        ← catálogo normalizado (lo genera catalog.py)
│  └─ site.json            ← configuración: contacto, envíos, IVA, endpoint de pago
├─ src/
│  ├─ styles.css           ← sistema de diseño (se incrusta en cada página)
│  └─ app.js               ← carrito, filtros, checkout (se incrusta en cada página)
├─ tools/
│  ├─ feed_sync.py         ← descarga catálogo + imágenes del proveedor
│  ├─ pricing.py           ← audita precios y packs, genera el Excel de auditoría
│  ├─ catalog.py           ← normaliza el catálogo, compone imágenes de pack
│  ├─ build.py             ← genera todas las páginas HTML, sitemap, OG y precios de servidor
│  └─ margins_xlsx.py      ← Excel de márgenes (modelo base)
├─ assets/img/             ← fotos de producto, miniaturas y OG
├─ supabase/               ← esquema SQL + funciones Edge (Stripe)
└─ docs/                   ← pendientes, guía de Stripe/Supabase y Excel de márgenes
```

## Actualizar el catálogo (precios, stock, nuevos productos)

```bash
# 1) descarga del proveedor (token en variable de entorno, nunca en el repo)
AIKU_TOKEN='tu_token' python3 tools/feed_sync.py

# 2) audita precios y recalcula márgenes y packs
python3 tools/pricing.py

# 3) normaliza catálogo y procesa imágenes (incluye packs)
python3 tools/catalog.py --raw data/raw

# 4) regenera el sitio
python3 tools/build.py
```

> Si añades productos nuevos, define su ficha comercial (nombre, precio, copy, audiencia)
> en `data/pricing.json`. Los productos sin ficha se omiten con aviso.
>
> Staging del proveedor: `python3 tools/feed_sync.py --api https://api.aiku-sandbox.uk`
> (el token de staging se resetea cada domingo a las 03:00 UTC).

## Publicar en GitHub Pages

```bash
git add -A && git commit -m "Actualizar catálogo" && git push
```

GitHub Pages sirve la rama `main` en la raíz: los cambios están online en ~1 minuto.

---

## Cómo vender hoy

Manual completo en **`docs/COMO_VENDER_YA.md`** (2 h de configuración para estar vendiendo):

1. **Datos legales** (razón social, NIF, domicilio, teléfono) → a `legal.html`.
2. **Stripe**: cuenta + funciones desplegadas + endpoint en `data/site.json`.
3. **Supabase**: ejecutar `supabase/schema.sql` (pedidos, suscriptores, KPIs).
4. **Flujo de pedidos**: manual (panel de AW Dropshipping) o automático con
   `supabase/functions/fulfill-order`.
5. **Seguimiento**: guardas el tracking en `orders.tracking_code` y el cliente recibe el
   email con las plantillas de `docs/emails/`.

Sin Stripe, el checkout ya funciona en modo «confirmar por email» con el desglose completo
(referencia, artículos, IVA, envío y total), y sin Supabase la tienda opera igualmente.

---

© GRANKHA · ZENQA LIFE · *GRANKHA por la salud animal*

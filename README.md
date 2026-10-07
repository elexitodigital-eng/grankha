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
| `tienda.html` | Las 38 referencias con filtros por categoría, búsqueda y ordenación |
| `<slug>.html` × 38 | Ficha de producto: galería, características, medidas, variantes, envío, schema.org |
| `carrito.html` | Carrito con cantidades, método de envío, IVA y checkout |
| `compromiso.html` | La historia completa (texto original) y preguntas sobre la donación |
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
- Envío gratis en península a partir de **49 €** (umbral editable).
- Gastos del proveedor, comisión de Stripe, devoluciones y CAC modelados en
  `docs/GRANKHA_Margenes_IVA_Envios.xlsx`.

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
│  ├─ catalog.py           ← normaliza el catálogo y procesa las imágenes
│  ├─ build.py             ← genera todas las páginas HTML, sitemap y OG
│  └─ margins_xlsx.py      ← genera el Excel de márgenes
├─ assets/img/             ← fotos de producto, miniaturas y OG
├─ supabase/               ← esquema SQL + funciones Edge (Stripe)
└─ docs/                   ← pendientes, guía de Stripe/Supabase y Excel de márgenes
```

## Actualizar el catálogo (precios, stock, nuevos productos)

```bash
# 1) descarga del proveedor (token en variable de entorno, nunca en el repo)
AIKU_TOKEN='tu_token' python3 tools/feed_sync.py

# 2) normaliza catálogo y procesa imágenes
python3 tools/catalog.py --raw data/raw

# 3) regenera el sitio
python3 tools/build.py
```

> Si añades productos nuevos, define su ficha (título comercial, talla, color, peso…) en la
> tabla `SPECS` de `tools/catalog.py`. Los productos sin especificación se omiten con aviso.
>
> Staging del proveedor: `python3 tools/feed_sync.py --api https://api.aiku-sandbox.uk`
> (el token de staging se resetea cada domingo a las 03:00 UTC).

## Publicar en GitHub Pages

```bash
git add -A && git commit -m "Actualizar catálogo" && git push
```

GitHub Pages sirve la rama `main` en la raíz: los cambios están online en ~1 minuto.

---

## Pendiente (ver `docs/PENDIENTES.md`)

1. **Datos fiscales** en `legal.html` (razón social, NIF, domicilio, teléfono) — antes de vender.
2. **Stripe**: cuenta + desplegar funciones → pegar endpoint en `data/site.json`
   (`docs/CONECTAR_STRIPE_SUPABASE.md`).
3. **Supabase**: ejecutar `supabase/schema.sql` para registrar pedidos y suscriptores.

Sin Stripe, el checkout ya funciona en modo «confirmar por email» con el desglose completo
(referencia, artículos, IVA, envío y total), y sin Supabase la tienda opera igualmente.

---

© GRANKHA · ZENQA LIFE · *GRANKHA por la salud animal*

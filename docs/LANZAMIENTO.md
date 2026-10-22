# GRANKHA · estado del lanzamiento

_Actualizado: 22 de octubre de 2026 · Resend configurado y panel de pedidos en marcha_

## Dominio definitivo

**https://grankha.roadshop.online** ← esta es la web. Dominio verificado en Vercel y sirviendo producción.
`https://grankha-beta.vercel.app` sigue viva como alias secundario (mismo proyecto, mismo contenido).

## Qué está funcionando ya (comprobado hoy, no "debería")

| Pieza | Estado |
|---|---|
| **Web** | 85 páginas en producción en `grankha.roadshop.online`. Todas responden 200 (portada, tienda, packs, fichas, compromiso, envíos, legal, carrito, contacto, sitemap, robots). |
| **Dominio** | `grankha.roadshop.online` verificado en Vercel. Canonical, Open Graph, JSON-LD, `sitemap.xml` y `robots.txt` apuntan ya al dominio nuevo. Cero referencias a `grankha-beta` en el HTML publicado. |
| **Datos de empresa** | Titular **GRANKHA**, correo **grankha@roadshop.online**, modelo de envío **directo (dropshipping) con AW Dropshipping**. Publicado en aviso legal, condiciones (punto 4), privacidad (destinatarios) y página de envíos. |
| **Pago con tarjeta** | Stripe en modo real (`rk_live`). Probado hoy en el dominio nuevo: la cesta crea la sesión y devuelve URL de Stripe Checkout. Referencia `GRK-261022-46UE`, total **58,80 €**, moneda **EUR**, IVA incluido 10,20 €, envío 0 € (gratis desde 39 €), reserva interna 0,90 €. Precio adaptativo de Stripe desactivado: siempre euros. |
| **Precios y envío** | Se recalculan **en el servidor**; el navegador no puede tocar importes. Zonas (península, Baleares, Canarias/Ceuta/Melilla, Portugal, UE) y tramos iguales que la web. Canarias sin IVA (IGIC/IPSI en destino). |
| **Base de datos** | Supabase `ravvjwyjaxofidgueopc`: `orders`, `order_items`, `subscribers`, `contact_messages` + vistas de KPIs. RLS activo. El pedido de prueba se guardó y se leyó correctamente; luego se borró. |
| **Webhook de Stripe** | `we_1URVX35u1hLzWyIGYIjzIbo9` → **`https://grankha.roadshop.online/api/stripe-webhook`** (URL actualizada hoy). Firma mala → 400, comprobado en el dominio nuevo. |
| **Formulario de contacto** | `/api/contact` → 200 y mensaje guardado en `contact_messages`, comprobado hoy en el dominio nuevo. Si el backend fallara, cae a mailto. |
| **Newsletter** | Guarda el email en Supabase con la clave pública. |
| **Pantalla de gracias** | `carrito.html?estado=ok` limpia la cesta y confirma el pedido. Si se cancela, avisa y deja la cesta intacta. |

## Variables de entorno en Vercel (proyecto `grankha`)

- `STRIPE_SECRET_KEY` (restringida, `rk_live_…`)
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL` · `SUPABASE_SERVICE_ROLE_KEY`
- `SITE_URL` = `https://grankha.roadshop.online`
- `EMAIL_PROVIDER` = `resend` · `RESEND_API_KEY` (cifrada)
- `EMAIL_FROM` = `GRANKHA <grankha@roadshop.online>`
- `EMAIL_REPLY_TO` = `grankha@roadshop.online`
- `EMAIL_AVISO` = `elexitodigital@gmail.com`
- `ADMIN_TOKEN` (cifrada) · credencial del panel `/api/panel`
- `SUPPLIER_NAME` = `AW Dropshipping` · `DELIVERY_DAYS` = `3-8`

## Correo con Resend · estado

Proveedor elegido: **Resend**. Las tres plantillas están escritas, probadas con envíos reales y
conectadas:

| Correo | Para quién | Cuándo |
|---|---|---|
| Pedido confirmado | el cliente | automático al cobrar Stripe |
| Aviso de venta (margen + bloque para copiar a AW) | tú | automático, a la vez |
| Envío con seguimiento | el cliente | cuando lo marcas en el panel |

Plantillas en `api/_lib/emails.js`; las usan `api/stripe-webhook.js` y `api/admin.js`.

**Falta un paso, y es tuyo:** verificar `roadshop.online` en Resend y añadir 3 registros DNS en
IONOS. Hoy Resend responde `The roadshop.online domain is not verified`, así que los correos se
generan pero no salen. **Ningún pedido se pierde**: se guarda en Supabase, el fallo queda anotado
en `orders.order_email_error` y se reenvía con un clic desde el panel en cuanto el dominio esté
verificado. Instrucciones paso a paso en **`docs/RESEND_Y_PANEL.md`**.

Los registros van sobre `send.roadshop.online` y `resend._domainkey.roadshop.online`, **no sobre
la raíz**: el MX de IONOS y el buzón `grankha@roadshop.online` no se tocan.

## Panel privado de pedidos

**`https://grankha.roadshop.online/api/panel?token=<ADMIN_TOKEN>`** · la primera vez fija una
cookie HttpOnly y redirige a `/api/panel`. Sin credencial devuelve 404 idéntico al de cualquier
otra URL inexistente: no hay ninguna página pública que delate el panel.

Fuera del sitemap y con `noindex`. Sin token el servidor devuelve 401. Desde ahí: ver pedidos,
filtrar los que faltan por pasar a AW o por avisar, copiar el bloque para el proveedor, marcar
enviado con seguimiento (manda el correo al cliente) y reenviar cualquier correo que fallara.
Endpoint `api/admin.js`, todo protegido por token con comparación en tiempo constante.

## Lo único que falta para cerrar

### 1. Verificar el dominio en Resend 🔴 (el único bloqueante)

Añadir `roadshop.online` en https://resend.com/domains y copiar los 3 registros que te dé
Resend al panel DNS de IONOS. Detalle completo en **`docs/RESEND_Y_PANEL.md`**.

Ya está puesto en Vercel: `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, `EMAIL_FROM`,
`EMAIL_REPLY_TO=grankha@roadshop.online`, `EMAIL_AVISO=elexitodigital@gmail.com`,
`ADMIN_TOKEN`, `SUPPLIER_NAME`, `DELIVERY_DAYS`. No hay que tocar nada más: en cuanto
Resend verifique el dominio, los correos salen solos.

### 2. NIF y domicilio fiscal 🟡 (obligatorio en el aviso legal)

Ya están publicados titular, email, web, actividad y modelo de envío. La LSSI (art. 10) exige
además **NIF** y **domicilio fiscal**. Mientras no estén, la web muestra este párrafo en su lugar:

> «Los datos fiscales completos de la empresa (NIF y domicilio fiscal) se facilitan gratuitamente
> a cualquier consumidor que los solicite escribiendo a grankha@roadshop.online, y se publicarán
> en esta página en cuanto finalice el alta.»

Para publicarlo: `data/site.json` → `legal.nif` y `legal.domicilio`, luego
`python3 tools/build.py` y desplegar. Se pintan solos en cuanto tengan valor.

### 3. Teléfono de atención al cliente 🟢 (opcional)

No es obligatorio teniendo email, pero ayuda. Se añade en `legal.html` y en contacto.

### 4. Operativa diaria 🟢

- Pasar cada pedido al panel de AW Dropshipping (hoy es manual, copiar y pegar).
- Confirmar la tarifa real de envío y los plazos del proveedor (la web dice 3-8 días).
- Canarias/Ceuta/Melilla: confirmar con AW si el envío incluye aduanas.
- Instagram/TikTok de la marca y enlazarlos en el footer.
- Google Search Console con `https://grankha.roadshop.online/sitemap.xml` y Merchant Center.

## Cómo se envía un pedido al proveedor (AW Dropshipping)

Tu tienda cobra → el pedido queda en Supabase con todos los datos → se pasa a AW para que lo
prepare y lo envíe directamente al cliente. Hoy es manual. En `supabase/functions/` quedan
preparadas `fulfill-order` y `notify-tracking` para automatizarlo cuando quieras dar el paso.

## Arreglado de paso hoy

- **Bug de caché corregido.** El sello `styles.css?v=…` / `app.js?v=…` se calculaba con `hash()`
  de Python, que lleva sal aleatoria por proceso: cada rebuild cambiaba el sello en las 85 páginas
  (git siempre sucio) y rompía la caché del navegador de todos los visitantes sin motivo. Ahora usa
  SHA-1 del CSS+JS. Build idempotente verificado: dos rebuilds seguidos dan ficheros idénticos, y el
  sello sigue cambiando cuando se toca el CSS o el JS.
- **`package-lock.json`** subido al repo para que el build de Vercel sea reproducible.
- **Fichero de verificación de Google** publicado: `googlec2e45e8990a69adf.html` responde 200 en el
  dominio. Solo falta que el titular verifique la propiedad en Search Console y envíe el sitemap.

## Si algún día hay que mover la web

- El sitio estático se genera con `python3 tools/build.py`.
- Las funciones de pago viven en `api/` y se despliegan con `vercel deploy --prod`.
- Al cambiar de dominio: Vercel → Domains, `SITE_URL`, `data/site.json` (url + endpoints),
  webhook de Stripe, reconstruir y desplegar.
- La copia de GitHub Pages (`elexitodigital-eng.github.io/grankha`) sigue viva y apunta al
  mismo backend de Vercel.

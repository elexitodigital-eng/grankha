# GRANKHA · estado del lanzamiento

_Actualizado: 22 de octubre de 2026_

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
- `EMAIL_AVISO` = `grankha@roadshop.online`
- `EMAIL_FROM` = `GRANKHA <grankha@roadshop.online>`

## Lo único que falta para cerrar

### 1. Proveedor de correo 🔴 (bloqueante para los emails propios)

Los correos de «pedido confirmado» y el aviso interno de venta **se generan pero no salen**,
porque no hay proveedor de correo configurado. Ya está el código listo en `api/_lib/mail.js`
con tres caminos; solo hace falta que me pases **uno**:

**Opción A — SMTP del buzón de la empresa (la más directa, ya tienes `grankha@roadshop.online`)**

| Variable | Valor |
|---|---|
| `EMAIL_PROVIDER` | `smtp` |
| `SMTP_HOST` | el del proveedor del dominio (si `roadshop.online` está en IONOS: `smtp.ionos.es`) |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `grankha@roadshop.online` |
| `SMTP_PASS` | la contraseña del buzón |

**Opción B — Resend:** crear cuenta en resend.com, verificar el dominio `roadshop.online`
(añadiendo los registros TXT/MX que te dé) y pasarme `RESEND_API_KEY` + `EMAIL_PROVIDER=resend`.

**Opción C — Brevo:** cuenta en brevo.com y pasarme `BREVO_API_KEY` + `EMAIL_PROVIDER=brevo`.

> Mientras no haya proveedor, Stripe sigue mandando **su** recibo de pago al cliente si en
> Dashboard → Settings → Emails está activado *Successful payments*. El pedido se cobra y se
> guarda igual; lo que no sale es el correo con la marca GRANKHA.

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

## Si algún día hay que mover la web

- El sitio estático se genera con `python3 tools/build.py`.
- Las funciones de pago viven en `api/` y se despliegan con `vercel deploy --prod`.
- Al cambiar de dominio: Vercel → Domains, `SITE_URL`, `data/site.json` (url + endpoints),
  webhook de Stripe, reconstruir y desplegar.
- La copia de GitHub Pages (`elexitodigital-eng.github.io/grankha`) sigue viva y apunta al
  mismo backend de Vercel.

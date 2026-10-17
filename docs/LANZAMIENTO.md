# GRANKHA · estado del lanzamiento

_Actualizado: 17 de octubre de 2026_

## Qué está funcionando ya (comprobado, no "debería")

| Pieza | Estado |
|---|---|
| **Web** | Desplegada en Vercel: **https://grankha-beta.vercel.app** (85 páginas, 0 enlaces rotos, 0 errores de JS) |
| **Pago con tarjeta** | Stripe **en modo real** (`rk_live`). El carrito crea la sesión de pago y redirige a Stripe Checkout. Probado de punta a punta: la sesión se crea con el importe correcto (73,80 €) y el cliente aterriza en la pasarela. |
| **Precios y envío** | Se recalculan **en el servidor**: el navegador no puede tocar importes. Zonas (península, Baleares, Canarias/Ceuta/Melilla, Portugal, UE) y tramos de envío gratis iguales que la web. Canarias sin IVA (IGIC/IPSI en destino). |
| **Base de datos** | Supabase `ravvjwyjaxofidgueopc` con las tablas `orders`, `order_items`, `subscribers`, `contact_messages` + vistas de KPIs. RLS activo: el público solo puede dejar el email; los pedidos los escribe el servidor. |
| **Pedidos guardados** | Cada compra se guarda como `pending` y pasa a **`paid`** cuando Stripe confirma el cobro (webhook verificado con firma: firma buena → 200, firma mala → 400). |
| **Reserva para investigación** | Se calcula por pedido en `orders.donation` (interno, nunca público). |
| **Newsletter** | Guarda el email en Supabase con la clave pública. Probado: 201. |
| **Formulario de contacto** | Guarda en `contact_messages` vía `/api/contact`. Probado: 200. Si el backend fallara, cae al correo del cliente (mailto). |
| **Pantalla de gracias** | `carrito.html?estado=ok` limpia la cesta y muestra el pedido confirmado + qué pasa ahora. Si se cancela, avisa y deja la cesta intacta. |

## Lo que falta para cerrar (por orden de importancia)

1. **Proveedor de correo (BLOQUEANTE para los emails).** Ahora mismo los correos de "pedido confirmado" y el aviso de venta se generan pero **no salen**, porque no hay proveedor configurado. Hace falta una cuenta de **Resend** o **Brevo** y verificarlo. Después, en Vercel → Settings → Environment Variables:
   - `EMAIL_PROVIDER=resend` y `RESEND_API_KEY=re_...` (o `BREVO_API_KEY=xkeysib-...`)
   - `EMAIL_FROM="GRANKHA <hola@tudominio.com>"`
   Mientras tanto, Stripe puede mandar el recibo de pago al cliente si en el Dashboard → Settings → Emails está activado *Successful payments*.

2. **Dominio propio.** `grankha.vercel.app` está pillado por otro proyecto de la cuenta, así que el sitio vive en `grankha-beta.vercel.app`. Para lanzar hace falta un dominio (por ejemplo `grankha.com`) y añadirlo en Vercel → Domains. Cuando esté, se cambia `SITE_URL` en Vercel y `data/site.json`, se reconstruye y listo.

3. **Aviso legal y condiciones con los datos reales.** La web ya tiene las páginas, pero conviene revisar NIF, dirección fiscal y correo de contacto definitivo (ahora `zenqalife@gmail.com`).

4. **Email de las notificaciones internas.** `EMAIL_AVISO` está en `zenqalife@gmail.com`; cámbialo si quieres que las ventas lleguen a otra cuenta.

## Cómo se envía un pedido al proveedor (AW Dropshipping)

El flujo es: tu tienda cobra → el pedido queda en Supabase con todos los datos → se pasa a AW para que lo prepare. Hoy es manual (copiar y pegar el pedido en el panel de AW), que es como trabaja la mayoría de tiendas con dropshipper al empezar. En `supabase/functions/` quedan preparadas `fulfill-order` y `notify-tracking` para automatizarlo más adelante, cuando decidas dar el paso.

## Variables de entorno que hay ahora en Vercel

- `STRIPE_SECRET_KEY` (restringida, `rk_live_…`)
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL` · `SUPABASE_SERVICE_ROLE_KEY`
- `SITE_URL` = `https://grankha-beta.vercel.app`
- `EMAIL_AVISO` = `zenqalife@gmail.com`

Webhook de Stripe creado: `we_1URVX35u1hLzWyIGYIjzIbo9` → `https://grankha-beta.vercel.app/api/stripe-webhook`
(eventos: `checkout.session.completed`, `charge.refunded`).

## Si algún día hay que mover la web

- El sitio estático se genera con `python3 tools/build.py`.
- Las funciones de pago viven en `api/` y se despliegan con `vercel deploy --prod`.
- La versión de GitHub Pages (`elexitodigital-eng.github.io/grankha`) sigue viva como copia, apuntando al mismo backend de Vercel.

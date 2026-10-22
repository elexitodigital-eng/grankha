# ⚠ Estas Edge Functions NO están desplegadas

El flujo de correo y pedidos de GRANKHA corre **entero en Vercel**, no aquí:

| Esto (referencia, sin desplegar) | Lo que manda de verdad en producción |
|---|---|
| `create-checkout/index.ts` | `api/create-checkout.js` |
| `stripe-webhook/index.ts` | `api/stripe-webhook.js` |
| `notify-tracking/index.ts` | `api/admin.js` (acción `shipped`) |
| `fulfill-order/index.ts` | manual, desde el panel (`/api/panel`) |
| `_shared/email.ts` | `api/_lib/mail.js` + `api/_lib/emails.js` |

**No las despliegues tal cual.** Si las activas mientras el webhook de Vercel sigue en marcha,
el cliente recibirá **dos correos por pedido**, porque ambos escuchan el mismo evento de Stripe
(`checkout.session.completed`) y ambos envían confirmación.

## Para qué siguen aquí

Como referencia de dos cosas que el flujo de Vercel no hace todavía:

- **`notify-tracking/index.ts`** llama directamente a la API de AW Dropshipping
  (`${AW_BASE}/dropshipping/order`) para crear el pedido en el proveedor. Hoy ese paso es manual:
  se copia el bloque del panel y se pega en AW. Si algún día se automatiza, la lógica de firma y
  de mapeo de campos está aquí.
- **`fulfill-order/index.ts`** contiene el mismo mapeo de campos para el alta en AW.

## Si en algún momento se quisieran activar

1. Elegir **un** solo camino: o Vercel o Supabase. Nunca los dos para el mismo evento.
2. Si se migra a Supabase, retirar antes el endpoint de Vercel del webhook de Stripe
   (dashboard de Stripe → Developers → Webhooks) o hacer que devuelva 200 sin enviar nada.
3. Portar la idempotencia que tiene `api/stripe-webhook.js` (comprueba `order_email_sent_at`
   antes de reenviar), porque Stripe puede entregar el mismo evento más de una vez.
4. Portar `api/_lib/emails.js`, que es la versión buena y actual de las plantillas: lleva el
   margen y el bloque para copiar a AW. `_shared/email.ts` es anterior y más pobre.

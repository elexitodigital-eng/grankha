# GRANKHA · Resend y panel de pedidos

_Cómo están los correos montados y qué falta para que salgan con tu propia dirección._

---

## 1. Lo que ya está funcionando

Tres correos, con las plantillas ya escritas y probadas:

| Correo | Para quién | Cuándo sale |
|---|---|---|
| **Pedido confirmado** | el cliente | automático, cuando Stripe confirma el cobro |
| **Aviso de venta** (con margen y datos para AW) | tú | automático, a la vez que el anterior |
| **Envío con seguimiento** | el cliente | cuando lo marcas tú en el panel |

Las plantillas viven en `api/_lib/emails.js` y las usan `api/stripe-webhook.js` y `api/admin.js`,
así que los tres correos comparten diseño y datos.

El aviso de venta lleva lo que necesitas para operar: SKU, venta, coste y margen de cada línea;
desglose de IVA, coste del proveedor, beneficio bruto y reserva para investigación; y un
**bloque listo para copiar y pegar en el panel de AW Dropshipping** con destinatario, dirección,
teléfono y artículos.

---

## 2. Lo único que falta: verificar el dominio en Resend

Hoy Resend **rechaza** enviar desde `grankha@roadshop.online` con este error:

> `validation_error: The roadshop.online domain is not verified.`

Mientras eso siga así, **los correos a clientes no salen**. Pero hay una red de seguridad
montada para que tú no te quedes a ciegas:

| Correo | ¿Sale hoy, sin verificar el dominio? |
|---|---|
| **Aviso de venta (a ti)** | ✅ **SÍ.** Sale por un remitente de reserva (`onboarding@resend.dev`), que Resend acepta sin verificar pero solo hacia la dirección de tu propia cuenta, que es justo donde va `EMAIL_AVISO`. |
| Confirmación al cliente | ❌ No. Resend lo bloquea hasta verificar el dominio. |
| Envío con seguimiento | ❌ No. Igual. |

Así que **te enteras de cada venta en cuanto ocurre**, aunque el cliente aún no reciba tu correo.

Y ningún pedido se pierde: se guarda igual en Supabase, el fallo queda anotado en la columna
`order_email_error` (nunca en `notes`, que puede llevar el comentario del cliente), el panel lo
muestra con el filtro «Con email de pedido fallido», y lo reenvías con un clic en cuanto el
dominio esté verificado. Stripe sigue mandando su propio recibo de pago al cliente.

### Pasos (unos 10 minutos)

1. Entra en **https://resend.com/domains** con la cuenta `elexitodigital@gmail.com`.
2. **Add Domain** → escribe `roadshop.online`.
   - Región: **eu-west-1 (Ireland)**, es la más cercana a España.
   - Return-Path: déjalo por defecto (`send.roadshop.online`).
3. Resend te mostrará la pestaña **Records** con 3 registros. Cópialos **exactamente**.
   Serán algo así (los valores reales te los da Resend, no los inventes):

   | Tipo | Nombre / Host | Valor |
   |---|---|---|
   | `TXT` | `send.roadshop.online` | `v=spf1 include:amazonses.com ~all` |
   | `TXT` | `resend._domainkey.roadshop.online` | `p=MIGfMA0GCSq…` (clave DKIM larga) |
   | `MX` | `send.roadshop.online` | `feedback-smtp.eu-west-1.amazonses.com` (prioridad 10) |

4. Añádelos en el **panel de IONOS** → Dominios y SSL → `roadshop.online` → DNS.

> **Importante, y es buena noticia:** los tres registros van sobre `send.roadshop.online` y
> `resend._domainkey.roadshop.online`, **no sobre el dominio raíz**. Tu MX actual
> (`mx00.ionos.es` / `mx01.ionos.es`) y tu buzón `grankha@roadshop.online` **no se tocan** y
> siguen recibiendo correo como siempre. No hay conflicto.

5. Espera la verificación: normalmente **15 minutos**, hasta 72 h en el peor caso. Puedes
   comprobar los registros en https://dns.email/. Si a las 72 h no verifica, pulsa
   *Restart verification* en Resend.

6. **Compruébalo tú mismo en 10 segundos:** entra en el panel (`/pedidos.html`), en la tarjeta
   «Estado del correo» pulsa **«Probar envío»**.
   - Si el mensaje dice **«Enviado con tu propio remitente: el dominio ya está verificado»** →
     ya está. No hay que cambiar nada en el código ni redesplegar, porque `EMAIL_FROM` ya está
     puesto en `GRANKHA <grankha@roadshop.online>`. Los tres correos salen solos.
   - Si dice **«por el remitente de RESERVA»** → el dominio sigue sin verificar.
   - Si sale ⚠, el panel te explica el motivo en cristiano (dominio sin verificar, clave
     inválida, límite de envíos…) en vez de soltar un error técnico.

### Después, recomendado: DMARC

Ya tienes un DMARC heredado de IONOS con `p=none` (no bloquea nada). Cuando el dominio esté
verificado conviene dejar uno propio, por ejemplo:

```
TXT  _dmarc.roadshop.online   v=DMARC1; p=none; rua=mailto:grankha@roadshop.online
```

Empezar en `p=none` y subir a `quarantine` más adelante, cuando veas que todo llega bien.

---

## 3. El panel de pedidos

**URL:** `https://grankha.roadshop.online/pedidos.html`
**Token:** el valor de la variable `ADMIN_TOKEN` en Vercel → proyecto `grankha` → Settings →
Environment Variables. Es largo y empieza por `grk_`. Guárdalo en tu gestor de contraseñas.

La página no contiene ningún secreto y está fuera del sitemap y con `noindex`: sin el token el
servidor no devuelve nada (401). El token se guarda solo en tu navegador.

### Qué puedes hacer desde ahí

- Ver los últimos 100 pedidos con estado, cliente, importe y qué correos salieron.
- Filtrar: **pagados sin enviar al proveedor**, **enviados sin aviso de seguimiento**,
  **con email fallido**.
- **Ver / copiar para AW**: abre el detalle y el bloque de texto listo para pegar en el panel
  de AW Dropshipping.
- **Marcar enviado y avisar**: rellenas número de seguimiento, transportista, enlace y plazo
  (y opcionalmente el nº de pedido en AW). Marca el pedido como `shipped`, guarda la fecha y
  **manda el correo de seguimiento al cliente**.
- **Reenviar confirmación**: si el correo de pedido falló en su día, lo reenvías.
- **Reenviar seguimiento**: si te equivocaste en el número, lo corriges y reenvías.
- **Reenviarme el aviso**: te vuelve a llegar a ti el aviso interno con el margen.
- **Probar envío**: manda un correo de prueba a `EMAIL_AVISO` para comprobar que el remitente ya
  funciona. Útil justo después de verificar el dominio, sin esperar a un pedido real. No toca la
  base de datos.

Endpoint: `api/admin.js`. Todo exige el token; la comparación se hace en tiempo constante.

---

## 4. Variables de correo en Vercel

Ya están todas puestas:

| Variable | Valor |
|---|---|
| `EMAIL_PROVIDER` | `resend` |
| `RESEND_API_KEY` | cifrada |
| `EMAIL_FROM` | `GRANKHA <grankha@roadshop.online>` |
| `EMAIL_REPLY_TO` | `grankha@roadshop.online` |
| `EMAIL_AVISO` | `elexitodigital@gmail.com` |
| `EMAIL_FALLBACK_FROM` | opcional · por defecto `GRANKHA <onboarding@resend.dev>` |
| `ADMIN_TOKEN` | cifrada |
| `SUPPLIER_NAME` | `AW Dropshipping` |
| `DELIVERY_DAYS` | `3-8` |
| `SITE_URL` | `https://grankha.roadshop.online` |

`EMAIL_REPLY_TO` importa: aunque Resend envíe desde un subdominio o cambies el remitente, las
respuestas del cliente caen en `grankha@roadshop.online`.

Si algún día quieres que los avisos de venta vayan al buzón de la empresa en vez de al Gmail,
cambia `EMAIL_AVISO` a `grankha@roadshop.online` en Vercel y redespliega.

El código admite también SMTP (`EMAIL_PROVIDER=smtp` con el buzón de IONOS) y Brevo, por si
prefieres no depender de Resend. Está en `api/_lib/mail.js`.

---

## 5. Comprobado con envíos reales

Las tres plantillas se enviaron de verdad por Resend y llegaron a `elexitodigital@gmail.com`
(mientras el dominio no está verificado, Resend solo permite enviar a la dirección de la cuenta):

- `01a16439-fbc9-74e7-84de-1957c4dd5d50` · pedido confirmado
- `01a16439-fc9b-70d9-8c66-16a9eef527c8` · aviso interno de venta
- `01a16439-fd44-77c6-9f43-0a5bffb20b5f` · envío con seguimiento

Y el flujo completo del panel se probó con un pedido real de punta a punta: creado en el
checkout, marcado como pagado, y desde el panel reenviada la confirmación, marcado como enviado
con seguimiento (que mandó el correo) y reenviado el aviso interno. En la base de datos quedaron
`status=shipped`, `shipped_at`, `tracking_code`, `tracking_carrier`, `tracking_url`,
`tracking_eta`, `supplier_order_id`, `order_email_sent_at` y `tracking_email_sent_at`.
Después se borró el pedido de prueba y se expiró su sesión de Stripe.

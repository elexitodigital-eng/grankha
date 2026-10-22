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

### Se verifica un SUBDOMINIO, no la raíz

El dominio que se da de alta en Resend es **`grankha.roadshop.online`**, igual que en el otro
proyecto se usó `sscarsgarage.roadshop.online`. El remitente pasa a ser
`GRANKHA <pedidos@grankha.roadshop.online>`.

Por qué así y no la raíz:

- **Aísla la reputación.** Si algún correo cae en spam, no mancha `roadshop.online` ni el
  buzón real, que sigue recibiendo las respuestas gracias a `EMAIL_REPLY_TO`.
- **No se toca nada existente.** Los cuatro registros van bajo `send.grankha`,
  `rsend.grankha` y `resend._domainkey.grankha`. El MX y el SPF del buzón de IONOS están en
  la raíz y no se modifican.

Está comprobado en la propia zona que el patrón funciona: `sscarsgarage.roadshop.online` es
un CNAME a Vercel **y** tiene sus cuatro registros de Resend debajo, activos. `grankha` está
en la misma situación. Un CNAME impide añadir registros *en ese mismo nombre*, no en nombres
por debajo.

### Son 4 registros, y sin DMARC

| # | Tipo | Nombre de host en IONOS | Valor / destino | Prioridad |
|---|------|-------------------------|-----------------|-----------|
| 1 | `TXT` | `resend._domainkey.grankha` | `p=MIGfMA0…` (la da Resend) | — |
| 2 | `MX` | `send.grankha` | `feedback-smtp.eu-west-1.amazonses.com` | `10` |
| 3 | `TXT` | `send.grankha` | `v=spf1 include:amazonses.com ~all` | — |
| 4 | `CNAME` | `rsend.grankha` | `send.forge.rmta.net` | — |

> **En IONOS se escriben SIN el sufijo `.roadshop.online`.** Solo existe la zona de
> `roadshop.online` e IONOS añade el sufijo automáticamente. Si lo escribes tú, queda
> duplicado y no verifica nunca.

**No se añade DMARC.** El de la raíz (`_dmarc.roadshop.online` → `v=DMARC1; p=none;`) no
lleva etiqueta `sp=`, así que cubre automáticamente a todos los subdominios, `grankha`
incluido. Poner otro sería redundante.

La guía completa, con el paso a paso de IONOS, qué no tocar y qué hacer si IONOS avisa de un
choque, está en **`ops/resend_dns_IONOS.md`**.

### Lo que falta para poder hacerlo

El registro 1 necesita la clave DKIM, que solo genera Resend al dar de alta el dominio. La
clave actual (`re_RHDGFx6G_…`) es *restricted*: solo permite enviar, y al intentar leer o
crear dominios devuelve `401 This API key is restricted to only send emails`.

Hace falta una de estas dos cosas:

- una clave de Resend con permiso de **Domains**, o
- dar de alta `grankha.roadshop.online` en el panel de Resend y pegar los valores de la
  pestaña **Records**.

El detalle de ambas vías está en `ops/resend_dns_IONOS.md` §6.

### Cuando ya esté verificado

**Compruébalo tú mismo en 10 segundos:** entra en el panel (`/api/panel`), en la tarjeta
«Estado del correo» pulsa **«Probar envío»**.

- Si dice **«Enviado con tu propio remitente: el dominio ya está verificado»** → ya está.
- Si dice **«por el remitente de RESERVA»** → el dominio sigue sin verificar.
- Si sale ⚠, el panel te explica el motivo en cristiano (dominio sin verificar, clave
  inválida, límite de envíos…) en vez de soltar un error técnico.

A diferencia de antes, aquí **sí hace falta un cambio tras verificar**: hay que poner
`EMAIL_FROM=GRANKHA <pedidos@grankha.roadshop.online>` en Vercel y redesplegar, porque el
remitente tiene que pertenecer al dominio verificado. `EMAIL_REPLY_TO` se queda en
`grankha@roadshop.online` para que las respuestas sigan llegando al buzón de siempre.

---

## 3. El panel de pedidos

**URL:** `https://grankha.roadshop.online/api/panel?token=<ADMIN_TOKEN>`
**Token:** el valor de la variable `ADMIN_TOKEN` en Vercel → proyecto `grankha` → Settings →
Environment Variables. Es largo y empieza por `grk_`. Guárdalo en tu gestor de contraseñas.

### No es una página pública

El panel **no existe como página del sitio**. Antes estaba en `/pedidos.html`, en la raíz,
visible para cualquiera que probara esa URL aunque no pudiera entrar. Ahora no:

- **`/pedidos.html` → 404.** El fichero se borró del repositorio.
- **`/api/panel` sin credencial → 404.** Y no un 404 propio: devuelve **exactamente** el
  mismo cuerpo, las mismas cabeceras y el mismo `content-type` que cualquier ruta
  inexistente de Vercel (`The page could not be found / NOT_FOUND / <id de petición>`,
  79 bytes). Comprobado byte a byte. Desde fuera no hay forma de distinguir «aquí hay un
  panel protegido» de «aquí no hay nada».
- **`/api/admin` sin credencial → 404.** Antes devolvía 401, 405 o 500 según el caso, y
  cada uno de esos códigos delataba que el endpoint existía. Ahora todo es 404: sin
  credencial, con método raro, con JSON inválido.
- Nada de esto está en el `sitemap.xml`, y la respuesta buena lleva `X-Robots-Tag: noindex`,
  `Referrer-Policy: no-referrer` y `X-Frame-Options: DENY`.

### Cómo se entra

1. Abres la URL con `?token=…` una sola vez.
2. El servidor comprueba el token **en tiempo constante**, fija una cookie y responde
   **302 a `/api/panel`** — así el token desaparece de la barra de direcciones y no queda
   en el historial, en los marcadores ni en el `Referer`.
3. La cookie `grankha_panel` es `HttpOnly` (ningún script puede leerla), `Secure`,
   `SameSite=Strict` y con `Path=/api` (no se envía al resto del sitio). Dura **8 horas**;
   pasado ese tiempo vuelves a usar la URL con token.
4. El botón **Salir** apunta a `/api/panel?logout=1`, borra la cookie y devuelve 404.

El HTML del panel está incrustado en `api/_lib/panel-html.js`, no es un fichero suelto que
se sirva. Ya no usa `localStorage` para el token.

Endpoint: `api/panel.js` sirve el HTML; `api/admin.js` sirve los datos y las acciones.
Ambos comparten la credencial desde `api/_lib/auth.js`.

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
| `RESEND_API_KEY` | cifrada · **solo envío**, sin permiso de dominios |
| `EMAIL_FROM` | `GRANKHA <grankha@roadshop.online>` → **cambiará** a `GRANKHA <pedidos@grankha.roadshop.online>` en cuanto el subdominio esté verificado |
| `EMAIL_REPLY_TO` | `grankha@roadshop.online` · **no cambia nunca** |
| `EMAIL_AVISO` | `elexitodigital@gmail.com` |
| `EMAIL_FALLBACK_FROM` | opcional · por defecto `GRANKHA <onboarding@resend.dev>` |
| `ADMIN_TOKEN` | cifrada · credencial única de `/api/panel` y `/api/admin` |
| `SUPPLIER_NAME` | `AW Dropshipping` |
| `DELIVERY_DAYS` | `3-8` |
| `SITE_URL` | `https://grankha.roadshop.online` |

`EMAIL_REPLY_TO` es lo que hace viable el subdominio: el cliente ve
`pedidos@grankha.roadshop.online` como remitente, pero cuando pulsa «Responder» el correo
cae en `grankha@roadshop.online`, el buzón de siempre.

Ojo con `EMAIL_FROM`: mientras el subdominio no esté verificado en Resend, poner ahí una
dirección de `grankha.roadshop.online` no arregla nada — Resend seguirá rechazándolo con
`domain is not verified`. El orden correcto es: DNS primero, verificación después, cambio de
variable al final.

Si algún día quieres que los avisos de venta vayan al buzón de la empresa en vez de al Gmail,
cambia `EMAIL_AVISO` a `grankha@roadshop.online` en Vercel y redespliega. Ten en cuenta que
la **red de reserva** solo funciona mientras `EMAIL_AVISO` sea la dirección de la cuenta de
Resend (`elexitodigital@gmail.com`): `onboarding@resend.dev` únicamente puede enviar hacia
esa dirección. Si la cambias antes de verificar el dominio, te quedas sin avisos internos.

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

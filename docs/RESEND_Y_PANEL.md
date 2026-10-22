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

### Se verifica la RAÍZ `roadshop.online`

El dominio que se da de alta en Resend es **`roadshop.online`**, y el remitente sigue siendo
`GRANKHA <grankha@roadshop.online>`.

Se barajó primero enviar desde un subdominio (`pedidos@grankha.roadshop.online`), que es lo
que se hizo en el otro proyecto con `sscarsgarage`. Se descarta por dos motivos concretos:

- **No hay que cambiar nada.** `EMAIL_FROM` en Vercel ya vale
  `GRANKHA <grankha@roadshop.online>`. En cuanto el dominio verifique, los tres correos salen
  solos: sin tocar variables y **sin redesplegar**.
- **Es la dirección ya publicada.** `grankha@roadshop.online` aparece en 8 sitios de
  `legal.html`. Con un subdominio el cliente vería un remitente distinto al que la propia web
  le indica.

El coste es que no se aísla la reputación por proyecto. Se asume a sabiendas.

### Son 4 registros, y sin DMARC

| # | Tipo | Nombre de host en IONOS | Valor / destino | Prioridad |
|---|------|-------------------------|-----------------|-----------|
| 1 | `TXT` | `resend._domainkey` | `p=MIGfMA0…` (la da Resend) | — |
| 2 | `MX` | `send` | `feedback-smtp.eu-west-1.amazonses.com` | `10` |
| 3 | `TXT` | `send` | `v=spf1 include:amazonses.com ~all` | — |
| 4 | `CNAME` | `rsend` | `send.forge.rmta.net` | — |

> **En IONOS se escriben SIN el sufijo `.roadshop.online`.** Solo existe la zona de
> `roadshop.online` e IONOS añade el sufijo automáticamente. Si lo escribes tú, queda
> duplicado y no verifica nunca.

**No se añade DMARC.** El de la raíz (`_dmarc.roadshop.online` → `v=DMARC1; p=none;`) ya
existe y no lleva etiqueta `sp=`, así que cubre también a todos los subdominios.

Comprobado antes de escribir esto: `resend._domainkey.roadshop.online`,
`send.roadshop.online` y `rsend.roadshop.online` **no existen hoy**, así que ningún registro
nuevo pisa uno existente. Y la raíz no tiene CNAME, que era el único impedimento técnico
posible. El MX (`mx00/mx01.ionos.es`), el SPF (`include:_spf-eu.ionos.com`) y el A
(`217.160.0.140`) de la raíz **no se tocan**.

**El SPF de la raíz no se modifica**, y conviene entender por qué: el SPF se comprueba contra
el Return-Path, no contra el From visible. Resend envía con Return-Path en
`send.roadshop.online`, que lleva su propio SPF con `include:amazonses.com`. El de la raíz
sigue autorizando a IONOS para el correo que mandes tú desde el buzón. Dos comprobaciones
sobre dos nombres distintos, sin estorbarse.

DMARC pasa por las dos vías: DKIM firma con `d=roadshop.online` (coincide exacto con el From)
y el Return-Path `send.roadshop.online` pertenece al mismo dominio organizativo.

La guía completa, con el paso a paso de IONOS, qué no tocar y qué hacer si IONOS avisa de un
choque, está en **`ops/resend_dns_IONOS.md`**.

### Ya está dado de alta en Resend

El dominio **`roadshop.online` ya existe en la cuenta de Resend**, en región **eu-west-1
(Irlanda)**, y los cuatro registros que pide ya están volcados en `ops/resend_dns_IONOS.md`
§5 con sus valores reales.

| | |
|---|---|
| Id del dominio | `43a0dc99-c8e1-4d4a-9b28-2f1be6cb5603` |
| Estado | `not_started` — espera los registros en el DNS |
| Registros que pide | 4 · **ninguno es DMARC** |

Dos cosas confirmadas al hacerlo:

- **Resend no pide DMARC.** Devolvió exactamente cuatro registros: DKIM, MX y TXT bajo
  `send`, y CNAME bajo `rsend`. El DMARC de la raíz ya cubre, así que no se añade nada.
- **No había riesgo de solapamiento con el otro proyecto.** La cuenta tenía 0 dominios, así
  que `sscarsgarage.roadshop.online` vive en otra cuenta de Resend distinta. El alta devolvió
  `HTTP 201` a la primera.

**Lo único que falta es tu paso en IONOS**: copiar los cuatro registros de
`ops/resend_dns_IONOS.md` §5 en la zona DNS de `roadshop.online`. Es lo que no puedo hacer yo.

La clave API con permisos de dominio se ha usado solo para esto y ya está borrada del
entorno. La que usa la web en producción (`re_RHDGFx6G_…`, solo envío) **no hace falta
cambiarla**: para enviar no necesita permisos de dominio.

### Cuando ya esté verificado

**Compruébalo tú mismo en 10 segundos:** entra en el panel (`/api/panel`), en la tarjeta
«Estado del correo» pulsa **«Probar envío»**.

- Si dice **«Enviado con tu propio remitente: el dominio ya está verificado»** → ya está.
- Si dice **«por el remitente de RESERVA»** → el dominio sigue sin verificar.
- Si sale ⚠, el panel te explica el motivo en cristiano (dominio sin verificar, clave
  inválida, límite de envíos…) en vez de soltar un error técnico.

Y no hace falta tocar nada más: como se verifica la raíz, `EMAIL_FROM` ya apunta a una
dirección del dominio verificado. Los tres correos empiezan a salir en cuanto Resend marque
el dominio como *Verified*.


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
| `EMAIL_FROM` | `GRANKHA <grankha@roadshop.online>` · **no cambia** al verificar la raíz |
| `EMAIL_REPLY_TO` | `grankha@roadshop.online` |
| `EMAIL_AVISO` | `elexitodigital@gmail.com` |
| `EMAIL_FALLBACK_FROM` | opcional · por defecto `GRANKHA <onboarding@resend.dev>` |
| `ADMIN_TOKEN` | cifrada · credencial única de `/api/panel` y `/api/admin` |
| `SUPPLIER_NAME` | `AW Dropshipping` |
| `DELIVERY_DAYS` | `3-8` |
| `SITE_URL` | `https://grankha.roadshop.online` |

Como se verifica la raíz, `EMAIL_FROM` y `EMAIL_REPLY_TO` son la misma dirección y **ninguna
de las dos hay que tocarla**. Es la ventaja principal de este planteamiento frente al
subdominio: cuando Resend marque el dominio como *Verified*, los tres correos empiezan a
salir sin cambiar variables ni redesplegar.

Hasta entonces no hay nada que ajustar en Vercel. `EMAIL_FROM` ya apunta a
`grankha@roadshop.online`, que es justo la dirección que quedará autorizada; lo único que
falta es que Resend deje de responder `domain is not verified`. El orden es: DNS en IONOS →
verificación en Resend → los correos salen solos.

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

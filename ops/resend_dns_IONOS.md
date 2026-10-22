# Resend en IONOS — GRANKHA

Guía para verificar **`grankha.roadshop.online`** en Resend y que los correos de la tienda
salgan desde el subdominio.

Fecha de comprobación del DNS: 22/10/2026.

---

## 0. Estado actual: te falta cambiar UN solo valor

Ya diste de alta los cuatro registros en IONOS y **tres son correctos tal como están**.
No los toques.

Comprobado por DNS contra lo que pide Resend:

| # | Tipo | Nombre completo | Estado |
|---|------|-----------------|--------|
| 1 | TXT | `resend._domainkey.grankha.roadshop.online` | ⚠️ **valor incorrecto — hay que sustituirlo** |
| 2 | MX | `send.grankha.roadshop.online` | ✅ correcto, no tocar |
| 3 | TXT | `send.grankha.roadshop.online` | ✅ correcto, no tocar |
| 4 | CNAME | `rsend.grankha.roadshop.online` | ✅ correcto, no tocar |

### Por qué el registro 1 está mal

No es un error tuyo. Ese registro lleva la **clave DKIM**, y Resend genera una clave
distinta para cada dominio que se da de alta. La que tienes publicada es la clave del
dominio raíz `roadshop.online`, de cuando en un momento dado se barajó verificar la raíz en
vez del subdominio. El nombre del registro es el correcto; el valor pertenece a otro dominio.

Al dar de alta `grankha.roadshop.online` en Resend se generó una clave nueva, que es la que
hay que poner.

### El arreglo

En IONOS → Dominios y SSL → `roadshop.online` → DNS:

1. Busca el registro **TXT** cuyo nombre de host es `resend._domainkey.grankha`.
2. Edítalo y **sustituye el valor** por el de §5. El nombre de host no se cambia.
3. Guarda.

Los otros tres registros se quedan exactamente como están.

---

## 1. Qué se está verificando

| | Valor |
|---|---|
| Dominio dado de alta en Resend | `grankha.roadshop.online` (subdominio) |
| Región | `eu-west-1` (Irlanda) |
| Id en Resend | `a0183708-5bdc-4967-8027-707c119d43a2` |
| Estado | `not_started` — en cuanto el DKIM sea el bueno pasa a `verified` |
| Remitente que verá el cliente | `GRANKHA <pedidos@grankha.roadshop.online>` |
| Reply-To | `grankha@roadshop.online` (el buzón real de IONOS) |

**Por qué un subdominio y no la raíz.** Aísla la reputación de envío: si algún correo cae en
spam, no mancha `roadshop.online` ni el buzón real, que sigue recibiendo las respuestas
gracias al Reply-To. Es además el mismo patrón que ya funciona en tu otro proyecto
(`sscarsgarage.roadshop.online`).

**Coste del subdominio, para que no te pille por sorpresa**: el remitente tiene que
pertenecer al dominio verificado, así que hay que cambiar `EMAIL_FROM` en Vercel y
redesplegar. Con la raíz no habría hecho falta. Es un cambio de una variable, no de código.

El cliente verá `pedidos@grankha.roadshop.online` como remitente, pero al pulsar
«Responder» el correo cae en `grankha@roadshop.online`, que es la dirección publicada en
`legal.html`. La dirección de contacto de la web no cambia.

---

## 2. Comprobado antes de escribir esta guía

### Lo que NO se toca

| Nombre | Tipo | Valor actual | Para qué sirve |
|---|---|---|---|
| `roadshop.online` | MX | `10 mx00.ionos.es` / `10 mx01.ionos.es` | Recibir correo en el buzón real |
| `roadshop.online` | TXT | `v=spf1 include:_spf-eu.ionos.com ~all` | Autorizar a IONOS a enviar desde el buzón |
| `roadshop.online` | A | `217.160.0.140` | Web principal en IONOS |
| `_dmarc.roadshop.online` | TXT | `v=DMARC1; p=none;` | Política DMARC |
| `grankha` | CNAME | `63e57cf5614e4cf1.vercel-dns-017.com` | **La tienda en Vercel** |

Los cuatro registros de Resend van bajo `resend._domainkey.grankha`, `send.grankha` y
`rsend.grankha`. **Ninguno aparece en esta tabla.**

### «¿No romperé la tienda? Los registros cuelgan del mismo `grankha`»

No. Es la duda razonable, porque `grankha.roadshop.online` es un CNAME a Vercel y los
registros de Resend viven por debajo de ese nombre.

Un CNAME impide añadir otros registros **en ese mismo nombre**, no en nombres hijos.
`send.grankha.roadshop.online` es un nombre distinto de `grankha.roadshop.online`, así que
no hay conflicto. Vercel sigue resolviendo la tienda exactamente igual.

Y no es teoría: **en esta misma zona de IONOS ya hay un caso idéntico funcionando**.
`sscarsgarage.roadshop.online` es un CNAME a Vercel y tiene debajo sus cuatro registros de
Resend activos:

```
sscarsgarage.roadshop.online               CNAME d1aff6f9ab81ad45.vercel-dns-017.com.
send.sscarsgarage.roadshop.online          TXT   v=spf1 include:amazonses.com ~all
send.sscarsgarage.roadshop.online          MX    10 feedback-smtp.eu-west-1.amazonses.com.
rsend.sscarsgarage.roadshop.online         CNAME send.forge.rmta.net.
resend._domainkey.sscarsgarage.roadshop…   TXT   p=MIGfMA0…
```

Prueba adicional: tus tres registros correctos **ya resuelven hoy** por DNS público, con el
CNAME de la tienda en su sitio. La tienda sigue respondiendo 200 en sus 10 rutas principales.

---

## 3. ¿Y el SPF y el DMARC del buzón?

**El SPF de la raíz no se modifica.** No hay que añadirle `include:amazonses.com`.

Los servidores de correo comprueban el SPF contra el **Return-Path** (el sobre técnico del
mensaje), no contra el From que ve el cliente. Resend envía con Return-Path en
`send.grankha.roadshop.online`, y ese nombre lleva **su propio SPF** con
`include:amazonses.com` — es tu registro 3, que ya está bien. Son dos comprobaciones sobre
dos nombres distintos:

- El correo que mandes tú desde el buzón de IONOS → valida con el SPF de la raíz.
- El correo que mande Resend → valida con el SPF de `send.grankha`.

Ninguno estorba al otro.

**DMARC pasa por las dos vías**, y no hay que añadir ningún registro:

| Comprobación | Valor | ¿Alineado con el From? |
|---|---|---|
| From | `pedidos@grankha.roadshop.online` | — |
| DKIM `d=` | `grankha.roadshop.online` | ✅ coincide exacto |
| Return-Path | `send.grankha.roadshop.online` | ✅ mismo dominio organizativo (`roadshop.online`) |

El DMARC existente está en `_dmarc.roadshop.online` y vale `v=DMARC1; p=none;` **sin
etiqueta `sp=`**, lo que significa que cubre también a todos los subdominios, `grankha`
incluido. Poner un segundo DMARC en `_dmarc.grankha` sería redundante y podría contradecir
al primero.

---

## 4. ⚠️ La regla de oro en IONOS

En IONOS solo existe la zona de `roadshop.online`, e IONOS **añade `.roadshop.online` al
final** de lo que escribas en «Nombre de host».

> **Escribe el nombre SIN el sufijo `.roadshop.online`.**
>
> - Correcto: `resend._domainkey.grankha`
> - Incorrecto: `resend._domainkey.grankha.roadshop.online` → crearía
>   `…grankha.roadshop.online.roadshop.online` y no verificaría nunca.

Fíjate que el `.grankha` **sí forma parte del nombre de host**: lo que se quita es únicamente
`.roadshop.online`, que es lo que IONOS añade solo.

**TTL:** déjalo como venga por defecto. No lo toques.

---

## 5. Los registros

**No hay DMARC** — ver §3. Son cuatro registros y ya tienes tres bien.

### Registro 1 — DKIM · ⚠️ EL ÚNICO QUE HAY QUE CAMBIAR

| Campo | Valor |
|---|---|
| Tipo | `TXT` |
| Nombre de host | `resend._domainkey.grankha` *(no se cambia)* |
| Valor | **sustituir** por el bloque de abajo |
| TTL | el que venga |

```
p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDQqPkp/6YNq/eZMBp8lgj7N1stXN72fJHiPQoTijn/P0neSNZ9oe2ncI6QRSdzFlWNBsWRAUxD3MXJ+ltWl6krELhFvzi7hQVDZDz6KBny5eFG3NQneGBKNSYz+3gBL+c6Gp5QhdE5lpD8ZrcXcWw/tJCacpWOssWIB9w29cH5ewIDAQAB
```

> Cópialo **entero**, desde `p=` hasta `AQAB`, en una sola pieza. Son **218 caracteres**.
> Los navegadores de IONOS a veces cortan visualmente las líneas largas: no te fíes de lo
> que se ve, pega y guarda. Sin comillas alrededor, sin espacios al principio ni al final.

Es la clave que Resend generó al dar de alta `grankha.roadshop.online`. La que tienes puesta
ahora es la de `roadshop.online` y por eso no verifica.

### Registros 2, 3 y 4 — ✅ YA ESTÁN BIEN, NO LOS TOQUES

| # | Tipo | Nombre de host | Valor | Prioridad |
|---|------|----------------|-------|-----------|
| 2 | MX | `send.grankha` | `feedback-smtp.eu-west-1.amazonses.com` | `10` |
| 3 | TXT | `send.grankha` | `v=spf1 include:amazonses.com ~all` | — |
| 4 | CNAME | `rsend.grankha` | `send.forge.rmta.net` | — |

Los tres están publicados y resuelven correctamente. Verificados uno a uno contra lo que
pide Resend: coinciden.

Nota: los registros 2 y 3 **comparten nombre de host** (`send.grankha`). Es normal —uno es
MX y otro TXT, tipos distintos bajo la misma etiqueta— y no es un duplicado.

### Si IONOS te avisa de algo

Si al guardar el registro 1 aparece un aviso de que **reemplaza**, **sobrescribe** o **choca**
con otro existente: en este caso concreto **sí es esperable**, porque estás sustituyendo el
valor de un TXT que ya existe. Aceptar el reemplazo de **ese** registro es justo lo que hay
que hacer.

Distinto sería que avisara al tocar los registros 2, 3 o 4, o cualquier otro de la zona. Ahí
**no aceptes**: cancela y mándame una captura.

---

## 6. Lo que hago yo en cuanto lo cambies

1. **Comprobar la propagación por DNS** y confirmar que los cuatro registros coinciden con
   lo que pide Resend (§8).
2. **Confirmar que Resend pasa el dominio a `verified`**. Lo normal son 15 minutos; el
   máximo que admite son 72 h. Si se atasca, en Resend → Domains hay un botón
   *Restart verification*.
3. **Cambiar `EMAIL_FROM` en Vercel** a `GRANKHA <pedidos@grankha.roadshop.online>`.
   `EMAIL_REPLY_TO` se queda en `grankha@roadshop.online`.
4. **Redesplegar** y lanzar un **pedido de prueba real** de punta a punta: confirmación al
   cliente, aviso interno de venta y, al marcarlo enviado, el correo de seguimiento.
5. **Borrar el pedido de prueba** de Supabase y dejar las tablas a cero.

Ninguna prueba implica un pago real: se dispara desde el panel y desde el webhook firmado,
sin pasar por la pasarela.

> El cambio de `EMAIL_FROM` es **obligatorio** con el subdominio. Mientras el dominio no esté
> verificado, poner ahí una dirección de `grankha.roadshop.online` no arregla nada: Resend
> seguirá rechazándolo con `domain is not verified`. El orden es: DNS primero, verificación
> después, variable al final.

---

## 7. Mientras tanto, nada está roto

| Correo | ¿Sale hoy? |
|---|---|
| **Aviso de venta (a ti)** | ✅ Sí, por el remitente de reserva `GRANKHA <onboarding@resend.dev>` |
| Confirmación al cliente | ❌ No. Resend lo bloquea con `domain is not verified` |
| Envío con seguimiento | ❌ No. Igual |

Y ningún pedido se pierde: se guarda en Supabase, el fallo queda en la columna
`order_email_error` (nunca en `notes`, que puede llevar el comentario del cliente), el panel
lo muestra con el filtro «Con email de pedido fallido» y se reenvía con un clic en cuanto el
dominio esté verificado. Stripe además manda su propio recibo de pago al cliente.

La red de reserva solo funciona mientras `EMAIL_AVISO` sea `elexitodigital@gmail.com`, que es
la dirección de la cuenta de Resend: `onboarding@resend.dev` únicamente puede enviar hacia
esa dirección. Si la cambias antes de verificar el dominio, te quedas sin avisos internos.

---

## 8. Comprobación rápida

La haré yo, pero puedes ejecutarla tú:

```bash
for n in resend._domainkey.grankha send.grankha rsend.grankha; do
  for t in TXT MX CNAME; do
    echo "-- $n.roadshop.online $t"
    curl -s "https://dns.google/resolve?name=$n.roadshop.online&type=$t" \
      | python3 -c "import json,sys;[print('  ',x['data'][:80]) for x in json.load(sys.stdin).get('Answer',[])]"
  done
done
```

Tienen que salir: el TXT de DKIM empezando por `p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDQqPkp`
(ojo, ese principio concreto: si empieza por `…CQKBgQDr4dDT` es que sigue puesta la clave
vieja de la raíz), el TXT de SPF y el MX bajo `send.grankha`, y el CNAME bajo `rsend.grankha`.

Si algo sale vacío, o no ha propagado todavía (lo normal son unos minutos) o el nombre se
escribió con el sufijo duplicado (§4).

---

## 9. Resumen de una línea

Cuatro registros bajo `grankha.roadshop.online`, que ya tienes puestos y **tres son
correctos**. Solo hay que sustituir el valor del TXT `resend._domainkey.grankha` por la clave
DKIM de §5, porque la que está puesta pertenece al dominio raíz. Sin DMARC. Sin tocar el MX,
el SPF ni el A de la raíz, ni el CNAME de la tienda a Vercel.

# Resend en IONOS — GRANKHA

Guía para verificar **`roadshop.online`** (el dominio raíz) en Resend y que los correos de
GRANKHA salgan desde `grankha@roadshop.online`.

Fecha de comprobación del DNS: 22/10/2026.

---

## ⚠️ 0. LO QUE HA PASADO Y CÓMO ARREGLARLO (leer primero)

Pusiste los cuatro registros en IONOS. **Los valores son todos correctos.** El problema es el
nombre de host: les añadiste `.grankha`, y no va.

Comprobado por DNS el 22/10/2026:

| Lo que hay ahora (no sirve) | Lo que Resend busca (no existe) |
|---|---|
| `resend._domainkey.grankha.roadshop.online` ✅ valor correcto | `resend._domainkey.roadshop.online` ❌ vacío |
| `send.grankha.roadshop.online` TXT ✅ valor correcto | `send.roadshop.online` TXT ❌ vacío |
| `send.grankha.roadshop.online` MX ✅ valor correcto | `send.roadshop.online` MX ❌ vacío |
| `rsend.grankha.roadshop.online` CNAME ✅ valor correcto | `rsend.roadshop.online` CNAME ❌ vacío |

Verifiqué que el valor DKIM publicado bajo `grankha` es **idéntico byte a byte** al que
Resend generó para la raíz. O sea: no hay que cambiar ningún valor, solo el nombre.

### El arreglo: quitar `.grankha` a los cuatro nombres

En IONOS → Dominios y SSL → `roadshop.online` → DNS, edita (o borra y vuelve a crear) estos
cuatro registros. **El valor se queda igual en los cuatro.** Solo cambia el nombre de host:

| # | Tipo | Nombre AHORA (mal) | Nombre CORRECTO | Valor |
|---|------|--------------------|-----------------|-------|
| 1 | TXT | `resend._domainkey.grankha` | **`resend._domainkey`** | el mismo, no lo toques |
| 2 | MX | `send.grankha` | **`send`** | `feedback-smtp.eu-west-1.amazonses.com` · prio `10` |
| 3 | TXT | `send.grankha` | **`send`** | `v=spf1 include:amazonses.com ~all` |
| 4 | CNAME | `rsend.grankha` | **`rsend`** | `send.forge.rmta.net` |

### Por qué pasó

Es exactamente la trampa que avisa la §4: IONOS **añade `.roadshop.online` al final** de lo que
escribas. Escribiste `send.grankha` y quedó `send.grankha.roadshop.online`. Como el dominio que
verificamos es la raíz, el nombre de host es `send` a secas, y IONOS produce
`send.roadshop.online`, que es lo que Resend busca.

El `.grankha` solo habría sido correcto si hubiéramos decidido verificar el subdominio
`grankha.roadshop.online`. Elegiste la raíz, así que no va.

### Los registros actuales no estorban

Los cuatro bajo `grankha` son inertes: no los busca nadie y no chocan con el CNAME de
`grankha` a Vercel (son nombres distintos). Puedes dejarlos o borrarlos. **Recomiendo
borrarlos** cuando los nuevos funcionen, para que la zona no quede confusa.

### Alternativa, si prefieres editar un solo registro

Si te da menos trabajo tocar uno que cuatro, dime y cambio el plan: doy de alta
`grankha.roadshop.online` en Resend, y entonces tres de tus cuatro registros actuales ya
serían correctos tal cual — solo habría que sustituir el valor DKIM, porque Resend genera uno
distinto para cada dominio. El coste es que el remitente pasaría a ser
`pedidos@grankha.roadshop.online` en vez de `grankha@roadshop.online`, y habría que cambiar
`EMAIL_FROM` y redesplegar. **No lo recomiendo**: elegiste la raíz precisamente para que el
remitente coincidiera con el correo que ya aparece en 8 sitios de `legal.html`.

---


## 1. Qué vamos a hacer

| | Valor |
|---|---|
| Dominio que se verifica en Resend | `roadshop.online` (la raíz) |
| Remitente que verá el cliente | `GRANKHA <grankha@roadshop.online>` |
| Reply-To | `grankha@roadshop.online` |

**Decidido así a propósito.** Se barajó enviar desde un subdominio
(`pedidos@grankha.roadshop.online`), que es lo que se hizo en el otro proyecto. Se descarta
porque la raíz tiene dos ventajas concretas aquí:

1. **El remitente ya es el correcto y no hay que cambiar nada.** `EMAIL_FROM` en Vercel ya
   vale `GRANKHA <grankha@roadshop.online>`. En cuanto el dominio verifique, los tres correos
   salen solos: sin tocar variables y **sin redesplegar**.
2. **Es la dirección que ya está publicada.** `grankha@roadshop.online` aparece en 8 sitios
   de `legal.html`. Con un subdominio, el cliente vería un remitente distinto al que la web
   le dice que use.

El coste es que no se aísla la reputación por proyecto. Se asume: `roadshop.online` es un
dominio con poco tráfico y todos los proyectos son tuyos.

---

## 2. Comprobado antes de escribir esta guía

### Los tres nombres que hay que crear están libres

```
resend._domainkey.roadshop.online   → no existe
send.roadshop.online                → no existe
rsend.roadshop.online               → no existe
```

**No hay nada que reemplazar.** Ninguno de los cuatro registros pisa un registro existente.

### La raíz no tiene CNAME, así que no hay impedimento técnico

```
roadshop.online   CNAME   → no existe
roadshop.online   A       → 217.160.0.140
```

Esto importa: un CNAME en un nombre impide añadir otros registros en ese mismo nombre. En la
raíz no lo hay, así que se puede añadir lo que haga falta sin conflicto.

### Lo que NO se toca

| Nombre | Tipo | Valor actual | Para qué sirve |
|---|---|---|---|
| `roadshop.online` | MX | `10 mx00.ionos.es` / `10 mx01.ionos.es` | Recibir correo en `grankha@roadshop.online` |
| `roadshop.online` | TXT | `v=spf1 include:_spf-eu.ionos.com ~all` | Autorizar a IONOS a enviar desde el buzón |
| `roadshop.online` | A | `217.160.0.140` | Web principal en IONOS |
| `_dmarc.roadshop.online` | TXT | `v=DMARC1; p=none;` | Política DMARC |
| `grankha` | CNAME | `63e57cf5614e4cf1.vercel-dns-017.com` | La tienda en Vercel |

Los registros de Resend van todos bajo `resend._domainkey`, `send` y `rsend`. **Ninguno
aparece en esta tabla.**

---

## 3. La duda razonable: ¿y el SPF de la raíz?

Es lo que más preocupa y la respuesta es que **no se modifica**.

El SPF de la raíz (`v=spf1 include:_spf-eu.ionos.com ~all`) sigue ahí, intacto, autorizando a
IONOS. No hay que añadirle `include:amazonses.com`.

Por qué no hace falta: los servidores de correo comprueban el SPF contra el **Return-Path**
(el sobre técnico del mensaje), no contra el From que ve el cliente. Resend envía con
Return-Path en `send.roadshop.online`, y ese nombre lleva **su propio SPF** con
`include:amazonses.com`. Son dos comprobaciones sobre dos nombres distintos.

Resultado:

- El correo que mandes tú desde el buzón de IONOS → sigue validando con el SPF de la raíz.
- El correo que mande Resend → valida con el SPF de `send`.
- Ninguno estorba al otro.

Y **DMARC pasa por las dos vías**, porque todo queda dentro de `roadshop.online`:

| Comprobación | Valor | ¿Alineado con el From? |
|---|---|---|
| From | `grankha@roadshop.online` | — |
| DKIM `d=` | `roadshop.online` | ✅ coincide exacto |
| Return-Path | `send.roadshop.online` | ✅ mismo dominio organizativo |

El DMARC actual es `p=none`, así que de todos modos no rechaza nada. Pero con esto, cuando
algún día lo subas a `quarantine` o `reject`, los correos de GRANKHA seguirán pasando.

---

## 4. ⚠️ La regla de oro en IONOS

En IONOS solo existe la zona de `roadshop.online`, e IONOS **añade `.roadshop.online` al
final** de lo que escribas en «Nombre de host».

> **Escribe el nombre SIN el sufijo `.roadshop.online`.**
>
> - Correcto: `send`
> - Incorrecto: `send.roadshop.online` → crearía
>   `send.roadshop.online.roadshop.online` y no verificaría nunca.

**TTL:** déjalo como venga por defecto. No lo toques.

---

## 5. Los registros — VALORES REALES, ya generados por Resend

El dominio **`roadshop.online` ya está dado de alta en Resend** (región eu-west-1, Irlanda).
Id interno: `43a0dc99-c8e1-4d4a-9b28-2f1be6cb5603`. Estado actual: `not_started`, a la
espera de estos registros.

Resend ha devuelto **exactamente cuatro** registros y **ninguno es DMARC**, así que queda
confirmado que no hay que añadirlo: el de la raíz (`v=DMARC1; p=none;`) ya existe, no lleva
etiqueta `sp=` y cubre también a todos los subdominios.

Copia y pega estos valores tal cual. Son los que ha generado Resend para tu dominio, no una
estimación.

### Registro 1 — DKIM

| Campo | Valor |
|---|---|
| Tipo | `TXT` |
| Nombre de host | `resend._domainkey` |
| Valor | ver bloque de abajo |
| TTL | Auto / el que venga |

```
p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDr4dDTcZ/36Bo8s+JdY55oFP6wE3CUntPdvpIItX4JIg8w3vHTg4N+8OX0AxrVwxwlWclNv8r/QF1y5g0dVk1ZfWyYWGgpxKBOlVuKrYxzQ7Pgw+LBbmBBejqzQrshxfIT9qv+HVFjveEtBKJovyqlD7G2VAb7oGNnfKVIi9ikyQIDAQAB
```

> Cópiala **entera**, desde `p=` hasta `AQAB`, en una sola pieza. Es una línea larga y los
> navegadores de IONOS a veces la cortan visualmente: no te fíes de lo que se ve, pega y
> guarda. Sin comillas alrededor, sin espacios al principio ni al final.

### Registros 2, 3 y 4

| # | Tipo | Nombre de host | Valor / destino | Prioridad |
|---|------|----------------|-----------------|-----------|
| 2 | **MX** | `send` | `feedback-smtp.eu-west-1.amazonses.com` | `10` |
| 3 | **TXT** | `send` | `v=spf1 include:amazonses.com ~all` | — |
| 4 | **CNAME** | `rsend` | `send.forge.rmta.net` | — |

Notas:

- Los registros **2 y 3 comparten nombre de host** (`send`). Es normal: uno es MX y otro TXT,
  tipos distintos bajo la misma etiqueta. IONOS lo admite sin problema. No es un duplicado.
- Estos tres valores son fijos e idénticos a los que ya funcionan en el otro proyecto:

  ```
  send.sscarsgarage.roadshop.online        TXT   v=spf1 include:amazonses.com ~all
  send.sscarsgarage.roadshop.online        MX    10 feedback-smtp.eu-west-1.amazonses.com.
  rsend.sscarsgarage.roadshop.online       CNAME send.forge.rmta.net.
  ```

- El registro 1 (DKIM) es el único distinto, porque es único de tu dominio.


---

## 6. Paso a paso en IONOS

1. **IONOS** → **Dominios y SSL**.
2. Busca **roadshop.online** → pulsa **DNS**.
3. **Añadir registro** → rellena el registro **1** de la tabla.
4. Repite con el **2**, el **3** y el **4**.
5. Guarda.

### Si IONOS te avisa de algo

Si al guardar aparece un aviso de que un registro **reemplaza**, **sobrescribe** o **choca**
con otro existente:

> **NO aceptes.** Cancela y mándame una captura.

Con lo comprobado en §2 no debería ocurrir — los tres nombres están libres — pero si IONOS
dice lo contrario quiero verlo antes de que se borre nada.

---

## 7. Estado en Resend: ya está dado de alta

**Hecho.** `roadshop.online` ya existe en la cuenta de Resend, en región **eu-west-1
(Irlanda)**, la más cercana a España y la misma que usa el otro proyecto.

| | |
|---|---|
| Id del dominio en Resend | `43a0dc99-c8e1-4d4a-9b28-2f1be6cb5603` |
| Estado | `not_started` — espera los registros de §5 |
| Sending | `enabled` |
| Receiving | `disabled` (correcto: el buzón sigue en IONOS) |
| Registros que pide | 4, ninguno DMARC |

**El riesgo de solapamiento que temía no existe.** Comprobado al dar de alta el dominio: esta
cuenta de Resend tenía **0 dominios**, así que `sscarsgarage.roadshop.online` está en otra
cuenta distinta. No hay conflicto posible entre los dos proyectos, y el alta devolvió
`HTTP 201` a la primera.

### Lo que falta es tu parte: poner los registros en IONOS

Solo queda copiar los cuatro valores de §5 en la zona DNS de `roadshop.online`. Es lo que no
puedo hacer yo: no tengo acceso a tu panel de IONOS.

En cuanto los pongas, yo hago el resto:

1. **Comprobar la propagación por DNS**, registro a registro (§9).
2. **Confirmar que Resend pasa el dominio a *Verified***. Si a las 72 h no verifica, hay un
   botón *Restart verification*; lo normal son 15 minutos.
3. **Lanzar un pedido de prueba real** de punta a punta y confirmarte los tres correos:
   confirmación al cliente, aviso interno de venta y, al marcarlo enviado, el de seguimiento.
4. **Borrar el pedido de prueba** de Supabase y dejar las tablas a cero.

**Y no hace falta redesplegar ni tocar variables.** Como se ha verificado la raíz y no un
subdominio, `EMAIL_FROM` ya vale `GRANKHA <grankha@roadshop.online>`, que es una dirección
del dominio verificado. Los tres correos empiezan a salir en cuanto Resend marque *Verified*.

> La clave API con permisos de dominio ya se ha usado y se borra del entorno. La clave
> anterior (`re_RHDGFx6G_…`, solo envío) sigue siendo la que usa la web en producción, y
> **no hace falta cambiarla**: para enviar no necesita permisos de dominio. Si prefieres
> retirar la que me has dado ahora, puedes borrarla en Resend → API Keys en cuanto el dominio
> esté verificado; no afecta a nada.


---

## 8. Mientras tanto, nada está roto

El comportamiento actual se mantiene hasta que el dominio verifique:

| Correo | ¿Sale hoy? |
|---|---|
| **Aviso de venta (a ti)** | ✅ Sí, por el remitente de reserva `GRANKHA <onboarding@resend.dev>` |
| Confirmación al cliente | ❌ No. Resend lo bloquea con `domain is not verified` |
| Envío con seguimiento | ❌ No. Igual |

Y ningún pedido se pierde: se guarda en Supabase, el fallo queda en la columna
`order_email_error` (nunca en `notes`, que puede llevar el comentario del cliente), el panel lo
muestra con el filtro «Con email de pedido fallido» y se reenvía con un clic en cuanto el
dominio esté verificado. Stripe además manda su propio recibo de pago al cliente.

---

## 9. Comprobación rápida

La haré yo, pero puedes ejecutarla tú:

```bash
for n in resend._domainkey.roadshop.online send.roadshop.online rsend.roadshop.online; do
  for t in TXT MX CNAME; do
    echo "-- $n $t"
    curl -s "https://dns.google/resolve?name=$n&type=$t" \
      | python3 -c "import json,sys;[print('  ',x['data']) for x in json.load(sys.stdin).get('Answer',[])]"
  done
done
```

Tienen que aparecer el TXT de DKIM, el TXT de SPF y el MX bajo `send`, y el CNAME bajo `rsend`
si Resend lo pidió. Si algo sale vacío, o no ha propagado todavía (Resend admite hasta 72 h,
lo normal son 15 minutos) o el nombre se escribió con el sufijo duplicado (§4).

---

## 10. Resumen de una línea

Tres o cuatro registros en la zona `roadshop.online` de IONOS, bajo los nombres
`resend._domainkey`, `send` y `rsend`, escritos **sin** el sufijo `.roadshop.online`. Sin
DMARC. Sin tocar el MX, el SPF ni el A de la raíz. Falta la clave DKIM, que solo Resend
genera al dar de alta el dominio (§7).

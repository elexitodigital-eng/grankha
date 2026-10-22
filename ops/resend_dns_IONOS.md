# Resend en IONOS — GRANKHA

Guía para verificar **`roadshop.online`** (el dominio raíz) en Resend y que los correos de
GRANKHA salgan desde `grankha@roadshop.online`.

Fecha de comprobación del DNS: 22/10/2026.

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

## 5. Los registros

**No hay que añadir DMARC.** El de la raíz (`v=DMARC1; p=none;`) ya existe, no lleva etiqueta
`sp=` y por tanto cubre también a todos los subdominios. Poner otro sería redundante.

| # | Tipo | Nombre de host en IONOS | Valor / destino | Prioridad |
|---|------|-------------------------|-----------------|-----------|
| 1 | **TXT** | `resend._domainkey` | `p=MIGfMA0…` ← **la genera Resend, ver §7** | — |
| 2 | **MX** | `send` | `feedback-smtp.eu-west-1.amazonses.com` | `10` |
| 3 | **TXT** | `send` | `v=spf1 include:amazonses.com ~all` | — |
| 4 | **CNAME** | `rsend` | `send.forge.rmta.net` | — |

Notas:

- Los registros **2 y 3 comparten nombre de host** (`send`). Es normal: uno es MX y otro TXT,
  tipos distintos bajo la misma etiqueta. IONOS lo admite sin problema.
- Los valores 2, 3 y 4 son fijos. Son los mismos que ya funcionan en el otro proyecto, donde
  están publicados y resuelven correctamente:

  ```
  send.sscarsgarage.roadshop.online        TXT  v=spf1 include:amazonses.com ~all
  send.sscarsgarage.roadshop.online        MX   10 feedback-smtp.eu-west-1.amazonses.com.
  rsend.sscarsgarage.roadshop.online       CNAME send.forge.rmta.net.
  ```

- El registro 1 (DKIM) es **único de tu dominio**. No se puede copiar del otro proyecto ni
  inventar.
- El registro 4 solo aparece si Resend te lo pide en la pestaña **Records**. En algunos
  dominios Resend muestra tres registros y no cuatro. **Copia exactamente los que te muestre
  a ti**, ni uno más ni uno menos. Yo lo confirmaré en cuanto dé de alta el dominio (§7).

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

## 7. Falta un dato: la clave DKIM

El registro 1 necesita el valor `p=MIGfMA0…`, que solo existe una vez dado de alta el dominio
en Resend. **Con la clave actual no puedo obtenerlo**: es de tipo *restricted*, solo permite
enviar, y al intentar leer o crear dominios responde

```
401  "This API key is restricted to only send emails"
```

Has elegido darme una clave con permisos de dominio. Cuando me la pegues, yo hago esto:

1. **Dar de alta `roadshop.online`** en Resend, región **eu-west-1 (Irlanda)** — la misma que
   usa el otro proyecto y la más cercana a España.
2. **Leer los registros exactos** que genere Resend y volcarlos en esta guía, sustituyendo los
   valores esperados por los reales. Si Resend pide tres registros en vez de cuatro, lo
   ajusto.
3. **Dejarte la tabla lista para copiar y pegar** en IONOS, con los nombres ya escritos sin el
   sufijo.
4. Cuando los hayas puesto: **comprobar la propagación por DNS**, confirmar que Resend pasa el
   dominio a *Verified* y **lanzar un pedido de prueba real** de punta a punta.
5. **Borrar el pedido de prueba** de Supabase y dejar las tablas a cero.

La clave se borra del entorno en cuanto se use, igual que se hizo con la anterior.

> **Alternativa si prefieres no darme la clave:** entra tú en Resend → **Domains** →
> **Add Domain** → `roadshop.online`, región eu-west-1, y pégame los valores de la pestaña
> **Records**. Con eso me vale para rellenar la guía y comprobar que coinciden.

### Un riesgo que vigilaré al dar de alta el dominio

En esa misma cuenta de Resend ya está verificado `sscarsgarage.roadshop.online`, que es un
subdominio de `roadshop.online`. En principio Resend trata cada dominio como una entrada
independiente y no debería haber conflicto. Pero si al dar de alta la raíz respondiera que el
dominio **ya está en uso** o **solapa** con el otro, no insistiré: te lo digo y volvemos al
plan B, que es verificar `grankha.roadshop.online` y cambiar `EMAIL_FROM` a
`pedidos@grankha.roadshop.online`. Los nombres de ese plan B (`send.grankha`,
`rsend.grankha`, `resend._domainkey.grankha`) también están libres, comprobado.

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

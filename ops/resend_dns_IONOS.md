# Resend en IONOS — GRANKHA

Guía para verificar el dominio de envío de GRANKHA en Resend.
Mismo montaje que ya funciona en `sscarsgarage.roadshop.online`.

Fecha de comprobación del DNS: 22/10/2026.

---

## 1. Qué vamos a hacer y por qué

Los correos de GRANKHA saldrán de un **subdominio de envío**, no del dominio raíz:

| | Valor |
|---|---|
| Dominio que se verifica en Resend | `grankha.roadshop.online` |
| Remitente que verá el cliente | `GRANKHA <pedidos@grankha.roadshop.online>` |
| Reply-To (sin cambio) | `grankha@roadshop.online` |

**Por qué un subdominio y no la raíz:**

- Aísla la reputación. Si un día un correo cae en spam, no mancha `roadshop.online`
  ni el buzón real `grankha@roadshop.online`, que sigue recibiendo las respuestas.
- Es exactamente lo que se hizo en el otro proyecto: `pedidos@sscarsgarage.roadshop.online`.
- No hay que tocar el SPF ni el MX del buzón de IONOS. Ni un registro existente se modifica.

**Consecuencia visible, para que no te sorprenda:** el cliente verá
`pedidos@grankha.roadshop.online` como remitente en vez de `grankha@roadshop.online`.
Cuando pulse «Responder», el correo llegará a `grankha@roadshop.online` igual que ahora,
porque el Reply-To no cambia.

---

## 2. Ya está comprobado que esto funciona en tu zona

La duda razonable es: *`grankha.roadshop.online` es un CNAME a Vercel, ¿se pueden añadir
registros debajo?* Sí. Lo he verificado en tu propia zona, no es teoría:

```
sscarsgarage.roadshop.online          CNAME  d1aff6f9ab81ad45.vercel-dns-017.com.   ← la web
send.sscarsgarage.roadshop.online     TXT    v=spf1 include:amazonses.com ~all       ← Resend
send.sscarsgarage.roadshop.online     MX     10 feedback-smtp.eu-west-1.amazonses.com.
resend._domainkey.sscarsgarage...     TXT    p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDK56PacZkk…
rsend.sscarsgarage.roadshop.online    CNAME  send.forge.rmta.net.
```

`sscarsgarage` es un CNAME a Vercel **y** tiene los cuatro registros de Resend debajo,
funcionando. `grankha` está en la misma situación:

```
grankha.roadshop.online               CNAME  63e57cf5614e4cf1.vercel-dns-017.com.
```

Un CNAME impide añadir otros registros **en ese mismo nombre**, pero no en nombres
*por debajo* (`send.grankha…`, `rsend.grankha…`). Son etiquetas distintas.

Y confirmado también: **ninguno de los cuatro nombres que vamos a crear existe hoy.**
No hay nada que reemplazar.

```
send.roadshop.online                    → no existe
resend._domainkey.roadshop.online       → no existe
send.grankha.roadshop.online            → no existe
resend._domainkey.grankha.roadshop.online → no existe
rsend.grankha.roadshop.online           → no existe
```

---

## 3. ⚠️ La regla de oro en IONOS

En IONOS **solo existe la zona de `roadshop.online`**. El subdominio `grankha` no tiene
zona propia. IONOS **añade `.roadshop.online` al final** de lo que escribas.

> **Escribe el nombre de host SIN el sufijo `.roadshop.online`.**
>
> - Correcto: `send.grankha`
> - Incorrecto: `send.grankha.roadshop.online` → crearía
>   `send.grankha.roadshop.online.roadshop.online` y no funcionaría nunca.

**TTL:** déjalo como venga por defecto. No lo toques.

---

## 4. Los 4 registros

Son cuatro, no cinco. **No hay que añadir DMARC**: el que ya existe en la raíz
(`_dmarc.roadshop.online` → `v=DMARC1; p=none;`) no lleva etiqueta `sp=`, así que
**cubre automáticamente a todos los subdominios**, incluido `grankha`.

| # | Tipo | Nombre de host (escribir exactamente así) | Valor / destino | Prioridad |
|---|------|-------------------------------------------|-----------------|-----------|
| 1 | **TXT** | `resend._domainkey.grankha` | `p=MIGfMA0…` ← **te la da Resend, ver §6** | — |
| 2 | **MX** | `send.grankha` | `feedback-smtp.eu-west-1.amazonses.com` | `10` |
| 3 | **TXT** | `send.grankha` | `v=spf1 include:amazonses.com ~all` | — |
| 4 | **CNAME** | `rsend.grankha` | `send.forge.rmta.net` | — |

Notas:

- Los registros **2 y 3 comparten nombre de host** (`send.grankha`). Es normal y correcto:
  uno es MX y otro TXT, tipos distintos bajo la misma etiqueta. IONOS lo admite.
- Los valores 2, 3 y 4 son fijos, idénticos a los del otro proyecto. No cambian.
- El valor 1 (DKIM) es **único para tu dominio** y solo lo genera Resend al darlo de alta.
  No se puede inventar ni copiar del otro proyecto.

---

## 5. Paso a paso en IONOS

1. Entra en **IONOS** → **Dominios y SSL**.
2. Busca **roadshop.online** y pulsa **DNS**.
3. Pulsa **Añadir registro**.
4. Rellena el **registro 1** de la tabla:
   - Tipo: `TXT`
   - Nombre de host: `resend._domainkey.grankha`
   - Valor: la clave DKIM que te dé Resend (§6)
5. Repite para los registros **2**, **3** y **4**.
6. Guarda.

### Si IONOS te avisa de algo

Si al guardar aparece un aviso de que un registro **reemplaza**, **sobrescribe** o
**choca** con otro existente:

> **NO aceptes.** Cancela y mándame una captura de la pantalla.

Con lo verificado en §2 no debería pasar — los cuatro nombres están libres — pero si
IONOS dice lo contrario, quiero verlo antes de que borres nada.

---

## 6. Falta un dato: la clave DKIM

El registro 1 necesita el valor `p=MIGfMA0…`, que solo existe una vez que el dominio está
dado de alta en Resend. **No puedo obtenerlo yo con la clave actual**: la clave
`re_RHDGFx6G_…` es de tipo *restricted* (solo enviar). Al intentar leer o crear dominios
devuelve:

```
401  "This API key is restricted to only send emails"
```

Dos caminos, elige el que prefieras:

**Opción A — me das una clave con permisos de dominio (yo hago todo)**

1. Resend → **API Keys** → **Create API Key**.
2. En permisos, activa **Domains** (lectura y escritura), no solo *Sending access*.
3. Pégame la clave. Yo doy de alta `grankha.roadshop.online`, recojo los cuatro valores
   exactos, relleno esta guía y te la dejo lista para copiar y pegar en IONOS.
4. Cuando termines en IONOS, verifico la propagación por DNS y lanzo el correo de prueba.

La clave se borra del entorno en cuanto se use, igual que se hizo con la anterior.

**Opción B — lo das de alta tú en el panel de Resend**

1. Resend → **Domains** → **Add Domain**.
2. Nombre: `grankha.roadshop.online`. Región: **eu-west-1 (Irlanda)**, la misma que usa
   el otro proyecto.
3. Entra en la pestaña **Records** del dominio creado.
4. Pégame los cuatro valores tal cual aparecen ahí (o al menos el TXT de
   `resend._domainkey`), y yo actualizo esta guía y compruebo que coincidan con la tabla.

**En cualquiera de las dos opciones, copia los valores literalmente.** Sin añadir comillas,
sin espacios al final, sin puntos extra. Un carácter de más y la verificación falla.

---

## 7. Qué NO tocar

Estos registros son del buzón real y de la web. **No se modifican ni se borran:**

| Nombre | Tipo | Valor actual | Para qué sirve |
|---|---|---|---|
| `roadshop.online` | MX | `10 mx00.ionos.es` / `10 mx01.ionos.es` | Recibir correo en `grankha@roadshop.online` |
| `roadshop.online` | TXT | `v=spf1 include:_spf-eu.ionos.com ~all` | Autorizar a IONOS a enviar |
| `_dmarc.roadshop.online` | TXT | `v=DMARC1; p=none;` | Política DMARC (ya cubre subdominios) |
| `grankha` | CNAME | `63e57cf5614e4cf1.vercel-dns-017.com` | Sirve la tienda en Vercel |
| `roadshop.online` | A | `217.160.0.140` | Web principal en IONOS |

Los cuatro registros de Resend van todos bajo `send.grankha`, `rsend.grankha` y
`resend._domainkey.grankha`. **Ninguno pisa nada de esta tabla.**

---

## 8. Después de guardar en IONOS

Avísame. Yo hago, en este orden:

1. **Compruebo la propagación por DNS** (los cuatro registros, uno a uno).
   Suele tardar entre 15 minutos y unas horas; Resend admite hasta 72 h.
2. **Verifico el dominio en Resend** y confirmo que pasa a estado *Verified*.
3. **Cambio `EMAIL_FROM` en Vercel** a `GRANKHA <pedidos@grankha.roadshop.online>`
   y mantengo `EMAIL_REPLY_TO=grankha@roadshop.online`.
4. **Lanzo un pedido de prueba real** de punta a punta y te confirmo los tres correos:
   confirmación al cliente, aviso interno de venta y, al marcarlo enviado, el correo
   de seguimiento.
5. **Borro el pedido de prueba** de Supabase y dejo las tablas a cero.

Mientras el dominio no esté verificado, el comportamiento actual se mantiene sin cambios:
los avisos internos siguen saliendo por la red de reserva desde
`GRANKHA <onboarding@resend.dev>` y los correos a clientes no salen. Nada se rompe
por esperar.

---

## 9. Comprobación rápida (la haré yo, pero puedes ejecutarla tú)

```bash
for n in resend._domainkey.grankha.roadshop.online send.grankha.roadshop.online rsend.grankha.roadshop.online; do
  for t in TXT MX CNAME; do
    echo "-- $n $t"
    curl -s "https://dns.google/resolve?name=$n&type=$t" \
      | python3 -c "import json,sys;[print('  ',x['data']) for x in json.load(sys.stdin).get('Answer',[])]"
  done
done
```

Los cuatro registros tienen que aparecer. Si alguno sale vacío, no ha propagado todavía
o el nombre de host se escribió con el sufijo duplicado (§3).

---

## 10. Resumen de una línea

Cuatro registros en la zona `roadshop.online` de IONOS, escritos **sin** el sufijo
`.roadshop.online`, bajo `send.grankha` / `rsend.grankha` / `resend._domainkey.grankha`.
Sin DMARC. Sin tocar el buzón ni el CNAME de Vercel. Falta la clave DKIM, que solo
Resend puede dar (§6).

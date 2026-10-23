# Acciones pendientes · GRANKHA

**Estado: 23/10/2026, producción desplegada y verificada.**

Lo que estaba bloqueado ya está hecho:

| Pendiente anterior | Estado |
|---|---|
| Desplegar los 5 commits | ✅ desplegado (`vercel deploy --prod`); `/tienda` da 200 |
| Corregir el registro TXT de Resend en IONOS | ✅ corregido por el usuario; DNS verificado registro a registro |
| Confirmar `verified` en Resend | ✅ `verified`, los 4 registros en verde |
| Actualizar `EMAIL_FROM` al subdominio | ✅ `GRANKHA <pedidos@grankha.roadshop.online>` + redeploy |
| Reemplazar la clave API de Resend revocada | ✅ sustituida en el entorno + redeploy |
| Probar el envío real | ✅ `ok: true`; E2E completo (confirmación, venta y seguimiento) |
| Activar `checkout.session.expired` en Stripe | ✅ activado vía API (webhook `enabled`) |

Lo que sigue abajo son los pasos que **aún** faltan y quién los hace.

---

## A. Lo que queda (3 acciones del usuario, 1 opcional)

### A1. Search Console: cambiar el método de verificación ⚠️ importante

**Confirmado en producción:** con `cleanUrls:true` Vercel redirige **todas** las rutas que
terminan en `.html`, y los `rewrites` de `vercel.json` no preemptan esa redirección. Por eso
`/googlec2e45e8990a69adf.html` responde **308** y no 200. Es una limitación de plataforma,
no un fallo del despliegue; no hay configuración de Vercel que lo resuelva sin renunciar a
las URLs limpias.

**Solución:** verificar por un método inmune a los cambios de URL.

- **Opción recomendada — TXT de DNS.** En Search Console, al añadir la propiedad, elige
  «Proveedor de nombres de dominio» → Google te da un TXT que empieza por
  `google-site-verification=`. Lo añades en IONOS en la **raíz** `roadshop.online`, tipo TXT,
  TTL 3600. No toca nada del correo ni del sitio. Cuando esté publicado, avísame y lo
  compruebo yo por DNS.
- **Alternativa — meta tag.** Si prefieres no tocar DNS, pégame el `<meta>` que te da Search
  Console y lo incrusto en el `<head>` de las 86 páginas y redespliego.

Después: enviar `https://grankha.roadshop.online/sitemap.xml` en «Sitemaps».

> Si Search Console ya te aparece como verificado, no hace falta repetir nada: aun así el
> TXT es más duradero que el fichero, que ahora es inalcanzable.

### A2. Supabase: quitar la política que deja escribir suscriptores

Los formularios ya no tocan Supabase (van a Google Forms por servidor), así que la inserción
pública de `subscribers` es superficie de abuso sin uso. La clave de servicio no puede
ejecutar DDL, así que hay que hacerlo en el **SQL Editor** de Supabase:

```sql
drop policy if exists "subscribers_insert_public" on public.subscribers;
```

### A3. Datos legales que faltan en el pie y en `legal.html`

Art. 10 de la LSSI-CE: **NIF y domicilio fiscal** de GRANKHA. Sin eso la tienda no cumple el
mínimo legal para vender en España. Pásamelos y los publico en un minuto.

### A4. Opcional: limpieza de las respuestas de prueba en Google Forms

Durante las pruebas se colaron respuestas de test (~10 en el de newsletter y ~9 en el de
contacto). Bórralas desde las pestañas «Respuestas» de cada formulario si no quieres verlas
en las estadísticas.

---

## B. Recordatorio de operación

- El proyecto **no tiene integración con GitHub**: los pushes no despliegan solos. Tras cada
  cambio hay que ejecutar `vercel deploy --prod` (o `ops/deploy_vercel.sh`).
- Backups: el plan Free de Supabase no los incluye. Si quieres copia de seguridad de pedidos,
  activa Point-in-Time Recovery o exporta `orders`/`order_items` periódicamente.
- Comprobación post-despliegue: `bash ops/post_deploy.sh`. Ahora avisa (sin contar fallo) del
  308 del fichero de Google, y verifica que `/pedidos.html` se comporta igual que cualquier
  otra ruta `.html` inexistente (308→404), de modo que no delata el panel.


---

## 1. Desplegar (bloquea todo lo demás)

Cinco commits están en `main` pero **no en producción**. Comprobado: `/tienda` devuelve 404
y la página de error aún enlaza `.html`, o sea que producción sirve el build anterior.

| Commit | Contenido |
|---|---|
| `0f15ea9` | Remitente alineado con el subdominio |
| `3c8b194` | Resend: subdominio, no raíz |
| `361cac8` | Auditoría + guía DNS + salvaguarda vercel.json |
| `16cd9dd` | Clean URLs, formularios a Google, pop-up, huecos de auditoría |
| `12f8bdc` | El logout ya no delata el panel |

El proyecto **no tiene integración con GitHub**: los pushes no despliegan solos.

```bash
cd /home/user/grankha
timeout 900 npx --yes vercel@latest deploy --prod --yes \
  --token "$(cat /tmp/vt)" --scope grankha
```

Falta `/tmp/vt` con el token de <https://vercel.com/account/tokens>.

Al terminar: `bash ops/post_deploy.sh` — verifica clean URLs, formularios, panel, claves,
sitemap y fichero de Google, y si todo cuadra avisa a IndexNow y Pingomatic.

### Riesgo cubierto: el fichero de verificación de Google

`cleanUrls: true` hace que Vercel redirija `/x.html` → `/x` con un 308. Search Console exige
que `/googlec2e45e8990a69adf.html` responda **200 en esa URL exacta**, así que la redirección
rompería la verificación.

Solución aplicada: se creó `google-verify.txt`, gemelo idéntico byte a byte del fichero de
verificación, y `vercel.json` lleva un `rewrites.beforeFiles` que apunta la URL `.html` a ese
`.txt`. Funciona porque `cleanUrls` **solo actúa sobre rutas `.html`**: al ser el destino un
`.txt`, se esquiva la redirección por completo. Un rewrite que apuntara a otro `.html` no
serviría, porque volvería a entrar en `cleanUrls`.

El paso 2 de `ops/post_deploy.sh` lo comprueba tras desplegar: espera 200 y el texto
`google-site-verification` en la URL con `.html`.

Si aun así fallara, queda una salida que no depende de `cleanUrls`: verificar la propiedad en
Search Console por **registro TXT en DNS** en vez de por fichero. Hace falta el token que da
Search Console, que es distinto del de fichero.

---

## 2. DNS: sustituir el valor del DKIM (bloquea los correos a clientes)

De los cuatro registros de `grankha.roadshop.online`, **tres ya son correctos**. Solo falla
el TXT de DKIM, porque lleva la clave del dominio raíz y Resend genera una distinta por
dominio.

En IONOS → Dominios y SSL → `roadshop.online` → DNS, editar el registro **TXT** cuyo nombre
de host es `resend._domainkey.grankha` y sustituir el valor por:

```
p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDQqPkp/6YNq/eZMBp8lgj7N1stXN72fJHiPQoTijn/P0neSNZ9oe2ncI6QRSdzFlWNBsWRAUxD3MXJ+ltWl6krELhFvzi7hQVDZDz6KBny5eFG3NQneGBKNSYz+3gBL+c6Gp5QhdE5lpD8ZrcXcWw/tJCacpWOssWIB9w29cH5ewIDAQAB
```

218 caracteres, de `p=` a `AQAB`, en una sola pieza. El nombre de host **no** se cambia.

Los otros tres no se tocan. Detalle y porqués en `ops/resend_dns_IONOS.md`.

Comprobación:

```bash
curl -s "https://dns.google/resolve?name=resend._domainkey.grankha.roadshop.online&type=TXT" \
  | python3 -c "import json,sys;print(json.load(sys.stdin).get('Answer',[{}])[0].get('data','')[:60])"
```

Si empieza por `p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDQqPkp` está bien. Si empieza por
`…CQKBgQDr4dDT` sigue la clave vieja.

---

## 3. Cambiar EMAIL_FROM (solo DESPUÉS de que Resend verifique)

Con el subdominio verificado, el remitente debe pertenecer a él.

```bash
PID=prj_FbwcbsYMNlr6cbJlRY6R4UEp2rYs
TID=team_NkO4XOT5Nz1RHuxlKFSpWGnH
# obtener el id de la variable EMAIL_FROM y parchearla
curl -sS "https://api.vercel.com/v10/projects/$PID/env?teamId=$TID&decrypt=true" \
  -H "Authorization: Bearer $(cat /tmp/vt)"
```

Valor nuevo: `GRANKHA <pedidos@grankha.roadshop.online>`
`EMAIL_REPLY_TO` **no cambia**: sigue en `grankha@roadshop.online`, que es el buzón real y la
dirección publicada en `legal.html`.

Después, redesplegar. El orden importa: si se cambia antes de verificar, Resend seguirá
respondiendo `domain is not verified` y no se gana nada.

> Recordatorio de un error propio anterior: el `PATCH` de una variable de entorno afecta a
> los tres targets a la vez, y mutar el env de producción para probar cortó los avisos
> internos. No tocar `EMAIL_PROVIDER` ni crear variables de prueba.

---

## 4. Stripe: activar `checkout.session.expired` en el webhook

El handler ya está escrito en `api/stripe-webhook.js`, pero no se disparará mientras el
evento no esté activado en el endpoint.

Panel de Stripe → Developers → Webhooks → `we_1URVX35u1hLzWyIGYIjzIbo9` → *Update details* →
añadir **`checkout.session.expired`** a la lista de eventos.

**No hace falta rotar el secreto**: cambiar solo la lista de eventos no invalida
`STRIPE_WEBHOOK_SECRET`.

Por API, si se prefiere:

```bash
# requiere leer STRIPE_SECRET_KEY del env de Vercel (paso 3)
curl -sS -X POST "https://api.stripe.com/v1/webhook_endpoints/we_1URVX35u1hLzWyIGYIjzIbo9" \
  -u "$STRIPE_SECRET_KEY:" \
  -d "enabled_events[]=checkout.session.completed" \
  -d "enabled_events[]=charge.refunded" \
  -d "enabled_events[]=checkout.session.expired"
```

Ojo: `enabled_events[]` **reemplaza** la lista entera, no añade. Hay que incluir los tres.

---

## 5. Supabase: quitar la política huérfana

`subscribers_insert_public` permitía que cualquiera, sin autenticar, insertara filas en
`subscribers`. Existía porque la newsletter escribía desde el navegador; ahora va por el
servidor y esa puerta solo sirve para que alguien llene la tabla de basura.

```sql
drop policy if exists "subscribers_insert_public" on public.subscribers;
```

Desde el SQL Editor de Supabase (proyecto `ravvjwyjaxofidgueopc`), o por API con un token
de la Management API. El resto del RLS está bien: las cuatro tablas tienen RLS activo y no
hay ninguna política de SELECT para `anon`.

De paso, comprobar en **Database → Backups** si hay copias automáticas. El plan Free no las
incluye; antes de la primera venta conviene tenerlo resuelto.

---

## 6. Borrar las respuestas de prueba de los Google Forms

Mientras se depuraba la detección del acuse de recibo se colaron envíos de prueba. La
detección inicial buscaba «response **was** recorded» y Google responde «response **has**
been recorded», así que varios envíos que se dieron por fallidos **sí entraron**.

| Formulario | Respuestas a borrar | Cómo reconocerlas |
|---|---|---|
| NEWSLETTER GRANKHA | ~10 | todas `prueba.tecnica.grankha@gmail.com` |
| CONTACTO GRANKHA | ~7 | una de «Prueba Técnica GRANKHA» con pedido `GRK-TEST-0001`/`-0002`, y varias con nombre «Spam» y `s@example.com` |

---

## 7. Datos fiscales

`legal.nif` y `legal.domicilio` siguen vacíos en `data/site.json`, y `legal.html` publicado
dice que se facilitan a quien los pida. El art. 10 de la LSSI-CE obliga a publicarlos.

En cuanto estén:

```bash
# editar data/site.json → legal.nif y legal.domicilio
cd /home/user/grankha && python3 tools/build.py
```

Y redesplegar. El generador ya deja esos campos en el aviso legal y en la política de
privacidad; no hay que tocar `tools/build.py`.

---

## Ninguna prueba ha tocado Stripe

Confirmado: no se ha creado ninguna sesión de checkout ni ningún PaymentIntent en esta
tanda. Las pruebas de correo y de margen se hicieron renderizando plantillas en local, y las
de formularios contra los Google Forms (de ahí el punto 6).

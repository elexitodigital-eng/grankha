# Acciones pendientes · GRANKHA

Todo el código de la tanda está commiteado y publicado en GitHub. Lo de abajo es lo que
**no** se ha podido ejecutar por falta de credenciales o porque depende de un paso manual.

Fecha: 22/10/2026.

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

### Riesgo a comprobar en ese script

`cleanUrls: true` hace que Vercel redirija `/x.html` → `/x`. Search Console exige que
`/googlec2e45e8990a69adf.html` responda **200 en esa URL exacta**. Se intentó cubrir con un
`rewrites.beforeFiles` en `vercel.json`, pero **no está confirmado que Vercel lo respete**:
un rewrite que apunta a sí mismo puede ser un no-op y dejar pasar la redirección.

El paso 2 del script lo comprueba. Si falla, la alternativa es cambiar la verificación de
Search Console al método de **registro TXT en DNS** (no depende de ninguna URL y sobrevive a
`cleanUrls`). Hace falta el token que da Search Console, que es distinto del de fichero.

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

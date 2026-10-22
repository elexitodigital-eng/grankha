# GRANKHA · Auditoría de lanzamiento

Revisión punto por punto de la lista de riesgos, con lo verificado en el código y en
producción. Fecha: 22/10/2026.

Leyenda: ✅ resuelto · ⚠️ acción pendiente · ❌ no cubierto

---

## Resumen ejecutivo

**No se puede lanzar todavía.** Hay dos bloqueos que no dependen del código:

1. **Los registros DNS de Resend están mal colocados** → los correos a clientes no salen.
2. **Faltan NIF y domicilio fiscal** → incumple el art. 10 de la LSSI-CE.

Y un tercero operativo: **falta desplegar** los cambios de esta tanda (clean URLs,
formularios, pop-up, margen con Stripe). El código está commiteado (`16cd9dd`) pero no
publicado.

Todo lo demás de la lista está resuelto o tiene una acción concreta y pequeña asociada.

---

## 1. Webhooks verificados y procesados una sola vez ✅

`api/stripe-webhook.js`:

- **Firma verificada** con `stripe.webhooks.constructEvent(body, sig, STRIPE_WEBHOOK_SECRET)`.
  Firma inválida → `400` y no se toca nada. Probado con el `whsec_` real: evento firmado
  correctamente → 200; firma mala → 400.
- **Cuerpo leído en crudo** (`bodyParser: false`), que es lo que exige la verificación de
  firma. Si se dejara parsear a Vercel, la firma nunca cuadraría.
- **Idempotencia**: antes de actuar se consulta `order_email_sent_at` por
  `stripe_session_id`. Si ya salió el correo, se responde 200 con `duplicado: true` y no se
  repite nada. Probado con el pedido `GRK-261022-IDEM`: entrega duplicada → no repite;
  reintento tras fallo → sí reintenta.

## 2. Protección frente a pagos duplicados ✅

Dos capas:

- La guarda de idempotencia anterior impide duplicar correos y estados.
- Cada checkout genera una **referencia nueva** (`GRK-AAMMDD-XXXX`) y su propia sesión de
  Stripe. No existe el camino por el que dos cobros queden ligados al mismo pedido.

Complemento: las sesiones abandonadas se expiran (ver §6) para que no queden cobros
colgando.

## 3. Confirmación del pago antes de crear el pedido ✅

El pedido se inserta en `create-checkout.js` con **`status: "pending"`**. Solo el webhook,
al recibir `checkout.session.completed` (que Stripe emite cuando el cobro es firme), lo
pasa a **`paid`**.

Es decir: la fila existe desde antes del pago —necesario para poder vincular la sesión—,
pero **nunca se trata como venta** hasta que Stripe confirma. Los correos, el aviso interno
y el filtro «pagados sin enviar al proveedor» del panel solo miran `paid`.

## 4. Reconciliación entre Stripe, Supabase y el proveedor ⚠️

El proveedor aquí es **AW Dropshipping**, no Printful/Printify, y **no tiene integración
API**: el pedido se pasa a mano desde el panel.

Lo que sí está atado:

- `stripe_session_id` se guarda al crear el pedido y es la clave que usa el webhook.
- `stripe_payment_intent` se guarda al confirmar el cobro, y es la clave que usa
  `charge.refunded`.
- El aviso interno de venta incluye un **bloque listo para copiar y pegar** en AW con
  destinatario, dirección, teléfono y artículos.

**Falta**: no hay comprobación automática de que el pedido exista en AW. Es inherente al
modelo manual. Mitigación disponible: el filtro del panel «pagados sin enviar al proveedor».

**Recomendación**: mientras el paso a AW sea manual, revisar ese filtro una vez al día.

## 5. Gestión de pedidos fallidos ✅

- Un fallo de correo **no pierde el pedido**: se guarda en Supabase igualmente.
- El error va a su propia columna `order_email_error` (no a `notes`, que puede llevar el
  comentario del cliente).
- El panel tiene el filtro **«Con email de pedido fallido»** y botón de reenvío.
- Red adicional: `create-checkout.js` manda `receipt_email`, así que **Stripe envía su
  propio recibo** aunque Resend falle por completo.

## 6. Reembolsos y cancelaciones ⚠️

- **Reembolsos** ✅: `charge.refunded` → `status: "refunded"`.
- **Abandono del pago** ✅ *(nuevo en esta tanda)*: añadido el handler de
  `checkout.session.expired`, que marca el pedido como `expired`. Antes no existía y los
  carritos abandonados se quedaban en `pending` para siempre, ensuciando el panel.
  Lleva guarda: un `.neq("status","paid")` para que un evento fuera de orden nunca degrade
  una venta real.

> ⚠️ **Acción necesaria en Stripe**: el handler no sirve de nada si el webhook no tiene
> activado el evento. Hay que añadir **`checkout.session.expired`** a la lista de eventos
> del endpoint `we_1URVX35u1hLzWyIGYIjzIbo9` en el panel de Stripe. Rotar el secreto no
> hace falta: cambiar solo la lista de eventos no invalida `STRIPE_WEBHOOK_SECRET`.

## 7. Control de variantes agotadas ❌ (riesgo aceptado)

No hay control de stock. El catálogo es un volcado del feed de AW y **AW es univariante**:
el «PVP» del feed ya es el precio final y no hay inventario que consultar por variante.

Consecuencia real: **se puede vender algo que AW ya no tiene**. Es un riesgo estructural
del dropshipping sin API de stock, no un fallo de implementación.

Mitigaciones posibles, por orden de esfuerzo:
1. Revisar el feed de AW periódicamente y retirar lo que desaparezca (ya lo hace
   `tools/build.py` al regenerar).
2. Añadir un campo de stock manual en `data/products.json` para las referencias críticas.
3. Pedir a AW acceso a su endpoint de disponibilidad, si lo ofrece.

## 8. Márgenes con IVA, Stripe, producción y envío ✅ *(corregido en esta tanda)*

**Antes el margen informado estaba mal**: el aviso interno calculaba
`venta sin IVA − coste proveedor` y lo llamaba beneficio, sin descontar la comisión de
Stripe ni el embalaje. Sobre un pedido de 58,80 € informaba **11,22 €** cuando quedan
**9,49 €**.

Ahora `api/_lib/emails.js` descuenta:

| Concepto | Valor | Origen |
|---|---|---|
| Venta sin IVA | `subtotal − vat_included` | pedido |
| − Coste proveedor | por SKU | `prices.json → costs` |
| = **Beneficio bruto** | | |
| − Comisión Stripe | `1,5 % + 0,25 €` **sobre el total cargado** | `prices.json → meta` |
| − Embalaje | `0,60 €` por pedido | `prices.json → meta` |
| = **Beneficio neto estimado** | | |

Detalle importante: la comisión se calcula **sobre el total cobrado** (IVA y envío
incluidos), no sobre la base, porque así es como la cobra Stripe. Calcularla sobre la base
la subestimaría.

Verificado con pedido de prueba: bruto 11,22 − Stripe 1,13 − embalaje 0,60 = **neto 9,49**,
y las tres cifras aparecen en el correo. El asunto ahora dice `neto 9,49 €`.

**Lo que el neto todavía NO descuenta** (y el correo lo declara explícitamente para que no
lleve a error):

- El **coste real del envío cuando sale gratis** (lo asume la tienda).
- Las **devoluciones** (`returns_rate 3 %`, `returns_cost 8,00 €` están en `meta` pero no
  se aplican al vuelo).

Es decir: es lo que queda del producto, no la caja final del mes. Para la cuenta de
resultados real hay que sumar esos dos conceptos.

## 9. Backups de Supabase ⚠️ no verificado

No he podido comprobarlo: hace falta el token de la Management API de Supabase.

**Cómo comprobarlo tú en 1 minuto**: panel de Supabase → proyecto `ravvjwyjaxofidgueopc` →
**Database** → **Backups**. Ahí se ve si están activos y la retención.

Ojo: el plan **Free no incluye backups automáticos diarios** (solo PITR en planes de pago).
Si estás en Free, las opciones son:

- `pg_dump` manual periódico (te puedo dejar un script).
- Activar PITR si decides pasar a Pro.

**Contexto que reduce el riesgo**: hoy las cuatro tablas están a 0 filas y los formularios
ya no escriben en Supabase (ver §12). Lo único crítico que se guarda son los pedidos.
Perder la base antes de la primera venta duele poco; después, mucho. Conviene resolverlo
**antes** de empezar a vender.

## 10. RLS correctamente configurado ⚠️

`supabase/schema.sql` activa RLS en las cuatro tablas:

```sql
alter table public.orders           enable row level security;
alter table public.order_items      enable row level security;
alter table public.subscribers      enable row level security;
alter table public.contact_messages enable row level security;
```

Y **no hay ninguna política de SELECT para `anon`**, así que el acceso de lectura público
queda denegado por defecto. Correcto.

> ⚠️ **Queda una política huérfana que conviene quitar**:
>
> ```sql
> create policy "subscribers_insert_public"
>   on public.subscribers for insert to anon with check (true);
> ```
>
> Permitía que **cualquiera, sin autenticar, insertara filas en `subscribers`**. Existía
> porque la newsletter escribía directamente desde el navegador. Ahora la newsletter va por
> el servidor, así que esa política ya no la usa nada y solo deja una puerta abierta a que
> alguien llene la tabla de basura.
>
> **Acción**: `drop policy "subscribers_insert_public" on public.subscribers;`
> Necesito el token de Supabase para ejecutarlo, o lo lanzas tú desde el SQL Editor.

## 11. Claves de API solo en backend ✅

**Dónde está cada clave:**

| Clave | Dónde vive | ¿Llega al navegador? |
|---|---|---|
| `STRIPE_SECRET_KEY` (`rk_live_…`) | Variable de entorno de Vercel, cifrada | **No** |
| `STRIPE_WEBHOOK_SECRET` (`whsec_…`) | Variable de entorno de Vercel | **No** |
| `SUPABASE_SERVICE_ROLE_KEY` | Variable de entorno de Vercel | **No** |
| `RESEND_API_KEY` | Variable de entorno de Vercel | **No** |
| `ADMIN_TOKEN` (`grk_…`) | Variable de entorno de Vercel | **No** |
| Clave publishable de Supabase | — | **Ya no** (ver abajo) |

Son **13 variables** en Vercel → proyecto `grankha` → Settings → Environment Variables.
Solo las lee el runtime de las funciones en `api/`; nunca se interpolan en el HTML.

**Mejora hecha en esta tanda**: la clave publishable de Supabase (`sb_publishable_…`) y la
URL del proyecto **viajaban incrustadas en las 86 páginas**, dentro de
`window.GRANKHA_CONFIG`, porque la newsletter escribía en la base de datos desde el
navegador. Al mover la newsletter al servidor se ha eliminado esa clave del HTML público.
Verificado: `grep` de `sb_publishable` y `supabase.co` sobre las 86 páginas y `app.js` →
**0 apariciones**.

Era una clave *publishable* (diseñada para ser pública y protegida por RLS), así que no era
una fuga grave, pero ya no está.

**Protección específica de Stripe:**

- La clave secreta solo se usa dentro de `api/create-checkout.js` y `api/stripe-webhook.js`,
  que se ejecutan en el servidor de Vercel.
- **Los precios no vienen del navegador**: `create-checkout.js` recalcula todo contra
  `api/_lib/prices.json`, que se sirve desde el bundle de la función. Un cliente puede
  mandar el precio que quiera en el POST; se ignora. Verificado en el código:
  `const official = PRICES[sku]` y `official.price` es lo que va a Stripe.
- `api/_lib/` **no es accesible por HTTP**: comprobado en producción, devuelve 404.
- El fichero `prices.json` **no está bajo `data/`** (que se excluye del despliegue): vive en
  `api/_lib/`, dentro del bundle de la función, y Vercel no sirve los ficheros de `api/`
  como estáticos.

**Barrido de secretos en el repositorio** (8 patrones: `whsec_`, `re_`, `vcp_`, `ghp_`,
`rk_live_`, `sbp_`, `grk_`, JWT): **0 claves reales**. Las 3 apariciones de `whsec_` son
placeholders de documentación.

## 12. Límites de uso y logs ⚠️

**Límites** *(añadidos en esta tanda)*: `api/_lib/ratelimit.js`, ventana de 10 minutos por IP.

| Endpoint | Límite | Motivo |
|---|---|---|
| `/api/contact` | 4 | spam de formulario |
| `/api/newsletter` | 6 | altas masivas |
| `/api/create-checkout` | 15 | sondeo de catálogo y basura en el panel |

Superado → `429`. Probado: 4 envíos correctos y el 5º → 429.

**Limitación honesta**: el conteo vive en memoria de la instancia serverless. Cada
instancia fría empieza de cero, así que **no es un límite global duro**. Corta el abuso
realista (un script machacando desde una IP), no un ataque distribuido. Para un límite real
haría falta Upstash o similar.

**Logs**: `console.log`/`console.error` en los cuatro endpoints críticos, con email
enmascarado (`pr***@gmail.com`).

> ⚠️ **Los logs no se pueden leer con este plan de Vercel**:
> `GET /v3/deployments/{id}/runtime-logs` devuelve siempre 0 líneas. Se ven en el panel web
> de Vercel → proyecto → **Deployments** → **Functions** → **Logs**, en tiempo real.

## 13. Emails transaccionales reales ⚠️

**Bloqueado por el DNS**, no por el código. Las tres plantillas están escritas, probadas y
**se entregaron de verdad** en su día (ids `01a16439-fbc9…`, `01a16439-fc9b…`,
`01a16439-fd44…`).

Estado actual:

| Correo | ¿Sale hoy? |
|---|---|
| Aviso de venta (a ti) | ✅ Sí, por el remitente de reserva `onboarding@resend.dev` |
| Confirmación al cliente | ❌ No. Resend responde `domain is not verified` |
| Envío con seguimiento | ❌ No. Igual |

**Causa**: los cuatro registros DNS de Resend se crearon en IONOS con `.grankha` de más en
el nombre de host. Los valores son correctos; solo hay que quitarles ese sufijo.
Diagnóstico y tabla de corrección en `ops/resend_dns_IONOS.md` §0.

Mientras tanto **ningún pedido se pierde**: se guarda, el fallo queda anotado y se reenvía
con un clic desde el panel en cuanto el dominio verifique.

## 14. Política de privacidad y tratamiento de datos ✅ *(actualizada en esta tanda)*

Al pasar los formularios a Google Forms había obligación de declararlo (art. 13 RGPD).
Hecho en `legal.html`:

- **Destinatarios**: se nombra a Google como proveedor técnico de gestión de formularios,
  junto a AW Dropshipping, transportista y Stripe. Con la regla de que cada uno recibe solo
  lo imprescindible y **no se venden datos a terceros**.
- **Transferencias internacionales** *(nuevo)*: se declara que Stripe y Google tratan datos
  fuera del EEE, con su base jurídica —Decisión de Adecuación UE–EE. UU. (Data Privacy
  Framework) y cláusulas contractuales tipo donde aplica—.
- **Se explica el diseño de los formularios**: el envío va siempre a esta web y es el
  servidor quien lo entrega; el navegador no contacta con terceros ni carga recursos de
  terceros al rellenarlos.
- **Cookies** *(actualizado)*: se declara la única cookie técnica que existe, la del área
  privada de gestión —`HttpOnly`, 8 h de vida, nunca se instala al visitar la tienda, y al
  no ser publicitaria ni de medición no requiere consentimiento—.

**Diseño de los formularios** (lo pediste explícitamente y se cumple): el navegador solo
habla con `/api/newsletter` y `/api/contact`. Quien contacta con Google es
`api/_lib/gforms.js`, en el servidor. Verificado: `grep` de `docs.google.com` y `googleapis`
sobre `app.js` y las 86 páginas → **0 apariciones**.

> ⚠️ **Dos efectos colaterales que debes conocer:**
>
> 1. **Las tablas `subscribers` y `contact_messages` dejan de alimentarse.** Los datos
>    ahora viven solo en tus Google Forms. Si quieres conservar también el registro en
>    Supabase, dímelo y lo añado como copia en el servidor.
> 2. **He dejado respuestas de prueba en tus dos formularios** mientras depuraba la
>    detección del acuse de recibo: unas **10 en NEWSLETTER** (todas
>    `prueba.tecnica.grankha@gmail.com`) y unas **7 en CONTACTO** (una de prueba real más
>    varias con nombre «Spam» y `s@example.com`). **Bórralas** para que no ensucien tus
>    listas.

## 15. Gestión de devoluciones conforme a tu mercado ✅

- **30 días** desde la recepción, frente a los 14 naturales legales. Publicado en
  `legal.html` §5 y en `envios.html#devoluciones`.
- **Garantía legal de 3 años** (RDL 1/2007), con reparación, sustitución, rebaja o
  reembolso a cargo de GRANKHA.
- **Interlocutor único**: `legal.html` deja por escrito que cualquier incidencia se gestiona
  con GRANKHA, nunca con el proveedor logístico. Es lo correcto siendo dropshipping: el
  vendedor legal eres tú.
- **Canarias, Ceuta y Melilla**: sin IVA, IGIC/IPSI y aduana a cargo del destinatario,
  declarado antes de la compra.
- **Resolución de conflictos**: Junta Arbitral de Consumo y plataforma ODR europea
  enlazadas, con la declaración honesta de no estar adheridos a ningún sistema arbitral.

## 16. Recibo automático de Stripe ✅

Ya estaba activo y se mantiene:

```js
payment_intent_data: {
  description: `GRANKHA ${reference}`,
  receipt_email: email,          // Stripe manda el recibo de pago al cliente
  metadata: { reference },
}
```

Con `receipt_email` en la sesión, Stripe envía su recibo al cliente **sin depender de
Resend**. Es una red de seguridad independiente: aunque el correo de confirmación falle,
el cliente recibe el recibo de pago de Stripe.

No hace falta tocar nada en el panel de Stripe para esto; `receipt_email` fuerza el envío.

---

## Bloqueos para lanzar

| # | Qué | Quién | Esfuerzo |
|---|---|---|---|
| 1 | **DNS de Resend**: quitar `.grankha` a los 4 nombres de host en IONOS | Tú | 5 min |
| 2 | **NIF y domicilio fiscal** → `data/site.json` y regenerar | Tú (dato) + yo | 5 min |
| 3 | **Desplegar** `16cd9dd` (necesito el token de Vercel) | Yo | 3 min |
| 4 | **Activar `checkout.session.expired`** en el webhook de Stripe | Tú o yo con la clave | 2 min |
| 5 | **Quitar la política `subscribers_insert_public`** | Yo con token de Supabase | 1 min |

Los puntos 1 y 2 son los únicos que impiden legal y funcionalmente vender. El resto son
mejoras que pueden ir justo después.

## Sobre el NIF: por qué importa más de lo que parece

Ahora mismo `legal.html` dice que los datos fiscales «se facilitan gratuitamente a cualquier
consumidor que los solicite». Es un parche razonable mientras se tramita el alta, pero el
**art. 10 de la LSSI-CE obliga a publicar** nombre, dirección y NIF del prestador de
servicios. Con la tienda abierta al público y cobrando, es el punto donde una reclamación o
una inspección tiene más recorrido.

En cuanto me pases NIF y domicilio los publico y regenero el sitio.

## Lo que NO hace falta tocar

Confirmado como correcto en esta revisión:

- Verificación de firma del webhook e idempotencia.
- Recálculo de precios en servidor (el cliente no puede manipular importes).
- Claves solo en backend; la publishable de Supabase ya fuera del HTML.
- Recibo automático de Stripe.
- Devoluciones y garantía por encima del mínimo legal.
- El panel no es una página pública: `/api/panel` sin credencial devuelve un 404 idéntico
  byte a byte al de cualquier ruta inexistente.

# Cómo dejar GRANKHA vendiendo HOY

Guía en orden. Los pasos 1-4 son obligatorios y llevan **~2 horas**. Los pasos 5-8
(correo automático, pedido automático al proveedor, analítica) se pueden hacer después:
la tienda ya vende sin ellos.

---

## Resumen del flujo completo de un pedido

```
1. El cliente entra en la web, llena la cesta y paga con tarjeta (Stripe)
        ↓
2. Stripe cobra y avisa a Supabase (webhook) → pedido marcado como PAGADO
        ↓
3. El pedido llega a AW Dropshipping (manual o con la función fulfill-order)
        ↓
4. El proveedor prepara, envía y devuelve un Nº DE SEGUIMIENTO
        ↓
5. Tú (o la función) guardas el tracking → el cliente recibe el email "en camino"
        ↓
6. Dinero de Stripe a tu banco (payouts automáticos)
```

Lo que hace falta para cada eslabón está abajo, con el detalle exacto.

---

## PASO 1 · Datos legales y de contacto (30 min) 🔴 OBLIGATORIO

Sin esto no puedes vender legalmente (LSSI art. 10). Necesito que me des:

| Dato | Ejemplo | Dónde va |
|---|---|---|
| Nombre completo o razón social | GRANKHA (ya puesto en la web) | Aviso legal, privacidad, facturas |
| NIF / CIF | 12345678Z ← **falta, dímelo** | Aviso legal |
| Domicilio fiscal | Calle X, 1, 3ºB, 28939 Arroyomolinos, Madrid ← **falta, dímelo** | Aviso legal |
| Teléfono de atención | +34 6XX XXX XXX ← **falta, dímelo** | Aviso legal, footer de la web |
| Email de la tienda | grankha@roadshop.online ✅ ya en todo el sitio | Todo el sitio |

**Alternativa**: si aún no tienes alta de autónomo, puedes empezar como particular sin
facturación empresarial, pero **es arriesgado**: Hacienda considerará la actividad
económica desde la primera venta. Lo recomendable: alta censal (modelo 037) + IAE
antes de la primera venta. Los recibos de Stripe + el registro de pedidos de la web
te dan todo lo necesario para facturar.

> ⚠️ Con los pagos electrónicos, los datos del titular (NIF, IBAN) deben coincidir con
> la actividad. Si vas a facturar, pide cita con un gestor antes de vender.

---

## PASO 2 · Stripe: cobrar de verdad (45 min) 🔴 OBLIGATORIO

1. **Crear cuenta** en [stripe.com](https://stripe.com) → verificar identidad, IBAN y (si eres
   autónomo) datos fiscales. Tarda de minutos a 1-2 días según la verificación.
2. **Copiar la clave secreta**: Developers → API keys → `sk_live_...`
3. **Desplegar las funciones** (5 min, ver `CONECTAR_STRIPE_SUPABASE.md`):
   ```bash
   supabase functions deploy create-checkout --no-verify-jwt
   supabase functions deploy stripe-webhook  --no-verify-jwt
   supabase secrets set STRIPE_SECRET_KEY=sk_live_xxx
   supabase secrets set SITE_URL=https://elexitodigital-eng.github.io/grankha
   ```
4. **Pegar la URL** de `create-checkout` en `data/site.json` → `checkout.endpoint`
5. **Webhook** en Stripe → Developers → Webhooks → `checkout.session.completed` + `charge.refunded`
   apuntando a la URL de `stripe-webhook`.
6. Regenerar y subir:
   ```bash
   python3 tools/build.py && git add -A && git commit -m "Activar Stripe" && git push
   ```
7. **Probar**: pedido real con tu tarjeta de 1 artículo barato → devuélvete el dinero desde Stripe.
8. **Activar Apple Pay / Google Pay**: en Stripe → Settings → Payment methods (un clic).

**Cuándo llega el dinero**: Stripe hace payouts automáticos a tu banco (normalmente 7 días
después del primer cobro, luego cada 2-3 días en España). El primer pago puede tardar más
mientras verifican la cuenta.

**Coste de Stripe**: 1,5 % + 0,25 € por tarjeta europea. En un pedido de 40 € son 0,85 €
(ya está calculado en la auditoría de precios).

---

## PASO 3 · Supabase: registro de pedidos (15 min) 🟡 MUY RECOMENDADO

Sin esto el pedido se guarda solo en el navegador del cliente y te llega por email. Con esto:
base de datos de pedidos, suscriptores, y las funciones de Stripe tienen dónde escribir.

1. Crear proyecto en [supabase.com](https://supabase.com) (gratis).
2. SQL Editor → pegar `supabase/schema.sql` → Run.
3. `supabase link --project-ref TU_REF` y desplegar las funciones del paso 2.

Consejo: activa también **Database → Backups** (gratis en plan free) y guarda la
contraseña de la base de datos en un gestor de contraseñas.

---

## PASO 4 · Cómo llega el producto al cliente (el dropshipping, bien explicado)

Aquí está la clave de tu pregunta: **tú no tocas el producto**, lo envía el proveedor
directamente a la dirección del cliente. Así funciona:

### 4.1 Tarifas de envío del proveedor ✅ VERIFICADO

Consultado en la web pública de AW Dropship España (aw-dropship.es/shipping) el 15/10/2026.
**Importes sin IVA** (el IVA soportado es deducible) y **por pedido completo**, según su peso:

| Zona | Destino | 0-1 kg | 1-5 kg | +5 kg | Plazo |
|---|---|---|---|---|---|
| 1 | España península y Baleares | **2,95 €** | **4,00 €** | 6,50 € | 1-3 días laborables |
| 2 | Portugal continental | 3,50 € | 4,50 € | 10,50 € | 2-4 días laborables |
| 3 | Francia, Alemania, Austria, Bélgica, Italia, Luxemburgo, Países Bajos | 6,95 € | 7,95 € | 10,50 € | 4-5 días |
| 4 | Chequia, Dinamarca, Polonia, Eslovenia, Eslovaquia | 8,15 € | 12,15 € | 18,65 € | 4-6 días |
| 5 | Bulgaria, Estonia, Finlandia, Croacia, Hungría, Irlanda, Lituania, Serbia, Rumanía, Suecia | 16,45 € | 27,90 € | — | 6-7 días |

Qué significa para ti:

- Un pedido normal (arnés, correa, comedero, fuente) pesa **menos de 1 kg** → el envío te cuesta **2,95 €**.
- Los packs y las camas pueden pasar de 1 kg → **4,00 €**. Nada de tu catálogo llega a 5 kg.
- Lo que cobramos al cliente (5,95 € / 3,95 € / gratis desde 39 €) **cubre de sobra** el coste real, y en los
  pedidos pequeños incluso deja margen.
- El peso de cada artículo es el real del feed de AW (peso de paquete) + 100 g de caja por pedido. Está todo
  en `docs/GRANKHA_Beneficio_Real_Por_Producto.xlsx`.
- Canarias, Ceuta y Melilla: AW las sirve **sin IVA y con aduana a cargo del destinatario**, y su tarifa no está
  publicada. Los 14,95 € que cobramos pueden quedarse cortos: pregunta el precio exacto en tu panel antes de
  vender a esas zonas (o desactívalas en el checkout).

### 4.2 Cómo se tramita cada pedido

**Opción A · Manual (los primeros 10-20 pedidos, 5 min por pedido)**

1. Recibes un email con el pedido (o lo ves en Supabase → Table Editor → `orders`).
2. En el panel de AW Dropshipping → **crear pedido**: pega la dirección del cliente y añade
   los SKU con sus cantidades (la referencia de tu pedido es GRK-XXXXXX-XXXX).
   - Los **packs** se piden por sus piezas (en la ficha de cada pack tienes la lista exacta:
     por ejemplo, Pack Primeros Días Gato = PAWFB-08 ×1 + PAWFB-09 ×1 + PAWFB-07 ×1).
3. Marca el pedido como enviado (submit). El proveedor lo prepara y lo despacha.
4. Cuando te devuelven el **Nº de seguimiento**, se lo envías al cliente con la plantilla
   `docs/emails/2-pedido-enviado.html`.
5. Actualizas el pedido en Supabase:
   ```sql
   update orders set tracking_code='XXXX', tracking_url='https://...', shipped_at=now()
   where reference='GRK-XXXXXX-XXXX';
   ```

**Opción B · Automática (cuando vendas >2-3 pedidos/día)**

Ya tienes escrita la función `supabase/functions/fulfill-order`. Hace los pasos 2-3 sola:
crea el cliente en el proveedor, monta el pedido con los SKU (descompone los packs en
piezas) y lo envía al almacén. Se activa así:

```bash
supabase functions deploy fulfill-order --no-verify-jwt
supabase secrets set AIKU_TOKEN='690|tu_token_del_canal'   # el token NO va al repositorio
# prueba en seco, sin crear nada:
curl -X POST "https://TU_REF.functions.supabase.co/fulfill-order?dry_run=1" -d '{}'
```
Revisa la respuesta del dry-run y, si es correcta, lánzala sin `dry_run`. Si el proveedor
cambia algún nombre de campo, el error te lo dirá con detalle (la función devuelve el texto
exacto de la API) y se ajusta en 1 minuto.

> **Importante**: el proveedor debe poder enviar a la dirección del cliente sin incluir
> factura con tus precios. Confírmalo en AW (opción "envío como regalo" o "sin factura").

### 4.3 Seguimiento: lo que ve el cliente

| Momento | Email | Plantilla |
|---|---|---|
| Pago confirmado | "Gracias, {{name}}" + pedido y total | `docs/emails/1-pedido-recibido.html` |
| Envío despachado | Nº de seguimiento + enlace + fecha estimada | `docs/emails/2-pedido-enviado.html` |
| Consulta del cliente | Respuesta rápida con tracking | `docs/emails/3-seguimiento-cliente.html` |

Ya está explicado en la web: `envios.html` tiene la sección **"Seguimiento del pedido"**
donde se cuenta exactamente este proceso (y se pide la referencia GRK- para atender más rápido).

**Enviar esos emails sin pagar nada**:
- **Opción simple**: Gmail con respuestas guardadas (plantillas de arriba). Suficiente hasta
  ~20 pedidos/día.
- **Opción automática**: [Brevo](https://brevo.com) o [Resend](https://resend.com) (plan gratis
  300 emails/día / 3.000 al mes). Se conecta con Supabase: al actualizar `tracking_code`, un
  trigger envía el email. Puedo prepararlo cuando quieras: dime si prefieres Brevo o Resend
  y lo dejo configurado con tus plantillas.

---

## PASO 4-bis · Cómo le llegan los correos al cliente (explicado sin tecnicismos)

Un cliente compra y tiene que recibir **dos correos**. Ninguno se escribe a mano si no quieres:

**Correo 1 · «Pedido recibido»** — con el resumen de la compra, la dirección de envío y el total.

- **Automático (con Stripe):** el cliente paga en la web → Stripe avisa al webhook (`stripe-webhook`) → ese
  webhook marca el pedido como pagado y llama a `_shared/email.ts`, que envía el correo con todos los datos.
  Tú no tocas nada; llega en segundos.
- **Manual (hoy, sin Stripe):** el pedido te llega al email de la tienda → abres
  `docs/emails/1-pedido-recibido.html`, rellenas los huecos (referencia, líneas, total, dirección) y lo envías
  desde tu correo. Dos minutos.

**Correo 2 · «Tu pedido va de camino»** — con el **número de seguimiento** y un botón para ver dónde está.

- El seguimiento lo genera AW cuando expide el paquete (normalmente 1-2 días laborables después).
- **Automático:** la función `notify-tracking` pregunta a AW por los pedidos pagados que aún no tienen aviso
  enviado y, en cuanto aparece el número, manda el correo. Se puede programar para que se ejecute solo cada
  30 minutos (pg_cron). Ese correo lleva el número y un botón que abre el seguimiento
  (`17track.net` si no tenemos la URL directa de la agencia).
- **Manual:** cuando AW te dé el número, lanza una sola orden y el correo sale solo:
  ```bash
  curl -X POST https://<proyecto>.functions.supabase.co/notify-tracking \
    -H "Content-Type: application/json" \
    -d '{"reference":"GRK-261015-4E7O","tracking_code":"PQ123456789ES"}'
  ```
  O si prefieres enviarlo desde tu correo: `docs/emails/2-pedido-enviado.html`.

**Qué hay que configurar una sola vez** (5 minutos, y elige proveedor):

```bash
supabase functions deploy notify-tracking --no-verify-jwt
supabase secrets set EMAIL_PROVIDER=brevo BREVO_API_KEY=xkeysib-... EMAIL_FROM="GRANKHA <grankha@roadshop.online>"
# o, si prefieres Resend:
supabase secrets set EMAIL_PROVIDER=resend RESEND_API_KEY=re_... EMAIL_FROM="GRANKHA <grankha@roadshop.online>"
```

Si aún no hay claves, las funciones **no fallan**: escriben el correo en el log (modo simulación), así que puedes
probar el flujo entero antes de decidir. Diferencia rápida: **Brevo** tiene plan gratis de 300 correos/día y
factura española; **Resend** es más cómodo de configurar pero 100/día y sin factura española. Para tu volumen,
cualquiera de los dos sobra.

## PASO 5 · Poner los datos legales en la web (5 min)

Con lo del paso 1, sustituyo los `[ ]` de `legal.html`. También hay que:

- [ ] Añadir el teléfono al footer (opcional, pero sube confianza).
- [ ] Enlazar tu Instagram/TikTok en el footer (cuando existan).
- [ ] Si vendes con factura: añadir mención al sistema de facturación en las condiciones.

---

## PASO 6 · Prueba de compra completa (20 min) 🔴 ANTES DE ABRIR

Con Stripe en modo test (`sk_test_...`) o con un pedido real de 1 artículo:

1. Añade al carrito un producto y un pack.
2. Paga con `4242 4242 4242 4242` (test) o con tu tarjeta (real).
3. Comprueba: pedido en Supabase (estado `pending` → `paid` al webhook), email de Stripe,
   pedido creado en AW Dropshipping.
4. **Devuelve el dinero** desde Stripe → Payments → Refund.
5. Repite el pedido pero esta vez desde el móvil.

---

## PASO 7 · Lo que hay que confirmar sí o sí (contesta estas 4 y lo dejo listo)

1. **Tarifa real de envío del proveedor** a España peninsular (y si cobra más por peso).
2. **Plazos reales** de preparación y entrega del proveedor (¿3-8 días es correcto?).
3. **Datos legales** del paso 1 (nombre, NIF, dirección, teléfono).
4. **Email de la tienda** definitivo (¿gmail o uno con dominio?).

Con esas cuatro respuestas, la tienda queda lista para vender hoy mismo.

---

## Extras recomendados (no bloquean la venta)

- **Dominio propio**: ya en marcha en `grankha.roadshop.online`. Se configura en 5 minutos:
  repositorio → Settings → Pages → Custom domain (+ CNAME en el registrador).
  Una URL propia transmite más confianza que `github.io`.
- **Google Search Console**: dar de alta el dominio y enviar `sitemap.xml`.
- **Google Merchant Center**: subir el feed de productos (los datos estructurados ya están
  puestos) para aparecer en Shopping con precio y envío.
- **Instagram/TikTok** con el nombre de marca reservado desde el primer día.
- **Analítica sin cookies**: [Plausible](https://plausible.io) o Cloudflare Web Analytics
  (5 min). Si se añade píxel de Meta/TikTok, hay que actualizar la política de cookies y
  pedir consentimiento.

---

## Día a día (rutina de operación)

| Frecuencia | Tarea | Tiempo |
|---|---|---|
| Cada pedido | Tramitar el pedido al proveedor + enviar tracking | 5 min |
| 2 veces/semana | Revisar stock del catálogo (`tools/feed_sync.py` + `catalog.py` + `build.py`) | 5 min |
| Semanal | Comprobar devoluciones y reembolsos en Stripe | 5 min |
| Mensual | Revisar ventas (`select * from v_sales_daily`), margen real y fondo de donación | 15 min |
| Trimestral | IVA (modelo 303) con los recibos de Stripe + pedidos registrados | con el gestor |
| Anual | Resumen de donaciones a publicar + memoria del proyecto apoyado | 2 h |

**Actualizar precios o añadir productos**: se editan en `data/pricing.json`, se ejecuta
`python3 tools/pricing.py && python3 tools/catalog.py --raw data/raw && python3 tools/build.py`
y se sube. La auditoría se recalcula sola.

---

## Preguntas que suelen surgir

**¿Y si el proveedor no tiene stock?** El catálogo ya muestra el stock real del feed
(se actualiza con `feed_sync.py`). Si un producto se agota, la web lo sigue mostrando hasta
que regeneres; conviene revisar stock 2 veces por semana.

**¿Quién tiene la culpa si el producto llega roto?** Tú ante el cliente (garantía legal de 3
años). Ante el proveedor, reclamas tú. Por eso insiste en que el embalaje sea correcto y
guarda siempre el número de pedido del proveedor.

**¿Puedo vender a Canarias/Melilla?** Sí, con aviso de IGIC/IPSI en destino. Está en la web.

**¿Hace falta aviso de cookies?** No con la configuración actual: la web no usa cookies
(solo almacenamiento local propio). Si añades analítica con cookies o píxeles, sí.

**¿Necesito RGSEAA (registro sanitario)?** Para comederos y bebederos **no** (no son
alimentos). Si algún día vendes pienso, snacks o suplementos, sí.

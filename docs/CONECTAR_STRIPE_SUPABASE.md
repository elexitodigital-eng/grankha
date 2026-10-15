# Conectar Stripe y Supabase (20-30 minutos)

El código ya está escrito y probado. Solo hay que crear las cuentas y pegar dos valores.

---

## Paso 1 · Supabase (base de datos)

1. Entra en [supabase.com](https://supabase.com) → **New project** (plan gratuito suficiente).
   Guarda la contraseña de la base de datos que te genere.
2. Abre **SQL Editor** → pega todo el contenido de `supabase/schema.sql` → **Run**.
   Se crean las tablas `orders`, `order_items`, `subscribers`, `contact_messages` y las
   vistas de ventas y de fondo de donación.
3. Instala la CLI en tu ordenador:
   ```bash
   npm install -g supabase
   ```
4. Enlaza tu proyecto (Project Settings → API → copia `project-ref`):
   ```bash
   supabase login
   supabase link --project-ref <TU_PROJECT_REF>
   ```

## Paso 2 · Stripe (pagos)

1. Crea la cuenta en [stripe.com](https://stripe.com) y activa los cobros
   (datos fiscales + IBAN).
2. Copia la clave secreta: **Developers → API keys → Secret key** (`sk_live_...`).
   Para probar sin cobrar usa la `sk_test_...`.

## Paso 3 · Desplegar las funciones

```bash
cd grankha

# secretos
supabase secrets set STRIPE_SECRET_KEY=sk_live_xxxxxxxx
supabase secrets set SITE_URL=https://elexitodigital-eng.github.io/grankha

# funciones
supabase functions deploy create-checkout --no-verify-jwt
supabase functions deploy stripe-webhook  --no-verify-jwt
supabase functions deploy fulfill-order   --no-verify-jwt   # crea el pedido en AW Dropshipping
```

> `create-checkout` usa `prices.json` (se regenera con `tools/build.py`) para recalcular los
> importes en servidor: nadie puede manipular precios ni el envío cobrado desde el navegador.
> También calcula la donación (5 % del beneficio real del pedido) y la guarda.

Al terminar, la CLI imprime la URL de cada función, del estilo
`https://abcdefgh.functions.supabase.co/create-checkout`.

## Paso 4 · Webhook de Stripe (confirmar pagos)

1. Stripe → **Developers → Webhooks → Add endpoint**.
2. URL: `https://abcdefgh.functions.supabase.co/stripe-webhook`
3. Eventos: `checkout.session.completed` y `charge.refunded`.
4. Copia el **Signing secret** (`whsec_...`) y guárdalo:
   ```bash
   supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxx
   supabase functions deploy stripe-webhook --no-verify-jwt
   ```

## Paso 5 · Activar la pasarela en la web

Edita `data/site.json`:

```json
"checkout": {
  "endpoint": "https://abcdefgh.functions.supabase.co/create-checkout"
}
```

Regenera y sube:

```bash
python3 tools/build.py
git add -A && git commit -m "Activar pago con Stripe" && git push
```

A partir de ese momento, «Confirmar pedido» crea la sesión de Stripe, guarda el pedido en
Supabase y redirige al cliente a la pasarela segura (tarjeta, Apple Pay, Google Pay).
El webhook marca el pedido como `paid` automáticamente.

---

## Cómo comprobar que funciona

1. Haz un pedido de prueba con la tarjeta de test `4242 4242 4242 4242` (fecha futura, CVC cualquiera).
2. En Supabase → Table Editor → `orders`: debe aparecer el pedido en `pending`.
3. Al completar el pago, el webhook lo pasa a `paid` y rellena `stripe_payment_intent`.
4. En Stripe → Payments verás el cobro y la comisión real, para contrastar con el Excel
   `docs/GRANKHA_Margenes_IVA_Envios.xlsx`.

## Ver tus ventas y el fondo de donación

En Supabase, SQL Editor:

```sql
select * from v_sales_daily;      -- ventas por día
select * from v_donation_fund;    -- importe reservado para investigación por mes
```

## Pasar pedidos al proveedor (AW Dropshipping)

**Manual**: crea el pedido en el panel de AW con los SKU del pedido (los packs se piden por
sus piezas; la ficha de cada pack en la web indica cuáles) y marca enviado.

**Automático**: la función `fulfill-order` lo hace sola.

```bash
supabase secrets set AIKU_TOKEN='690|tu_token_del_canal'   # nunca en el repositorio
supabase secrets set AIKU_API=https://api.aiku.io          # staging: https://api.aiku-sandbox.uk

# prueba en seco (no crea nada, solo valida el pedido)
curl -X POST "https://TU_REF.functions.supabase.co/fulfill-order?dry_run=1" -H 'Content-Type: application/json' -d '{}'

# ejecución real de los pedidos pagados pendientes
curl -X POST "https://TU_REF.functions.supabase.co/fulfill-order" -H 'Content-Type: application/json' -d '{}'
```

Los pedidos ya traen referencia, SKU, cantidades, dirección completa y método de envío.
Cuando el proveedor despache, guarda el tracking:

```sql
update orders set tracking_code='XXXX', tracking_url='https://...', shipped_at=now()
where reference='GRK-XXXXXX-XXXX';
```

y envía al cliente la plantilla `docs/emails/2-pedido-enviado.html`.

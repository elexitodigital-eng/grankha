# GRANKHA · Qué queda por hacer

La tienda está **completa y publicada**: catálogo real, fichas, carrito, checkout, envíos,
IVA, páginas legales y SEO. Estos son los únicos puntos que dependen de datos o cuentas
que solo tú puedes proporcionar.

---

## 1. Datos legales obligatorios (antes de vender) 🔴

Ahora mismo `legal.html` tiene marcadores `[ ]`. **No vendas sin completarlos**: la LSSI
obliga a publicar la identidad del titular.

| Dato | Dónde se usa | Qué necesito |
|---|---|---|
| Razón social o nombre completo | `legal.html` (aviso legal, privacidad) | Ej. «ZENQA LIFE S.L.» o «Jorge X Y» |
| NIF / CIF | `legal.html` | — |
| Domicilio fiscal completo | `legal.html` | Calle, nº, CP, localidad, Madrid |
| Teléfono de contacto | `legal.html`, footer | El de atención al cliente |
| Email de la tienda | Todo el sitio | Ahora: `zenqalife@gmail.com` (¿creamos uno tipo `hola@grankha.com`?) |

> Con esos datos me lo dices y los sustituyo en 2 minutos (o los editas en `tools/build.py`
> y vuelves a generar el sitio).

**Recomendación**: si vas a facturar como autónomo, revisa también el alta en el censo de
actividades (IAE) y si necesitas RGSEAA / registro sanitario para los comederos y fuentes.

---

## 2. Pagos con Stripe 🟡 (todo preparado)

Ya está escrito el código, solo falta tu cuenta:

1. Crear cuenta en [stripe.com](https://stripe.com) y verificar identidad/IBAN.
2. Desplegar las funciones incluidas en `supabase/functions/` (ver
   [CONECTAR_STRIPE_SUPABASE.md](CONECTAR_STRIPE_SUPABASE.md)).
3. Pegar la URL de la función en `data/site.json`:
   ```json
   "checkout": { "endpoint": "https://<proyecto>.functions.supabase.co/create-checkout" }
   ```
4. Ejecutar `python3 tools/build.py` y subir los cambios.

Mientras el endpoint esté vacío, el checkout funciona igual: guarda el pedido en el
navegador y te ofrece **confirmar por email** con todo el desglose (referencia, artículos,
IVA, envío y total). Es un modo «válido» para las primeras ventas.

---

## 3. Supabase (opcional pero recomendado) 🟡

Sirve para guardar pedidos, suscriptores y mensajes de contacto, y ver tus KPIs.

1. Crear proyecto en [supabase.com](https://supabase.com) (plan gratuito).
2. Ejecutar `supabase/schema.sql` en el SQL Editor → crea `orders`, `order_items`,
   `subscribers`, `contact_messages`, vistas de ventas y política RLS.
3. Desplegar las funciones (`create-checkout`, `stripe-webhook`).
4. Newsletter: ahora guarda los emails en el navegador del visitante. Para guardarlos de
   verdad, activa el endpoint en `data/site.json` → `newsletter.endpoint`.

Sin Supabase, la web funciona al 100 %; solo pierdes el registro centralizado de pedidos.

---

## 4. Marketing y operación (recomendado)

- [ ] Sustituir las imágenes de marca (`assets/img/hero.jpg`, `memorial.jpg`) por fotos
      propias si algún día las tienes. Las actuales son generadas y encajan con la estética.
- [ ] Instagram / TikTok de la marca y enlazarlos en el footer.
- [ ] Google Search Console: `https://elexitodigital-eng.github.io/grankha/sitemap.xml`.
- [ ] Google Merchant Center (Shopping): los datos estructurados ya están puestos.
- [ ] Píxel de Meta / TikTok solo si haces publicidad (requiere actualizar la política de
      cookies y añadir consentimiento).
- [ ] Textos de reseñas: cuando tengas las primeras, añadimos un bloque en las fichas
      (con schema `AggregateRating`).

---

## 5. Decisiones que dependen de tus números

- [ ] **Envío gratis a partir de 49 €**: está puesto en el sitio. Ajusta el umbral en
      `data/site.json` según lo que veas en `docs/GRANKHA_Margenes_IVA_Envios.xlsx`.
- [ ] **Precios**: mantengo el PVP que has fijado (el 100 % sobre coste del proveedor).
      Ojo: en pedidos de 1 unidad de artículos baratos el margen real es bajo (~12 %)
      porque el envío del proveedor y la comisión fija se comen el beneficio. Recomendado
      empujar packs (arnés + correa) y el umbral de envío gratis.
- [ ] **% destinado a investigación**: he puesto 5 % del beneficio como reserva en el
      simulador y en la base de datos. Confírmame el porcentaje real y lo ajusto.
- [ ] Canarias/Ceuta/Melilla: revisar con el proveedor si el envío incluye aduanas.

---

## 6. Mejoras que puedo construir cuando quieras

- Guía de tallas interactiva para arneses (con medida de contorno en cm).
- Packs «arnés + correa» con descuento automático.
- Cuentas de cliente y seguimiento de pedidos (Supabase Auth).
- Sistema de reseñas con fotos.
- Blog / revista con contenido SEO («cómo elegir un arnés», «señales de dolor en perros»).
- Programa de donación visible: contador de importe donado con datos reales de Supabase.

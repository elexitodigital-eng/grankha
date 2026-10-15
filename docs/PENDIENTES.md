# GRANKHA · Qué queda por hacer

> Para el plan de puesta en marcha paso a paso, usa **COMO_VENDER_YA.md**. Este archivo es la lista de pendientes técnicos.

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

- [ ] Sustituir la foto de `assets/img/khalid.jpg` por **una foto real de khalid** cuando la tengas
      (mantén el formato cuadrado y el blanco y negro para que encaje). El resto de imágenes
      generadas (hero con perro y gato) están listas para producción.
- [ ] Instagram / TikTok de la marca y enlazarlos en el footer.
- [ ] Google Search Console: `https://elexitodigital-eng.github.io/grankha/sitemap.xml`.
- [ ] Google Merchant Center (Shopping): los datos estructurados ya están puestos.
- [ ] Píxel de Meta / TikTok solo si haces publicidad (requiere actualizar la política de
      cookies y añadir consentimiento).
- [ ] Textos de reseñas: cuando tengas las primeras, añadimos un bloque en las fichas
      (con schema `AggregateRating`).

---

## 5. Decisiones que dependen de tus números

- [x] **Envío gratis desde 39 €** con tramos (20 € → 3,95 €; mínimo → 5,95 €). Configurado en
      `data/site.json` → `shipping.options[].tiers`. Si la tarifa real del proveedor sube,
      ajustar aquí y regenerar.
- [x] **Precios auditados** contra el mercado (octubre 2026): 8 referencias subidas, 11 ajustadas
      a la baja, 19 validadas. Detalle por producto en `docs/GRANKHA_Auditoria_Precios.xlsx`.
- [x] **Donación 5 %** de los beneficios, reservada pedido a pedido (Supabase `orders.donation`).
- [x] **6 packs** con 5,8-9 % de descuento y contribución de 10-30 € por pedido.
- [ ] **Tarifa real de envío del proveedor** (estimada en 4,95 € + 1,10 €/kg): confirmar en el panel.
- [ ] **Plazos reales** de preparación y entrega del proveedor (la web muestra 3-8 días).
- [ ] Canarias/Ceuta/Melilla: revisar con el proveedor si el envío incluye aduanas.

---

## 6. Mejoras que puedo construir cuando quieras

- Guía de tallas interactiva para arneses (con medida de contorno en cm).
- Packs «arnés + correa» con descuento automático.
- Cuentas de cliente y seguimiento de pedidos (Supabase Auth).
- Sistema de reseñas con fotos.
- Blog / revista con contenido SEO («cómo elegir un arnés», «señales de dolor en perros»).
- Programa de donación visible: contador de importe donado con datos reales de Supabase.

---

## Corregido en la revisión del 15/10/2026 (bloque 0 de la auditoría)

- ✅ El carrito se vacía al confirmar el pedido (ya no se pueden duplicar).
- ✅ El país del formulario manda sobre la zona de envío (Portugal 6,95 € · UE 13,95 €).
- ✅ Canarias, Ceuta y Melilla sin IVA, con aviso de IGIC/IPSI y aduana en destino.
- ✅ Newsletter con casilla de consentimiento (y envío a Supabase cuando exista el proyecto).
- ✅ Contraste del gris secundario corregido a 5,2:1 (WCAG AA).
- ✅ CSS y JS como archivos externos y fotos sin base64: las páginas pesan entre un 77 % y un 91 % menos.
- ✅ 108 imágenes antiguas sin uso eliminadas (3,2 MB).
- ✅ Enlace a la plataforma europea de resolución de litigios en la página legal.

Sigue pendiente de ti: datos fiscales (razón social, NIF, domicilio, teléfono), email definitivo
de la tienda, elección Brevo/Resend y confirmar la tarifa de Canarias con AW.

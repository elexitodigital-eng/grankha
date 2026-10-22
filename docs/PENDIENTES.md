# GRANKHA · Qué queda por hacer

> Para el estado real y comprobado de hoy, usa **LANZAMIENTO.md**. Este archivo es la lista de pendientes.

La tienda está **completa, publicada y cobrando** en **https://grankha.roadshop.online**:
catálogo real, fichas, carrito, checkout con Stripe, pedidos en Supabase, envíos, IVA,
páginas legales con los datos de la empresa y SEO apuntando al dominio definitivo.

---

## 1. Datos legales 🔴 casi cerrados

Publicados ya: titular **GRANKHA**, email **grankha@roadshop.online**, web, actividad y
modelo de envío (**dropshipping con AW Dropshipping**).

| Dato | Estado | Dónde se pone |
|---|---|---|
| Titular / nombre de la empresa | ✅ GRANKHA | `data/site.json` → `legal.titular` |
| Email de la tienda | ✅ `grankha@roadshop.online` | `data/site.json` → `contactEmail` |
| Modelo de envío y proveedor | ✅ AW Dropshipping (dropshipping) | `data/site.json` → `legal.fulfillment` |
| **NIF / CIF** | ⬜ pendiente | `data/site.json` → `legal.nif` |
| **Domicilio fiscal** | ⬜ pendiente | `data/site.json` → `legal.domicilio` |
| Teléfono de atención | ⬜ opcional | `tools/build.py` (aviso legal y contacto) |

> NIF y domicilio se pintan **solos** en `legal.html` en cuanto tengan valor. Mientras estén
> vacíos, la web ofrece el dato a petición del consumidor por correo (párrafo automático).
> Tras rellenarlos: `python3 tools/build.py` y desplegar.

**Recomendación**: si vas a facturar como autónomo, revisa también el alta en el censo de
actividades (IAE) y si necesitas RGSEAA / registro sanitario para los comederos y fuentes.

---

## 2. Pagos con Stripe ✅ hecho

Cuenta real activa (`acct_1URVBw5u1hLzWyIG`, ES, EUR, cobros y pagos habilitados, sin
requisitos pendientes). Checkout probado de punta a punta en el dominio definitivo.
Webhook `we_1URVX35u1hLzWyIGYIjzIbo9` → `https://grankha.roadshop.online/api/stripe-webhook`.

---

## 3. Supabase ✅ hecho

Proyecto `ravvjwyjaxofidgueopc` con `orders`, `order_items`, `subscribers`,
`contact_messages`, vistas `v_sales_daily` y `v_donation_fund`, y RLS activo.
Pedidos, newsletter y contacto escriben de verdad en la base de datos.

---

## 4. Correo de la tienda 🔴 el único bloqueante

Los emails con marca GRANKHA (pedido confirmado + aviso interno de venta) se generan pero
**no salen**: falta proveedor. Código listo en `api/_lib/mail.js` con tres caminos:

- **SMTP del buzón** (`EMAIL_PROVIDER=smtp` + `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`)
  → la vía más directa, ya tienes `grankha@roadshop.online`.
- **Resend** (`RESEND_API_KEY`) verificando el dominio `roadshop.online`.
- **Brevo** (`BREVO_API_KEY`).

Detalle de las variables en `LANZAMIENTO.md`.

---

## 5. Marketing y operación (recomendado)

- [x] Foto real de Khalid en portada, compromiso y banda «Te quiero amigo, esto va por ti.»
- [ ] Instagram / TikTok de la marca y enlazarlos en el footer.
- [ ] Google Search Console: `https://grankha.roadshop.online/sitemap.xml`.
- [ ] Google Merchant Center (Shopping): los datos estructurados ya están puestos.
- [ ] Píxel de Meta / TikTok solo si haces publicidad (requiere actualizar la política de
      cookies y añadir consentimiento).
- [ ] Textos de reseñas: cuando tengas las primeras, añadimos un bloque en las fichas
      (con schema `AggregateRating`).
- [ ] Pasar los pedidos a AW Dropshipping (hoy manual); automatizar con
      `supabase/functions/fulfill-order` y `notify-tracking` cuando quieras.

---

## 6. Decisiones que dependen de tus números

- [x] **Envío gratis desde 39 €** con tramos (20 € → 3,95 €; mínimo → 5,95 €). Configurado en
      `data/site.json` → `shipping.options[].tiers`. Si la tarifa real del proveedor sube,
      ajustar aquí y regenerar.
- [x] **Precios auditados** contra el mercado (octubre 2026): 8 referencias subidas, 11 ajustadas
      a la baja, 19 validadas. Detalle por producto en `docs/GRANKHA_Auditoria_Precios.xlsx`.
- [x] **Donación 5 %** de los beneficios, reservada pedido a pedido (Supabase `orders.donation`).
      En público solo se dice «un porcentaje de los beneficios».
- [x] **6 packs** con 5,8-9 % de descuento y contribución de 10-30 € por pedido.
- [ ] **Tarifa real de envío del proveedor** (estimada en 4,95 € + 1,10 €/kg): confirmar en el panel.
- [ ] **Plazos reales** de preparación y entrega del proveedor (la web muestra 3-8 días).
- [ ] Canarias/Ceuta/Melilla: revisar con el proveedor si el envío incluye aduanas.

---

## 7. Mejoras que puedo construir cuando quieras

- Guía de tallas interactiva para arneses (con medida de contorno en cm).
- Packs «arnés + correa» con descuento automático.
- Cuentas de cliente y seguimiento de pedidos (Supabase Auth).
- Sistema de reseñas con fotos.
- Blog / revista con contenido SEO («cómo elegir un arnés», «señales de dolor en perros»).
- Programa de donación visible: contador de importe donado con datos reales de Supabase.

---

## Cerrado el 22/10/2026

- ✅ Dominio definitivo `grankha.roadshop.online` verificado y en producción.
- ✅ Canonical, Open Graph, JSON-LD, sitemap y robots apuntando al dominio nuevo.
- ✅ Datos de la empresa publicados: GRANKHA, `grankha@roadshop.online`, dropshipping con AW Dropshipping.
- ✅ Divulgación del modelo de envío directo en legal (aviso legal, punto 4 de condiciones,
      destinatarios de privacidad) y en la página de envíos.
- ✅ Variables de Vercel actualizadas: `SITE_URL`, `EMAIL_AVISO`, `EMAIL_FROM`.
- ✅ Webhook de Stripe movido al dominio nuevo.
- ✅ Correo unificado en `api/_lib/mail.js` con soporte SMTP (buzón propio), Resend y Brevo.
- ✅ Prueba real en el dominio nuevo: checkout con sesión de Stripe en EUR, pedido guardado en
      Supabase, contacto guardado, webhook rechazando firma mala. Datos de prueba borrados después.

## Corregido en la revisión del 15/10/2026 (bloque 0 de la auditoría)

- ✅ El carrito se vacía al confirmar el pedido (ya no se pueden duplicar).
- ✅ El país del formulario manda sobre la zona de envío (Portugal 6,95 € · UE 13,95 €).
- ✅ Canarias, Ceuta y Melilla sin IVA, con aviso de IGIC/IPSI y aduana en destino.
- ✅ Newsletter con casilla de consentimiento (y envío a Supabase).
- ✅ Contraste del gris secundario corregido a 5,2:1 (WCAG AA).
- ✅ CSS y JS como archivos externos y fotos sin base64: las páginas pesan entre un 77 % y un 91 % menos.
- ✅ 108 imágenes antiguas sin uso eliminadas (3,2 MB).
- ✅ Enlace a la plataforma europea de resolución de litigios en la página legal.


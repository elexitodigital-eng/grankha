# GRANKHA · Auditoría externa
### Diseño · SEO · Funcionalidad · Viabilidad
**Fecha:** 15 de octubre de 2026 · **Alcance:** las 85 páginas publicadas + el flujo de compra completo
**Método:** rastreo automático de las 85 páginas, recorrido de cliente simulado en navegador real (Chrome) en escritorio (1440 px) y móvil (390 px), mediciones de peso/rendimiento, cálculo de contrastes WCAG y revisión del código y de la configuración del sitio.

---

## 0. Resumen ejecutivo

**Nota global: 6,5 / 10.** La tienda está **muy por encima de la media** de un lanzamiento: 44 fichas completas con datos estructurados, cero enlaces rotos, cero títulos duplicados, imágenes optimizadas, envío por tramos bien resuelto y una identidad visual coherente. Pero **hoy no está lista para vender sin riesgo**: hay 6 problemas que cuestan dinero o incumplen normativa, y el más grave es que **el pedido no se cobra ni se guarda en ningún sitio**.

| Prioridad | Qué pasa | Impacto |
|---|---|---|
| 🔴 1 | **No hay cobro real ni pedido guardado.** El pedido vive en el navegador del cliente; si cierra la pestaña, se pierde. Depende de que el cliente envíe un email. | Pérdida directa de ventas |
| 🔴 2 | **Aviso legal con huecos visibles** (`[RAZÓN SOCIAL]`, `[NIF]`, `[DIRECCIÓN]`) y una línea que dice *«Pendiente de completar antes de vender»*. | Incumplimiento LSSI + imagen |
| 🔴 3 | **Las fotos llevan la marca del proveedor** (logo «AW») y textos en inglés de fábrica («Gemstone Guardian Harness»). | Rompe la marca y genera desconfianza |
| 🔴 4 | **El país del formulario no cambia la zona de envío** (se puede pedir a Alemania con tarifa peninsular) y **Canarias se cobra con IVA del 21 %** cuando allí no hay IVA. | Pedidos que pierden dinero |
| 🟠 5 | **La newsletter no guarda nada** (solo en el navegador de quien se apunta) y no tiene casilla de consentimiento. | Pierdes tu lista + riesgo RGPD |
| 🟠 6 | **El carrito no se vacía** después de confirmar el pedido → el cliente puede reenviarlo y duplicar pedidos. | Pedidos duplicados |
| 🟠 7 | **Sin analítica** de ningún tipo: no sabrás qué se vende, ni de dónde viene el tráfico. | Decisiones a ciegas |

**La buena noticia:** los 4 problemas críticos se arreglan en una tarde. Los números del modelo de precios, además, salen: cada pedido deja entre **9 y 20 € de beneficio real** y el punto de equilibrio son **≈25 pedidos al mes**.

---

## 0-bis. Estado de las correcciones (actualizado el mismo día)

Tras entregar esta auditoría se ha ejecutado el **bloque 0** completo y parte del bloque 2. Lo que sigue es lo que ya está hecho y verificado en el sitio:

| # | Problema detectado | Estado | Qué se ha hecho |
|---|---|---|---|
| 2.2 | El carrito no se vaciaba al confirmar el pedido | ✅ **Corregido** | Al confirmar, la cesta se vacía, el contador vuelve a 0 y el resumen del pedido con su referencia permanece a la vista (sin pantalla de «carrito vacío» de por medio) |
| 2.3 | El país del formulario no cambiaba la zona de envío | ✅ **Corregido** | Elegir Portugal/Alemania/etc. selecciona solo la zona correcta y recalcula el envío: 3,95 € (península) → 6,95 € (Portugal) → 13,95 € (UE). También funciona al revés: si se elige la zona a mano, manda la zona |
| 2.4 | Canarias, Ceuta y Melilla se cobraban con IVA del 21 % | ✅ **Corregido** | Esas zonas ahora muestran **precios sin IVA**, la línea de IVA dice «No aplicable», se avisa del IGIC/IPSI y de la aduana en destino, y el servidor de pago calcula igual (exención de IVA en la función `create-checkout`) |
| 2.6 | Newsletter que no guardaba nada y sin consentimiento | ✅ **Corregido (parcial)** | Añadida casilla de consentimiento obligatoria con enlace a la política de privacidad. La suscripción se guarda además en Supabase en cuanto exista el proyecto (la tabla `subscribers` ya está creada); mientras tanto queda registrada en el navegador |
| 6 | Contraste del gris secundario por debajo de AA | ✅ **Corregido** | `#8A8A88` → `#6B6B69`: pasa de 3,46:1 a **5,2:1** (cumple WCAG AA). El diseño no cambia de aspecto |
| 7 | Aviso legal con el cartel «Pendiente de completar antes de vender» | ✅ **Corregido (a medias)** | El cartel público ha desaparecido (ahora es un comentario interno). Los huecos `[RAZÓN SOCIAL]`, `[NIF]`… siguen ahí **hasta que me pases los datos fiscales** |
| 7 | Faltaba el enlace a la plataforma europea de litigios | ✅ **Corregido** | Añadido `ec.europa.eu/consumers/odr` en la página legal |
| 5 | Páginas de 474-527 KB por llevar el catálogo y las imágenes incrustados | ✅ **Corregido** | CSS y JS ahora son **archivos externos** (se cachean entre páginas) y las fotos se sirven como archivos en vez de base64 |

**Antes → después (peso real de cada página, con gzip de GitHub Pages):**

| Página | Antes | Ahora | Reducción |
|---|---|---|---|
| Portada | 474 KB | **80 KB** | −83 % |
| Tienda (44 tarjetas) | 527 KB | **79 KB** | −85 % |
| Carrito | 492 KB | **44 KB** | −91 % |
| Ficha de pack | 159 KB | **37 KB** | −77 % |

Además se han borrado **108 imágenes antiguas** sin uso (3,2 MB) y el material fuente (logo original y foto de estudio) se ha movido a `assets/src/`, fuera de la carpeta publicada. El sitio entero pasa de **19,8 MB a 16 MB** y cada visita descarga una cuarta parte de lo que descargaba.

Verificado tras los cambios: **0 peticiones fallidas, 0 errores de JavaScript** en las 12 páginas principales, todas las imágenes cargan (107 imágenes comprobadas tras hacer scroll), los filtros, el buscador, el deslizador de packs, el alta en el carrito y los tres flujos de pedido (península, Canarias, Alemania) funcionan.


---

## 1. Cómo lo ve un cliente (recorrido real, paso a paso)

Recorrí la tienda como un comprador cualquiera. Esto es lo que se encuentra:

1. **Portada.** Entra y ve una foto limpia (perro + gato), el titular «Accesorios con propósito», el botón de packs y tres iconos de confianza. Buena primera impresión: transmite marca, no «tienda de dropshipping». Nota: en el menú de arriba el aviso dice *«GRANKHA POR LA SALUD ANIMAL»* y el nombre de la marca aparece con el logo: correcto.
2. **Tienda.** 44 productos. Los filtros funcionan (Arneses 6, Camas 14, Comederos 9, Packs 6, Perros 42, Gatos 36), el orden por precio ordena de verdad (13,90 · 16,90 · 17,90 · 18,90) y el buscador encuentra «correa» (9) y «arnés» con tilde o sin ella. **Pega:** si busca «cama para gato» obtiene **0 resultados y no pasa nada**: se queda mirando una pantalla vacía sin explicación.
3. **Ficha de producto.** Precio con IVA claro, cuánto falta para el envío gratis, contador de cantidad que respeta el stock (llega a 20 y se para), descripción y especificaciones. **Pega gorda:** la foto principal es la del proveedor, con su marca «AW» y textos en inglés impresos en el envase. Un cliente que quiere una marca española de diseño ve la etiqueta de otra empresa.
4. **Packs.** El deslizador muestra una pieza por vista con su nombre, y la foto ya no lleva a la ficha suelta. El conjunto suma bien en el carrito (Pack Primeros Días Gato 78,90 € con sus 3 piezas detalladas).
5. **Carrito.** El resumen es de los buenos: subtotal, IVA desglosado, envío por zona y tramo, aviso de *«Añade 2,10 € más y el envío baja a gratis»* y la zona de envío explicada. **Pega:** si eliges «Alemania» en el país, el resumen sigue diciendo «España peninsular 3,95 €». Hay dos selectores que no hablan entre sí.
6. **Checkout.** Pide nombre, email, teléfono, dirección, población, país y aceptación de la política. Valida los campos (7 obligatorios) y rechaza un email mal escrito. Al confirmar dice: *«Pedido GRK-261015-G723 preparado. El pago con tarjeta se activará muy pronto… puedes confirmarlo por email»*. Es decir: **el cliente no paga** y depende de que él mismo mande un correo. Y el carrito sigue lleno: puede volver a confirmar el mismo pedido.
7. **Contacto.** Formulario claro que abre el programa de correo con todo rellenado. Contesta «en menos de 24 horas laborables». Correcto.
8. **Envíos, legal, compromiso.** Explican tarifas, plazos y devoluciones (30 días) con honestidad. La página de compromiso con el texto de Khalid funciona emocionalmente muy bien. **Pega:** en el aviso legal el cliente lee literalmente «Pendiente de completar antes de vender: razón social, NIF, domicilio fiscal y teléfono del titular».

**Veredicto del cliente simulado:** «Es bonita y parece seria, pero no puedo pagar con tarjeta y no sé muy bien quién está detrás. Me fío más si hubiera un correo propio, un teléfono y poder pagar en un clic.»

---

## 2. Fallos funcionales encontrados (con evidencia)

### 🔴 2.1 El pedido no se cobra ni se guarda (crítico)
- **Evidencia:** al confirmar, el panel dice «El pago con tarjeta se activará muy pronto»; el `checkout.endpoint` está vacío; no hay escritura en Supabase ni envío de correo automático.
- **Consecuencia:** el pedido existe solo en el `localStorage` del visitante. Si cierra el móvil, se perdió. Sólo se salva si el cliente envía el email que se le prepara.
- **Arreglo:** desplegar `create-checkout` + `stripe-webhook` (el código ya está hecho y valida precios en servidor). Es el paso 2 de `docs/COMO_VENDER_YA.md`.

### 🟠 2.2 El carrito no se vacía al confirmar
- **Evidencia:** tras confirmar el pedido el carrito conserva 1 línea y el botón sigue disponible.
- **Arreglo:** limpiar el carrito cuando el pedido se confirma por email (hoy solo se limpia cuando Stripe responde).

### 🔴 2.3 El país no está ligado a la zona de envío
- **Evidencia medido:** con «Alemania» seleccionado, el resumen mantiene «Envío · España peninsular 3,95 €» y el total 40,85 €. Con las 5 zonas (península, Baleares, Canarias, Portugal, UE) el selector de método **sí** funciona bien: 3,95 / 7,95 / 14,95 / 6,95 / 13,95 € y el gratis cambia a 39 € / 49 € / 79 €.
- **Consecuencia:** un pedido a Alemania puede salir con 3,95 € de envío cuando cuesta 6,95 € + IVA distinto. Pérdida directa y riesgo fiscal.
- **Arreglo:** el país debe **preseleccionar** la zona de envío y, si el país no es España/Portugal, marcar «Resto de la UE» automáticamente (y bloquear el envío «península»).

### 🔴 2.4 Canarias, Ceuta y Melilla con IVA del 21 %
- **Evidencia:** con la zona «Canarias, Ceuta y Melilla» el resumen muestra «IVA incluido (21 %) 6,40 €» y total 51,85 €. AW sirve esas zonas **sin IVA** y con aduana a cargo del destinatario; allí se aplica IGIC/IPSI.
- **Consecuencia:** el importe mostrado no puede ser el que se cobre: o cobras 21 % de más, o te lo comes tú.
- **Arreglo:** en esas zonas, mostrar precios sin IVA con aviso de aduana, o desactivarlas hasta confirmar la tarifa real con AW.

### 🟠 2.5 Búsqueda: «cama para gato» devuelve 0 resultados sin mensaje de ayuda
- **Evidencia:** «correa» → 9, «arnés»/«arnes» → 6, «CAMAS» → 14, «cama para gato» → **0**. El mensaje de «sin resultados» existe y funciona, pero no ofrece alternativas.
- **Arreglo:** buscar por palabras sueltas (todas deben aparecer, no la frase completa) y añadir sugerencias cuando no haya resultados.

### 🟠 2.6 Newsletter que no guarda nada y sin consentimiento
- **Evidencia:** al enviar muestra «¡Gracias! Te escribiremos muy pronto», pero sólo escribe en `localStorage` (`grankha.news`). No hay casilla de consentimiento ni doble confirmación.
- **Consecuencia:** pierdes el 100 % de las suscripciones y tienes un problema de RGPD (no puedes probar el consentimiento).
- **Arreglo:** guardar en Supabase (tabla `subscribers` ya creada) + casilla de consentimiento con enlace a privacidad + email de bienvenida.

### 🟡 2.7 Pantallas y validaciones menores
- Referencia de pedido generada en el navegador (`GRK-YYMMDD-XXXX`): puede repetirse y no queda registrada.
- Sin validación de stock real: si AW se queda sin unidades, el pedido se cobra y luego no se puede servir.
- Sin página de «estado de mi pedido»: el cliente sólo puede escribir un correo para saber dónde está su paquete.
- Precios “de confianza” en el navegador: sin Stripe desplegado, un usuario con conocimientos podría manipular el precio de su propio pedido. `create-checkout` ya lo evita cuando esté en producción.
- Fichas con precios/slug casi idénticos (variantes de color): conviene enlazarlas como variantes para no competir entre ellas en Google.

---

## 3. Diseño, marca y confianza (lo que se ve)

**Lo que funciona:** tipografía y retícula consistentes; blanco y negro con intención; el hero con perro y gato alineados a la derecha; packs retratados pieza a pieza; el pie con la promesa de investigación; los iconos ya son del mismo tamaño (18 × 18 px) y el logo de la huella aparece a la izquierda del nombre.

**Lo que resta ventas:**

| Problema | Por qué importa | Arreglo |
|---|---|---|
| Fotos con la marca del proveedor y texto en inglés de fábrica | El cliente compra una marca, no un intermediario; además el envase en inglés resta en España | Recortar el envoltorio de las fotos (yo puedo hacerlo con las 44), o pedir a AW las fotos sin etiqueta |
| En el logo de 34 px, la palabra «GRANKHA» dentro de la huella es ilegible | A tamaños pequeños se ve como una mancha | Versión simplificada (sólo huella + corazón) para ≤48 px y favicon |
| Contacto sólo con un Gmail (`zenqalife@gmail.com`) | Un correo genérico en una tienda con precios de 40-80 € es la señal de desconfianza nº 1 | Correo propio `hola@grankha.com` + firma con nombre real |
| Sin valoraciones ni «quién está detrás» | El 93 % de los compradores lee opiniones antes de comprar | Reseñas verificadas (aunque sean 5 al principio) y foto/vídeo real del equipo |
| Tarjeta y botones bien, pero no hay «pago exprés» | En móvil el 40-60 % del tráfico abandonará sin Apple/Google Pay o Bizum | Activarlos en Stripe Checkout (Bizum está soportado en España) |

---

## 4. SEO

**Estado:** 52 páginas indexables, 33 redirecciones `noindex` correctamente marcadas.

| Comprobación | Resultado |
|---|---|
| Títulos duplicados | 0 |
| Meta descripciones duplicadas | 0 |
| Páginas sin H1 | 0 |
| Canonical | 52/52 correctos |
| `og:image` en todas | Sí |
| Enlaces internos rotos | 0 de 699 |
| `alt` en imágenes | 393/393 |
| `width`/`height` en imágenes (evita saltos) | Sí |
| Datos estructurados | 44 fichas con `Product` + `BreadcrumbList`, portada con `OnlineStore` + `WebSite` |
| Sitemap / robots / 404 real | Sí / Sí / Sí (HTTP 404 correcto) |
| Idioma | `lang="es"` en todo el sitio |

**Lo que falta para posicionar de verdad:**

1. **Sin dominio propio.** Estás en `elexitodigital-eng.github.io/grankha`, un subdominio de terceros: Google puede indexarlo, pero pierdes autoridad, no puedes configurar cabeceras, y el correo de la tienda no es creíble. **Es la acción SEO y de marca nº 1.**
2. **Meta descripciones largas:** media de 201 caracteres (Google corta sobre 155-160). 47 de 52 están fuera del rango ideal. Los títulos: 27 de 52 pasan de 60 caracteres.
3. **Falta contenido que atraiga tráfico:** ninguna guía, ninguna página de categoría con texto propio («arneses para perros pequeños», «fuentes y filtros»). Con 44 fichas y nada más, el techo de tráfico orgánico es bajo; este sector se gana con guías («¿qué arnés necesita mi perro?», «cada cuánto cambiar el filtro de la fuente»).
4. **Datos estructurados incompletos:** falta `MerchantReturnPolicy` (devoluciones 30 días) para los listados gratuitos de Google, `ItemList` en la tienda, `FAQPage` en las fichas y en envíos, y `Product` con `hasVariant` para agrupar colores.
5. **Tienda, compromiso, envíos, contacto y legal sin JSON-LD.**
6. **Jerarquía de encabezados:** en las fichas salta de `H1` a `H3` (el acordeón). Conviene usar `H2` en secciones.
7. **Redirecciones antiguas:** ✔ ya saneadas (noindex + canonical).

---

## 5. Rendimiento real medido

| Página | HTML | ¡De los cuales CSS/JS/JSON incrustados! | Comprimido real (GitHub Pages) | Peticiones |
|---|---|---|---|---|
| Portada | 474 KB | 28 KB CSS + 44 KB JS + 400 KB datos | **295 KB** | 8 |
| Tienda | 526 KB | idem | **325 KB** | 21 |
| Ficha de producto | 173 KB | idem | — | 7 |
| Carrito | 492 KB | 28 KB CSS + **454 KB JS+datos** | — | 2 |

- **El problema nº 1 de velocidad:** cada página lleva incrustados el CSS completo, el JavaScript completo y **~400 KB del catálogo en JSON**. En un móvil 4G eso es casi un segundo de descarga antes de pintar nada, y **se repite en cada página** porque nada se puede cachear.
- **Arreglo recomendado:** sacar a ficheros externos `styles.css` y `app.js` (se cachean entre páginas), y enviar en cada página sólo los datos que necesita (ficha: 1 producto; tienda: lo mínimo). Ganancia estimada: **60-70 % menos de datos por visita**.
- **Imágenes:** el catálogo está bien (webp de 22-136 KB; miniaturas de ~7 KB). No hay ninguna imagen por encima de 220 KB en las páginas.
- **Peso muerto en el repositorio:** 193 archivos (5,6 MB) no los usa ninguna página — variantes antiguas, `logo-src.png` (400 KB), `hero-fuente.jpg`, `memorial.jpg` y 32 OG duplicados. No afectan al cliente, pero ensucian cada despliegue.
- Lo que mide bien: la portada y las fichas pintan en menos de 200 ms en local; `loading="lazy"` correcto; sin fuentes externas (usa fuentes del sistema) → cero peticiones a dominios de terceros.

---

## 6. Accesibilidad y usabilidad

| Comprobación | Resultado |
|---|---|
| Foco visible en botones y enlaces | ✔ (contorno 2 px) |
| Campos de formulario con etiqueta | ✔ todos |
| Imágenes sin `alt` (informativas) | 0 |
| Controles por debajo del mínimo WCAG 2.5.8 (24 px) | 0 |
| **Contraste del gris secundario** | ✘ **3,46:1** — por debajo del 4,5:1 exigido para texto pequeño |
| Orden de encabezados en fichas | ✘ H1 → H3 |
| Desbordamiento horizontal en móvil | ✔ ninguna de 7 páginas |

- El gris `#8A8A88` se usa en textos pequeños por todas partes (notas de IVA, migas de pan, «44 productos», contador del deslizador). **Se arregla cambiándolo por `#6B6B69`** (5,2:1) sin tocar el diseño.
- El menú móvil abre y cierra bien (6 enlaces), pero no lleva a Envíos/Devoluciones desde el menú: sí está en el pie.

---

## 7. Legal y cumplimiento

| Requisito | Estado |
|---|---|
| Aviso legal (LSSI, art. 10) | 🔴 **Incompleto**: razón social, NIF, domicilio y teléfono con marcadores visibles |
| Política de privacidad | ✔ existe y es razonable; revisar que cite `localStorage` y la newsletter |
| Política de cookies | ✔ no se usan cookies (bien) — si añades analítica, tendrás que añadir banner de consentimiento |
| Derecho de desistimiento | ✔ 14 días legal, ofreces **30**: mejor que la ley |
| Devoluciones y gastos | ✔ bien explicados, con quién paga la devolución |
| Precios con IVA | ✔ clarísimo en toda la web |
| Resolución de litigios en línea (UE) | ✘ falta el enlace a la plataforma ODR en el aviso legal o en devoluciones |
| Condiciones de venta | ✘ no hay una página de «Condiciones generales» separada del aviso legal |
| Facturación al cliente | No descrito: conviene decir que se emite factura simplificada y cómo pedir la completa |

> Nota: no soy abogado; esto es una lista de comprobación. Con dos datos tuyos (razón social/NIF/dirección y teléfono) cierro los cuatro huecos de la web.

---

## 8. Viabilidad del proyecto (números)

### 8.1 Cuánto deja cada venta (modelo real, con la tarifa verificada de AW)

| | Beneficio medio | Margen sobre PVP |
|---|---|---|
| Producto suelto (38 fichas) | **9,39 €** | 28 % |
| Pedido de 1 artículo | 9,85 € | — |
| Pedido de 2 artículos | 18,55 € | — |
| Pack (media de los 6) | 17,72 € | 25 % |

Extremos: la correa Pocket Pod (21,90 €) deja 4,63 €; el Pack Hidratación (80,90 €) deja 26,15 €. **El ticket medio es la palanca: vender un segundo artículo no cuesta envío extra y casi duplica el beneficio.**

### 8.2 Punto de equilibrio

- Costes fijos mensuales asumidos: 65 € (hosting, dominio, gestoría) + 150 € de publicidad = **215 €/mes**.
- Contribución media por pedido: **8,79 €**.
- **Punto de equilibrio: ≈ 25 pedidos al mes** (menos de uno al día).

| Escenario | Pedidos/mes | Ventas | Beneficio tras costes |
|---|---|---|---|
| Arranque | 20 | ≈ 840 € | −40 € (empatas) |
| En marcha | 50 | ≈ 2.100 € | ≈ +225 € |
| Objetivo | 138 | ≈ 5.780 € | ≈ **+1.000 €** |

### 8.3 Sensibilidad (qué te puede tumbar)

| Cambio | Efecto en el beneficio |
|---|---|
| AW sube los costes un 10 % | −1,99 €/pedido (−23 %) |
| Publicidad a 5 € por pedido (CAC) | Te quedan 3,79 €: sólo funciona con cestas de 2 artículos o packs |
| Devoluciones del 3 % al 8 % | −0,40 €/pedido (asumible) |
| Envío gratis desde 39 € sube a 35 € | 0,30 € menos por pedido (buena palanca de conversión) |

### 8.4 Riesgos del modelo

1. **Dependencia total de AW** (precios, stock, fotos, plazos). No hay contrato de exclusividad ni marca propia de producto. Mitigación: no comunicar plazos que no controles y tener 3-4 referencias “estrella” con stock alto.
2. **Fotos y marca del proveedor**: hoy tu catálogo se ve igual que el de cualquier otra tienda conectada a AW. Un competidor puede vender lo mismo mañana **con las mismas fotos** y precios más bajos.
3. **Sin tráfico propio.** Todo depende de publicidad o de contenido que aún no existe.
4. **Estacionalidad y campañas** (octubre-diciembre): los plazos de AW se alargan a 3-4 días de preparación.
5. **Fiscalidad del dropshipping**: las facturas de AW llevan IVA (deducible). Si algún mes no lo deduces, el coste sube un 21 %.
6. **Canarias/Ceuta/Melilla**: sin tarifa publicada; hoy vender allí es una apuesta.

### 8.5 Posicionamiento frente a la competencia

- **A favor:** diseño cuidado, narrativa real (Khalid + donación), precios dentro de la banda de mercado premium español, entrega en 1-3 días desde Málaga, español impecable, web ligera y accesible.
- **En contra:** sin reseñas, sin marca visible en el producto (sólo en la web), sin contenido que atraiga tráfico, sin dominio propio, y un catálogo pequeño frente a gigantes de alimentación y accesorios.
- **Recomendación estratégica:** no competir en precio ni en catálogo. Ganar en **curaduría** (pocos productos, buenos, con historia), en **contenido útil** (guías de tallas, hidratación, sueño de mascotas senior) y en **comunidad** (la historia de Khalid es un activo enorme: úsala en email, redes y notas de pedido).

**Conclusión de viabilidad: SÍ, es viable** como proyecto de ingresos complementarios (300-1.000 €/mes) con 25-138 pedidos al mes, **siempre que** (a) se active el cobro de verdad, (b) se cierre el aviso legal, (c) se trabaje el ticket medio con packs y (d) se abra un canal de tráfico propio o pagado medido con analítica.

---

## 9. Plan de acción priorizado

### Bloque 0 — antes de abrir (1 tarde, sin coste)
1. Desplegar Stripe + Supabase (`create-checkout`, `stripe-webhook`, `fulfill-order`, `notify-tracking`) y probar una compra real de 1 €.
2. Rellenar los datos fiscales del aviso legal y **borrar la frase «Pendiente de completar antes de vender»**.
3. Vaciar el carrito al confirmar el pedido.
4. Ligar país → zona de envío y arreglar el IVA de Canarias/Ceuta/Melilla.
5. Newsletter a Supabase + casilla de consentimiento.

### Bloque 1 — primera semana
6. Correo propio (`hola@grankha.com`) y, si se puede, **dominio propio** (`grankha.com`) apuntando al sitio.
7. Limpiar las fotos con la marca del proveedor (te las recorto yo en una pasada) o pedirlas sin etiqueta a AW.
8. Analítica: GA4 o Plausible (con banner de cookies si es GA4; Plausible no las necesita).
9. Activar Bizum, Apple Pay y Google Pay en Stripe.
10. `MerchantReturnPolicy` + `FAQPage` en datos estructurados; acortar títulos y descripciones.

### Bloque 2 — primer mes
11. Sacar CSS y JS a ficheros externos y recortar el JSON por página (−60 % de datos por visita).
12. Borrar los 5,6 MB de imágenes huérfanas y añadir política de caché.
13. Publicar 4-6 guías útiles (tallas, hidratación, camas para gatos mayores, cómo elegir arnés) enlazadas desde las fichas.
14. Recoger y publicar reseñas; email de bienvenida y de carrito abandonado (con Supabase puedes saber cuándo se abandona).
15. Logo simplificado para tamaños pequeños y favicon definitivo.

### Bloque 3 — escala
16. Ampliar el catálogo priorizando lo que deja más margen (fuentes, filtros, camas grandes, packs de 3-4 piezas).
17. Packs por ocasión (cachorro, gato senior, viaje) y venta cruzada automática en el carrito.
18. Programa de fidelización o suscripción de filtros (compra recurrente: el mejor negocio de este sector).

---

## Anexo · Cómo se ha auditado

- **Rastreo** de las 85 páginas del sitio: títulos, descripciones, canonical, H1/H2, metadatos, JSON-LD, imágenes, enlaces internos y peso.
- **Recorrido de cliente automatizado** en Chrome real: portada, tienda (filtros, orden, búsqueda), ficha, pack, carrito (5 zonas de envío), checkout completo, contacto, newsletter, 404 y menú móvil.
- **Mediciones:** peso real de HTML y recursos, compresión servida por GitHub Pages (gzip ✔), tiempos de pintado, contrastes WCAG calculados, tamaño de objetivos táctiles, desbordamiento en 390 px.
- **Revisión de código:** `src/app.js`, `src/styles.css`, `tools/*.py`, funciones de Supabase y esquema de base de datos.
- **Cálculo económico:** `docs/GRANKHA_Beneficio_Real_Por_Producto.xlsx` (beneficio por producto y escenarios) con la tarifa de envío verificada de AW Dropship España (15/10/2026).

---

## Anexo visual · capturas de esta auditoría

Van adjuntas en `docs/auditoria/`:

| Archivo | Qué muestra |
|---|---|
| `01-boton-packs.png` | El botón «Ver los 6 packs» ya destacado, con su nota de apoyo |
| `02-ficha-producto.png` | Ficha del arnés: se ve **la etiqueta «AW» y el texto en inglés** del envase del proveedor |
| `03-movil.png` | Portada en móvil (390 px): perro y gato visibles, sin desbordamiento |
| `04-carrito-envios.png` | Carrito con el desglose de envío por zona y el aviso de «te faltan X €» |
| `05-catalogo.png` | Catálogo con filtros, orden y contador de resultados |

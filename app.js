/* ==========================================================================
   GRANKHA · app.js
   Carrito, filtros, ficha de producto y checkout (listo para conectar Stripe)
   ========================================================================== */
(function () {
  "use strict";

  var CFG = window.GRANKHA_CONFIG || {};
  var LITE = window.GRANKHA_CATALOG || [];        // catálogo ligero (todas las páginas)
  var FULL = window.GRANKHA_CATALOG_FULL || [];   // catálogo con miniaturas (carrito)
  var KEY = "grankha.cart.v1";
  var ORDER_KEY = "grankha.lastOrder.v1";

  var byslug = {};
  (FULL.length ? FULL : LITE).forEach(function (p) { byslug[p.slug] = p; });

  /* ---------------------------------------------------------------- utils */
  function eur(n) {
    return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n || 0);
  }
  function num(n) { return new Intl.NumberFormat("es-ES").format(n); }
  function $(s, c) { return (c || document).querySelector(s); }
  function $$(s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); }

  /* ---------------------------------------------------------------- estado */
  function readCart() {
    try {
      var raw = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(raw) ? raw.filter(function (l) { return l && l.slug && l.qty > 0; }) : [];
    } catch (e) { return []; }
  }
  function writeCart(lines) {
    try { localStorage.setItem(KEY, JSON.stringify(lines)); } catch (e) {}
    paintCount();
    document.dispatchEvent(new CustomEvent("grankha:cart", { detail: lines }));
    return lines;
  }
  function addToCart(slug, qty) {
    qty = Math.max(1, parseInt(qty || 1, 10));
    var p = byslug[slug];
    var lines = readCart();
    var line = lines.filter(function (l) { return l.slug === slug; })[0];
    var max = p && p.stock ? p.stock : 99;
    if (line) { line.qty = Math.min(max, line.qty + qty); }
    else { lines.push({ slug: slug, qty: Math.min(max, qty) }); }
    writeCart(lines);
    var name = p ? (p.title + (p.subtitle ? " · " + p.subtitle : "")) : "Producto";
    toast("Añadido al carrito — " + name, "Ver carrito", "carrito");
    bump();
    return lines;
  }
  function setQty(slug, qty) {
    qty = parseInt(qty, 10);
    var lines = readCart().map(function (l) {
      if (l.slug === slug) {
        var max = byslug[slug] && byslug[slug].stock ? byslug[slug].stock : 99;
        l.qty = Math.max(1, Math.min(max, qty || 1));
      }
      return l;
    });
    return writeCart(lines);
  }
  function removeLine(slug) {
    return writeCart(readCart().filter(function (l) { return l.slug !== slug; }));
  }
  function clearCart() { return writeCart([]); }

  /* ------------------------------------------------------------- cabecera */
  function cartCount() {
    return readCart().reduce(function (n, l) { return n + l.qty; }, 0);
  }
  var EN_CARRITO = /\/carrito(\.html)?\/?$/.test(location.pathname);
  function cartSubtotal() {
    return readCart().reduce(function (s, l) {
      var p = byslug[l.slug];
      return s + (p && p.price ? p.price * l.qty : 0);
    }, 0);
  }
  /* barra de envío gratis (zona por defecto) para la vista rápida */
  function barraEnvio(subtotal) {
    var zona = shippingFor((CFG.shipping && CFG.shipping.default) || "pen", subtotal);
    var libre = (zona.tiers || []).filter(function (x) { return x.price === 0; })[0];
    if (!libre) return "";
    if (subtotal >= libre.min) {
      return '<div class="free-bar">✓ Envío gratuito (' + esc(zona.name || "") + ') aplicado</div>';
    }
    var pct = Math.min(100, (subtotal / libre.min) * 100);
    return '<div class="free-bar">Te faltan <b>' + eur(libre.min - subtotal) +
      '</b> para el envío gratuito<div class="free-bar__track"><div class="free-bar__fill" style="width:' +
      pct + '%"></div></div></div>';
  }

  /* ------------------------------------------------- vista rápida de la cesta */
  var miniEl = null, miniTimer = null, miniAuto = null;
  function miniAbierta() { return !!(miniEl && miniEl.classList.contains("is-open")); }
  function abrirMini() {
    if (!miniEl || !cartCount()) return;
    clearTimeout(miniAuto);
    miniEl.hidden = false;
    miniEl.classList.add("is-open");
    miniEl.setAttribute("aria-hidden", "false");
  }
  function cerrarMini() {
    clearTimeout(miniAuto);
    if (!miniEl) return;
    miniEl.classList.remove("is-open");
    miniEl.setAttribute("aria-hidden", "true");
    setTimeout(function () { if (miniEl && !miniAbierta()) miniEl.hidden = true; }, 300);
  }
  function paintMini() {
    var box = $("#mini-cart");
    if (!box) return;
    miniEl = box;
    var lines = readCart();
    if (!lines.length) { cerrarMini(); return; }
    var visibles = lines.slice(0, 4);
    var html = visibles.map(function (l) {
      var p = byslug[l.slug];
      if (!p) return "";
      return '<div class="mini__line">' +
        '<a href="' + p.url + '"><img src="' + (p.thumb || "") + '" alt="' + esc(p.title) + '" loading="lazy" decoding="async"></a>' +
        '<div><a class="mini__t" href="' + p.url + '">' + esc(p.title) + '</a>' +
        '<div class="mini__s">' + l.qty + ' × ' + eur(p.price) + '</div></div>' +
        '<div class="mini__p mono">' + eur(p.price * l.qty) + '</div>' +
      '</div>';
    }).join("");
    if (lines.length > visibles.length) {
      html += '<p class="mini__s">y ' + (lines.length - visibles.length) + ' producto(s) más en la cesta</p>';
    }
    $("[data-mini-lines]", box).innerHTML = html;
    var tot = $("[data-mini-total]", box);
    if (tot) tot.textContent = eur(cartSubtotal());
    var bar = $("[data-mini-bar]", box);
    if (bar) bar.innerHTML = barraEnvio(cartSubtotal());
  }

  function paintCount() {
    var n = cartCount();
    $$("[data-cart-count]").forEach(function (el) {
      el.textContent = n;
      el.classList.toggle("hide", n === 0);
    });
    var sub = cartSubtotal();
    /* el importe se enseña en la pastilla de la cabecera y en el botón flotante */
    $$("[data-cart-total]").forEach(function (el) { el.textContent = n ? eur(sub) : ""; });
    $$(".cart-pill").forEach(function (el) { el.classList.toggle("has-items", n > 0); });
    /* botón flotante de cesta (móvil y tablet): aparece en cuanto hay algo dentro */
    var fab = $("#cart-fab");
    if (fab) {
      var on = n > 0 && !EN_CARRITO;
      fab.hidden = false;
      fab.classList.toggle("is-on", on);
      fab.setAttribute("aria-hidden", on ? "false" : "true");
      document.body.classList.toggle("has-fab", on);
    }
    paintMini();
  }
  function bump() {
    $$("[data-cart-count]").forEach(function (el) {
      el.classList.add("is-bump");
      setTimeout(function () { el.classList.remove("is-bump"); }, 330);
    });
    $$(".cart-pill").forEach(function (el) {
      el.classList.add("is-pulse");
      setTimeout(function () { el.classList.remove("is-pulse"); }, 950);
    });
    $$(".cart-fab").forEach(function (el) {
      el.classList.add("is-bump");
      setTimeout(function () { el.classList.remove("is-bump"); }, 520);
    });
    /* en escritorio la vista rápida se abre sola 4 s para que se vea qué llevas */
    if (miniEl && cartCount()) {
      abrirMini();
      miniAuto = setTimeout(cerrarMini, 4000);
    }
  }

  /* ----------------------------------------------------------------- toast */
  var toastTimer;
  function toast(msg, linkText, href) {
    var t = $("#toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast";
      t.className = "toast";
      t.innerHTML = '<span data-toast-msg></span><a data-toast-link href="#"></a>';
      document.body.appendChild(t);
    }
    $("[data-toast-msg]", t).textContent = msg;
    var a = $("[data-toast-link]", t);
    if (linkText && href) { a.textContent = linkText; a.href = href; a.style.display = ""; }
    else { a.style.display = "none"; }
    t.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("is-on"); }, 4200);
  }

  /* ----------------------------------------------------------------- modal */
  // Pop-up de confirmación. Se usa para los dos formularios: el cliente ve
  // siempre una ventana de GRANKHA con su botón de cerrar, nunca un iframe ni
  // una redirección a un servicio de terceros.
  function modal(titulo, texto, opts) {
    opts = opts || {};
    var m = $("#grankha-modal");
    if (!m) {
      m = document.createElement("div");
      m.id = "grankha-modal";
      m.className = "modal";
      m.innerHTML =
        '<div class="modal__bg" data-mclose></div>' +
        '<div class="modal__box" role="dialog" aria-modal="true" aria-labelledby="gm-t" aria-describedby="gm-p">' +
          '<div class="modal__ico" aria-hidden="true"></div>' +
          '<h2 class="modal__t" id="gm-t"></h2>' +
          '<p class="modal__p" id="gm-p"></p>' +
          '<button type="button" class="btn modal__btn" data-mclose>Cerrar</button>' +
        '</div>';
      document.body.appendChild(m);
      m.addEventListener("click", function (e) {
        if (e.target.closest("[data-mclose]")) closeModal();
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && m.classList.contains("is-on")) closeModal();
      });
    }
    var ico = $(".modal__ico", m);
    ico.className = "modal__ico" + (opts.error ? " modal__ico--err" : "");
    ico.innerHTML = opts.error
      ? '<svg viewBox="0 0 24 24"><path d="M12 8v5"/><path d="M12 16.5v.5"/></svg>'
      : '<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>';
    $("#gm-t", m).textContent = titulo;
    $("#gm-p", m).textContent = texto;
    m.classList.add("is-on");
    document.documentElement.classList.add("no-scroll");
    var b = $(".modal__btn", m);
    if (b) setTimeout(function () { b.focus(); }, 40);
  }

  function closeModal() {
    var m = $("#grankha-modal");
    if (m) m.classList.remove("is-on");
    document.documentElement.classList.remove("no-scroll");
  }

  /* ----------------------------------------------------------------- envío */
  function shippingOptions() {
    return (CFG.shipping && CFG.shipping.options) || [];
  }
  function shippingFor(id, subtotal) {
    var o = shippingOptions().filter(function (s) { return s.id === id; })[0] || shippingOptions()[0];
    if (!o) return { id: "none", name: "Envío", price: 0, next: null };
    var price = 0, next = null;
    if (o.tiers && o.tiers.length) {
      price = o.tiers[0].price;
      o.tiers.forEach(function (t) {
        if (subtotal >= t.min) price = t.price;
      });
      // siguiente tramo al que aspira el cliente (para el aviso del carrito)
      var pend = o.tiers.filter(function (t) { return subtotal < t.min; });
      if (pend.length) next = { min: pend[0].min, price: pend[0].price };
    } else {
      price = o.price || 0;
      if (o.free_from && subtotal >= o.free_from) price = 0;
    }
    return { id: o.id, name: o.name, price: price, eta: o.eta, next: next, tiers: o.tiers };
  }
  // Zonas sin IVA español (el impuesto se liquida en destino: IGIC/IPSI)
  function zonaSinIva(id) { return id === "can"; }
  function round2(n) { return Math.round(n * 100) / 100; }

  function totals(lines, shipId) {
    var subtotal = 0, units = 0;
    lines.forEach(function (l) {
      var p = byslug[l.slug];
      if (!p) return;
      subtotal += p.price * l.qty;      // precios de catálogo, con IVA incluido
      units += l.qty;
    });
    var id = shipId || (CFG.shipping && CFG.shipping.default);
    var sinIva = zonaSinIva(id);
    var vatRate = (CFG.shipping && CFG.shipping.vat) || 0.21;
    // En Canarias, Ceuta y Melilla los precios se muestran sin IVA
    var base = sinIva ? subtotal / (1 + vatRate) : subtotal;
    var ship = shippingFor(id, base);
    var shipPrice = sinIva ? ship.price / (1 + vatRate) : ship.price;
    return {
      subtotal: base, catalogo: subtotal, units: units, sinIva: sinIva, vatRate: vatRate,
      ship: { id: ship.id, name: ship.name, price: round2(shipPrice), next: ship.next, eta: ship.eta },
      total: round2(base + shipPrice),
      vat: sinIva ? 0 : subtotal - subtotal / (1 + vatRate)
    };
  }

  // El país del formulario manda sobre la zona de envío
  var ZONA_POR_PAIS = { "España": "pen", "Portugal": "prt", "Francia": "ue", "Alemania": "ue",
                        "Italia": "ue", "Países Bajos": "ue", "Bélgica": "ue", "Irlanda": "ue",
                        "Austria": "ue", "Luxemburgo": "ue" };

  /* ------------------------------------------------- añadir desde listados */
  function bindAddButtons(root) {
    $$("[data-add]", root || document).forEach(function (btn) {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var qty = btn.getAttribute("data-qty");
        if (!qty) {
          var box = $("[data-pdqty] input");
          qty = box ? box.value : 1;
        }
        addToCart(btn.getAttribute("data-add"), qty);
        /* confirmación en el propio botón: "Añadido" durante un segundo */
        btn.classList.add("is-added");
        clearTimeout(btn._ok);
        btn._ok = setTimeout(function () { btn.classList.remove("is-added"); }, 1300);
      });
    });
  }

  /* --------------------------------------------------------- steppers qty */
  function bindQty(root) {
    $$("[data-qty],[data-pdqty]", root || document).forEach(function (box) {
      if (box.dataset.bound) return;
      box.dataset.bound = "1";
      var input = $("input", box);
      var slug = box.getAttribute("data-qty");
      var max = parseInt(box.getAttribute("data-max") || "99", 10);
      function set(v) {
        v = Math.max(1, Math.min(max, v || 1));
        input.value = v;
        if (slug) setQty(slug, v);
      }
      $$("button", box).forEach(function (b) {
        b.addEventListener("click", function () {
          set(parseInt(input.value, 10) + parseInt(b.getAttribute("data-step"), 10));
        });
      });
      input.addEventListener("change", function () { set(parseInt(input.value, 10)); });
    });
  }

  /* --------------------------------------------------------- lote de compra */
  function bindBuy(root) {
    $$("[data-buy]", root || document).forEach(function (btn) {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var box = $("[data-pdqty] input") || $("[data-qty] input");
        addToCart(btn.getAttribute("data-buy"), box ? box.value : 1);
        location.href = "carrito";
      });
    });
  }

  /* --------------------------------------------------------------- tienda */
  function initShop() {
    var grid = $("#shop-grid");
    if (!grid) return;
    var state = { cat: "todo", sort: "destacados", q: "", aud: "todos" };
    var cards = $$(".card[data-cat]", grid);

    function apply() {
      var shown = 0;
      cards.forEach(function (c) {
        var okCat = state.cat === "todo" || c.getAttribute("data-cat") === state.cat;
        var aud = c.getAttribute("data-aud") || "ambos";
        var okAud = state.aud === "todos" || aud === "ambos" || aud === state.aud;
        var q = state.q.trim().toLowerCase();
        var hay = (c.getAttribute("data-search") || "").toLowerCase();
        var okQ = !q || hay.indexOf(q) !== -1;
        if (okCat && okAud && okQ) { c.classList.remove("hide"); shown++; }
        else c.classList.add("hide");
      });
      var none = $("#shop-empty");
      if (none) none.classList.toggle("hide", shown > 0);
      var count = $("#shop-count");
      if (count) count.textContent = shown + (shown === 1 ? " producto" : " productos");
    }

    var container = $(".products", grid) || grid;

    function sort() {
      var sorters = {
        "precio-asc": function (a, b) { return +a.dataset.price - +b.dataset.price; },
        "precio-desc": function (a, b) { return +b.dataset.price - +a.dataset.price; },
        "nombre": function (a, b) { return a.dataset.search.localeCompare(b.dataset.search, "es"); },
        "destacados": function (a, b) { return +a.dataset.rank - +b.dataset.rank; }
      };
      var s = sorters[state.sort] || sorters["destacados"];
      cards.slice().sort(s).forEach(function (c) { container.appendChild(c); });
    }

    $$("[data-filter]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $$("[data-filter]").forEach(function (c) { c.classList.remove("is-on"); });
        chip.classList.add("is-on");
        state.cat = chip.getAttribute("data-filter");
        apply();
      });
    });
    $$("[data-aud]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $$("[data-aud]").forEach(function (c) { c.classList.remove("is-on"); });
        chip.classList.add("is-on");
        state.aud = chip.getAttribute("data-aud");
        apply();
      });
    });
    var sel = $("#shop-sort");
    if (sel) sel.addEventListener("change", function () { state.sort = sel.value; sort(); });
    var search = $("#shop-search");
    if (search) search.addEventListener("input", function () { state.q = search.value; apply(); });

    // filtro por querystring: tienda.html?cat=camas
    var m = location.search.match(/[?&]cat=([^&]+)/);
    if (m) {
      var chip = $('[data-filter="' + m[1] + '"]');
      if (chip) chip.click();
    }
    var mAud = location.search.match(/[?&]aud=([^&]+)/);
    if (mAud) {
      var chipA = $('[data-aud="' + mAud[1] + '"]');
      if (chipA) chipA.click();
    }
    sort(); apply();
  }

  /* -------------------------------------------------------------- carrito */
  // Al volver de la pasarela: confirmación del pedido (o aviso de cancelado)
  function initGracias() {
    var q = location.search;
    var ok = /[?&]estado=ok/.test(q);
    var cancelado = /[?&]estado=cancelado/.test(q);
    if (!ok && !cancelado) return;
    var ref = (q.match(/[?&]pedido=([^&]+)/) || [])[1] || "";
    var main = document.querySelector("main");
    if (!main) return;

    if (cancelado) {
      var aviso = document.createElement("div");
      aviso.className = "wrap";
      aviso.style.padding = "24px 0 0";
      aviso.innerHTML = '<div class="notice"><b>No se ha completado el pago.</b><br>' +
        'Tu cesta sigue aquí y no se te ha cobrado nada. Puedes volver a intentarlo cuando quieras.</div>';
      main.insertBefore(aviso, main.firstElementChild);
      return;
    }

    // pedido pagado: limpiamos la cesta y damos la bienvenida
    clearCart();
    paintCount();
    main.innerHTML =
      '<section class="section section--tight"><div class="wrap" style="max-width:720px">' +
        '<p class="kicker">Pedido confirmado</p>' +
        '<h1 class="h2">Gracias de corazón.</h1>' +
        '<p class="lede mt-s">Hemos recibido tu pago' + (ref ? ' del pedido <b>' + ref + '</b>' : '') +
          '. Te acabamos de enviar el recibo por correo con todos los datos de la compra.</p>' +
        '<div class="donate-note" style="margin:26px 0"><div><b>Qué pasa ahora</b><br>' +
          '<span style="font-size:.9rem">1. Preparamos tu pedido y lo confirmamos con el almacén.<br>' +
          '2. En cuanto salga, te escribimos con el enlace de seguimiento.<br>' +
          '3. Lo recibes en 3-8 días laborables y tienes 30 días para devolverlo.</span></div></div>' +
        '<p class="small">Si algo no cuadra, respóndenos a ese correo o escríbenos desde la página de contacto ' +
          'con la referencia del pedido.</p>' +
        '<div class="pd__buy"><a class="btn" href="tienda">Seguir comprando</a>' +
        '<a class="btn btn--ghost" href="compromiso">Nuestra historia</a></div>' +
      '</div></section>';
    window.scrollTo(0, 0);
  }

  function initCart() {
    var root = $("#cart-root");
    if (!root) return;
    var list = $("#cart-lines"), sum = $("#cart-summary");
    var shipBox = $("#cart-shipping");
    var shipId = (CFG.shipping && CFG.shipping.default) || "pen";
    var paisAplicado = false;

    function render() {
      var lines = readCart();
      var checkout = $("#checkout");
      if (checkout) checkout.classList.toggle("hide", !lines.length);
      if (!lines.length) {
        root.classList.add("hide");
        $("#cart-empty").classList.remove("hide");
        paintCount();
        return;
      }
      root.classList.remove("hide");
      $("#cart-empty").classList.add("hide");

      list.innerHTML = lines.map(function (l) {
        var p = byslug[l.slug];
        if (!p) return "";
        return '' +
        '<div class="line">' +
          '<a class="line__media" href="' + p.url + '"><img src="' + (p.thumb || "") + '" alt="' + esc(p.title) + '" loading="lazy" decoding="async"></a>' +
          '<div>' +
            '<a class="line__t" href="' + p.url + '">' + esc(p.title) + '</a>' +
            '<div class="line__s">' + esc(p.subtitle || "") + '</div>' +
            (p.packOf ? '<div class="line__s">Incluye: ' + esc(p.packOf) + '</div>' : '') +
            '<div class="line__s mono">' + eur(p.price) + ' ud. · IVA incl.</div>' +
            '<button class="line__rm" data-rm="' + p.slug + '">Quitar</button>' +
          '</div>' +
          '<div class="line__right">' +
            '<div class="qty" data-qty="' + p.slug + '" data-max="' + (p.stock || 99) + '">' +
              '<button type="button" data-step="-1" aria-label="Menos">−</button>' +
              '<input type="number" value="' + l.qty + '" min="1" max="' + (p.stock || 99) + '" aria-label="Cantidad">' +
              '<button type="button" data-step="1" aria-label="Más">+</button>' +
            '</div>' +
            '<div class="price mono">' + eur(p.price * l.qty) + '</div>' +
          '</div>' +
        '</div>';
      }).join("");

      var t = totals(lines, shipId);
      sum.innerHTML = '' +
        '<h3 class="h4">Resumen del pedido</h3>' +
        '<p class="small mb-m">' + (t.sinIva ? 'Precios sin IVA · IGIC/IPSI en destino' : 'Precios con IVA incluido') +
          ' · Entrega en 3-8 días laborables</p>' +
        '<div class="sum-row"><span>Subtotal (' + t.units + ' art.)</span><span class="mono">' + eur(t.subtotal) + '</span></div>' +
        '<div class="sum-row"><span>Envío · ' + esc(t.ship.name) + '</span><span class="mono">' +
          (t.ship.price === 0 ? "Gratis" : eur(t.ship.price)) + '</span></div>' +
        (t.ship.next && t.ship.next.price < t.ship.price
          ? '<div class="free-bar">Añade <b>' + eur(t.ship.next.min - t.subtotal) +
            '</b> más y el envío baja a ' + (t.ship.next.price === 0 ? 'gratis' : eur(t.ship.next.price)) + '</div>'
          : '') +
        (t.sinIva
          ? '<div class="sum-row"><span>IVA</span><span class="mono">No aplicable</span></div>' +
            '<div class="sum-row"><span class="small">En Canarias, Ceuta y Melilla el impuesto (IGIC/IPSI) y la aduana se abonan en destino.</span><span></span></div>'
          : '<div class="sum-row"><span>IVA incluido (' + Math.round(t.vatRate * 100) + '%)</span><span class="mono">' + eur(t.vat) + '</span></div>') +
        '<div class="sum-row sum-row--total"><span>Total</span><span class="mono">' + eur(t.total) + '</span></div>' +
        freeBar(t.subtotal, shipId) +
        '<a class="btn btn--block mt-m" href="#checkout">Finalizar compra</a>' +
        '<p class="small mt-s">Pago seguro con tarjeta. No guardamos datos de pago.</p>';

      shipBox.innerHTML = '<div class="field"><label for="ship-sel">Método de envío</label>' +
        '<div class="ship-pick">' + shippingOptions().map(function (o) {
          var s2 = shippingFor(o.id, t.subtotal);
          var gr = (o.tiers || []).filter(function (x) { return x.price === 0; })[0];
          return '<label class="ship-opt' + (o.id === shipId ? " is-on" : "") + '">' +
            '<input type="radio" name="ship" value="' + o.id + '"' + (o.id === shipId ? " checked" : "") + '>' +
            '<span><b>' + esc(o.name) + '</b><br><span class="small">' + esc(o.eta || "") +
            (gr ? ' · envío gratis desde ' + eur(gr.min) : '') + '</span></span>' +
            '<span class="mono" style="margin-left:auto;white-space:nowrap">' + (s2.price === 0 ? "Gratis" : eur(s2.price)) + '</span>' +
          '</label>';
        }).join("") + '</div></div>' +
        '<p class="small mt-s">' + esc((CFG.shipping && CFG.shipping.note) || "") + '</p>';

      bindQty(list);
      $$("[data-rm]", list).forEach(function (b) {
        b.addEventListener("click", function () {
          removeLine(b.getAttribute("data-rm"));
          toast("Producto eliminado");
          render();
        });
      });
      $$('input[name="ship"]').forEach(function (r) {
        r.addEventListener("change", function () {
          shipId = r.value;
          render();
        });
      });
      // cambiar el país del formulario cambia la zona de envío y su precio
      var pais = $("#f-country");
      if (pais && !pais.dataset.bound) {
        pais.dataset.bound = "1";
        pais.addEventListener("change", function () {
          var z = ZONA_POR_PAIS[pais.value];
          if (z && z !== shipId) { shipId = z; render(); }
        });
      }
      // al cargar la página, el país del formulario fija la zona una sola vez
      // (si no, no se podría elegir Canarias o Baleares a mano)
      if (pais && !paisAplicado) {
        paisAplicado = true;
        var zz = ZONA_POR_PAIS[pais.value];
        if (zz && zz !== shipId) { shipId = zz; render(); return; }
      }
      paintCount();
      var tc = $("#to-checkout");
      if (tc) tc.href = "#checkout";
    }

    function freeBar(subtotal, shipId) {
      var zona = shippingFor(shipId || (CFG.shipping && CFG.shipping.default), subtotal);
      var libre = (zona.tiers || []).filter(function (x) { return x.price === 0; })[0];
      if (!libre) return "";
      var nombre = zona.name || "";
      if (subtotal >= libre.min) {
        return '<div class="free-bar">✓ Envío gratuito (' + esc(nombre) + ') aplicado</div>';
      }
      var falta = libre.min - subtotal, pct = Math.min(100, (subtotal / libre.min) * 100);
      return '<div class="free-bar">Te faltan <b>' + eur(falta) + '</b> para el envío gratuito (' + esc(nombre) + ')' +
        '<div class="free-bar__track"><div class="free-bar__fill" style="width:' + pct + '%"></div></div></div>';
    }

    document.addEventListener("grankha:cart", render);
    render();

    // ---- checkout
    var form = $("#checkout-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!form.reportValidity()) return;
        var lines = readCart();
        if (!lines.length) { toast("Tu carrito está vacío"); return; }
        var t = totals(lines, shipId);
        var data = {};
        new FormData(form).forEach(function (v, k) { data[k] = v; });
        var order = {
          reference: "GRK-" + new Date().toISOString().slice(2, 10).replace(/-/g, "") + "-" +
            Math.random().toString(36).slice(2, 6).toUpperCase(),
          created_at: new Date().toISOString(),
          currency: "EUR",
          lines: lines.map(function (l) {
            var p = byslug[l.slug];
            return {
              sku: p.sku, slug: p.slug, kind: p.kind || "product",
              name: p.title + " · " + (p.subtitle || ""),
              components: p.components || null,          // los packs se piden por sus piezas
              qty: l.qty, unit_price: p.price, line_total: +(p.price * l.qty).toFixed(2),
              weight_g: p.weight_g || 0
            };
          }),
          subtotal: +t.subtotal.toFixed(2),
          shipping_method: t.ship.name,
          shipping_price: +t.ship.price.toFixed(2),
          vat_included: +t.vat.toFixed(2),
          total: +t.total.toFixed(2),
          customer: {
            name: data.name, email: data.email, phone: data.phone,
            address: data.address, address2: data.address2 || "", zip: data.zip,
            city: data.city, province: data.province || "", country: data.country,
            nif: data.nif || ""
          },
          notes: data.notes || "",
          zone: shipId
        };

        var endpoint = CFG.checkout && CFG.checkout.endpoint;
        var pay = $("#checkout-pay");
        form.querySelector("button[type=submit]").disabled = true;

        function done(msg) {
          try { localStorage.setItem(ORDER_KEY, JSON.stringify(order)); } catch (e) {}
          var body = order.lines.map(function (l) {
            return "• " + l.qty + " × " + l.name + " — " + eur(l.line_total);
          }).join("\n");
          var mail = "mailto:" + CFG.contactEmail +
            "?subject=" + encodeURIComponent("Pedido " + order.reference) +
            "&body=" + encodeURIComponent(
              "Pedido " + order.reference + "\n\n" + body + "\n\nSubtotal: " + eur(order.subtotal) +
              "\nEnvío (" + order.shipping_method + "): " + eur(order.shipping_price) +
              (order.zone === "can" ? "\nIVA: no aplicable (IGIC/IPSI en destino)"
                                    : "\nIVA incluido: " + eur(order.vat_included)) +
              "\nTOTAL: " + eur(order.total) +
              "\n\nDatos de envío:\n" + order.customer.name + "\n" + order.customer.address +
              (order.customer.address2 ? " " + order.customer.address2 : "") + "\n" +
              order.customer.zip + " " + order.customer.city + "\n" + order.customer.country +
              "\nTel: " + (order.customer.phone || "—") + "\nEmail: " + order.customer.email +
              (order.notes ? "\n\nNotas: " + order.notes : ""));

          pay.classList.remove("hide");
          pay.innerHTML = '' +
            '<div class="notice"><b>Pedido ' + order.reference + ' preparado.</b><br>' +
            (msg || "El pago con tarjeta se activará muy pronto. Hemos guardado tu pedido; puedes confirmarlo por email y te enviaremos el enlace de pago seguro.") +
            '</div>' +
            '<p class="small mt-s">Total a pagar: <b class="mono">' + eur(order.total) + '</b> (IVA y envío incluidos)</p>' +
            '<div class="pd__buy"><a class="btn" href="' + mail + '">Confirmar por email</a>' +
            '<a class="btn btn--ghost" href="tienda">Seguir comprando</a></div>';
          // el pedido ya está hecho: vaciamos la cesta (sin duplicados) pero
          // dejamos a la vista el resumen del pedido y el botón de confirmación
          clearCart();
          paintCount();
          var _l = $("#cart-lines");
          if (_l) _l.innerHTML = '<p class="small">Tu cesta se ha vaciado: el pedido <b>' + order.reference +
            '</b> queda registrado. Completa el pago con el botón de abajo.</p>';
          var _s = $("#cart-summary"); if (_s) _s.innerHTML = "";
          var _sh = $("#cart-shipping"); if (_sh) _sh.innerHTML = "";
          var _f = $("#checkout-form"); if (_f) _f.classList.add("hide");
          pay.scrollIntoView({ behavior: "smooth", block: "center" });
          form.querySelector("button[type=submit]").disabled = false;
          toast("Pedido " + order.reference + " guardado", "Ver resumen", "#checkout-pay");
        }

        if (endpoint) {
          fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(order)
          }).then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json().catch(function () { return {}; });
          }).then(function (res) {
            if (res && res.url) { location.href = res.url; return; }  // Stripe Checkout
            clearCart(); render();
            done(res && res.message);
          }).catch(function (err) {
            form.querySelector("button[type=submit]").disabled = false;
            toast("No se pudo enviar el pedido. Inténtalo de nuevo.");
            console.error(err);
          });
        } else {
          done();
        }
      });
    }
  }

  /* ------------------------------------------------------ ficha producto */
  function initProduct() {
    var root = $("#pd");
    if (!root) return;
    var slug = root.getAttribute("data-slug");
    // los packs muestran sus piezas en la ficha
    var box = $("#pd-pack");
    if (box) {
      var sku = root.getAttribute("data-sku");
      var packs = (window.GRANKHA_CATALOG || []).filter(function (p) { return p.kind === "pack"; });
      var conmigo = (window.GRANKHA_PACKS || []).filter(function (p) {
        return (p.components || []).some(function (c) { return c.sku === sku; });
      });
      if (conmigo.length) {
        box.innerHTML = '<p class="small mb-m">Este artículo forma parte de estos packs:</p><div class="filters">' +
          conmigo.map(function (p) {
            return '<a class="chip" href="' + p.slug + '">' + p.name + '</a>';
          }).join("") + '</div>';
      }
    }

    // variantes: si es un arnés, enlaza variantes del mismo modelo/talla
    $$("[data-variant]").forEach(function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); location.href = a.getAttribute("href"); });
    });
    bindQty(document);
    bindBuy(document);
    bindAddButtons(document);

    // aviso de stock bajo
    var st = $("[data-stock]");
    if (st) {
      var s = parseInt(st.getAttribute("data-stock"), 10);
      st.textContent = s > 10 ? "Disponible · envío en 3-8 días laborables"
        : (s > 0 ? "Últimas unidades (" + s + ")" : "Agotado");
    }
  }

  /* ------------------------------------------------------------- menú móvil */
  function initMenu() {
    var btn = $("#menu-btn");
    if (!btn) return;
    var panel = document.createElement("div");
    panel.className = "menu-panel hide";
    panel.style.cssText = "position:fixed;inset:0;background:#fff;z-index:80;padding:84px var(--pad) 40px;overflow:auto";
    panel.innerHTML = '<button class="icon-btn" id="menu-close" aria-label="Cerrar" style="position:absolute;top:22px;right:var(--pad);font-size:1.5rem">×</button>' +
      '<nav style="display:grid;gap:6px;font-size:1.6rem;letter-spacing:-.02em">' +
      ['tienda|Tienda', 'tienda?cat=packs|Packs', 'compromiso|Compromiso',
       'contacto|Contacto']
        .map(function (i) {
          var parts = i.split("|");
          return '<a href="' + parts[0] + '" style="padding:12px 0;border-bottom:1px solid var(--line)">' + parts[1] + '</a>';
        }).join("") +
      '</nav>';
    document.body.appendChild(panel);
    function toggle(open) {
      panel.classList.toggle("hide", !open);
      document.body.style.overflow = open ? "hidden" : "";
    }
    btn.addEventListener("click", function () { toggle(panel.classList.contains("hide")); });
    panel.addEventListener("click", function (e) {
      if (e.target.id === "menu-close" || e.target.tagName === "A") toggle(false);
    });
  }

  /* ---------------------------------------------------------------- reveal */
  function initReveal() {
    var els = $$(".reveal");
    if (!els.length) return;
    function show(el, i) {
      setTimeout(function () { el.classList.add("is-in"); }, ((i || 0) % 4) * 70);
    }
    if (!("IntersectionObserver" in window)) { els.forEach(show); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en, i) {
        if (en.isIntersecting) { show(en.target, i); io.unobserve(en.target); }
      });
    }, { rootMargin: "120px 0px 40px 0px", threshold: .05 });
    els.forEach(function (el) {
      io.observe(el);
      // red de seguridad: lo que ya está a la vista se muestra siempre
      var r = el.getBoundingClientRect();
      if (r.top < (window.innerHeight || 800) * 1.35) show(el, 0);
    });
    // y ante cualquier cambio de tamaño/scroll, reintento puntual
    window.addEventListener("resize", function () {
      els.forEach(function (el) {
        if (!el.classList.contains("is-in")) {
          var r = el.getBoundingClientRect();
          if (r.top < (window.innerHeight || 800) * 1.35) show(el, 0);
        }
      });
    }, { passive: true });
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function initNewsletter() {
    $$("form[data-news]").forEach(function (f) {
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        var input = $("input[type=email]", f);
        var ok = $("input[type=checkbox]", f);
        var btn = f.querySelector("button[type=submit]") || f.querySelector("button");

        // Sin email válido no se avanza.
        if (!input || !input.value.trim() || !input.checkValidity()) {
          if (input) input.focus();
          modal("Revisa tu email", "Escribe una dirección de correo válida para poder suscribirte.", { error: true });
          return;
        }
        // Sin consentimiento expreso no se envía nada: bloqueamos el submit.
        if (ok && !ok.checked) {
          ok.focus();
          modal("Falta tu consentimiento",
                "Debes marcar la casilla y aceptar la política de privacidad antes de suscribirte.",
                { error: true });
          return;
        }

        var email = input.value.trim();
        if (btn) btn.disabled = true;
        // Se envía a nuestro propio endpoint. Quien habla con el destino final
        // es el servidor: el navegador no ve ningún servicio de terceros.
        fetch(CFG.newsletterEndpoint || "/api/newsletter", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, consent: true })
        }).then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        }).then(function () {
          f.reset();
          modal("¡Bienvenido a la familia GRANKHA!",
                "Hemos registrado tu correo. Te escribiremos muy pronto con consejos de cuidado, novedades y avances en investigación animal.");
        }).catch(function () {
          modal("No hemos podido registrarte",
                "Vuelve a intentarlo en unos minutos o escríbenos a " + CFG.contactEmail + " y te añadimos nosotros.",
                { error: true });
        }).then(function () { if (btn) btn.disabled = false; });
      });
    });
  }

  function initContact() {
    $$("form[data-contact]").forEach(function (f) {
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!f.reportValidity()) return;
        var d = {};
        new FormData(f).forEach(function (v, k) { d[k] = v; });
        var btn = f.querySelector("button[type=submit]") || f.querySelector("button");
        if (btn) btn.disabled = true;

        // Consentimiento obligatorio: sin la casilla marcada no se envía.
        var ok = f.querySelector("input[type=checkbox]");
        if (ok && !ok.checked) {
          ok.focus();
          if (btn) btn.disabled = false;
          modal("Falta tu consentimiento",
                "Debes marcar la casilla y aceptar la política de privacidad antes de enviar el mensaje.",
                { error: true });
          return;
        }

        function fallback() {
          if (btn) btn.disabled = false;
          modal("No hemos podido enviar tu mensaje",
                "Escríbenos a " + CFG.contactEmail + " y te atendemos igualmente. Sentimos las molestias.",
                { error: true });
        }

        // El mensaje va a nuestro propio endpoint; el servidor es quien lo
        // entrega. El navegador no contacta con ningún tercero.
        var ep = CFG.contactEndpoint || "/api/contact";
        fetch(ep, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(d)
        }).then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        }).then(function () {
          f.reset();
          modal("Mensaje enviado",
                "Gracias por escribirnos. Te contestamos en 24 horas laborables al correo que nos has indicado.");
        }).catch(function () {
          fallback();
        }).then(function () { if (btn) btn.disabled = false; });
      });
    });
  }

  /* -------------------------------------------------------------- galería */
  function initGallery() {
    $$("[data-gallery]").forEach(function (g) {
      var track = $(".gallery__track", g);
      var slides = $$(".gallery__slide", g);
      if (!track || slides.length < 2) { $$(".gallery__nav", g).forEach(function (b) { b.remove(); }); return; }
      var dots = $("[data-gdots]", g), pos = $("[data-gpos]", g), i = 0;

      if (dots) {
        dots.innerHTML = slides.map(function (_, k) {
          return '<button type="button" aria-label="Ver pieza ' + (k + 1) + '"></button>';
        }).join("");
      }
      var dbs = dots ? $$("button", dots) : [];

      function go(n) {
        i = (n + slides.length) % slides.length;
        track.style.transform = "translateX(" + (-i * 100) + "%)";
        dbs.forEach(function (d, k) { d.classList.toggle("is-on", k === i); });
        if (pos) pos.textContent = (i + 1) + " / " + slides.length;
        slides.forEach(function (s2, k) {
          s2.setAttribute("aria-hidden", k === i ? "false" : "true");
          var a = $("a", s2); if (a) a.setAttribute("tabindex", k === i ? "0" : "-1");
        });
      }
      $$("[data-gprev]", g).forEach(function (b) { b.addEventListener("click", function () { go(i - 1); }); });
      $$("[data-gnext]", g).forEach(function (b) { b.addEventListener("click", function () { go(i + 1); }); });
      dbs.forEach(function (d, k) { d.addEventListener("click", function () { go(k); }); });
      g.setAttribute("tabindex", "0");
      g.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") { go(i - 1); }
        if (e.key === "ArrowRight") { go(i + 1); }
      });
      var x0 = null, y0 = null;
      g.addEventListener("touchstart", function (e) {
        x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
      }, { passive: true });
      g.addEventListener("touchend", function (e) {
        if (x0 === null) return;
        var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
        if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { go(dx < 0 ? i + 1 : i - 1); }
        x0 = y0 = null;
      }, { passive: true });
      go(0);
    });
  }

  function initMini() {
    var wrap = $("[data-cart-wrap]");
    if (!wrap) return;
    miniEl = $("#mini-cart");
    if (!miniEl) return;
    /* ratón: se abre al pasar por encima y se cierra al salir */
    wrap.addEventListener("mouseenter", function () { clearTimeout(miniTimer); abrirMini(); });
    wrap.addEventListener("mouseleave", function () {
      clearTimeout(miniTimer);
      miniTimer = setTimeout(cerrarMini, 240);
    });
    wrap.addEventListener("focusin", function () { clearTimeout(miniTimer); abrirMini(); });
    wrap.addEventListener("focusout", function () {
      clearTimeout(miniTimer);
      miniTimer = setTimeout(cerrarMini, 240);
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) cerrarMini();
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") cerrarMini(); });
    var x = $("[data-mini-close]", miniEl);
    if (x) x.addEventListener("click", function (e) { e.preventDefault(); cerrarMini(); });
    paintMini();
  }

  function initMisc() {
    $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });
    var t = $("#toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast"; t.className = "toast";
      t.innerHTML = '<span data-toast-msg></span><a data-toast-link href="#"></a>';
      document.body.appendChild(t);
    }
  }

  /* ------------------------------------------------------------------ init */
  function boot() {
    initMisc();
    paintCount();
    bindAddButtons(document);
    bindQty(document);
    bindBuy(document);
    initShop();
    initProduct();
    initCart();
    initGracias();
    initMenu();
    initGallery();
    initMini();
    initContact();
    initReveal();
    initNewsletter();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.GRANKHA = { add: addToCart, remove: removeLine, clear: clearCart, cart: readCart, totals: totals, toast: toast, eur: eur, num: num };
})();

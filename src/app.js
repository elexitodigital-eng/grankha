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
    toast("Añadido al carrito — " + name, "Ver carrito", "carrito.html");
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
  function paintCount() {
    var n = cartCount();
    $$("[data-cart-count]").forEach(function (el) {
      el.textContent = n;
      el.classList.toggle("hide", n === 0);
    });
    if (n === 0) $$("[data-cart-count]").forEach(function (el) { el.textContent = "0"; });
  }
  function bump() {
    $$("[data-cart-count]").forEach(function (el) {
      el.classList.add("is-bump");
      setTimeout(function () { el.classList.remove("is-bump"); }, 320);
    });
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

  /* ----------------------------------------------------------------- envío */
  function shippingOptions() {
    return (CFG.shipping && CFG.shipping.options) || [];
  }
  function shippingFor(id, subtotal) {
    var o = shippingOptions().filter(function (s) { return s.id === id; })[0] || shippingOptions()[0];
    if (!o) return { id: "none", name: "Envío", price: 0 };
    var price = o.price;
    if (o.free_from && subtotal >= o.free_from) price = 0;
    return { id: o.id, name: o.name, price: price, eta: o.eta, free_from: o.free_from };
  }
  function totals(lines, shipId) {
    var subtotal = 0, units = 0;
    lines.forEach(function (l) {
      var p = byslug[l.slug];
      if (!p) return;
      subtotal += p.price * l.qty;
      units += l.qty;
    });
    var ship = shippingFor(shipId || (CFG.shipping && CFG.shipping.default), subtotal);
    var vatRate = (CFG.shipping && CFG.shipping.vat) || 0.21;
    return {
      subtotal: subtotal, ship: ship, total: subtotal + ship.price, units: units,
      vat: subtotal - subtotal / (1 + vatRate)
    };
  }

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
        location.href = "carrito.html";
      });
    });
  }

  /* --------------------------------------------------------------- tienda */
  function initShop() {
    var grid = $("#shop-grid");
    if (!grid) return;
    var state = { cat: "todo", sort: "destacados", q: "" };
    var cards = $$(".card[data-cat]", grid);

    function apply() {
      var shown = 0;
      cards.forEach(function (c) {
        var okCat = state.cat === "todo" || c.getAttribute("data-cat") === state.cat;
        var okCol = true, q = state.q.trim().toLowerCase();
        var hay = (c.getAttribute("data-search") || "").toLowerCase();
        var okQ = !q || hay.indexOf(q) !== -1;
        if (okCat && okCol && okQ) { c.classList.remove("hide"); shown++; }
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
    var sel = $("#shop-sort");
    if (sel) sel.addEventListener("change", function () { state.sort = sel.value; sort(); });
    var search = $("#shop-search");
    if (search) search.addEventListener("input", function () { state.q = search.value; apply(); });

    // filtro por querystring: tienda.html?cat=camas
    var m = location.search.match(/[?&]cat=([^&]+)/);
    if (m) {
      var chip = $('[data-filter="' + m[1] + '"]');
      if (chip) { chip.click(); }
    } else { sort(); apply(); }
    sort(); apply();
  }

  /* -------------------------------------------------------------- carrito */
  function initCart() {
    var root = $("#cart-root");
    if (!root) return;
    var list = $("#cart-lines"), sum = $("#cart-summary");
    var shipBox = $("#cart-shipping");
    var shipId = (CFG.shipping && CFG.shipping.default) || "pen";

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
        '<p class="small mb-m">Precios con IVA incluido · Entrega en 3-8 días laborables</p>' +
        '<div class="sum-row"><span>Subtotal (' + t.units + ' art.)</span><span class="mono">' + eur(t.subtotal) + '</span></div>' +
        '<div class="sum-row"><span>Envío · ' + esc(t.ship.name) + '</span><span class="mono">' +
          (t.ship.price === 0 ? "Gratis" : eur(t.ship.price)) + '</span></div>' +
        '<div class="sum-row"><span>IVA incluido (21%)</span><span class="mono">' + eur(t.vat) + '</span></div>' +
        '<div class="sum-row sum-row--total"><span>Total</span><span class="mono">' + eur(t.total) + '</span></div>' +
        freeBar(t.subtotal) +
        '<a class="btn btn--block mt-m" href="#checkout">Finalizar compra</a>' +
        '<p class="small mt-s">Pago seguro con tarjeta. No guardamos datos de pago.</p>';

      shipBox.innerHTML = '<div class="field"><label for="ship-sel">Método de envío</label>' +
        '<div class="ship-pick">' + shippingOptions().map(function (o) {
          var free = o.free_from && t.subtotal >= o.free_from;
          var price = free ? 0 : o.price;
          return '<label class="ship-opt' + (o.id === shipId ? " is-on" : "") + '">' +
            '<input type="radio" name="ship" value="' + o.id + '"' + (o.id === shipId ? " checked" : "") + '>' +
            '<span><b>' + esc(o.name) + '</b><br><span class="small">' + esc(o.eta || "") +
            (o.free_from ? ' · gratis desde ' + eur(o.free_from) : '') + '</span></span>' +
            '<span class="mono" style="margin-left:auto;white-space:nowrap">' + (price === 0 ? "Gratis" : eur(price)) + '</span>' +
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
      paintCount();
      var tc = $("#to-checkout");
      if (tc) tc.href = "#checkout";
    }

    function freeBar(subtotal) {
      var free = (CFG.shipping && CFG.shipping.freeFromPeninsular) || 49;
      if (subtotal >= free) return '<div class="free-bar">✓ Envío gratuito (península) aplicado</div>';
      var falta = free - subtotal, pct = Math.min(100, (subtotal / free) * 100);
      return '<div class="free-bar">Te faltan <b>' + eur(falta) + '</b> para el envío gratuito en península' +
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
              sku: p.sku, slug: p.slug, name: p.title + " · " + (p.subtitle || ""),
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
          notes: data.notes || ""
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
              "\nIVA incluido: " + eur(order.vat_included) + "\nTOTAL: " + eur(order.total) +
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
            '<a class="btn btn--ghost" href="tienda.html">Seguir comprando</a></div>';
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
      ['index.html|Inicio', 'tienda.html|Tienda', 'compromiso.html|Compromiso',
       'envios.html|Envíos y devoluciones', 'contacto.html|Contacto', 'legal.html|Legal']
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
        if (!input || !input.checkValidity()) { toast("Revisa tu email"); return; }
        var list = [];
        try { list = JSON.parse(localStorage.getItem("grankha.news") || "[]"); } catch (err) {}
        if (list.indexOf(input.value) === -1) list.push(input.value);
        try { localStorage.setItem("grankha.news", JSON.stringify(list)); } catch (err) {}
        input.value = "";
        toast("¡Gracias! Te escribiremos muy pronto.");
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
        var subject = "Consulta web GRANKHA" + (d.pedido ? " · " + d.pedido : "");
        var body = "Nombre: " + (d.nombre || "") + "\nEmail: " + (d.email || "") +
          (d.pedido ? "\nPedido: " + d.pedido : "") + "\n\n" + (d.mensaje || "");
        location.href = "mailto:" + CFG.contactEmail + "?subject=" + encodeURIComponent(subject) +
          "&body=" + encodeURIComponent(body);
        toast("Abriendo tu correo para enviar el mensaje…");
      });
    });
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
    initMenu();
    initContact();
    initReveal();
    initNewsletter();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.GRANKHA = { add: addToCart, remove: removeLine, clear: clearCart, cart: readCart, totals: totals, toast: toast, eur: eur, num: num };
})();

#!/usr/bin/env bash
# ============================================================================
# GRANKHA · verificación post-despliegue + aviso a buscadores
#
# Se ejecuta DESPUÉS de desplegar. Comprueba que los cambios de esta tanda
# están vivos y, si todo cuadra, avisa a los buscadores.
#
# Uso:  bash ops/post_deploy.sh
# ============================================================================
set -uo pipefail
SITE="https://grankha.roadshop.online"
# La clave IndexNow es el nombre del único .txt de 32 hex en la raíz del repo.
# Es pública por diseño: IndexNow la descarga de $SITE/<clave>.txt para validar.
KEY="$(cd "$(dirname "$0")/.." && ls *.txt 2>/dev/null \
       | grep -E '^[0-9a-f]{32}\.txt$' | head -1 | sed 's/\.txt$//')"
FAIL=0
# Espaciado entre peticiones: los barridos rápidos disparan el Vercel Security
# Checkpoint contra la IP y entonces TODO devuelve 403, incluido lo que funciona.
nap() { sleep 3; }

chk() { # chk <esperado> <ruta> <etiqueta>
  local want="$1" path="$2" label="$3"
  local got
  got=$(curl -sS -o /dev/null -w '%{http_code}' -m 25 "$SITE$path")
  if [ "$got" = "$want" ]; then printf "  ✅ %-46s %s\n" "$label" "$got"
  else printf "  ❌ %-46s %s (esperado %s)\n" "$label" "$got" "$want"; FAIL=$((FAIL+1)); fi
  nap
}

echo "════ 1) Clean URLs vivas ════"
chk 200 "/tienda"            "clean URL /tienda"
chk 200 "/compromiso"        "clean URL /compromiso"
chk 200 "/cama-teddy-mediana" "clean URL de ficha de producto"
chk 200 "/"                  "portada"
# la URL antigua debe redirigir a la limpia, no servir contenido duplicado
r=$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' -m 25 "$SITE/tienda.html")
printf "  %-48s %s\n" "/tienda.html → redirección" "$r"
case "$r" in 308*|301*) printf "  ✅ redirige a la URL limpia\n";; *) printf "  ❌ no redirige como se esperaba\n"; FAIL=$((FAIL+1));; esac
nap

echo; echo "════ 2) Fichero de verificación de Google ════"
# CONFIRMADO en producción: con `cleanUrls:true` Vercel redirige TODAS las rutas que
# terminan en .html y los `rewrites` de vercel.json no preemptan esa redirección.
# No es un fallo del despliegue, es una limitación de plataforma: la verificación de
# Search Console debe hacerse por TXT DNS o por meta tag (ver PENDIENTES_ACCIONES.md).
# Se avisa sin sumar al contador de fallos.
g=$(curl -sS -m 25 -o /dev/null -w '%{http_code}' "$SITE/googlec2e45e8990a69adf.html")
if [ "$g" = "308" ]; then
  printf "  ⚠️  responde 308: cleanUrls redirige la ruta. Verificación por fichero\\n"
  printf "     NO es viable en Vercel con cleanUrls → usar TXT DNS o meta tag.\\n"
elif [ "$g" = "200" ]; then
  printf "  ✅ responde 200 en su URL exacta\\n"
else
  printf "  ❌ responde %s (inesperado)\\n" "$g"; FAIL=$((FAIL+1))
fi
nap

echo; echo "════ 3) Endpoints de formularios ════"
for p in /api/newsletter /api/contact; do
  m=$(curl -sS -o /dev/null -w '%{http_code}' -m 25 -X OPTIONS "$SITE$p")
  printf "  %-48s OPTIONS %s\n" "$p" "$m"
  nap
done
# sin cuerpo deben rechazar, no devolver 500
n=$(curl -sS -o /dev/null -w '%{http_code}' -m 25 -X POST -H 'Content-Type: application/json' -d '{}' "$SITE/api/newsletter")
printf "  %-48s POST vacío %s (esperado 400)\n" "/api/newsletter" "$n"
[ "$n" = "400" ] || FAIL=$((FAIL+1))
nap

echo; echo "════ 4) El panel sigue sin ser público ════"
chk 404 "/api/panel"          "/api/panel sin credencial"
chk 404 "/api/admin"          "/api/admin sin credencial"
# Con cleanUrls TODAS las rutas .html que no existen dan 308 y luego 404: el
# comportamiento de /pedidos.html es idéntico al de cualquier otra ruta inexistente,
# así que no delata que haya habido un panel. Se comprueba esa uniformidad.
chk 308 "/pedidos.html"       "/pedidos.html (308, como cualquier .html inexistente)"
chk 404 "/data/pricing.json"  "/data/pricing.json (costes)"
chk 404 "/data/site.json"     "/data/site.json (donation.rate)"
# el logout no debe delatar la cookie
h=$(curl -sS -m 25 -D - -o /dev/null "$SITE/api/panel?logout=1" | grep -ci '^set-cookie' || true)
if [ "$h" = "0" ]; then printf "  ✅ ?logout=1 no lleva Set-Cookie (no delata el panel)\n"
else printf "  ❌ ?logout=1 sigue llevando Set-Cookie\n"; FAIL=$((FAIL+1)); fi
nap

echo; echo "════ 5) Claves fuera del HTML público ════"
# Patrón genérico de clave de Resend (re_XXXXXXXX_…): así cubre la clave actual y
# cualquier rotación futura, no solo la que se revocó en su día.
for pat in sb_publishable supabase.co sk_live rk_live 'whsec_' 're_[A-Za-z0-9]\{8\}_'; do
  c=$(curl -sS -m 25 "$SITE/" "$SITE/tienda" "$SITE/contacto" 2>/dev/null | grep -c "$pat" || true)
  if [ "$c" = "0" ]; then printf "  ✅ %-16s 0 apariciones\n" "$pat"
  else printf "  ❌ %-16s %s apariciones\n" "$pat" "$c"; FAIL=$((FAIL+1)); fi
  nap
done

echo; echo "════ 6) sitemap y robots ════"
chk 200 "/sitemap.xml" "sitemap.xml"
chk 200 "/robots.txt"  "robots.txt"
s=$(curl -sS -m 25 "$SITE/sitemap.xml")
printf "  URLs en sitemap: %s\n" "$(printf '%s' "$s" | grep -c '<loc>')"
printf "  con extensión .html: %s (debe ser 0)\n" "$(printf '%s' "$s" | grep -c '\.html</loc>' || true)"

echo; echo "════ 7) Fichero de clave IndexNow ════"
if [ -z "$KEY" ]; then
  printf "  ⚠ no hay clave en .indexnow-key; se omite el aviso a buscadores\n"
else
  k=$(curl -sS -m 25 "$SITE/$KEY.txt")
  if [ "$k" = "$KEY" ]; then printf "  ✅ /%s.txt responde con la clave\n" "$KEY"
  else printf "  ❌ el fichero de clave no está accesible; IndexNow rechazará el envío\n"; FAIL=$((FAIL+1)); fi
  nap
fi

# ───────────────────────── aviso a buscadores ─────────────────────────
echo; echo "════ 8) Aviso a buscadores ════"
echo "  Nota: los endpoints clásicos de ping están muertos. Comprobado:"
echo "        google.com/ping  → 404 · bing.com/ping → 410 (Gone)"
echo "        Google se avisa por Search Console; Bing por IndexNow."

if [ -z "$KEY" ]; then
  printf "  ⏭ IndexNow omitido (falta la clave)\n"
else
  urls=$(curl -sS -m 25 "$SITE/sitemap.xml" | grep -o '<loc>[^<]*</loc>' | sed 's/<[^>]*>//g' \
         | python3 -c "import sys,json;print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")
  printf "  enviando %s URLs a IndexNow…\n" "$(printf '%s' "$urls" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))')"
  ix=$(curl -sS -m 60 -o /tmp/ix.out -w '%{http_code}' -X POST "https://api.indexnow.org/indexnow" \
        -H 'Content-Type: application/json; charset=utf-8' \
        -d "{\"host\":\"grankha.roadshop.online\",\"key\":\"$KEY\",\"keyLocation\":\"$SITE/$KEY.txt\",\"urlList\":$urls}")
  # 200 = OK · 202 = aceptado, pendiente de validación · 4xx = rechazado
  case "$ix" in
    200|202) printf "  ✅ IndexNow %s (Bing, Yandex, Seznam, Naver, Yep)\n" "$ix";;
    *)       printf "  ❌ IndexNow %s · %s\n" "$ix" "$(head -c 160 /tmp/ix.out)"; FAIL=$((FAIL+1));;
  esac
  nap
  po=$(curl -sS -m 60 -o /dev/null -w '%{http_code}' -G "https://pingomatic.com/ping/" \
        --data-urlencode "title=GRANKHA" \
        --data-urlencode "blogurl=$SITE/" \
        --data-urlencode "rssurl=$SITE/sitemap.xml" \
        --data-urlencode "chk_weblogscom=on" --data-urlencode "chk_blogs=on" \
        --data-urlencode "chk_technorati=on" --data-urlencode "chk_feedburner=on" \
        --data-urlencode "chk_syndic8=on" --data-urlencode "chk_newsgator=on" \
        --data-urlencode "chk_myyahoo=on" --data-urlencode "chk_pubsubcom=on" \
        --data-urlencode "chk_blogdigger=on" --data-urlencode "chk_blogrolling=on" \
        --data-urlencode "chk_blogstreet=on" --data-urlencode "chk_moreover=on" \
        --data-urlencode "chk_weblogalot=on" --data-urlencode "chk_icerocket=on" \
        --data-urlencode "chk_newsisfree=on" --data-urlencode "chk_topicexchange=on" \
        --data-urlencode "chk_google=on" --data-urlencode "chk_tailrank=on" \
        --data-urlencode "chk_bloglines=on" --data-urlencode "chk_aiderss=on" \
        --data-urlencode "chk_skygrid=on" --data-urlencode "chk_bitacoras=on" \
        --data-urlencode "chk_audioweb=on" --data-urlencode "chk_franco=on")
  [ "$po" = "200" ] && printf "  ✅ Pingomatic %s\n" "$po" || printf "  ⚠ Pingomatic %s\n" "$po"
fi

echo; echo "════ resultado ════"
if [ "$FAIL" = "0" ]; then echo "  ✅ todo correcto"; else echo "  ❌ $FAIL comprobaciones fallidas"; fi
exit "$FAIL"

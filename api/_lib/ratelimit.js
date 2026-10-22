// ============================================================================
// GRANKHA · api/_lib/ratelimit.js — límite de peticiones por IP
//
// Protección básica contra abuso de los formularios y del checkout. El conteo
// vive en memoria de la instancia serverless: no es un límite global perfecto
// (cada instancia fría empieza de cero), pero corta el envío masivo desde una
// sola IP, que es el abuso realista en una tienda de este tamaño.
// ============================================================================

const VENTANA_MS = 10 * 60 * 1000; // 10 minutos
const golpes = new Map();

function ipDe(req) {
  const xff = req && req.headers && req.headers["x-forwarded-for"];
  if (xff) return String(xff).split(",")[0].trim();
  return (req && req.socket && req.socket.remoteAddress) || "desconocida";
}

// Devuelve true si la IP ya ha agotado su cupo en la ventana.
function limitado(req, clave, max = 5) {
  const k = clave + ":" + ipDe(req);
  const ahora = Date.now();
  let lista = golpes.get(k);
  if (!lista) { lista = []; golpes.set(k, lista); }
  while (lista.length && ahora - lista[0] > VENTANA_MS) lista.shift();
  if (lista.length >= max) return true;
  lista.push(ahora);
  // poda periódica para que el mapa no crezca sin límite
  if (golpes.size > 5000) {
    for (const [kk, vv] of golpes) {
      if (!vv.length || ahora - vv[vv.length - 1] > VENTANA_MS) golpes.delete(kk);
    }
  }
  return false;
}

module.exports = { limitado, ipDe, VENTANA_MS };

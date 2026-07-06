import { criarMapa } from "./criar_mapa.js";
import { adicionarBaseWms } from "./camada_base.js";
import { adicionarResultado } from "./camada_resultado.js";

let mapa = null;
let camadaResultado = null;

function lerJson(id) {
  const el = document.getElementById(id);
  return el ? JSON.parse(el.textContent) : null;
}

function montarMapaBase() {
  const wms = lerJson("mapa-wms");
  const cfg = lerJson("mapa-config");
  if (!wms || !cfg || mapa) return;
  mapa = criarMapa("map", cfg.centro, cfg.zoom);
  adicionarBaseWms(mapa, wms);
}

// htmx:afterSwap dispara a cada swap (garantido) — nele buscamos o payload por id no DOM. O
// marcador dataset.aplicado garante que cada payload seja desenhado uma única vez: swaps de
// sugestão/aviso (sem payload novo) e disparos repetidos não redesenham; um novo resultado
// substitui o <script> anterior, entra sem marca e é aplicado. adicionarResultado já reenquadra
// o mapa (fitBounds) sobre as features.
function aplicarResultado() {
  if (!mapa) return;
  const script = document.getElementById("mapa-payload");
  if (!script || script.dataset.aplicado) return;
  script.dataset.aplicado = "1";
  const data = JSON.parse(script.textContent);
  if (camadaResultado) mapa.removeLayer(camadaResultado);
  camadaResultado = adicionarResultado(mapa, data.geometria, data.cor);
}

// §11 caso (1): callbacks de evento do HTMX, registrados uma única vez (carregados no base.html).
document.addEventListener("DOMContentLoaded", montarMapaBase);
htmx.on("htmx:afterSwap", aplicarResultado);

import { criarMapa } from "./criar_mapa.js";
import { adicionarBaseWms } from "./camada_base.js";
import { adicionarResultado } from "./camada_resultado.js";
import { inicializarControlesMapa } from "./controles_mapa.js";
import { inicializarApagar } from "./desenho/apagar.js";
import { inicializarBancadaDesenho } from "./desenho/bancada.js";
import { destacarSelecionados } from "./desenho/destaque.js";
import { inicializarEnvio } from "./desenho/envio.js";
import { inicializarSelecao } from "./desenho/selecao.js";
import { inicializarSincronia } from "./desenho/sincronia.js";

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
  const baseMaps = adicionarBaseWms(mapa, wms);
  inicializarControlesMapa(mapa, baseMaps);
  inicializarBancadaDesenho(mapa);
  inicializarSincronia(mapa, mapa.getContainer().parentElement);
  inicializarEnvio(mapa);
  inicializarSelecao(mapa);
  inicializarApagar(mapa);
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

// Trocar a marca de um poço repinta na hora; assentado um swap novo da gaveta (design/020), o
// selecionado de cada poço precisa do mesmo destaque — inclusive na primeira renderização.
function destacarSeHouverMapa() {
  if (mapa) destacarSelecionados(mapa);
}

// §11 caso (1): callbacks de evento do HTMX, registrados uma única vez (carregados no base.html).
document.addEventListener("DOMContentLoaded", montarMapaBase);
document.addEventListener("change", (evento) => {
  if (evento.target.matches(".linha-desenho__marca")) destacarSeHouverMapa();
});
htmx.on("htmx:afterSwap", aplicarResultado);
htmx.on("htmx:afterSettle", destacarSeHouverMapa);

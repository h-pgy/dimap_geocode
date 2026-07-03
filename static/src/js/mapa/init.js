import { criarMapa } from "./criar_mapa.js";
import { adicionarBaseWms } from "./camada_base.js";
import { adicionarResultado } from "./camada_resultado.js";

function lerJson(id) {
  const el = document.getElementById(id);
  return el ? JSON.parse(el.textContent) : null;
}

function montarMapa() {
  const div = document.getElementById("map");
  if (!div || div.dataset.pronto) return;
  const wms = lerJson("mapa-wms");
  const data = lerJson("mapa-payload");
  if (!wms || !data) return;
  const map = criarMapa("map", data.centro, data.zoom);
  adicionarBaseWms(map, wms);
  adicionarResultado(map, data.geometria, data.cor);
  div.dataset.pronto = "1";
}

// §11 caso (1): callback de evento do HTMX, registrado uma única vez (carregado no base.html).
htmx.onLoad(montarMapa);

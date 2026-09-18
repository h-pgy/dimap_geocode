import { ferramentaAtiva } from "./ferramentas.js";

// Um ouvinte no mapa, e não um por camada: camada que ouve click vira alvo do Leaflet, e o marcador
// (bubblingMouseEvents: false) engole o clique — inclusive o cursor do Geoman, que cria o vértice.
export function inicializarSelecao(mapa) {
  mapa.on("click", (evento) => selecionar(mapa, evento));
}

function selecionar(mapa, evento) {
  // Com ferramenta na mão o clique é do plugin: vértice, arrasto, apagar.
  if (mapa.pm.globalDrawModeEnabled() || ferramentaAtiva(mapa)) return;
  const alvo = evento.originalEvent.target;
  const camada = mapa.pm.getGeomanLayers().find((c) => c.getElement()?.contains(alvo));
  if (!camada) return;
  const radio = document.querySelector(`.linha-desenho__marca[value="${L.Util.stamp(camada)}"]`);
  if (!radio) return;

  // Sem isso o "clique fora" do design/019 recolheria a gaveta que este clique acabou de abrir.
  L.DomEvent.stopPropagation(evento.originalEvent);
  radio.checked = true;
  radio.dispatchEvent(new Event("change", { bubbles: true }));
  abrirGaveta(radio.closest(".gaveta-lateral"));
  radio.closest(".linha-desenho").scrollIntoView({ block: "nearest" });
}

// O change é o que a bancada escuta para se reacomodar, como no gesto da paleta.
function abrirGaveta(gaveta) {
  const toggle = gaveta.querySelector(".gaveta-lateral-toggle");
  if (toggle.checked) return;
  toggle.checked = true;
  toggle.dispatchEvent(new Event("change", { bubbles: true }));
}

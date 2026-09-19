// Utilitário de Leaflet para qualquer resultado de ação no mapa (SPEC localizacao_lote/003): os
// desenhos descem para baixo dele, a feature com url_ficha abre a gaveta dela, e a feature cujo id
// está sob o ponteiro, ou escolhido numa [data-id-feature] da gaveta inferior, acende. Estado visual
// do mapa, e só dele; o escolhido zera a cada resultado novo.
const DESENHO_SOB_RESULTADO = { fillOpacity: 0.2 };
// Traço em JS porque é estilo de <path> do Leaflet; o halo é classe do tema.
const REALCE = {
  normal: { weight: 1.5, fillOpacity: 0.18, brilho: null },
  ponteiro: { weight: 3, fillOpacity: 0.4, brilho: "realce-resultado" },
  escolhido: { weight: 4, fillOpacity: 0.55, brilho: "realce-resultado-forte" },
};
const BRILHOS = ["realce-resultado", "realce-resultado-forte"];

let resultado = null;
const estado = { idEscolhido: null, idSobPonteiro: null };

function pintar(camada, nome) {
  const { brilho, ...traco } = REALCE[nome];
  camada.setStyle(traco);
  const elemento = camada.getElement?.();
  elemento?.classList.remove(...BRILHOS);
  if (!brilho) return;
  elemento?.classList.add(brilho);
  camada.bringToFront();
}

function realcar() {
  resultado?.eachLayer((camada) => {
    const id = camada.feature?.properties?.id;
    if (id === undefined || !camada.setStyle) return;
    pintar(camada, id === estado.idEscolhido ? "escolhido" : id === estado.idSobPonteiro ? "ponteiro" : "normal");
  });
  // O escolhido fica por cima do que está sob o ponteiro.
  resultado?.eachLayer((camada) => {
    if (camada.feature?.properties?.id === estado.idEscolhido) camada.bringToFront?.();
  });
}

function escolher(id) {
  estado.idEscolhido = id;
  realcar();
}

// Uma vez, no init.js: os gatilhos vêm da gaveta inferior, que é trocada a cada resultado.
export function inicializarInteracaoResultado() {
  const linha = (evento) => evento.target.closest?.("#gaveta-inferior-conteudo [data-id-feature]");
  document.addEventListener("mouseover", (evento) => {
    const id = linha(evento)?.dataset.idFeature ?? null;
    if (id === estado.idSobPonteiro) return;
    estado.idSobPonteiro = id;
    realcar();
  });
  // A linha pede a gaveta pelo próprio hx-get; aqui ela só vira a escolhida.
  document.addEventListener("click", (evento) => {
    const id = linha(evento)?.dataset.idFeature;
    if (id) escolher(id);
  });
}

// A cada resultado aplicado, no aplicarResultado do init.js.
export function interagirComResultado(mapa, camadaResultado) {
  resultado = camadaResultado;
  estado.idEscolhido = null;
  estado.idSobPonteiro = null;
  mapa.pm.getGeomanLayers().forEach((camada) => {
    if (camada.setStyle) camada.setStyle(DESENHO_SOB_RESULTADO); // o marcador de ponto não tem estilo
    camada.bringToBack?.();
  });
  camadaResultado.eachLayer((camada) => {
    const { id, url_ficha: urlFicha } = camada.feature?.properties ?? {};
    if (!urlFicha) return;
    camada.on("click", (evento) => {
      // Sem isso o "clique fora" do design/019 recolheria a gaveta que este clique vai trocar.
      L.DomEvent.stopPropagation(evento.originalEvent);
      escolher(id);
      htmx.ajax("GET", urlFicha, { target: "#gaveta-entidade", swap: "innerHTML" });
    });
  });
  realcar();
}

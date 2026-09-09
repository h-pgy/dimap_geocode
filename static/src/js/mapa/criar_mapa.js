// Controles do Leaflet no canto inferior ESQUERDO: o direito é do atalho de conferência de
// documento (SPEC documentos_oficiais/008).
const MIN_ZOOM = 13;
// Acima do zoom nativo da ortofoto (settings WMS_ZOOM_NATIVO_ORTOFOTO) os níveis são zoom digital:
// aproximam a imagem já carregada, sem tile novo. Subir este teto alarga a ampliação disponível.
const MAX_ZOOM = 22;
export function criarMapa(elId, centro, zoom) {
  const mapa = L.map(elId, {
    minZoom: MIN_ZOOM,
    maxZoom: MAX_ZOOM,
    zoomControl: false,
    // Atribuição fora do mapa: a fonte dos dados é declarada na documentação do sistema.
    attributionControl: false,
    // Sem isso, o Leaflet só anima (CSS transform) reenquadramentos com até 4 níveis de zoom de
    // diferença (padrão da lib) — saltos maiores viram um "snap" instantâneo, sem suavidade. Como
    // o span de zoom aqui é maior que 4, cobre o span inteiro para que fitBounds/setView sempre
    // anime suave nativamente, sem pedir tile de nível intermediário (ao contrário do flyTo).
    zoomAnimationThreshold: MAX_ZOOM - MIN_ZOOM,
  }).setView(centro, zoom);
  return mapa;
}

// Nos cantos de baixo o Leaflet insere cada controle novo ANTES dos que já estão lá: a ordem de
// entrada é a pilha de baixo para cima. Daí o zoom, que fica em cima, entrar depois das camadas.
export function adicionarZoom(mapa) {
  L.control.zoom({ position: "bottomleft" }).addTo(mapa);
}

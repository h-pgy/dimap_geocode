// Controles no canto inferior direito: não colidem com a UI flutuante (busca/widget no topo).
const MIN_ZOOM = 13;
const MAX_ZOOM = 19;
export function criarMapa(elId, centro, zoom) {
  const mapa = L.map(elId, {
    minZoom: MIN_ZOOM,
    maxZoom: MAX_ZOOM,
    zoomControl: false,
    // Sem isso, o Leaflet só anima (CSS transform) reenquadramentos com até 4 níveis de zoom de
    // diferença (padrão da lib) — saltos maiores viram um "snap" instantâneo, sem suavidade. Como
    // o span de zoom aqui é maior que 4, cobre o span inteiro para que fitBounds/setView sempre
    // anime suave nativamente, sem pedir tile de nível intermediário (ao contrário do flyTo).
    zoomAnimationThreshold: MAX_ZOOM - MIN_ZOOM,
  }).setView(centro, zoom);
  L.control.zoom({ position: "bottomright" }).addTo(mapa);
  return mapa;
}

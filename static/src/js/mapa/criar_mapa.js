// Controles no canto inferior direito: não colidem com a UI flutuante (busca/widget no topo).
export function criarMapa(elId, centro, zoom) {
  const mapa = L.map(elId, { minZoom: 13, maxZoom: 19, zoomControl: false }).setView(centro, zoom);
  L.control.zoom({ position: "bottomright" }).addTo(mapa);
  return mapa;
}

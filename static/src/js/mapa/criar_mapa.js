export function criarMapa(elId, centro, zoom) {
  return L.map(elId, { minZoom: 13, maxZoom: 19 }).setView(centro, zoom);
}

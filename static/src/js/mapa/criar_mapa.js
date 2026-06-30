export function criarMapa(elId, centro, zoom) {
  return L.map(elId, { minZoom: 10, maxZoom: 19 }).setView(centro, zoom);
}

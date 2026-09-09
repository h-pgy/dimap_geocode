// Controles de mapa customizados do Onsen (SPEC design/016).
// Controles nativos do Leaflet inibidos: zoomControl: false e attributionControl: false.
const MIN_ZOOM = 13;
// Acima do zoom nativo da ortofoto (settings WMS_ZOOM_NATIVO_ORTOFOTO) os níveis são zoom digital:
// aproximam a imagem já carregada, sem tile novo. Subir este teto alarga a ampliação disponível.
const MAX_ZOOM = 22;

export function criarMapa(elId, centro, zoom) {
  return L.map(elId, {
    minZoom: MIN_ZOOM,
    maxZoom: MAX_ZOOM,
    zoomControl: false,          // Controles de zoom do Leaflet inibidos (SPEC design/016)
    attributionControl: false,
    zoomAnimationThreshold: MAX_ZOOM - MIN_ZOOM,
  }).setView(centro, zoom);
}

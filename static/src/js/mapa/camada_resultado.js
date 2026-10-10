// popup_html, rotulo e cor (opcional) já vêm prontos nas properties (servidor); o JS só os entrega ao Leaflet.
// Resultado não é desenho: sem pmIgnore o getGeomanLayers() o devolve junto dos traços da bancada, e
// ele seria repintado, rebaixado, listado na gaveta e apagado como um deles. O encaixe continua valendo.
const FORA_DA_BANCADA = { pmIgnore: true, snapIgnore: false };

export function adicionarResultado(map, geometria, corPadrao, enquadrar = true) {
  const camada = L.geoJSON(geometria, {
    ...FORA_DA_BANCADA,
    style: (f) => {
      const c = (f.properties && f.properties.cor) ? f.properties.cor : corPadrao;
      return { color: c, weight: 4, opacity: 1, fillColor: c, fillOpacity: 0.35 };
    },
    pointToLayer: (f, latlng) => {
      const c = (f.properties && f.properties.cor) ? f.properties.cor : corPadrao;
      return L.circleMarker(latlng, { ...FORA_DA_BANCADA, radius: 7, color: c, weight: 2, fillColor: c, fillOpacity: 0.85 });
    },
    onEachFeature: (f, layer) => {
      const p = f.properties || {};
      if (p.popup_html) layer.bindPopup(p.popup_html);
      if (p.rotulo) layer.bindTooltip(p.rotulo, { direction: "top", sticky: true });
    },
  }).addTo(map);
  if (enquadrar) enquadrarCamada(map, camada);
  return camada;
}

function enquadrarCamada(map, camada) {
  const b = camada.getBounds();
  b.isValid()
    ? map.fitBounds(b, { maxZoom: 18, padding: [20, 20] })
    : map.setView(b.getCenter(), 17);
}

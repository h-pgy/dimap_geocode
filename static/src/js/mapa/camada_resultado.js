// popup_html, rotulo e cor (opcional) já vêm prontos nas properties (servidor); o JS só os entrega ao Leaflet.
export function adicionarResultado(map, geometria, corPadrao) {
  const camada = L.geoJSON(geometria, {
    style: (f) => {
      const c = (f.properties && f.properties.cor) ? f.properties.cor : corPadrao;
      return { color: c, weight: 4, opacity: 1, fillColor: c, fillOpacity: 0.35 };
    },
    pointToLayer: (f, latlng) => {
      const c = (f.properties && f.properties.cor) ? f.properties.cor : corPadrao;
      return L.circleMarker(latlng, { radius: 7, color: c, weight: 2, fillColor: c, fillOpacity: 0.85 });
    },
    onEachFeature: (f, layer) => {
      const p = f.properties || {};
      if (p.popup_html) layer.bindPopup(p.popup_html);
      if (p.rotulo) layer.bindTooltip(p.rotulo, { direction: "top", sticky: true });
    },
  }).addTo(map);
  const b = camada.getBounds();
  b.isValid()
    ? map.fitBounds(b, { maxZoom: 18, padding: [20, 20] })
    : map.setView(b.getCenter(), 17);
  return camada;
}

// popup_html e rotulo já vêm prontos nas properties (servidor); o JS só os entrega ao Leaflet.
export function adicionarResultado(map, geometria, cor) {
  const camada = L.geoJSON(geometria, {
    style: () => ({ color: cor, weight: 3, opacity: 1, fillColor: cor, fillOpacity: 0.3 }),
    pointToLayer: (f, latlng) =>
      L.circleMarker(latlng, { radius: 7, color: cor, weight: 2, fillColor: cor, fillOpacity: 0.85 }),
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

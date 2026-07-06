// Acima de DISTANCIA_VOO_METROS entre o centro atual e o alvo, reenquadra com o arco do Leaflet
// (zoom-out → pan → zoom-in): os frames de zoom mais baixo cobrem o trajeto com tiles grosseiras/em
// cache em vez de branco, e a duração dá "tempinho" para o WMS do GeoSampa renderizar o destino.
// Abaixo do limiar, enquadra direto (o arco seria gratuito/irritante para deslocamentos curtos).
const DISTANCIA_VOO_METROS = 3000;
const DURACAO_VOO_S = 2.2;
const OPCOES_ENQUADRE = { maxZoom: 18, padding: [20, 20] };

function reenquadrar(map, bounds) {
  const alvo = bounds.getCenter();
  const longe = map.getCenter().distanceTo(alvo) > DISTANCIA_VOO_METROS;
  if (bounds.isValid()) {
    longe
      ? map.flyToBounds(bounds, { ...OPCOES_ENQUADRE, duration: DURACAO_VOO_S })
      : map.fitBounds(bounds, OPCOES_ENQUADRE);
  } else {
    longe ? map.flyTo(alvo, 17, { duration: DURACAO_VOO_S }) : map.setView(alvo, 17);
  }
}

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
  reenquadrar(map, camada.getBounds());
  return camada;
}

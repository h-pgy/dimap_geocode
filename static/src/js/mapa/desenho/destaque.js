// Repinta o que já está no mapa (SPEC design/020): o selecionado em tinta plena, os demais
// atenuados. Utilitário de Leaflet — nenhum estado de domínio aqui.
import { CORES_DESENHO } from "./catalogo.js";

// Marcador não tem setStyle: a atenuação dele é opacidade.
function pintar(camada, cor, pleno) {
  if (camada.setStyle) {
    camada.setStyle({
      color: cor,
      fillColor: cor,
      weight: pleno ? 4 : 2,
      opacity: pleno ? 1 : 0.45,
      fillOpacity: pleno ? 0.45 : 0.1,
    });
  } else {
    camada.setOpacity(pleno ? 1 : 0.45);
  }
}

// A camada diz o tipo dela: Rectangle herda de Polygon, e Polyline não — a mesma checagem da bancada.
function corDoTipo(camada) {
  if (camada instanceof L.Polygon) return CORES_DESENHO.poligono;
  if (camada instanceof L.Polyline) return CORES_DESENHO.linha;
  return CORES_DESENHO.ponto;
}

export function destacarSelecionados(mapa) {
  const marcados = new Set(
    Array.from(document.querySelectorAll(".linha-desenho__marca:checked")).map((radio) => radio.value),
  );
  mapa.pm.getGeomanLayers().forEach((camada) => {
    const id = String(L.Util.stamp(camada));
    pintar(camada, corDoTipo(camada), marcados.has(id));
  });
}

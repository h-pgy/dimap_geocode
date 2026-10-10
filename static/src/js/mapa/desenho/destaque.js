// Repinta o que já está no mapa (SPEC design/020): o selecionado ganha ênfase, os demais ficam no
// traço normal. Utilitário de Leaflet — nenhum estado de domínio aqui.
import { CORES_DESENHO, TRACO_POR_TIPO } from "./catalogo.js";
import { iconePonto } from "./ferramentas.js";

const Z_PONTO_SELECIONADO = 1000;

// A camada diz o tipo dela: Rectangle herda de Polygon, e Polyline não — a mesma checagem da bancada.
function tipoDaCamada(camada) {
  if (camada instanceof L.Polygon) return "poligono";
  if (camada instanceof L.Polyline) return "linha";
  return "ponto";
}

function pintar(camada, selecionado) {
  const tipo = tipoDaCamada(camada);
  const estado = selecionado ? "selecionado" : "normal";
  if (tipo === "ponto") {
    camada.setIcon(iconePonto(estado));
    camada.setZIndexOffset(selecionado ? Z_PONTO_SELECIONADO : 0);
    return;
  }
  const cor = CORES_DESENHO[tipo];
  camada.setStyle({ color: cor, fillColor: cor, ...TRACO_POR_TIPO[tipo][estado] });
  if (selecionado) camada.bringToFront();
}

export function destacarSelecionados(mapa) {
  const marcados = new Set(
    Array.from(document.querySelectorAll(".linha-desenho__marca:checked")).map((radio) => radio.value),
  );
  mapa.pm.getGeomanLayers().forEach((camada) => {
    pintar(camada, marcados.has(String(L.Util.stamp(camada))));
  });
}

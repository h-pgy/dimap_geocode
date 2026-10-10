// O adaptador do plugin Leaflet-Geoman (SPEC design/018): quem está ligado, o que ligar e quando
// o Ok se arma. O estado da bancada é LIDO do plugin, nunca guardado em paralelo.
import { CORES_DESENHO, DIAMETRO_PONTO, GEOMETRIAS, MODOS_GLOBAIS, TRACO_POR_TIPO } from "./catalogo.js";

// Qual cursor cada ferramenta pede. Recortar desenha o corte, então é mira, não mão.
export const CURSOR_DA_FERRAMENTA = {
  Marker: "desenhar",
  Line: "desenhar",
  Polygon: "desenhar",
  Rectangle: "desenhar",
  Circle: "desenhar",
  cut: "desenhar",
  edit: "modificar",
  drag: "modificar",
  rotate: "modificar",
  remove: "apagar",
};
export const CURSORES = ["desenhar", "modificar", "apagar"];

export function categoriaDaFerramenta(id) {
  return Object.keys(GEOMETRIAS).find((nome) => GEOMETRIAS[nome].some((f) => f.id === id));
}

// Quem está na mão: no modo de desenho o plugin não diz a forma, então ela vem do evento
// pm:globaldrawmodetoggled, guardado pelo chamador.
export function ferramentaAtiva(mapa, formaEmDesenho) {
  if (mapa.pm.globalDrawModeEnabled()) return formaEmDesenho;
  return Object.keys(MODOS_GLOBAIS).find((id) => mapa.pm[MODOS_GLOBAIS[id][2]]()) || null;
}

export function haGeometria(mapa) {
  return mapa.pm.getGeomanLayers().length > 0;
}

// L.Rectangle herda de L.Polygon; L.Polyline não — a checagem separa área de linha sozinha.
export function haPoligono(mapa) {
  return mapa.pm.getGeomanLayers().some((camada) => camada instanceof L.Polygon);
}

// Só forma de múltiplos vértices tem o que concluir: marcador, retângulo e círculo terminam no
// próprio clique que os cria.
const VERTICES_MINIMOS = { Line: 2, Polygon: 3 };

export function podeConcluir(mapa, forma) {
  const minimo = VERTICES_MINIMOS[forma];
  if (!minimo || !mapa.pm.globalDrawModeEnabled()) return false;
  const desenho = mapa.pm.Draw[forma];
  if (!desenho || !desenho._layer) return false;
  const vertices = desenho._layer.getLatLngs();
  const traco = Array.isArray(vertices[0]) ? vertices[0] : vertices;
  return traco.length >= minimo;
}

export function desligarTudo(mapa) {
  mapa.pm.disableDraw();
  Object.values(MODOS_GLOBAIS).forEach(([, desligar]) => mapa.pm[desligar]());
}

function tipoDaForma(forma) {
  if (forma === "Marker" || forma === "CircleMarker") return "ponto";
  if (forma === "Line") return "linha";
  return "poligono";
}

export function iconePonto(estado) {
  const diametro = DIAMETRO_PONTO[estado];
  return L.divIcon({
    className: "",
    iconSize: [diametro, diametro],
    iconAnchor: [diametro / 2, diametro / 2],
    html:
      '<span style="display:block;width:' +
      diametro +
      "px;height:" +
      diametro +
      "px;border-radius:9999px;background:" +
      CORES_DESENHO.ponto +
      ';border:2px solid rgba(255,255,255,.9);box-shadow:0 0 8px rgba(72,202,228,.9)"></span>',
  });
}

function opcoesDesenho(forma) {
  const tipo = tipoDaForma(forma);
  const cor = CORES_DESENHO[tipo];
  return {
    pathOptions: { color: cor, fillColor: cor, ...TRACO_POR_TIPO[tipo]?.normal },
    templineStyle: { color: cor, weight: 2 },
    hintlineStyle: { color: cor, dashArray: "6,6", weight: 2 },
    markerStyle: { icon: iconePonto("normal") },
  };
}

// Clicar na ferramenta que já está na mão a devolve à bancada: o toggle é o mesmo gesto.
export function acionar(mapa, id, formaEmDesenho) {
  const jaAtiva = ferramentaAtiva(mapa, formaEmDesenho) === id;
  desligarTudo(mapa);
  if (jaAtiva) return;
  if (MODOS_GLOBAIS[id]) mapa.pm[MODOS_GLOBAIS[id][0]]();
  else mapa.pm.enableDraw(id, opcoesDesenho(id));
}

// O adaptador do plugin Leaflet-Geoman (SPEC design/018): quem está ligado, o que ligar e quando
// o Ok se arma. O estado da bancada é LIDO do plugin, nunca guardado em paralelo.
import { GEOMETRIAS, MODOS_GLOBAIS } from "./catalogo.js";

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

// Cor do traço por tipo (SPEC §3 design/018): ponto em água, linha em accent, polígono em sakura.
const COR_PONTO = "#00B4D8";
const COR_LINHA = "#0F766E";
const COR_POLIGONO = "#D84F7F";

function pinturaDe(forma) {
  if (forma === "Marker" || forma === "CircleMarker") return COR_PONTO;
  if (forma === "Line") return COR_LINHA;
  return COR_POLIGONO;
}

function opcoesDesenho(forma) {
  const cor = pinturaDe(forma);
  return {
    pathOptions: { color: cor, fillColor: cor, fillOpacity: 0.35, weight: 3 },
    templineStyle: { color: cor, weight: 2 },
    hintlineStyle: { color: cor, dashArray: "6,6", weight: 2 },
    markerStyle: {
      icon: L.divIcon({
        className: "",
        iconSize: [14, 14],
        iconAnchor: [7, 7],
        html:
          '<span style="display:block;width:14px;height:14px;border-radius:9999px;background:' +
          COR_PONTO +
          ';border:2px solid rgba(255,255,255,.9);box-shadow:0 0 8px rgba(72,202,228,.9)"></span>',
      }),
    },
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

// Catálogo da bancada de desenho (SPEC design/018): a tabela do §3 em código, e mais nada.

// A ordem aqui é a ordem dos glifos na linha: o catálogo é a fonte do submenu.
export const GEOMETRIAS = {
  ponto: [{ id: "Marker", rotulo: "Marcador", glifo: "#glifo-ponto" }],
  linha: [{ id: "Line", rotulo: "Linha", glifo: "#glifo-linha" }],
  poligono: [
    { id: "Polygon", rotulo: "Polígono", glifo: "#glifo-poligono" },
    { id: "Rectangle", rotulo: "Retângulo", glifo: "#glifo-retangulo" },
    { id: "Circle", rotulo: "Círculo", glifo: "#glifo-circulo" },
  ],
  // Apagar não está aqui: destruir não é uma forma de modificar, e mora no poço.
  modificar: [
    { id: "edit", rotulo: "Vértices", glifo: "#glifo-vertices" },
    { id: "drag", rotulo: "Mover", glifo: "#glifo-mover" },
    { id: "rotate", rotulo: "Girar", glifo: "#glifo-girar" },
    { id: "cut", rotulo: "Recortar", glifo: "#glifo-recortar" },
  ],
};

// Cada modo global do plugin e o trio de métodos que o liga, desliga e responde se está ligado.
export const MODOS_GLOBAIS = {
  edit: ["enableGlobalEditMode", "disableGlobalEditMode", "globalEditModeEnabled"],
  drag: ["enableGlobalDragMode", "disableGlobalDragMode", "globalDragModeEnabled"],
  rotate: ["enableGlobalRotateMode", "disableGlobalRotateMode", "globalRotateModeEnabled"],
  cut: ["enableGlobalCutMode", "disableGlobalCutMode", "globalCutModeEnabled"],
  remove: ["enableGlobalRemovalMode", "disableGlobalRemovalMode", "globalRemovalModeEnabled"],
};

// Cor do traço por tipo (SPEC design/018 §3): ponto em água, linha em accent, polígono em sakura.
// ferramentas.js pinta ao desenhar, destaque.js repinta ao selecionar — os dois leem daqui.
export const CORES_DESENHO = { ponto: "#00B4D8", linha: "#0F766E", poligono: "#D84F7F" };

// O traço normal é o do desenho recém-feito; o selecionado só soma ênfase sobre ele. Linha não tem
// preenchimento: só a espessura a deixa visível e clicável.
export const TRACO_POR_TIPO = {
  linha: {
    normal: { weight: 5, opacity: 1 },
    selecionado: { weight: 8, opacity: 1 },
  },
  poligono: {
    normal: { weight: 3, opacity: 1, fillOpacity: 0.35 },
    selecionado: { weight: 6, opacity: 1, fillOpacity: 0.55 },
  },
};

// Diâmetro do marcador de ponto: marcador não passa de opacidade 1, então o realce é tamanho.
export const DIAMETRO_PONTO = { normal: 14, selecionado: 22 };

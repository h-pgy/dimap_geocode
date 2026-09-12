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

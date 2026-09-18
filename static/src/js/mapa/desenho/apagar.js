export function inicializarApagar(mapa) {
  document.addEventListener("click", (evento) => {
    const confirmar = evento.target.closest(".linha-desenho__confirmar-apagar");
    if (confirmar) apagar(mapa, confirmar.value);
    if (evento.target.closest("[data-limpar-desenhos]")) limpar(mapa);
  });
}

function apagar(mapa, id) {
  const camada = mapa.pm.getGeomanLayers().find((c) => String(L.Util.stamp(c)) === id);
  if (!camada) return;
  mapa.removeLayer(camada);
  // removeLayer não dispara pm:remove: sem ele, bancada e sincronia não veriam a deleção.
  mapa.fire("pm:remove", { layer: camada, shape: camada.pm.getShape() });
}

// Um pm:remove só: uma requisição por camada disputaria a gaveta.
function limpar(mapa) {
  mapa.pm.getGeomanLayers().forEach((camada) => mapa.removeLayer(camada));
  mapa.fire("pm:remove", { layer: null });
}

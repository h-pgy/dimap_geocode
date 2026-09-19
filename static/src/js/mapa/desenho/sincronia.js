// Cola de Leaflet → HTMX (SPEC design/020): a coleção é LIDA do plugin a cada envio; nada de
// lista paralela no navegador. Registrada DEPOIS da bancada: o handler de pm:create dela já
// converteu o círculo em polígono quando este roda.
let mapaDaBancada = null;
let urlDesenhos = null;

const marcado = () => document.querySelector(".linha-desenho__marca:checked")?.value ?? "";

// Exportado para o selecao.js (SPEC localizacao_lote/003): com a gaveta de uma entidade na lateral,
// o clique no desenho pede a bancada de volta, já com ele selecionado.
export function pedirGavetaDesenhos(selecionado) {
  if (!mapaDaBancada) return;
  const desenhos = mapaDaBancada.pm.getGeomanLayers().map((camada) => ({
    id_bancada: String(L.Util.stamp(camada)),
    geometria: camada.toGeoJSON().geometry,
  }));
  htmx.ajax("POST", urlDesenhos, {
    target: "#gaveta-entidade",
    swap: "innerHTML",
    values: {
      desenhos: JSON.stringify(desenhos),
      selecionado,
    },
  });
}

export function inicializarSincronia(mapa, container) {
  mapaDaBancada = mapa;
  urlDesenhos = container.dataset.urlDesenhos;
  const enviar = () => pedirGavetaDesenhos(marcado());

  ["pm:create", "pm:remove", "pm:cut"].forEach((evento) => mapa.on(evento, enviar));
  // Durante a modificação a geometria ainda muda: a medida se refaz quando o modo se fecha.
  ["pm:globaleditmodetoggled", "pm:globaldragmodetoggled", "pm:globalrotatemodetoggled"].forEach(
    (evento) => mapa.on(evento, (dado) => { if (!dado.enabled) enviar(); }),
  );
}

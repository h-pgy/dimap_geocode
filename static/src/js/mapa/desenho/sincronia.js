// Cola de Leaflet → HTMX (SPEC design/020): a coleção é LIDA do plugin a cada envio; nada de
// lista paralela no navegador. Registrada DEPOIS da bancada: o handler de pm:create dela já
// converteu o círculo em polígono quando este roda.
let mapaDaBancada = null;
let urlDesenhos = null;
// A seleção muda no navegador sem ida ao servidor: é ele quem lembra a última (SPEC design/021).
let ultimoMarcado = "";

const marcado = () => document.querySelector(".linha-desenho__marca:checked")?.value ?? "";

// Exportado para o selecao.js (SPEC localizacao_lote/003): com a gaveta de uma entidade na lateral,
// o clique no desenho pede a bancada de volta, já com ele selecionado.
export function pedirGavetaDesenhos(selecionado) {
  if (!mapaDaBancada) return;
  ultimoMarcado = selecionado;
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

  // O ponto que o Street View deixa já chega dizendo que é o selecionado (SPEC street_view/002);
  // no traço feito à mão a seleção não vem, e vale a que já estava marcada.
  mapa.on("pm:create", (evento) => pedirGavetaDesenhos(evento.selecionado ?? marcado()));
  ["pm:remove", "pm:cut"].forEach((evento) => mapa.on(evento, enviar));
  // Durante a modificação a geometria ainda muda: a medida se refaz quando o modo se fecha.
  ["pm:globaleditmodetoggled", "pm:globaldragmodetoggled", "pm:globalrotatemodetoggled"].forEach(
    (evento) => mapa.on(evento, (dado) => { if (!dado.enabled) enviar(); }),
  );
  document.addEventListener("change", (evento) => {
    if (evento.target.matches(".linha-desenho__marca")) ultimoMarcado = evento.target.value;
  });
  // O voltar à gaveta dos desenhos: ela não tem cena guardada, é o mapa que a remonta.
  document.addEventListener("click", (evento) => {
    if (evento.target.closest("[data-pedir-desenhos]")) pedirGavetaDesenhos(ultimoMarcado);
  });
}

// Cola de Leaflet → HTMX (SPEC design/020): a coleção é LIDA do plugin a cada envio; nada de
// lista paralela no navegador. Registrada DEPOIS da bancada: o handler de pm:create dela já
// converteu o círculo em polígono quando este roda.
export function inicializarSincronia(mapa, container) {
  const marcado = () => document.querySelector(".linha-desenho__marca:checked")?.value ?? "";

  const enviar = () => {
    const desenhos = mapa.pm.getGeomanLayers().map((camada) => ({
      id_bancada: String(L.Util.stamp(camada)),
      geometria: camada.toGeoJSON().geometry,
    }));
    htmx.ajax("POST", container.dataset.urlDesenhos, {
      target: "#gaveta-entidade",
      swap: "innerHTML",
      values: {
        desenhos: JSON.stringify(desenhos),
        selecionado: marcado(),
      },
    });
  };

  ["pm:create", "pm:remove", "pm:cut"].forEach((evento) => mapa.on(evento, enviar));
  // Durante a modificação a geometria ainda muda: a medida se refaz quando o modo se fecha.
  ["pm:globaleditmodetoggled", "pm:globaldragmodetoggled", "pm:globalrotatemodetoggled"].forEach(
    (evento) => mapa.on(evento, (dado) => { if (!dado.enabled) enviar(); }),
  );
}

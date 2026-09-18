// Callback de evento HTMX (SPEC design/020): a ação submete o `id_bancada` marcado, e a geometria
// é lida do mapa no momento do envio — não do HTML da gaveta —, o que entrega à ação o traço COMO
// ELE ESTÁ AGORA, inclusive depois de editado.
export function inicializarEnvio(mapa) {
  document.body.addEventListener("htmx:configRequest", (evento) => {
    const id = evento.detail.parameters.id_bancada;
    if (!id) return;
    const camada = mapa.pm.getGeomanLayers().find((c) => String(L.Util.stamp(c)) === String(id));
    if (camada) evento.detail.parameters.desenho = JSON.stringify(camada.toGeoJSON().geometry);
  });
}

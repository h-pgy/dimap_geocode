// Toda a config (url, versão, bases nomeadas) vem do servidor via json_script.
// Tile layers cliente direto ao WMS do GeoSampa — não passam pelo integrador server-side.
// A 1ª base da lista é a visível por padrão.
export function adicionarBaseWms(map, wms) {
  const baseMaps = {};
  wms.bases.forEach((b, i) => {
    // Cada base pode ter sua própria URL (ex.: a ortofoto vem do WMS de raster,
    // em outro domínio); sem `url` própria, cai no WMS geral.
    const layer = L.tileLayer.wms(b.url || wms.url, {
      layers: b.layers,
      version: wms.version,
      format: "image/png",
      transparent: false,
      // O padrão do L.TileLayer é maxZoom 18 e, acima dele, o GridLayer não clampa: ESCONDE a
      // camada inteira (_setView zera o tileZoom). Era isso que deixava o mapa branco sob o véu
      // azul no zoom mais próximo. O teto da camada acompanha o do mapa.
      maxZoom: map.getMaxZoom(),
      // Zoom digital: passado o último nível com detalhe real, o Leaflet amplia no cliente o tile
      // nativo em vez de pedir ao servidor um upscale que ele faria de qualquer jeito. Base sem
      // `zoom_nativo` (a vetorial) fica sem teto, como o Leaflet faz por padrão.
      maxNativeZoom: b.zoom_nativo,
    });
    baseMaps[b.nome] = layer;
    if (i === 0) layer.addTo(map);
  });
  L.control.layers(baseMaps, null, { position: "bottomleft" }).addTo(map);
  return baseMaps;
}

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
      attribution: "GeoSampa — PMSP",
    });
    baseMaps[b.nome] = layer;
    if (i === 0) layer.addTo(map);
  });
  L.control.layers(baseMaps).addTo(map);
  return baseMaps;
}

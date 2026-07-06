// Toda a config (url, versão, bases nomeadas) vem do servidor via json_script.
// Tile layers cliente direto ao WMS do GeoSampa — não passam pelo integrador server-side.
// A 1ª base da lista é a visível por padrão.
export function adicionarBaseWms(map, wms) {
  const baseMaps = {};
  wms.bases.forEach((b, i) => {
    // Cada base pode ter sua própria URL (ex.: a ortofoto vem do WMS de raster,
    // em outro domínio); sem `url` própria, cai no WMS geral.
    // keepBuffer alto mantém mais tiles ao redor do viewport durante o deslocamento, dando
    // imagem já carregada para o trajeto do voo (flyTo) em vez de branco. O fade das tiles do
    // Leaflet fica ligado por padrão (não desligar fadeAnimation) — é o que evita o "pisca" na
    // chegada quando alguma tile do destino ainda está renderizando no WMS do GeoSampa.
    const layer = L.tileLayer.wms(b.url || wms.url, {
      layers: b.layers,
      version: wms.version,
      format: "image/png",
      transparent: false,
      keepBuffer: 6,
      attribution: "GeoSampa — PMSP",
    });
    baseMaps[b.nome] = layer;
    if (i === 0) layer.addTo(map);
  });
  L.control.layers(baseMaps, null, { position: "bottomright" }).addTo(map);
  return baseMaps;
}

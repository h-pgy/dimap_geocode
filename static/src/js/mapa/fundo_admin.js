import { derivarMapa } from "./deriva.js";

// Fundo da área administrativa (SPEC user_admin/007): tiles públicos em P&B, sem interação e sem
// nenhuma chamada ao GeoSampa — na área administrativa não há território a mostrar, então gastar
// requisição no WMS oficial sugeriria uma semântica que aquele mapa não tem.
let mapa = null;

function lerJson(id) {
  const el = document.getElementById(id);
  return el ? JSON.parse(el.textContent) : null;
}

function criarMapaAdmin(centro, zoom) {
  return L.map("map-admin", {
    zoomControl: false,
    dragging: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
    touchZoom: false,
  }).setView(centro, zoom);
}

function montarFundoAdmin() {
  const wms = lerJson("mapa-admin-wms");
  const cfg = lerJson("mapa-admin-config");
  if (!wms || !cfg || mapa) return;
  mapa = criarMapaAdmin(cfg.centro, cfg.zoom);
  // Usa a ortofoto (1ª base da lista) do WMS, com dessaturação aplicada no CSS (#map-admin)
  const ortofoto = wms.bases[0];
  L.tileLayer.wms(ortofoto.url || wms.url, {
    layers: ortofoto.layers,
    version: wms.version,
    format: "image/png",
    transparent: false,
    attribution: "GeoSampa — PMSP",
  }).addTo(mapa);
  derivarMapa(mapa, cfg.centro, cfg.zoom);
}

document.addEventListener("DOMContentLoaded", montarFundoAdmin);

import { derivarMapa } from "./deriva.js";

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

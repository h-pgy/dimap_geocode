// Orquestrador JS de cola entre a UI dos controles Onsen e o mapa Leaflet (SPEC design/016).
export function inicializarControlesMapa(mapa, baseMaps) {
  const container = document.getElementById("controles-mapa");
  if (!container || !mapa) return;

  const btnZoomIn = document.getElementById("btn-mapa-zoom-in");
  const btnZoomOut = document.getElementById("btn-mapa-zoom-out");
  const btnAlternar = document.getElementById("btn-alternar-camadas");
  const torre = document.getElementById("torre-camadas");
  const itensCamada = torre ? torre.querySelectorAll(".torre-camadas__item") : [];

  // 1. Atualização dos limites de zoom
  function atualizarBotoesZoom() {
    const z = mapa.getZoom();
    if (btnZoomIn) btnZoomIn.disabled = z >= mapa.getMaxZoom();
    if (btnZoomOut) btnZoomOut.disabled = z <= mapa.getMinZoom();
  }
  mapa.on("zoomend", atualizarBotoesZoom);
  atualizarBotoesZoom();

  // 2. Disparos de zoom e feedback de rolagem do mouse
  function dispararSwell(btn) {
    if (!btn || btn.disabled) return;
    btn.classList.add("pilula-mapa__btn-zoom--swell");
    clearTimeout(btn._swellTimer);
    btn._swellTimer = setTimeout(() => {
      btn.classList.remove("pilula-mapa__btn-zoom--swell");
    }, 350);
  }

  if (btnZoomIn) btnZoomIn.addEventListener("click", () => { mapa.zoomIn(); dispararSwell(btnZoomIn); });
  if (btnZoomOut) btnZoomOut.addEventListener("click", () => { mapa.zoomOut(); dispararSwell(btnZoomOut); });

  // Captura eventos de rolagem (wheel / scroll) da bola do mouse sobre o mapa
  const mapContainer = mapa.getContainer ? mapa.getContainer() : mapa;
  if (mapContainer && mapContainer.addEventListener) {
    mapContainer.addEventListener("wheel", (e) => {
      if (e.deltaY < 0) {
        dispararSwell(btnZoomIn);
      } else if (e.deltaY > 0) {
        dispararSwell(btnZoomOut);
      }
    }, { passive: true });
  }

  // Sincronia complementar com qualquer variação de zoom do Leaflet
  let zoomAnterior = mapa.getZoom();
  mapa.on("zoomstart", () => { zoomAnterior = mapa.getZoom(); });
  mapa.on("zoom", () => {
    const z = mapa.getZoom();
    if (z > zoomAnterior) dispararSwell(btnZoomIn);
    else if (z < zoomAnterior) dispararSwell(btnZoomOut);
    zoomAnterior = z;
  });

  // 3. Abertura e fechamento da torrezinha
  function fecharTorre() {
    if (!torre) return;
    torre.classList.add("torre-camadas--fechada");
    torre.classList.remove("torre-camadas--aberta");
    if (btnAlternar) btnAlternar.setAttribute("aria-expanded", "false");
  }

  function alternarTorre(e) {
    e.stopPropagation();
    if (!torre) return;
    const abrindo = torre.classList.contains("torre-camadas--fechada");
    if (abrindo) {
      torre.classList.remove("torre-camadas--fechada");
      torre.classList.add("torre-camadas--aberta");
      if (btnAlternar) btnAlternar.setAttribute("aria-expanded", "true");
    } else {
      fecharTorre();
    }
  }

  if (btnAlternar) btnAlternar.addEventListener("click", alternarTorre);
  document.addEventListener("click", (e) => {
    if (container && !container.contains(e.target)) fecharTorre();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") fecharTorre();
  });

  // 4. Alternância de camadas base
  itensCamada.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const nomeCamada = btn.dataset.camadaNome;
      const layerAlvo = baseMaps[nomeCamada];
      if (!layerAlvo) return;

      Object.values(baseMaps).forEach((layer) => {
        if (mapa.hasLayer(layer)) mapa.removeLayer(layer);
      });
      layerAlvo.addTo(mapa);

      itensCamada.forEach((b) => {
        const ativo = b === btn;
        b.classList.toggle("torre-camadas__item--ativo", ativo);
        b.setAttribute("aria-checked", ativo ? "true" : "false");
      });
      fecharTorre();
    });
  });

  // 5. Sincronização do hover na torre (reforço cross-browser para migração imediata do seletor)
  itensCamada.forEach((item) => {
    item.addEventListener("mouseenter", () => torre && torre.classList.add("has-item-hover"));
    item.addEventListener("mouseleave", () => torre && torre.classList.remove("has-item-hover"));
  });
}

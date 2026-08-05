// Deriva do fundo administrativo (SPEC user_admin/007): reenquadramento contínuo a partir de um
// centro fixo — utilitário de Leaflet, não animação de UI (§7.2). Amplitude pequena e ciclo longo
// deixam a cena viva sem virar movimento perceptível.
const PERIODO_MS = 150000;
const AMPLITUDE_GRAUS = 0.008;
const INTERVALO_FRAME_MS = 50;

export function derivarMapa(mapa, centro, zoom) {
  // Movimento perpétuo é custo de bateria e gatilho vestibular: para com a aba oculta e com
  // prefers-reduced-motion. O matchMedia é consultado a cada quadro para acompanhar a troca
  // da preferência sem recarregar a página.
  const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)");
  let ultimoFrame = 0;

  function passo(agora) {
    requestAnimationFrame(passo);
    if (document.hidden || reduzido.matches) return;
    if (agora - ultimoFrame < INTERVALO_FRAME_MS) return;
    ultimoFrame = agora;
    // Lissajous 1:2 — a volta nunca repete o mesmo traço e o centro não escapa da amplitude.
    const fase = ((agora % PERIODO_MS) / PERIODO_MS) * 2 * Math.PI;
    const lat = centro[0] + AMPLITUDE_GRAUS * Math.sin(fase);
    const lng = centro[1] + (AMPLITUDE_GRAUS * Math.sin(2 * fase)) / 2;
    mapa.setView([lat, lng], zoom, { animate: false });
  }

  requestAnimationFrame(passo);
}

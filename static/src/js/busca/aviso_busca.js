// Controle de fade-out e dismissão de avisos e erros exibidos em #resultado-busca
// (sobre o mapa, abaixo da barra de busca).
// Não afeta alertas em formulários, gavetas ou modais.

const TEMPO_VISIVEL_MS = 3500;
const DURACAO_FADE_MS = 500;

const inputBusca = document.getElementById("input_search");
const alvoResultado = document.getElementById("resultado-busca");

let timerAviso = null;
let timerFade = null;
let tempoRestanteMs = TEMPO_VISIVEL_MS;
let inicioTimestamp = null;
let emPausa = false;

function limparTimers() {
  if (timerAviso) {
    clearTimeout(timerAviso);
    timerAviso = null;
  }
  if (timerFade) {
    clearTimeout(timerFade);
    timerFade = null;
  }
}

function resetarEstilos(el) {
  if (!el) return;
  el.style.transition = "";
  el.style.opacity = "";
  el.style.transform = "";
}

function fecharAvisoImediato() {
  limparTimers();
  if (!alvoResultado) return;
  resetarEstilos(alvoResultado);
  alvoResultado.innerHTML = "";
}

function iniciarFadeOut() {
  if (!alvoResultado) return;
  alvoResultado.style.transition = `opacity ${DURACAO_FADE_MS}ms ease, transform ${DURACAO_FADE_MS}ms ease`;
  alvoResultado.style.opacity = "0";
  alvoResultado.style.transform = "translateY(-6px)";

  timerFade = setTimeout(() => {
    alvoResultado.innerHTML = "";
    resetarEstilos(alvoResultado);
    timerFade = null;
  }, DURACAO_FADE_MS);
}

function agendarDismissao(tempoMs) {
  limparTimers();
  tempoRestanteMs = tempoMs;
  inicioTimestamp = Date.now();
  emPausa = false;

  timerAviso = setTimeout(() => {
    iniciarFadeOut();
  }, tempoRestanteMs);
}

function aoEntrarMouse() {
  if (!timerAviso || emPausa) return;
  clearTimeout(timerAviso);
  timerAviso = null;
  const decorrido = Date.now() - inicioTimestamp;
  tempoRestanteMs = Math.max(tempoRestanteMs - decorrido, 500);
  emPausa = true;
}

function aoSairMouse() {
  if (!emPausa) return;
  emPausa = false;
  inicioTimestamp = Date.now();
  timerAviso = setTimeout(() => {
    iniciarFadeOut();
  }, tempoRestanteMs);
}

function aoSwapResultado(evento) {
  if (!alvoResultado) return;
  if (evento.detail.target !== alvoResultado) return;

  limparTimers();
  resetarEstilos(alvoResultado);

  const alerta = alvoResultado.querySelector('.alert, [role="alert"]');
  if (!alerta) return;

  agendarDismissao(TEMPO_VISIVEL_MS);
}

if (alvoResultado) {
  document.body.addEventListener("htmx:afterSwap", aoSwapResultado);
  alvoResultado.addEventListener("mouseenter", aoEntrarMouse);
  alvoResultado.addEventListener("mouseleave", aoSairMouse);
}

if (inputBusca) {
  inputBusca.addEventListener("input", () => {
    if (alvoResultado && alvoResultado.querySelector('.alert, [role="alert"]')) {
      fecharAvisoImediato();
    }
  });
}

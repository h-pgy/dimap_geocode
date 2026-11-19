const DURACAO_MINIMA_MS = 250;
const DURACAO_MAXIMA_MS = 600;
const MS_POR_PIXEL = 0.4;
const MOVIMENTO_REDUZIDO = window.matchMedia("(prefers-reduced-motion: reduce)");

function alvoDe(hash) {
  return hash ? document.getElementById(decodeURIComponent(hash.slice(1))) : null;
}

function abrir(alvo) {
  if (alvo?.matches(".faq-item")) alvo.open = true;
}

// Quem rola é o .admin-shell, não o documento.
function roladorDe(elemento) {
  for (let pai = elemento.parentElement; pai; pai = pai.parentElement) {
    const { overflowY } = getComputedStyle(pai);
    if (/(auto|scroll)/.test(overflowY) && pai.scrollHeight > pai.clientHeight) return pai;
  }
  return document.scrollingElement;
}

function suavizar(x) {
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
}

function rolarAte(alvo, aoTerminar) {
  const rolador = roladorDe(alvo);
  const topoRolador = rolador === document.scrollingElement ? 0 : rolador.getBoundingClientRect().top;
  const margem = parseFloat(getComputedStyle(alvo).scrollMarginTop) || 0;
  const inicio = rolador.scrollTop;
  const distancia = alvo.getBoundingClientRect().top - topoRolador - margem;
  const duracao = MOVIMENTO_REDUZIDO.matches
    ? 0
    : Math.min(DURACAO_MAXIMA_MS, Math.max(DURACAO_MINIMA_MS, Math.abs(distancia) * MS_POR_PIXEL));
  const partida = performance.now();

  function passo(agora) {
    const progresso = duracao ? Math.min(1, (agora - partida) / duracao) : 1;
    rolador.scrollTop = inicio + distancia * suavizar(progresso);
    if (progresso < 1) requestAnimationFrame(passo);
    else aoTerminar();
  }
  requestAnimationFrame(passo);
}

document.addEventListener("click", (evento) => {
  const recolher = evento.target.closest("[data-recolher-respostas]");
  if (recolher) {
    recolher.closest(".faq-conjunto").querySelectorAll(".faq-item[open]").forEach((item) => {
      item.open = false;
    });
    return;
  }
  const fechar = evento.target.closest("[data-fecha-faq]");
  if (fechar) {
    const item = document.getElementById(fechar.dataset.fechaFaq);
    if (item) item.open = false;
    return;
  }
  const link = evento.target.closest("[data-rola-faq]");
  const alvo = link && alvoDe(link.hash);
  if (!alvo) return;
  evento.preventDefault();
  abrir(alvo);
  // O hash entra só no fim: atualiza o :target e o histórico sem o salto nativo no meio da animação.
  rolarAte(alvo, () => {
    if (location.hash !== link.hash) location.hash = link.hash;
  });
});

function sincronizarAbertas(conjunto) {
  conjunto.querySelectorAll("[data-resposta-aberta]").forEach((item) => {
    item.hidden = !document.getElementById(item.dataset.respostaAberta)?.open;
  });
}

// `toggle` não borbulha: só a captura no documento enxerga todos os itens.
document.addEventListener("toggle", (evento) => {
  const conjunto = evento.target.closest?.(".faq-conjunto");
  if (conjunto && evento.target.matches(".faq-item")) sincronizarAbertas(conjunto);
}, true);

abrir(alvoDe(location.hash));
document.querySelectorAll(".faq-conjunto").forEach(sincronizarAbertas);

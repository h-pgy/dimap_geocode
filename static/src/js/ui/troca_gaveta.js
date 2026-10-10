// Callback de htmx:beforeSwap (SPEC localizacao_lote/003): diz no alvo como a gaveta nova chega,
// comparando o data-gaveta da raiz de hoje com o da resposta. Quem anima é o CSS, lendo a marca.
const ALVO = "gaveta-entidade";
const TROCA_COM_FADE = "innerHTML swap:150ms settle:200ms";

function chave(raiz) {
  return raiz.querySelector(".gaveta-lateral")?.dataset.gaveta ?? null;
}

function moldeDe(html) {
  const molde = document.createElement("template");
  molde.innerHTML = html;
  return molde.content;
}

function modo(alvo, nova) {
  if (!alvo.querySelector(":scope > .gaveta-lateral > .gaveta-lateral-toggle:checked")) return "entrada";
  // A mesma gaveta redesenhada (a bancada, a cada traço) não anima: só outra entidade troca.
  return chave(nova) === chave(alvo) ? "mesma" : "troca";
}

export function inicializarTrocaGaveta() {
  htmx.on("htmx:beforeSwap", (evento) => {
    const alvo = evento.detail.target;
    if (alvo.id !== ALVO) return;
    alvo.dataset.trocaGaveta = modo(alvo, moldeDe(evento.detail.serverResponse));
    if (alvo.dataset.trocaGaveta === "troca") evento.detail.swapOverride = TROCA_COM_FADE;
  });
  // A cena chega por OOB (SPEC design/021), que não dispara o beforeSwap nem aceita espera de swap:
  // a marca vai no alvo do mesmo jeito, e a gaveta nova entra fundindo, sem o fade de saída.
  htmx.on("htmx:oobBeforeSwap", (evento) => {
    const alvo = evento.detail.target;
    if (alvo.id !== ALVO) return;
    alvo.dataset.trocaGaveta = modo(alvo, evento.detail.fragment);
  });
}

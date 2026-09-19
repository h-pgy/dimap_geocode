// Callback de htmx:beforeSwap (SPEC localizacao_lote/003): diz no alvo como a gaveta nova chega,
// comparando o data-gaveta da raiz de hoje com o da resposta. Quem anima é o CSS, lendo a marca.
const ALVO = "gaveta-entidade";
const TROCA_COM_FADE = "innerHTML swap:150ms settle:200ms";

function chave(raiz) {
  return raiz.querySelector(".gaveta-lateral")?.dataset.gaveta ?? null;
}

function modo(alvo, html) {
  if (!alvo.querySelector(":scope > .gaveta-lateral > .gaveta-lateral-toggle:checked")) return "entrada";
  const molde = document.createElement("template");
  molde.innerHTML = html;
  // A mesma gaveta redesenhada (a bancada, a cada traço) não anima: só outra entidade troca.
  return chave(molde.content) === chave(alvo) ? "mesma" : "troca";
}

export function inicializarTrocaGaveta() {
  htmx.on("htmx:beforeSwap", (evento) => {
    const alvo = evento.detail.target;
    if (alvo.id !== ALVO) return;
    alvo.dataset.trocaGaveta = modo(alvo, evento.detail.serverResponse);
    if (alvo.dataset.trocaGaveta === "troca") evento.detail.swapOverride = TROCA_COM_FADE;
  });
}

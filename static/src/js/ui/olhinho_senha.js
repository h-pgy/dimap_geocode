// Alternador de visibilidade de senha (SPEC autenticacao/001): estado visual de um controle —
// o campo troca de `type` (password/text), o botão só espelha o estado nos dois glifos.
function alternar(botao) {
  const alvo = document.querySelector(botao.dataset.olhinhoAlvo);
  if (!alvo) return;
  const paraTexto = alvo.type === "password";
  alvo.type = paraTexto ? "text" : "password";
  botao.querySelector(".icone-olho-aberto")?.classList.toggle("hidden", paraTexto);
  botao.querySelector(".icone-olho-fechado")?.classList.toggle("hidden", !paraTexto);
}

function montar(raiz) {
  raiz.querySelectorAll("[data-olhinho-alvo]").forEach((botao) => {
    botao.addEventListener("click", () => alternar(botao));
  });
}

document.addEventListener("DOMContentLoaded", () => montar(document));
// O partial dinâmico do login troca o campo de senha por HTMX: o botão que chega precisa montar.
document.body.addEventListener("htmx:load", (evento) => montar(evento.detail.elt));

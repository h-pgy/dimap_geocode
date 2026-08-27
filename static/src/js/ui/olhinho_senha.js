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

// O atributo de montagem marca o que já foi feito: `htmx:load` também dispara no scan inicial da
// página (não só num swap real) — sem a marca, um botão presente desde o carregamento ganhava dois
// ouvintes, e o segundo clique desfazia o primeiro (SPEC autenticacao/002).
function montar() {
  document.querySelectorAll("[data-olhinho-alvo]:not([data-olhinho-montado])").forEach((botao) => {
    botao.dataset.olhinhoMontado = "true";
    botao.addEventListener("click", () => alternar(botao));
  });
}

document.addEventListener("DOMContentLoaded", montar);
// O partial dinâmico do login troca o campo de senha por HTMX: o botão que chega precisa montar.
document.addEventListener("htmx:afterSwap", montar);

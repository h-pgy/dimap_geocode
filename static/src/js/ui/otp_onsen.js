// Caixas do átomo OTP (SPEC autenticacao/001): auto-avanço, backspace para a caixa anterior e
// colagem distribuída — estado visual de um controle. O valor que segue para o servidor é sempre
// a junção das 8 caixas no campo oculto apontado por [data-otp-alvo].
function juntar(caixas) {
  return caixas.map((caixa) => caixa.value).join("");
}

function escreverAlvo(container, caixas) {
  const alvo = document.querySelector(container.dataset.otpAlvo);
  if (alvo) alvo.value = juntar(caixas);
}

function montar(container) {
  const caixas = Array.from(container.querySelectorAll(".otp-caixa"));

  caixas.forEach((caixa, indice) => {
    caixa.addEventListener("input", () => {
      caixa.value = caixa.value.replace(/\D/g, "").slice(-1);
      if (caixa.value && indice < caixas.length - 1) caixas[indice + 1].focus();
      escreverAlvo(container, caixas);
    });

    caixa.addEventListener("keydown", (evento) => {
      if (evento.key === "Backspace" && !caixa.value && indice > 0) caixas[indice - 1].focus();
    });

    caixa.addEventListener("paste", (evento) => {
      evento.preventDefault();
      const colado = (evento.clipboardData?.getData("text") ?? "").replace(/\D/g, "");
      caixas.forEach((alvo, i) => {
        alvo.value = colado[i] ?? "";
      });
      caixas[Math.min(colado.length, caixas.length) - 1]?.focus();
      escreverAlvo(container, caixas);
    });
  });
}

function montarTodos(raiz) {
  raiz.querySelectorAll("[data-otp-alvo]").forEach(montar);
}

document.addEventListener("DOMContentLoaded", () => montarTodos(document));
document.body.addEventListener("htmx:load", (evento) => montarTodos(evento.detail.elt));

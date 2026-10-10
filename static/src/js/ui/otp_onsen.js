// Caixas do átomo OTP (SPEC autenticacao/001, documentos_oficiais/010): auto-avanço,
// backspace para a caixa anterior, colagem distribuída e redirecionamento ao completar —
// estado visual de um controle. O valor que segue para o servidor é a junção das caixas no
// campo oculto apontado por [data-otp-alvo].
function juntar(caixas) {
  return caixas.map((caixa) => caixa.value).join("");
}

function redirecionarSeConfigurado(container, valor) {
  if (!container.dataset.otpRedirecionar) return;
  const url = container.dataset.otpRedirecionar
    .replace("{valor}", encodeURIComponent(valor))
    .replace("{codigo}", encodeURIComponent(valor));
  window.location.href = url;
}

function submeterSeConfigurado(container) {
  if (!container.dataset.otpAutoSubmit) return;
  const form = document.querySelector(container.dataset.otpAutoSubmit);
  if (form) {
    if (typeof form.requestSubmit === "function") {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }
}

function escreverAlvo(container, caixas) {
  const alvo = document.querySelector(container.dataset.otpAlvo);
  const valor = juntar(caixas);
  if (alvo) alvo.value = valor;

  if (valor.length === caixas.length) {
    container.dispatchEvent(new CustomEvent("otp:completo", { detail: { valor }, bubbles: true }));
    redirecionarSeConfigurado(container, valor);
    submeterSeConfigurado(container);
  }
}

function montar(container) {
  if (container.dataset.otpMontado === "true") return;
  container.dataset.otpMontado = "true";

  const caixas = Array.from(container.querySelectorAll(".otp-caixa"));

  caixas.forEach((caixa, indice) => {
    const isNumeric = caixa.getAttribute("inputmode") === "numeric";
    const regex = isNumeric ? /\D/g : /[^a-zA-Z0-9]/g;

    caixa.addEventListener("input", () => {
      caixas.forEach((c) => c.classList.remove("campo-realce-erro"));
      let val = caixa.value.replace(regex, "").slice(-1);
      if (!isNumeric) val = val.toUpperCase();
      caixa.value = val;
      if (caixa.value && indice < caixas.length - 1) caixas[indice + 1].focus();
      escreverAlvo(container, caixas);
    });

    caixa.addEventListener("keydown", (evento) => {
      if (evento.key === "Backspace" && !caixa.value && indice > 0) {
        caixas[indice - 1].focus();
      }
    });

    caixa.addEventListener("paste", (evento) => {
      evento.preventDefault();
      caixas.forEach((c) => c.classList.remove("campo-realce-erro"));
      let colado = (evento.clipboardData?.getData("text") ?? "").replace(regex, "");
      if (!isNumeric) colado = colado.toUpperCase();
      caixas.forEach((alvo, i) => {
        alvo.value = colado[i] ?? "";
      });
      const proximoFoco = Math.min(colado.length, caixas.length - 1);
      if (proximoFoco >= 0) caixas[proximoFoco].focus();
      escreverAlvo(container, caixas);
    });
  });

  const seletorBotao = container.dataset.otpBotaoVerificar;
  const botao = seletorBotao ? document.querySelector(seletorBotao) : null;
  if (botao) {
    botao.addEventListener("click", (evento) => {
      const valor = juntar(caixas);
      if (valor.length === caixas.length) {
        redirecionarSeConfigurado(container, valor);
        submeterSeConfigurado(container);
      } else {
        if (evento.target.type === "submit") evento.preventDefault();
        const primeiraVazia = caixas.find((c) => !c.value);
        if (primeiraVazia) primeiraVazia.focus();
      }
    });
  }
}

function montarTodos(raiz) {
  if (!raiz || !raiz.querySelectorAll) return;
  raiz.querySelectorAll("[data-otp-alvo]").forEach(montar);
}

document.addEventListener("DOMContentLoaded", () => montarTodos(document));
document.body.addEventListener("htmx:load", (evento) => {
  const elemento = evento.detail?.elt || document;
  montarTodos(elemento);
});

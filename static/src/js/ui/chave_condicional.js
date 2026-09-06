// Campos condicionais pela chave de duas posições (SPEC autorizacao/008): estado visual de um
// controle, autorizado pelo usuário — a alternativa em CSS puro (`.chave-onsen` + `has()` sobre
// seletor de atributo aninhado) esbarrou em limite do @tailwindcss/browser (CDN de dev), que
// truncava a variante e deixava os dois campos sempre visíveis. Nenhuma regra de negócio aqui: o
// valor concedido segue vindo só do <select> que fica visível, e é ele quem o formulário envia.

function aplicar(escopo) {
  const selecionado = escopo.querySelector('input[type="radio"]:checked');
  if (!selecionado) return;
  escopo.querySelectorAll("[data-mostra-se]").forEach((campo) => {
    campo.hidden = campo.dataset.mostraSe !== selecionado.value;
  });
}

export function aplicarChavesCondicionais() {
  document.querySelectorAll("[data-chave-condicional]").forEach(aplicar);
}

// DOMContentLoaded para a carga inicial, htmx:afterSwap para o modal reaberto por hx-get — o
// mesmo par de gatilhos de select_onsen.js.
document.addEventListener("DOMContentLoaded", aplicarChavesCondicionais);
document.addEventListener("htmx:afterSwap", aplicarChavesCondicionais);

// Delegação: um ouvinte só cobre qualquer chave condicional presente na página.
document.addEventListener("change", (evento) => {
  if (!(evento.target instanceof HTMLInputElement) || evento.target.type !== "radio") return;
  const escopo = evento.target.closest("[data-chave-condicional]");
  if (escopo) aplicar(escopo);
});

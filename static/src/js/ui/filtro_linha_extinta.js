// Filtro client-side das linhas extintas nas tabelas-onsen (SPEC user_admin/029): o servidor manda
// SEMPRE todas as linhas, marcadas com .linha-extinta quando extintas; este módulo é quem esconde
// ou revela, a partir do toggle "Mostrar X extintos". Nenhum round-trip ao servidor — fazer o
// servidor saber do estado do toggle a cada requisição (filtro de coluna, ordenação, ou o swap fora
// de banda que os outros atos disparam) foi tentado e quebrou duas vezes seguidas (Caveats).

function aplicar(toggle) {
  const alvo = document.querySelector(toggle.dataset.filtroExtintos);
  if (!alvo) return;
  alvo.querySelectorAll(".linha-extinta").forEach((linha) => {
    linha.hidden = !toggle.checked;
  });
}

export function aplicarFiltrosDeExtintos() {
  document.querySelectorAll("[data-filtro-extintos]").forEach(aplicar);
}

// DOMContentLoaded para a carga inicial, htmx:afterSwap para toda vez que a tabela é substituída —
// o toggle não é filho do que é trocado, então o `checked` dele sobrevive ao swap; só a marcação das
// linhas novas precisa ser reaplicada.
document.addEventListener("DOMContentLoaded", aplicarFiltrosDeExtintos);
document.addEventListener("htmx:afterSwap", aplicarFiltrosDeExtintos);

// Delegação: um ouvinte só cobre qualquer toggle de extintos presente na página.
document.addEventListener("change", (evento) => {
  if (evento.target instanceof HTMLInputElement && evento.target.matches("[data-filtro-extintos]")) {
    aplicar(evento.target);
  }
});

// Ordenação da tabela de vidro (SPEC user_admin/013). O único trabalho que o CSS não faz: alternar
// asc → desc → sem ordem num alvo único e escrever a escolha nos campos que viajam no pedido.
// O filtro não passa por aqui — afundar a coluna é :has sobre o valor do campo, e o casamento
// textual é do servidor (a normalização única do §6.1 não se duplica em JavaScript).
// O foco também não: o swap troca só o <tbody>, então o campo em que se digita nem é tocado.

const PROXIMA_ORDEM = {
  "": "ascending",
  ascending: "descending",
  descending: "",
};
// O pedido é declarado no markup (hx-trigger da tabela); daqui sai só o aviso de que a ordem mudou.
const EVENTO_ORDENACAO = "ordenacao";

function celulasOrdenaveis(tabela) {
  return [...tabela.querySelectorAll(".th-onsen[data-coluna]")];
}

function repousar(tabela) {
  celulasOrdenaveis(tabela).forEach((celula) => celula.removeAttribute("aria-sort"));
  tabela.querySelector("[data-ordenar-por]").value = "";
  tabela.querySelector("[data-descendente]").value = "0";
}

function ordenarPor(tabela, celula) {
  const atual = celula.getAttribute("aria-sort") ?? "";
  const proxima = PROXIMA_ORDEM[atual];
  repousar(tabela);
  if (proxima) {
    celula.setAttribute("aria-sort", proxima);
    tabela.querySelector("[data-ordenar-por]").value = celula.dataset.coluna;
    tabela.querySelector("[data-descendente]").value = proxima === "descending" ? "1" : "0";
  }
  tabela.dispatchEvent(new Event(EVENTO_ORDENACAO));
}

function montarTabela(tabela) {
  // Delegação: as setas vivem no cabeçalho, que nunca é trocado, mas um ouvinte só continua sendo
  // menos peça em pé do que um por coluna.
  tabela.addEventListener("click", (evento) => {
    const seta = evento.target.closest(".sort-etched");
    if (!seta) return;
    ordenarPor(tabela, seta.closest(".th-onsen[data-coluna]"));
  });
}

function montarLimpeza(botao) {
  const tabela = document.querySelector(botao.dataset.limparFiltros);
  botao.addEventListener("click", () => {
    tabela
      .querySelectorAll(".th-onsen-input")
      .forEach((campo) => (campo.value = ""));
    repousar(tabela);
    tabela.dispatchEvent(new Event(EVENTO_ORDENACAO));
  });
}

export function montarTabelasOnsen() {
  document
    .querySelectorAll("[data-tabela-onsen]:not([data-tabela-onsen-montada])")
    .forEach((tabela) => {
      tabela.dataset.tabelaOnsenMontada = "true";
      montarTabela(tabela);
    });
  document
    .querySelectorAll("[data-limpar-filtros]:not([data-limpar-filtros-montado])")
    .forEach((botao) => {
      botao.dataset.limparFiltrosMontado = "true";
      montarLimpeza(botao);
    });
}

document.addEventListener("DOMContentLoaded", montarTabelasOnsen);
document.addEventListener("htmx:afterSwap", montarTabelasOnsen);

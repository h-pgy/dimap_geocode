// Árvore hierárquica (SPEC user_admin/018). Utilitário de UI: o organograma inteiro chega
// renderizado pelo servidor, com o caminho e o ego já marcados; abrir e fechar é estado VISUAL do
// controle — mover essas duas marcas e revelar/esconder ramos que já estão no DOM. Nenhum dado de
// domínio nasce aqui, e nada disto vai ao servidor (CLAUDE.md §7.2).

function paiDoNo(no) {
  return no.parentElement.closest(".no-arvore");
}

// Escavado (caminho ou ego) troca o material do card; ego, além disso, acende.
function vestir(no) {
  const card = no.querySelector(":scope > .card-unidade");
  const escavado = no.classList.contains("no-arvore-caminho") || no.classList.contains("no-arvore-ego");
  card.classList.toggle("card-unidade-repouso", !escavado);
  card.classList.toggle("glass-panel", !escavado);
  card.classList.toggle("card-unidade-poco", escavado);
  card.classList.toggle("card-unidade-ego", no.classList.contains("no-arvore-ego"));
}

function moverEgo(organograma, alvo, alternar = true) {
  const jaEraEgo = alvo.classList.contains("no-arvore-ego");
  const caminho = new Set();
  for (let no = alvo; no; no = paiDoNo(no)) caminho.add(no);
  organograma.querySelectorAll(".no-arvore").forEach((no) => {
    no.classList.remove("no-arvore-caminho", "no-arvore-ego");
    // Ramo abandonado se fecha; o que já estava aberto no caminho continua.
    if (!caminho.has(no)) no.classList.remove("no-arvore-aberto");
  });
  // Clicar de novo no ego é fechá-lo: o segundo clique é o que recolhe o nível.
  const abrir = alternar ? (jaEraEgo ? !alvo.classList.contains("no-arvore-aberto") : true) : false;
  alvo.classList.add("no-arvore-ego");
  alvo.classList.toggle("no-arvore-aberto", abrir);
  for (let acima = paiDoNo(alvo); acima; acima = paiDoNo(acima)) acima.classList.add("no-arvore-caminho");
  organograma.querySelectorAll(".no-arvore").forEach(vestir);
}

function abrirTudo(organograma, abrir) {
  organograma.querySelectorAll(".no-arvore").forEach((no) => {
    no.classList.toggle("no-arvore-aberto", abrir);
    vestir(no);
  });
}

function voltarAoInicio(organograma) {
  // O estado de partida é o que o servidor entregou: o ego na unidade da página, e fechado.
  organograma.querySelectorAll(".no-arvore").forEach((no) => no.classList.remove("no-arvore-aberto"));
  moverEgo(organograma, organograma.querySelector("[data-ego-inicial]"), false);
}

document.addEventListener("click", (evento) => {
  const volta = evento.target.closest("[data-voltar]");
  if (volta) {
    voltarAoInicio(document.querySelector(volta.dataset.voltar));
    return;
  }
  const tudo = evento.target.closest("[data-abrir-tudo]");
  if (tudo) {
    const abrir = tudo.dataset.aberta !== "1";
    abrirTudo(document.querySelector(tudo.dataset.abrirTudo), abrir);
    tudo.dataset.aberta = abrir ? "1" : "0";
    tudo.lastChild.textContent = abrir ? ` ${tudo.dataset.rotuloRecolher} ` : " Ver toda a árvore ";
    return;
  }
  const chamado = evento.target.closest(".no-arvore-irmas");
  if (chamado) {
    // As irmãs são as outras filhas do mesmo pai: quem abre a linha inteira é ele.
    const pai = paiDoNo(chamado.closest(".no-arvore"));
    if (pai) pai.classList.toggle("no-arvore-aberto");
    return;
  }
  const gatilho = evento.target.closest(".card-unidade-gatilho");
  if (!gatilho) return;
  const no = gatilho.closest(".no-arvore");
  moverEgo(no.closest(".organograma"), no);
});

// O servidor entrega o caminho e o ego já marcados nos nós; esta passada só veste os cards conforme
// essas marcas — nenhuma delas muda aqui.
export function vestirOrganogramas() {
  document.querySelectorAll(".organograma .no-arvore").forEach(vestir);
}

document.addEventListener("DOMContentLoaded", vestirOrganogramas);
document.addEventListener("htmx:afterSwap", vestirOrganogramas);

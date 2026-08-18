// Sincronia bidirecional entre Organograma e Tabela de Unidades (SPEC user_admin/019).
// Coordena os gestos:
// 1. Clicar em um nó do organograma move a linha correspondente para a 1ª posição da tabela,
//    aplica o destaque ciano ativo e rola a tabela ao topo.
// 2. Clicar numa linha da tabela ativa o nó correspondente na árvore superior.

function destacarLinhaNaTabela(sigla) {
  const tbody = document.getElementById("corpo-unidades");
  if (!tbody) return;
  const linha = tbody.querySelector(`tr[data-unidade-sigla="${sigla}"]`);
  if (!linha) return;

  tbody.querySelectorAll("tr").forEach((tr) => tr.removeAttribute("data-ativo"));
  tbody.prepend(linha);
  linha.setAttribute("data-ativo", "true");

  const rolador = document.getElementById("rolador-unidades");
  if (rolador) {
    rolador.scrollTo({ top: 0, behavior: "smooth" });
  }
}

document.addEventListener("click", (evento) => {
  // A. Clique no card do organograma -> Destaca linha na tabela
  const gatilho = evento.target.closest("#organograma-unidades .card-unidade-gatilho");
  if (gatilho) {
    const no = gatilho.closest(".no-arvore");
    const sigla = no?.dataset?.unidadeSigla || gatilho.querySelector(".card-unidade-sigla")?.textContent?.trim();
    if (sigla) {
      destacarLinhaNaTabela(sigla);
    }
    return;
  }

  // B. Clique na linha da tabela -> Ativa nó no organograma
  const linha = evento.target.closest("#corpo-unidades tr");
  if (linha) {
    // Se o clique foi direto num link ou botão de ação, preserva a navegação padrão
    if (evento.target.closest(".link-interno") || evento.target.closest("a") || evento.target.closest("button")) {
      return;
    }
    const sigla = linha.dataset.unidadeSigla;
    if (!sigla) return;

    const organograma = document.getElementById("organograma-unidades");
    if (organograma) {
      // Procura o nó com a mesma sigla no organograma
      const cards = organograma.querySelectorAll(".card-unidade-sigla");
      for (const cardSigla of cards) {
        if (cardSigla.textContent.trim() === sigla) {
          const botao = cardSigla.closest(".card-unidade-gatilho");
          if (botao) {
            botao.click();
            break;
          }
        }
      }
    }

    const tbody = document.getElementById("corpo-unidades");
    if (tbody) {
      tbody.querySelectorAll("tr").forEach((tr) => tr.removeAttribute("data-ativo"));
      linha.setAttribute("data-ativo", "true");
    }
  }
});

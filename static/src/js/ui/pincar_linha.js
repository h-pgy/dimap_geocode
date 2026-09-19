// Sobe uma linha de tabela até o topo deslizando, como a pincagem de unidades (SPEC user_admin/021):
// quem desliza é um clone, porque <tr> não aceita transform sem desmontar a grade. A pele é toda de
// .table-flutuante-clone e .linha-pincada (tema-dimap.dev.css); daqui saem só medidas, em custom properties.
const DURACAO_MS = 500;
const ALTURA_CABECALHO_PADRAO = 40;

let temporizador = null;

export function cancelarPincagem() {
  clearTimeout(temporizador);
  temporizador = null;
  document.querySelectorAll(".table-flutuante-clone").forEach((clone) => clone.remove());
  document.querySelectorAll("tr.linha-pincada").forEach((tr) => tr.classList.remove("linha-pincada"));
}

function montarClone(linha, rolador) {
  const tabela = document.createElement("table");
  tabela.className = "table table-onsen table-onsen-compacta table-flutuante-clone glass-panel-thick";
  tabela.style.setProperty("--topo-pincagem", `${linha.offsetTop}px`);
  tabela.style.setProperty("--altura-pincagem", `${linha.offsetHeight}px`);
  tabela.style.setProperty("--duracao-pincagem", `${DURACAO_MS}ms`);

  const copia = linha.cloneNode(true);
  copia.setAttribute("data-ativo", "true");
  // O clone é só imagem: sem o id ele não entra no realce linha ↔ lote nem nas buscas por linha.
  copia.removeAttribute("data-id-feature");

  // A largura sai do cabeçalho: é o thead que manda na grade, e o clone precisa cair alinhado com ela.
  const cabecalhos = linha.closest("table")?.querySelectorAll("thead th") ?? [];
  copia.querySelectorAll("td").forEach((td, indice) => {
    const referencia = cabecalhos[indice];
    if (referencia) td.style.setProperty("--largura-coluna", `${referencia.getBoundingClientRect().width}px`);
  });

  const corpo = document.createElement("tbody");
  corpo.appendChild(copia);
  tabela.appendChild(corpo);
  rolador.appendChild(tabela);
  return tabela;
}

export function pincarLinha(linha) {
  cancelarPincagem();
  const corpo = linha.parentElement;
  const rolador = linha.closest("[data-rolador]");
  if (!corpo || !rolador) return;

  // Já no topo não há trajeto: rolar até lá basta, e montar o clone só piscaria.
  if (corpo.firstElementChild === linha) {
    rolador.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  const topoFinal = rolador.querySelector("thead")?.offsetHeight ?? ALTURA_CABECALHO_PADRAO;
  const clone = montarClone(linha, rolador);
  linha.classList.add("linha-pincada");
  // Força o reflow antes de trocar o destino: sem isto o navegador funde as duas escritas e a transição não existe.
  void clone.offsetHeight;
  clone.style.setProperty("--topo-pincagem", `${topoFinal}px`);
  rolador.scrollTo({ top: 0, behavior: "smooth" });

  temporizador = setTimeout(() => {
    corpo.prepend(linha);
    cancelarPincagem();
  }, DURACAO_MS);
}

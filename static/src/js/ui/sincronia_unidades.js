// Sincronia entre o organograma e a tabela de unidades (SPEC user_admin/021): escolher uma unidade
// num deles a destaca no outro e pinça a linha dela até o topo da tabela.
//
// O deslizamento é estado visual de um controle — não vai ao servidor. Toda a PELE do clone que
// desliza mora em .table-flutuante-clone (tema-dimap.dev.css); daqui saem só as medidas que só
// existem em tempo de execução, escritas como custom properties: onde a linha está, para onde vai,
// que altura tem e quanto mede cada coluna.

const DURACAO_PINCAGEM_MS = 500;
// Sem cabeçalho medido, o clone pousa numa altura de linha padrão em vez de sumir sob a bandeja.
const ALTURA_CABECALHO_PADRAO = 40;

let timeoutsSincronia = [];

function limparAnimacoesSincronia() {
  timeoutsSincronia.forEach((t) => clearTimeout(t));
  timeoutsSincronia = [];
  document.querySelectorAll(".table-flutuante-clone").forEach((c) => c.remove());
  const tbody = document.getElementById("corpo-unidades");
  if (tbody) {
    tbody.querySelectorAll("tr").forEach((tr) => tr.classList.remove("linha-pincada"));
  }
}

function marcarAtiva(tbody, linha) {
  tbody.querySelectorAll("tr").forEach((tr) => tr.removeAttribute("data-ativo"));
  linha.setAttribute("data-ativo", "true");
}

function montarClone(linha, rolador, topoInicial, duracaoTotal) {
  const cloneTable = document.createElement("table");
  cloneTable.className = "table table-onsen table-flutuante-clone glass-panel-thick";
  cloneTable.style.setProperty("--topo-pincagem", `${topoInicial}px`);
  cloneTable.style.setProperty("--altura-pincagem", `${linha.offsetHeight}px`);
  cloneTable.style.setProperty("--duracao-pincagem", `${duracaoTotal}ms`);

  const cloneTr = linha.cloneNode(true);
  cloneTr.setAttribute("data-ativo", "true");

  // A largura sai do cabeçalho, e da célula só quando ele não existe: é o thead que manda na grade
  // enquanto a tabela está em table-layout auto, e o clone precisa cair alinhado com ela.
  const cabecalhos = linha.closest("table")?.querySelectorAll("thead th") ?? [];
  const celulasOriginais = linha.querySelectorAll("td");
  cloneTr.querySelectorAll("td").forEach((td, indice) => {
    const referencia = cabecalhos[indice] || celulasOriginais[indice];
    if (referencia) {
      td.style.setProperty("--largura-coluna", `${referencia.getBoundingClientRect().width}px`);
    }
  });

  const cloneTbody = document.createElement("tbody");
  cloneTbody.appendChild(cloneTr);
  cloneTable.appendChild(cloneTbody);
  rolador.appendChild(cloneTable);
  return cloneTable;
}

function destacarLinhaNaTabela(sigla, duracaoTotal = DURACAO_PINCAGEM_MS) {
  const tbody = document.getElementById("corpo-unidades");
  if (!tbody) return;
  const linha = tbody.querySelector(`tr[data-unidade-sigla="${sigla}"]`);
  if (!linha) return;

  limparAnimacoesSincronia();
  marcarAtiva(tbody, linha);

  const rolador = document.getElementById("rolador-unidades") || document.getElementById("rolador-tabela");
  if (!rolador) return;

  // Já no topo não há trajeto a percorrer: rolar até lá basta, e montar o clone só piscaria.
  const primeiraLinha = tbody.querySelector("tr:not([style*='display: none'])");
  if (!primeiraLinha || primeiraLinha === linha) {
    rolador.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  const thead = rolador.querySelector("thead");
  const topoFinal = thead ? thead.offsetHeight : ALTURA_CABECALHO_PADRAO;
  const cloneTable = montarClone(linha, rolador, linha.offsetTop, duracaoTotal);

  linha.classList.add("linha-pincada");
  // Força o reflow antes de trocar o destino: sem isto o browser funde as duas escritas e a
  // transição nunca chega a existir.
  void cloneTable.offsetHeight;

  cloneTable.style.setProperty("--topo-pincagem", `${topoFinal}px`);
  rolador.scrollTo({ top: 0, behavior: "smooth" });

  const t = setTimeout(() => {
    tbody.prepend(linha);
    marcarAtiva(tbody, linha);
    limparAnimacoesSincronia();
    rolador.scrollTo({ top: 0, behavior: "smooth" });
  }, duracaoTotal);
  timeoutsSincronia.push(t);
}

document.addEventListener("click", (evento) => {
  // Clique no card do organograma: destaca a linha correspondente na tabela.
  const gatilho = evento.target.closest("#organograma-unidades .card-unidade-gatilho");
  if (gatilho) {
    const sigla = gatilho.querySelector(".card-unidade-sigla")?.textContent?.trim();
    if (sigla) {
      destacarLinhaNaTabela(sigla);
    }
    return;
  }

  // Clique na linha da tabela: ativa o nó correspondente na árvore e pinça a linha.
  const linha = evento.target.closest("#corpo-unidades tr");
  if (!linha) return;
  // Link e botão dentro da linha respondem por si: pinçar por cima roubaria a navegação.
  if (evento.target.closest("a") || evento.target.closest("button")) return;

  const sigla = linha.dataset.unidadeSigla;
  if (!sigla) return;

  const organograma = document.getElementById("organograma-unidades");
  if (organograma) {
    const cards = organograma.querySelectorAll(".card-unidade-sigla");
    for (const cardSigla of cards) {
      if (cardSigla.textContent.trim() === sigla) {
        cardSigla.closest(".card-unidade-gatilho")?.click();
        break;
      }
    }
  }

  destacarLinhaNaTabela(sigla);
});

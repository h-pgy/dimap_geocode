// Sincronia bidirecional entre Organograma e Tabela de Unidades (SPEC user_admin/019).
// Coordena os gestos:
// 1. Clicar em um nó do organograma destaca a unidade e executa o deslizamento contínuo em Thick Glass
//    da linha correspondente até a 1ª posição da tabela (500ms) sem saltos.
// 2. Clicar numa linha da tabela ativa o nó correspondente na árvore superior e executa o deslizamento contínuo.

let timeoutsSincronia = [];

function limparAnimacoesSincronia() {
  timeoutsSincronia.forEach((t) => clearTimeout(t));
  timeoutsSincronia = [];
  document.querySelectorAll(".table-flutuante-clone").forEach((c) => c.remove());
  const tbody = document.getElementById("corpo-unidades");
  if (tbody) {
    tbody.querySelectorAll("tr").forEach((tr) => {
      tr.style.opacity = "";
      tr.style.transition = "";
      tr.style.transform = "";
      tr.style.zIndex = "";
      tr.style.position = "";
      tr.style.boxShadow = "";
    });
  }
}

function destacarLinhaNaTabela(sigla, duracaoTotal = 500) {
  const tbody = document.getElementById("corpo-unidades");
  if (!tbody) return;
  const linha = tbody.querySelector(`tr[data-unidade-sigla="${sigla}"]`);
  if (!linha) return;

  limparAnimacoesSincronia();

  tbody.querySelectorAll("tr").forEach((tr) => tr.removeAttribute("data-ativo"));
  linha.setAttribute("data-ativo", "true");

  const rolador = document.getElementById("rolador-unidades") || document.getElementById("rolador-tabela");
  if (!rolador) return;

  const primeiraLinha = tbody.querySelector("tr:not([style*='display: none'])");
  if (!primeiraLinha || primeiraLinha === linha) {
    rolador.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  const thead = rolador.querySelector("thead");
  const theadHeight = thead ? thead.offsetHeight : 40;
  const topInicial = linha.offsetTop;
  const topFinal = theadHeight;

  // Cria a tabela flutuante delimitada rigorosamente ao rolador em Thick Glass
  const cloneTable = document.createElement("table");
  cloneTable.className = "table table-onsen table-flutuante-clone glass-panel-thick";
  cloneTable.style.position = "absolute";
  cloneTable.style.top = `${topInicial}px`;
  cloneTable.style.left = "0";
  cloneTable.style.width = "100%";
  cloneTable.style.maxWidth = "100%";
  cloneTable.style.height = `${linha.offsetHeight}px`;
  cloneTable.style.boxSizing = "border-box";
  cloneTable.style.zIndex = "40";
  cloneTable.style.pointerEvents = "none";
  cloneTable.style.tableLayout = "fixed";
  cloneTable.style.borderRadius = "10px";
  cloneTable.style.overflow = "hidden";
  cloneTable.style.backdropFilter = "blur(28px)";
  cloneTable.style.background = "linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(220, 245, 255, 0.92) 50%, rgba(200, 235, 250, 0.88) 100%)";
  cloneTable.style.border = "1px solid rgba(255, 255, 255, 0.85)";
  cloneTable.style.boxShadow = "inset 0 1px 0 rgba(255,255,255,1), 0 12px 30px rgba(7,58,84,0.3), 0 0 28px rgba(72,202,228,0.3)";
  cloneTable.style.transition = `top ${duracaoTotal}ms cubic-bezier(0.16, 1, 0.3, 1)`;

  const cloneTbody = document.createElement("tbody");
  const cloneTr = linha.cloneNode(true);
  cloneTr.setAttribute("data-ativo", "true");
  cloneTr.style.background = "transparent";

  const tabela = tbody.closest("table");
  const ths = tabela ? tabela.querySelectorAll("thead th") : [];
  const cloneTds = cloneTr.querySelectorAll("td");
  cloneTds.forEach((td, i) => {
    const refEl = ths[i] || linha.querySelectorAll("td")[i];
    if (refEl) {
      const w = refEl.getBoundingClientRect().width;
      td.style.width = `${w}px`;
      td.style.minWidth = `${w}px`;
      td.style.maxWidth = `${w}px`;
      td.style.boxSizing = "border-box";
    }
  });

  cloneTbody.appendChild(cloneTr);
  cloneTable.appendChild(cloneTbody);
  rolador.appendChild(cloneTable);

  linha.style.opacity = "0.15";
  void cloneTable.offsetHeight;

  cloneTable.style.top = `${topFinal}px`;
  rolador.scrollTo({ top: 0, behavior: "smooth" });

  const t = setTimeout(() => {
    tbody.prepend(linha);
    linha.style.opacity = "1";
    tbody.querySelectorAll("tr").forEach((tr) => tr.removeAttribute("data-ativo"));
    linha.setAttribute("data-ativo", "true");
    cloneTable.remove();
    rolador.scrollTo({ top: 0, behavior: "smooth" });
    limparAnimacoesSincronia();
  }, duracaoTotal);
  timeoutsSincronia.push(t);
}

document.addEventListener("click", (evento) => {
  // A. Clique no card do organograma -> Destaca linha na tabela com deslizamento contínuo
  const gatilho = evento.target.closest("#organograma-unidades .card-unidade-gatilho");
  if (gatilho) {
    const no = gatilho.closest(".no-arvore");
    const sigla = no?.dataset?.unidadeSigla || gatilho.querySelector(".card-unidade-sigla")?.textContent?.trim();
    if (sigla) {
      destacarLinhaNaTabela(sigla);
    }
    return;
  }

  // B. Clique na linha da tabela -> Ativa nó no organograma e pina com deslizamento contínuo
  const linha = evento.target.closest("#corpo-unidades tr");
  if (linha) {
    if (evento.target.closest(".link-interno") || evento.target.closest("a") || evento.target.closest("button")) {
      return;
    }
    const sigla = linha.dataset.unidadeSigla;
    if (!sigla) return;

    const organograma = document.getElementById("organograma-unidades");
    if (organograma) {
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

    destacarLinhaNaTabela(sigla);
  }
});

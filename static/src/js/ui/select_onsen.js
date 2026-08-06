// Campo de seleção de vidro (SPEC user_admin/011). Utilitário de UI: constrói a casca em volta do
// <select> que o servidor renderizou, filtra por texto e escreve a escolha no próprio <select> —
// que segue sendo o campo do formulário e a fonte da verdade. Pele, geometria e teclado, nada mais:
// nenhuma regra de negócio, nenhum estado que o servidor não tenha (CLAUDE.md §7.2).

// Filtro só aparece quando a lista é grande o bastante para justificar o campo extra.
const MINIMO_PARA_FILTRO = 6;
// Folga entre gatilho e lista, e altura abaixo da qual vale mais abrir para cima.
const FOLGA_PX = 8;
const ALTURA_CONFORTAVEL_PX = 220;
const PASSO_DA_SETA = { ArrowDown: 1, ArrowUp: -1 };

let sequencia = 0;

function normalizar(texto) {
  return texto.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

function montarCasca(select) {
  const casca = document.createElement("div");
  casca.className = "select-onsen";
  select.parentNode.insertBefore(casca, select);
  casca.appendChild(select);
  // O select some da tela, não do formulário: continua enviando e recebendo change.
  select.hidden = true;
  return casca;
}

function montarTrigger(casca, select) {
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "select select-glass select-onsen-trigger";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  const rotulo = document.createElement("span");
  rotulo.className = "truncate";
  rotulo.textContent = select.options[select.selectedIndex]?.textContent ?? "";
  trigger.appendChild(rotulo);
  casca.appendChild(trigger);
  return { trigger, rotulo };
}

function montarPainel(casca, select, identificador) {
  const painel = document.createElement("div");
  painel.className = "select-onsen-panel";
  painel.id = `${identificador}-painel`;
  // popover=auto: top layer, e Esc e clique fora saem de graça.
  painel.popover = "auto";

  const busca = document.createElement("input");
  busca.type = "search";
  busca.className = "input input-glass select-onsen-busca";
  busca.placeholder = "Filtrar…";
  if (select.options.length >= MINIMO_PARA_FILTRO) painel.appendChild(busca);

  const lista = document.createElement("div");
  lista.className = "select-onsen-list";
  lista.setAttribute("role", "listbox");

  const vazio = document.createElement("p");
  vazio.className = "select-onsen-vazio";
  vazio.textContent = "Nada encontrado.";
  vazio.hidden = true;

  painel.appendChild(lista);
  painel.appendChild(vazio);
  casca.appendChild(painel);
  return { painel, busca, lista, vazio };
}

function montarOpcoes(lista, select, identificador) {
  return Array.from(select.options).map((opcao, indice) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "select-onsen-option";
    item.id = `${identificador}-opcao-${indice}`;
    item.setAttribute("role", "option");
    item.setAttribute("aria-selected", String(indice === select.selectedIndex));
    // O item nunca recebe foco: quem anda é o realce, e o Tab continua saindo do campo.
    item.tabIndex = -1;
    item.dataset.indice = String(indice);
    item.textContent = opcao.textContent;
    lista.appendChild(item);
    return item;
  });
}

function aprimorar(select) {
  const identificador = `select-onsen-${(sequencia += 1)}`;
  const casca = montarCasca(select);
  const { trigger, rotulo } = montarTrigger(casca, select);
  const { painel, busca, lista, vazio } = montarPainel(casca, select, identificador);
  const itens = montarOpcoes(lista, select, identificador);

  let ativo = null;

  // Quem segura o teclado enquanto a lista está aberta — e, portanto, quem aponta para o item
  // realçado.
  function focado() {
    return busca.isConnected ? busca : trigger;
  }

  function visiveis() {
    return itens.filter((item) => !item.hidden);
  }

  // O realce é estado do componente, não foco do navegador: seta e mouse movem o MESMO marcador, e
  // :focus-visible não acende em foco programático depois de clique.
  function realcar(item) {
    ativo?.removeAttribute("data-ativo");
    ativo = item ?? null;
    if (!ativo) {
      focado().removeAttribute("aria-activedescendant");
      return;
    }
    ativo.setAttribute("data-ativo", "true");
    ativo.scrollIntoView({ block: "nearest" });
    focado().setAttribute("aria-activedescendant", ativo.id);
  }

  function andar(passo) {
    const candidatos = visiveis();
    if (candidatos.length === 0) return;
    const atual = candidatos.indexOf(ativo);
    if (atual === -1) {
      realcar(passo > 0 ? candidatos[0] : candidatos[candidatos.length - 1]);
      return;
    }
    realcar(candidatos[(atual + passo + candidatos.length) % candidatos.length]);
  }

  function filtrar(termo) {
    const alvo = normalizar(termo);
    itens.forEach((item) => {
      item.hidden = !normalizar(item.textContent).includes(alvo);
    });
    const candidatos = visiveis();
    vazio.hidden = candidatos.length > 0;
    // Filtrou, o realce vai para o primeiro que sobrou — a menos que o atual tenha sobrado.
    realcar(candidatos.includes(ativo) ? ativo : candidatos[0]);
  }

  // A lista está na top layer, fora do fluxo: quem diz onde ela fica é o gatilho. Abre para cima
  // quando não há altura confortável abaixo.
  function posicionar() {
    const caixa = trigger.getBoundingClientRect();
    const abaixo = window.innerHeight - caixa.bottom - FOLGA_PX;
    const acima = caixa.top - FOLGA_PX;
    const paraCima = abaixo < ALTURA_CONFORTAVEL_PX && acima > abaixo;
    painel.style.left = `${caixa.left}px`;
    painel.style.width = `${caixa.width}px`;
    painel.style.maxHeight = `${paraCima ? acima : abaixo}px`;
    painel.style.top = paraCima ? "" : `${caixa.bottom + FOLGA_PX}px`;
    painel.style.bottom = paraCima ? `${window.innerHeight - caixa.top + FOLGA_PX}px` : "";
  }

  function escolher(item) {
    const indice = Number(item.dataset.indice);
    select.selectedIndex = indice;
    rotulo.textContent = select.options[indice].textContent;
    itens.forEach((candidato, i) => candidato.setAttribute("aria-selected", String(i === indice)));
    // change nativo: é assim que o HTMX (e qualquer outro ouvinte) vê a escolha, sem saber que
    // existe casca.
    select.dispatchEvent(new Event("change", { bubbles: true }));
    painel.hidePopover();
    trigger.focus();
  }

  // popovertarget: o navegador cuida de alternar, do Esc e do clique fora. A gente só posiciona e
  // acompanha a rolagem enquanto está aberto (a top layer não rola com o conteúdo).
  trigger.popoverTargetElement = painel;
  painel.addEventListener("beforetoggle", (evento) => {
    const abrindo = evento.newState === "open";
    trigger.setAttribute("aria-expanded", String(abrindo));
    if (!abrindo) {
      realcar(null);
      window.removeEventListener("scroll", posicionar, true);
      window.removeEventListener("resize", posicionar);
      return;
    }
    busca.value = "";
    filtrar("");
    posicionar();
    window.addEventListener("scroll", posicionar, true);
    window.addEventListener("resize", posicionar);
  });
  // Só depois de aberto: o realce nasce na escolha atual (a seta continua de onde o usuário parou)
  // e rolar até ela exige a lista já visível.
  painel.addEventListener("toggle", (evento) => {
    if (evento.newState !== "open") return;
    realcar(itens[select.selectedIndex] ?? visiveis()[0]);
    if (busca.isConnected) busca.focus();
  });
  busca.addEventListener("input", () => filtrar(busca.value));

  // Um ouvinte só para o teclado: o painel é popover (vive na top layer), mas continua filho da
  // casca no DOM, então o evento sobe até aqui venha ele do gatilho ou do campo de filtro.
  casca.addEventListener("keydown", (evento) => {
    if (!painel.matches(":popover-open")) {
      if (!Object.hasOwn(PASSO_DA_SETA, evento.key)) return;
      evento.preventDefault();
      painel.showPopover();
      return;
    }
    if (Object.hasOwn(PASSO_DA_SETA, evento.key)) {
      evento.preventDefault();
      andar(PASSO_DA_SETA[evento.key]);
      return;
    }
    if (evento.key === "Home" || evento.key === "End") {
      evento.preventDefault();
      const candidatos = visiveis();
      realcar(evento.key === "Home" ? candidatos[0] : candidatos[candidatos.length - 1]);
      return;
    }
    if (evento.key !== "Enter") return;
    // Sem este preventDefault o filtro submeteria o formulário (submissão implícita) e o gatilho
    // reabriria a lista pelo clique sintético que o Enter dispara no invoker.
    evento.preventDefault();
    if (ativo) escolher(ativo);
  });

  // Delegação: hover e clique falam com o mesmo realce, sem um ouvinte por item.
  lista.addEventListener("pointermove", (evento) => {
    const item = evento.target.closest(".select-onsen-option");
    if (item) realcar(item);
  });
  lista.addEventListener("click", (evento) => {
    const item = evento.target.closest(".select-onsen-option");
    if (item) escolher(item);
  });
}

// O [hidden] marca o que já foi aprimorado: swap do HTMX reexecuta isto sem duplicar casca.
export function aprimorarSelects() {
  document.querySelectorAll("select[data-select-onsen]:not([hidden])").forEach(aprimorar);
}

// §11 caso (1): callbacks de evento do HTMX, registrados uma única vez. Os eventos do HTMX sobem
// até o document, então o registro não depende do global `htmx` — é o que deixa o styleguide da
// skill carregar este mesmo módulo sem arrastar o HTMX junto.
document.addEventListener("DOMContentLoaded", aprimorarSelects);
document.addEventListener("htmx:afterSwap", aprimorarSelects);

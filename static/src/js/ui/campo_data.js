// Campo de data de vidro (SPEC design/012). Utilitário de UI: constrói a casca em volta do
// input[type="date"] que o servidor renderizou, escreve a data em dd/mm/aaaa na tela e o valor ISO
// no próprio campo — que segue sendo o campo do formulário e a fonte da verdade. Pele, geometria e
// teclado, nada mais: nenhuma regra de negócio, nenhum estado que o servidor não tenha.

const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];
const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const DIAS_DA_SEMANA = ["D", "S", "T", "Q", "Q", "S", "S"];
// Seis semanas sempre: mês que cabe em cinco encolheria o painel, e a linha de baixo dançaria sob o
// ponteiro a cada troca de mês.
const CELULAS = 42;
const ANOS_NO_BLOCO = 20;
const FOLGA_PX = 8;
const ALTURA_CONFORTAVEL_PX = 340;
const PASSO_POR_FACE = {
  dias: { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 },
  meses: { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -3, ArrowDown: 3 },
  anos: { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -4, ArrowDown: 4 },
};
const GLIFO_CALENDARIO = '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>';

let sequencia = 0;

function isoDe(data) {
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${data.getFullYear()}-${mes}-${dia}`;
}

function deIso(iso) {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return new Date(ano, mes - 1, dia);
}

function paraBr(iso) {
  if (!iso) return "";
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

// Data incompleta ou impossível devolve vazio: 31/02 existe como texto e não como data, e é a volta
// pelo Date que denuncia a diferença.
function paraIso(texto) {
  const digitos = texto.replace(/\D/g, "");
  if (digitos.length !== 8) return "";
  const dia = digitos.slice(0, 2);
  const mes = digitos.slice(2, 4);
  const ano = digitos.slice(4);
  const data = new Date(Number(ano), Number(mes) - 1, Number(dia));
  if (data.getDate() !== Number(dia) || data.getMonth() !== Number(mes) - 1) return "";
  return `${ano}-${mes}-${dia}`;
}

function mascarar(texto) {
  const digitos = texto.replace(/\D/g, "").slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

// Reformatar move o texto sob o cursor; o que o mantém no lugar é a contagem de dígitos à esquerda
// dele, que a máscara não altera.
function posicaoAposDigitos(texto, quantidade) {
  if (quantidade === 0) return 0;
  let vistos = 0;
  for (let i = 0; i < texto.length; i += 1) {
    if (!/\d/.test(texto[i])) continue;
    vistos += 1;
    if (vistos === quantidade) return i + 1;
  }
  return texto.length;
}

function diasDaGrade(ano, mes) {
  const primeiro = new Date(ano, mes, 1);
  // Domingo abre a semana no calendário brasileiro, e getDay() já conta a partir dele.
  const inicio = new Date(ano, mes, 1 - primeiro.getDay());
  return Array.from({ length: CELULAS }, (_, passo) => {
    const dia = new Date(inicio);
    dia.setDate(inicio.getDate() + passo);
    return dia;
  });
}

function celula(rotulo) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "calendario-celula";
  botao.textContent = rotulo;
  return botao;
}

function seta(glifo, rotulo) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "btn btn-ghost btn-sm btn-circle btn-etched-swell";
  botao.setAttribute("aria-label", rotulo);
  const glifoGravado = document.createElement("span");
  glifoGravado.className = "icon-etched";
  glifoGravado.textContent = glifo;
  botao.appendChild(glifoGravado);
  return botao;
}

function botaoGravado(rotulo) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "btn-etched btn-etched-sm btn-etched-swell etched";
  botao.textContent = rotulo;
  return botao;
}

function montarPainel(identificador) {
  const painel = document.createElement("div");
  painel.className = "calendario-onsen";
  painel.id = identificador;
  painel.tabIndex = -1;
  painel.setAttribute("role", "dialog");

  const topo = document.createElement("div");
  topo.className = "calendario-onsen-topo";
  const anterior = seta("‹", "Anterior");
  const titulo = botaoGravado("");
  titulo.classList.add("calendario-onsen-titulo");
  const rotulo = document.createElement("span");
  const caret = document.createElement("span");
  caret.textContent = "⌃";
  caret.setAttribute("aria-hidden", "true");
  titulo.replaceChildren(rotulo, caret);
  const proximo = seta("›", "Próximo");
  topo.append(anterior, titulo, proximo);

  const semana = document.createElement("div");
  semana.className = "calendario-onsen-semana";
  DIAS_DA_SEMANA.forEach((letra) => {
    const marca = document.createElement("span");
    marca.className = "text-overline";
    marca.textContent = letra;
    semana.appendChild(marca);
  });

  const dias = document.createElement("div");
  dias.className = "calendario-onsen-grade";
  dias.setAttribute("role", "grid");

  const meses = document.createElement("div");
  meses.className = "calendario-onsen-meses";

  const anos = document.createElement("div");
  anos.className = "calendario-onsen-anos";

  const corpo = document.createElement("div");
  corpo.className = "calendario-onsen-corpo";
  corpo.dataset.face = "dias";
  corpo.append(semana, dias, meses, anos);

  const rodape = document.createElement("div");
  rodape.className = "calendario-onsen-rodape";
  const hoje = botaoGravado("hoje");
  const limpar = botaoGravado("limpar");
  rodape.append(hoje, limpar);

  painel.append(topo, corpo, rodape);
  return { painel, anterior, titulo, rotulo, caret, proximo, corpo, dias, meses, anos, hoje, limpar };
}

function montarCasca(nativo) {
  const casca = document.createElement("div");
  casca.className = "campo-data";
  nativo.parentNode.insertBefore(casca, nativo);
  casca.appendChild(nativo);
  // O campo some da tela, não do formulário: continua enviando e recebendo change.
  nativo.hidden = true;
  return casca;
}

// A entrada herda as classes que o servidor escreveu no campo nativo — input-sm, w-full e o
// campo-realce-* de uma recusa chegam de graça. Entra ANTES do nativo: é ela que o <label>
// envolvente precisa achar como primeiro controle.
function montarEntrada(casca, nativo) {
  const entrada = document.createElement("input");
  entrada.type = "text";
  entrada.inputMode = "numeric";
  entrada.autocomplete = "off";
  entrada.className = `${nativo.className} campo-data-entrada`;
  entrada.placeholder = "dd/mm/aaaa";
  entrada.value = paraBr(nativo.value);
  entrada.disabled = nativo.disabled;
  casca.prepend(entrada);
  return entrada;
}

function montarGatilho(casca, identificador) {
  const gatilho = document.createElement("button");
  gatilho.type = "button";
  gatilho.className = "campo-data-gatilho";
  gatilho.setAttribute("aria-label", "Abrir calendário");
  gatilho.setAttribute("aria-haspopup", "dialog");
  gatilho.setAttribute("aria-expanded", "false");
  gatilho.setAttribute("aria-controls", identificador);
  gatilho.innerHTML = GLIFO_CALENDARIO;
  casca.appendChild(gatilho);
  return gatilho;
}

function aprimorar(nativo) {
  const identificador = `campo-data-${(sequencia += 1)}`;
  const casca = montarCasca(nativo);
  const entrada = montarEntrada(casca, nativo);
  const gatilho = montarGatilho(casca, identificador);
  const partes = montarPainel(identificador);
  const { painel, anterior, titulo, rotulo, caret, proximo, corpo, dias, meses, anos, hoje, limpar } = partes;
  painel.popover = "auto";
  casca.appendChild(painel);

  const realceDoServidor = entrada.classList.contains("campo-realce-erro");
  let face = "dias";
  let ativo = nativo.value ? deIso(nativo.value) : new Date();
  let visivel = new Date(ativo.getFullYear(), ativo.getMonth(), 1);

  function foraDoAlcance(iso) {
    return (nativo.min && iso < nativo.min) || (nativo.max && iso > nativo.max);
  }

  function inicioDoBloco() {
    return Math.floor(visivel.getFullYear() / ANOS_NO_BLOCO) * ANOS_NO_BLOCO;
  }

  function desenharDias() {
    const escolhido = nativo.value;
    const marcaDeHoje = isoDe(new Date());
    const grade = diasDaGrade(visivel.getFullYear(), visivel.getMonth()).map((data) => {
      const iso = isoDe(data);
      const botao = celula(String(data.getDate()));
      botao.dataset.iso = iso;
      if (data.getMonth() !== visivel.getMonth()) botao.dataset.fora = "true";
      if (iso === marcaDeHoje) botao.dataset.hoje = "true";
      if (iso === escolhido) botao.setAttribute("aria-selected", "true");
      if (iso === isoDe(ativo)) botao.dataset.ativo = "true";
      botao.disabled = foraDoAlcance(iso);
      return botao;
    });
    dias.replaceChildren(...grade);
  }

  function desenharMeses() {
    const escolhido = nativo.value ? deIso(nativo.value) : null;
    const grade = MESES_CURTOS.map((nome, indice) => {
      const botao = celula(nome);
      botao.dataset.mes = String(indice);
      if (indice === visivel.getMonth()) botao.dataset.ativo = "true";
      if (escolhido && escolhido.getFullYear() === visivel.getFullYear() && escolhido.getMonth() === indice) {
        botao.setAttribute("aria-selected", "true");
      }
      return botao;
    });
    meses.replaceChildren(...grade);
  }

  function desenharAnos() {
    const escolhido = nativo.value ? deIso(nativo.value) : null;
    const primeiro = inicioDoBloco();
    const grade = Array.from({ length: ANOS_NO_BLOCO }, (_, passo) => {
      const ano = primeiro + passo;
      const botao = celula(String(ano));
      botao.dataset.ano = String(ano);
      if (ano === visivel.getFullYear()) botao.dataset.ativo = "true";
      if (escolhido && escolhido.getFullYear() === ano) botao.setAttribute("aria-selected", "true");
      return botao;
    });
    anos.replaceChildren(...grade);
  }

  function desenhar() {
    corpo.dataset.face = face;
    titulo.toggleAttribute("data-topo", face === "anos");
    caret.hidden = face === "anos";
    titulo.setAttribute("aria-label", face === "anos" ? "Década em exibição" : "Subir um nível");
    if (face === "dias") {
      rotulo.textContent = `${MESES[visivel.getMonth()]} ${visivel.getFullYear()}`;
      desenharDias();
      return;
    }
    if (face === "meses") {
      rotulo.textContent = String(visivel.getFullYear());
      desenharMeses();
      return;
    }
    const primeiro = inicioDoBloco();
    rotulo.textContent = `${primeiro} – ${primeiro + ANOS_NO_BLOCO - 1}`;
    desenharAnos();
  }

  // change nativo: é assim que o HTMX (e qualquer outro ouvinte) vê a data, sem saber que existe
  // casca. Só quando o valor MUDA: a máscara reescreve o campo a cada tecla, e um formulário com
  // hx-trigger="change" dispararia um request por dígito.
  function escrever(iso) {
    if (nativo.value === iso) return;
    nativo.value = iso;
    nativo.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function escolher(iso) {
    escrever(iso);
    entrada.value = paraBr(iso);
    entrada.classList.toggle("campo-realce-erro", realceDoServidor);
    entrada.setAttribute("aria-invalid", "false");
    ativo = deIso(iso);
    visivel = new Date(ativo.getFullYear(), ativo.getMonth(), 1);
    painel.hidePopover();
    entrada.focus();
  }

  function andar(passo) {
    if (face === "dias") {
      const alvo = new Date(ativo);
      alvo.setDate(alvo.getDate() + passo);
      ativo = alvo;
      visivel = new Date(alvo.getFullYear(), alvo.getMonth(), 1);
    } else if (face === "meses") {
      const alvo = new Date(visivel);
      alvo.setMonth(alvo.getMonth() + passo);
      visivel = alvo;
    } else {
      const alvo = new Date(visivel);
      alvo.setFullYear(alvo.getFullYear() + passo);
      visivel = alvo;
    }
    desenhar();
  }

  function passear(passo) {
    const alvo = new Date(visivel);
    if (face === "dias") alvo.setMonth(alvo.getMonth() + passo);
    if (face === "meses") alvo.setFullYear(alvo.getFullYear() + passo);
    if (face === "anos") alvo.setFullYear(alvo.getFullYear() + passo * ANOS_NO_BLOCO);
    visivel = alvo;
    desenhar();
  }

  function abrir() {
    ativo = nativo.value ? deIso(nativo.value) : new Date();
    visivel = new Date(ativo.getFullYear(), ativo.getMonth(), 1);
    face = "dias";
    desenhar();
    painel.showPopover();
  }

  // O painel está na top layer, fora do fluxo: quem diz onde ele fica é o campo. Abre para cima
  // quando não há altura confortável abaixo.
  function posicionar() {
    const caixa = entrada.getBoundingClientRect();
    const abaixo = window.innerHeight - caixa.bottom - FOLGA_PX;
    const acima = caixa.top - FOLGA_PX;
    const paraCima = abaixo < ALTURA_CONFORTAVEL_PX && acima > abaixo;
    const largura = painel.offsetWidth;
    painel.style.left = `${Math.max(FOLGA_PX, Math.min(caixa.left, window.innerWidth - largura - FOLGA_PX))}px`;
    painel.style.top = paraCima ? "" : `${caixa.bottom + FOLGA_PX}px`;
    painel.style.bottom = paraCima ? `${window.innerHeight - caixa.top + FOLGA_PX}px` : "";
  }

  entrada.addEventListener("input", () => {
    const cursor = entrada.selectionStart ?? entrada.value.length;
    const digitosAEsquerda = entrada.value.slice(0, cursor).replace(/\D/g, "").length;
    entrada.value = mascarar(entrada.value);
    const posicao = posicaoAposDigitos(entrada.value, digitosAEsquerda);
    entrada.setSelectionRange(posicao, posicao);

    const iso = paraIso(entrada.value);
    const completo = entrada.value.replace(/\D/g, "").length === 8;
    escrever(iso);
    // Data impossível acende o campo, mas a recusa que decide continua sendo a do servidor.
    entrada.classList.toggle("campo-realce-erro", realceDoServidor || (completo && !iso));
    entrada.setAttribute("aria-invalid", completo && !iso ? "true" : "false");
  });

  entrada.addEventListener("keydown", (evento) => {
    if (evento.key !== "ArrowDown") return;
    evento.preventDefault();
    abrir();
  });

  // Clique manual, e não popovertarget: o <label> que envolve o campo rouba o foco no default, e
  // sem o preventDefault o painel abriria já perdendo o teclado.
  gatilho.addEventListener("click", (evento) => {
    evento.preventDefault();
    if (painel.matches(":popover-open")) painel.hidePopover();
    else abrir();
  });

  anterior.addEventListener("click", () => passear(-1));
  proximo.addEventListener("click", () => passear(1));
  // Sobe-se pelo título, desce-se escolhendo: clicar num ano devolve os meses, num mês devolve os dias.
  titulo.addEventListener("click", () => {
    if (face === "anos") return;
    face = face === "dias" ? "meses" : "anos";
    desenhar();
  });
  hoje.addEventListener("click", () => escolher(isoDe(new Date())));
  limpar.addEventListener("click", () => {
    escrever("");
    entrada.value = "";
    entrada.classList.toggle("campo-realce-erro", realceDoServidor);
    entrada.setAttribute("aria-invalid", "false");
    painel.hidePopover();
    entrada.focus();
  });

  // Mesmo motivo do gatilho: o painel é descendente do <label> do campo, e sem cancelar o default
  // cada clique dentro dele ativa o rótulo e o foco salta para a entrada.
  painel.addEventListener("click", (evento) => {
    if (evento.target.closest("button")) evento.preventDefault();
  });

  painel.addEventListener("click", (evento) => {
    const alvo = evento.target.closest(".calendario-celula");
    if (!alvo || alvo.disabled) return;
    if (alvo.dataset.iso) {
      escolher(alvo.dataset.iso);
      return;
    }
    if (alvo.dataset.mes) {
      visivel = new Date(visivel.getFullYear(), Number(alvo.dataset.mes), 1);
      face = "dias";
      desenhar();
      return;
    }
    if (alvo.dataset.ano) {
      visivel = new Date(Number(alvo.dataset.ano), visivel.getMonth(), 1);
      face = "meses";
      desenhar();
    }
  });

  painel.addEventListener("keydown", (evento) => {
    const passos = PASSO_POR_FACE[face];
    if (Object.hasOwn(passos, evento.key)) {
      evento.preventDefault();
      andar(passos[evento.key]);
      return;
    }
    if (evento.key === "PageUp" || evento.key === "PageDown") {
      evento.preventDefault();
      passear(evento.key === "PageUp" ? -1 : 1);
      return;
    }
    if (evento.key === "Home" || evento.key === "End") {
      evento.preventDefault();
      const ultimo = new Date(visivel.getFullYear(), visivel.getMonth() + 1, 0).getDate();
      ativo = new Date(visivel.getFullYear(), visivel.getMonth(), evento.key === "Home" ? 1 : ultimo);
      desenhar();
      return;
    }
    if (evento.key !== "Enter" && evento.key !== " ") return;
    evento.preventDefault();
    if (face === "dias") {
      const iso = isoDe(ativo);
      if (!foraDoAlcance(iso)) escolher(iso);
      return;
    }
    face = face === "meses" ? "dias" : "meses";
    desenhar();
  });

  painel.addEventListener("beforetoggle", (evento) => {
    const abrindo = evento.newState === "open";
    gatilho.setAttribute("aria-expanded", String(abrindo));
    if (!abrindo) {
      window.removeEventListener("scroll", posicionar, true);
      window.removeEventListener("resize", posicionar);
      if (painel.contains(document.activeElement)) entrada.focus();
      return;
    }
    posicionar();
    window.addEventListener("scroll", posicionar, true);
    window.addEventListener("resize", posicionar);
  });
  // Só depois de aberto: medir a largura do painel para ele não vazar da janela exige ele visível.
  painel.addEventListener("toggle", (evento) => {
    if (evento.newState !== "open") return;
    posicionar();
    painel.focus();
  });
}

// O [hidden] marca o que já foi aprimorado: swap do HTMX reexecuta isto sem duplicar casca.
export function aprimorarCamposDeData() {
  document.querySelectorAll('input[type="date"][data-campo-data]:not([hidden])').forEach(aprimorar);
}

document.addEventListener("DOMContentLoaded", aprimorarCamposDeData);
document.addEventListener("htmx:afterSwap", aprimorarCamposDeData);

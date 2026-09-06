// Barra de rolagem gravada (SPEC user_admin/013; segundo eixo na SPEC painel/002). Utilitário de UI,
// opt-in por atributo: monta a peça em qualquer poço rolável marcado com [data-scroll-etched]. Faz as
// duas contas que o CSS não alcança — onde a barra começa (a bandeja muda de altura quando a régua de
// filtros abre, e altura de elemento não se lê em CSS) e o tamanho/posição do polegar.
// Rolar continua sendo do navegador: roda, teclado e toque não passam por aqui (CLAUDE.md §7.2).

// Proporcional puro viraria um traço impossível de pegar num conteúdo muito longo.
const TAMANHO_MINIMO_POLEGAR = 28;
// Quanto a água fica no sulco depois do último gesto: curto demais e a barra pisca a cada roda do
// mouse; longo demais e ela deixa de ler como resposta ao gesto.
const REPOUSO_MS = 900;

// O eixo desce como dado: as duas barras fazem a MESMA conta sobre propriedades diferentes, e é isso
// que impede a deitada de nascer como cópia da em pé.
const EIXO_VERTICAL = {
  barra: "[data-barra]",
  polegar: "[data-polegar]",
  trilho: (barra) => barra.clientHeight,
  visivel: (rolador) => rolador.clientHeight,
  total: (rolador) => rolador.scrollHeight,
  posicao: (rolador) => rolador.scrollTop,
  medidaPolegar: (polegar) => polegar.offsetHeight,
  ponteiro: (evento) => evento.clientY,
  rolar: (rolador, valor) => {
    rolador.scrollTop = valor;
  },
  aplicar: (polegar, tamanho, deslocamento) => {
    polegar.style.height = `${tamanho}px`;
    polegar.style.transform = `translateY(${deslocamento}px)`;
  },
};

const EIXO_HORIZONTAL = {
  barra: "[data-barra-h]",
  polegar: "[data-polegar-h]",
  trilho: (barra) => barra.clientWidth,
  visivel: (rolador) => rolador.clientWidth,
  total: (rolador) => rolador.scrollWidth,
  posicao: (rolador) => rolador.scrollLeft,
  medidaPolegar: (polegar) => polegar.offsetWidth,
  ponteiro: (evento) => evento.clientX,
  rolar: (rolador, valor) => {
    rolador.scrollLeft = valor;
  },
  aplicar: (polegar, tamanho, deslocamento) => {
    polegar.style.width = `${tamanho}px`;
    polegar.style.transform = `translateX(${deslocamento}px)`;
  },
};

function montarEixo(poco, rolador, eixo) {
  const barra = poco.querySelector(eixo.barra);
  const polegar = barra && barra.querySelector(eixo.polegar);
  // Tabela de um eixo só não tem a deitada, e o poço segue montando o que tem.
  if (!polegar) return null;

  let ultimaPosicao = eixo.posicao(rolador);

  // "Está rolando" só se sabe pela ausência do próximo evento — daí o relógio. Arrastar o polegar
  // também move a rolagem, então passa por aqui e mantém a água acesa.
  let repouso;
  function acender() {
    barra.classList.add("scroll-etched-ativa");
    clearTimeout(repouso);
    repouso = setTimeout(() => barra.classList.remove("scroll-etched-ativa"), REPOUSO_MS);
  }

  function desenhar() {
    const trilho = eixo.trilho(barra);
    const visivel = eixo.visivel(rolador);
    const total = eixo.total(rolador);
    const rolavel = total - visivel;
    barra.classList.toggle("scroll-etched-ociosa", rolavel <= 0);
    if (rolavel <= 0) return;
    const tamanho = Math.max(trilho * (visivel / total), TAMANHO_MINIMO_POLEGAR);
    eixo.aplicar(polegar, tamanho, (eixo.posicao(rolador) / rolavel) * (trilho - tamanho));
  }

  function aoRolar() {
    // Só acende a barra do eixo que se moveu: rolar na vertical não pode piscar a deitada.
    const posicao = eixo.posicao(rolador);
    if (posicao !== ultimaPosicao) acender();
    ultimaPosicao = posicao;
    desenhar();
  }

  polegar.addEventListener("pointerdown", (evento) => {
    evento.preventDefault();
    const partidaPonteiro = eixo.ponteiro(evento);
    const partidaRolagem = eixo.posicao(rolador);
    // Converte pixel de trilho em pixel de conteúdo: o polegar percorre o vão, não o trilho todo.
    const razao =
      (eixo.total(rolador) - eixo.visivel(rolador)) /
      (eixo.trilho(barra) - eixo.medidaPolegar(polegar));
    const arrastar = (movimento) => {
      eixo.rolar(rolador, partidaRolagem + (eixo.ponteiro(movimento) - partidaPonteiro) * razao);
    };
    polegar.setPointerCapture(evento.pointerId);
    polegar.addEventListener("pointermove", arrastar);
    polegar.addEventListener(
      "pointerup",
      () => polegar.removeEventListener("pointermove", arrastar),
      { once: true });
  });

  return { desenhar, aoRolar };
}

function montar(poco) {
  const rolador = poco.querySelector("[data-rolador]");
  const cabecalho = poco.querySelector("[data-cabecalho]");
  const conteudo = rolador.firstElementChild;
  const eixos = [EIXO_VERTICAL, EIXO_HORIZONTAL]
    .map((eixo) => montarEixo(poco, rolador, eixo))
    .filter(Boolean);

  function desenhar() {
    eixos.forEach((eixo) => eixo.desenhar());
  }

  function medirCabecalho() {
    poco.style.setProperty("--altura-cabecalho", `${cabecalho ? cabecalho.offsetHeight : 0}px`);
    desenhar();
  }

  rolador.addEventListener("scroll", () => eixos.forEach((eixo) => eixo.aoRolar()));

  // O conteúdo muda de tamanho sozinho (swap do HTMX): observar a caixa evita acoplar a barra a
  // quem troca as linhas.
  const observador = new ResizeObserver(desenhar);
  observador.observe(rolador);
  observador.observe(conteudo);
  if (cabecalho) new ResizeObserver(medirCabecalho).observe(cabecalho);
  medirCabecalho();
}

// O atributo de montagem marca o que já foi feito: swap do HTMX reexecuta isto sem duplicar peça.
export function montarBarrasGravadas() {
  document
    .querySelectorAll("[data-scroll-etched]:not([data-scroll-etched-montado])")
    .forEach((poco) => {
      poco.dataset.scrollEtchedMontado = "true";
      montar(poco);
    });
}

document.addEventListener("DOMContentLoaded", montarBarrasGravadas);
document.addEventListener("htmx:afterSwap", montarBarrasGravadas);

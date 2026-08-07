// Barra de rolagem gravada (SPEC user_admin/013). Utilitário de UI, opt-in por atributo: monta a
// peça em qualquer poço rolável marcado com [data-scroll-etched]. Faz as duas contas que o CSS não
// alcança — onde a barra começa (a bandeja muda de altura quando a régua de filtros abre, e altura
// de elemento não se lê em CSS) e o tamanho/posição do polegar (scrollTop/scrollHeight).
// Rolar continua sendo do navegador: roda, teclado e toque não passam por aqui (CLAUDE.md §7.2).

// Proporcional puro viraria um traço impossível de pegar num conteúdo muito longo.
const ALTURA_MINIMA_POLEGAR = 28;
// Quanto a água fica no sulco depois do último gesto: curto demais e a barra pisca a cada roda do
// mouse; longo demais e ela deixa de ler como resposta ao gesto.
const REPOUSO_MS = 900;

function montar(poco) {
  const rolador = poco.querySelector("[data-rolador]");
  const barra = poco.querySelector("[data-barra]");
  const polegar = poco.querySelector("[data-polegar]");
  const cabecalho = poco.querySelector("[data-cabecalho]");
  const conteudo = rolador.firstElementChild;

  function desenhar() {
    const trilho = barra.clientHeight;
    const rolavel = rolador.scrollHeight - rolador.clientHeight;
    barra.classList.toggle("scroll-etched-ociosa", rolavel <= 0);
    if (rolavel <= 0) return;
    const altura = Math.max(
      trilho * (rolador.clientHeight / rolador.scrollHeight),
      ALTURA_MINIMA_POLEGAR);
    polegar.style.height = `${altura}px`;
    polegar.style.transform = `translateY(${(rolador.scrollTop / rolavel) * (trilho - altura)}px)`;
  }

  function medirCabecalho() {
    poco.style.setProperty("--altura-cabecalho", `${cabecalho ? cabecalho.offsetHeight : 0}px`);
    desenhar();
  }

  // "Está rolando" só se sabe pela ausência do próximo evento — daí o relógio. Arrastar o polegar
  // também move o scrollTop, então passa por aqui e mantém a água acesa.
  let repouso;
  function acender() {
    barra.classList.add("scroll-etched-ativa");
    clearTimeout(repouso);
    repouso = setTimeout(() => barra.classList.remove("scroll-etched-ativa"), REPOUSO_MS);
  }

  rolador.addEventListener("scroll", () => {
    acender();
    desenhar();
  });

  // O conteúdo muda de altura sozinho (swap do HTMX): observar a caixa evita acoplar a barra a
  // quem troca as linhas.
  const observador = new ResizeObserver(desenhar);
  observador.observe(rolador);
  observador.observe(conteudo);
  if (cabecalho) new ResizeObserver(medirCabecalho).observe(cabecalho);
  medirCabecalho();

  polegar.addEventListener("pointerdown", (evento) => {
    evento.preventDefault();
    const partidaY = evento.clientY;
    const partidaScroll = rolador.scrollTop;
    // Converte pixel de trilho em pixel de conteúdo: o polegar percorre o vão, não a altura toda.
    const razao =
      (rolador.scrollHeight - rolador.clientHeight) /
      (barra.clientHeight - polegar.offsetHeight);
    const arrastar = (movimento) => {
      rolador.scrollTop = partidaScroll + (movimento.clientY - partidaY) * razao;
    };
    polegar.setPointerCapture(evento.pointerId);
    polegar.addEventListener("pointermove", arrastar);
    polegar.addEventListener(
      "pointerup",
      () => polegar.removeEventListener("pointermove", arrastar),
      { once: true });
  });
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

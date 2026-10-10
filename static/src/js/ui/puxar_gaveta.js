const ALCA = ".tela-home .gaveta-inferior-puxavel > .gaveta-alca";
const LIMIAR_ARRASTO_PX = 6;

// `puxou` sobrevive ao pointerup: é o click que o navegador dispara em seguida que o lê.
const GESTO = { alca: null, origem: 0, folga: 0, puxou: false };

function apertar(evento) {
  GESTO.puxou = false;
  GESTO.alca = evento.target.closest?.(ALCA) ?? null;
  if (GESTO.alca === null) return;
  GESTO.origem = evento.clientY;
  // A folga se mantém durante o arrasto: sem ela a gaveta salta no primeiro movimento.
  GESTO.folga = evento.clientY - GESTO.alca.parentElement.getBoundingClientRect().top;
  // Sem a captura, o mapa e o panorama tomam o ponteiro assim que ele sai da alça.
  GESTO.alca.setPointerCapture(evento.pointerId);
}

function mover(evento) {
  if (GESTO.alca === null) return;
  if (!GESTO.puxou && Math.abs(evento.clientY - GESTO.origem) < LIMIAR_ARRASTO_PX) return;
  GESTO.puxou = true;
  const casca = GESTO.alca.closest(".tela-home");
  casca.dataset.puxando = "";
  // Altura absoluta, medida do rodapé da casca: nada se acumula entre um arrasto e outro.
  const altura = casca.getBoundingClientRect().bottom - evento.clientY + GESTO.folga;
  casca.style.setProperty("--gaveta-puxada-altura", altura + "px");
}

function soltar() {
  const alca = GESTO.alca;
  GESTO.alca = null;
  if (alca === null || !GESTO.puxou) return;
  delete alca.closest(".tela-home").dataset.puxando;
  alca.dispatchEvent(new CustomEvent("gaveta-inferior:puxada", { bubbles: true }));
}

// A alça é o <label> do recolher: sem isto, o click que fecha o arrasto recolheria a gaveta.
function pouparRecolher(evento) {
  if (!GESTO.puxou) return;
  GESTO.puxou = false;
  if (evento.target.closest?.(ALCA)) evento.preventDefault();
}

document.addEventListener("pointerdown", apertar);
document.addEventListener("pointermove", mover);
document.addEventListener("pointerup", soltar);
document.addEventListener("pointercancel", soltar);
document.addEventListener("click", pouparRecolher, { capture: true });

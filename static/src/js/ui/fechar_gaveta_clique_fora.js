const LIMIAR_ARRASTO_PX = 6;

function gavetasAbertas() {
  return document.querySelectorAll(".gaveta-lateral > .gaveta-lateral-toggle:checked");
}

function haFerramentaAtiva() {
  return Boolean(document.getElementById("bancada-conjunto")?.dataset.ferramentaAtiva);
}

function naBancada(alvo) {
  return Boolean(document.getElementById("bancada-conjunto")?.contains(alvo));
}

let origemClique = null;

// Captura: o clique que conclui o traço desliga a ferramenta, e o do submenu recria o próprio botão,
// ambos antes do "click" — lidos ali, já não diriam que o gesto era da bancada.
document.addEventListener(
  "pointerdown",
  (evento) => {
    origemClique = {
      x: evento.clientX,
      y: evento.clientY,
      poupaGaveta: haFerramentaAtiva() || naBancada(evento.target),
    };
  },
  { capture: true },
);

document.addEventListener("click", (evento) => {
  if (origemClique?.poupaGaveta) return;
  const arrastou =
    origemClique &&
    Math.hypot(evento.clientX - origemClique.x, evento.clientY - origemClique.y) > LIMIAR_ARRASTO_PX;
  if (arrastou) return;

  gavetasAbertas().forEach((toggle) => {
    if (toggle.parentElement.contains(evento.target)) return;
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change", { bubbles: true }));
  });
});

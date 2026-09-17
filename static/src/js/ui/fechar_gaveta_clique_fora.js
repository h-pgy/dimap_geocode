const LIMIAR_ARRASTO_PX = 6;

function gavetasAbertas() {
  return document.querySelectorAll(".gaveta-lateral > .gaveta-lateral-toggle:checked");
}

let origemClique = null;

document.addEventListener("pointerdown", (evento) => {
  origemClique = { x: evento.clientX, y: evento.clientY };
});

document.addEventListener("click", (evento) => {
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

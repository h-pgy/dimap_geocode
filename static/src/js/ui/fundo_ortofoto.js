const ID_CASCA = "fundo-ortofoto";
const SELETOR_CAMADA = ".fundo-ortofoto__camada";
const CLASSE_VISIVEL = "fundo-ortofoto__camada--visivel";

// A casca não é reescrita no swap: `atual` fixado na URL congelaria na primeira ortofoto e o
// sorteio voltaria a repetir a que está na tela. Quem sabe qual está em cima é a última camada.
document.body.addEventListener("htmx:configRequest", (evento) => {
  const casca = evento.detail.elt;
  if (casca.id !== ID_CASCA) return;
  evento.detail.parameters.atual = casca.lastElementChild?.dataset.ortofoto ?? "";
});

document.body.addEventListener("htmx:afterSwap", (evento) => {
  if (evento.target.id !== ID_CASCA) return;
  aparar(evento.target);
  revelar(evento.target.lastElementChild);
});

// Invariante: no máximo duas camadas. Com o fundo desligado o elemento é `display: none`, nenhuma
// transição roda e o descarte nunca dispara — sem esta poda o rodízio empilharia para sempre.
function aparar(casca) {
  const camadas = [...casca.querySelectorAll(SELETOR_CAMADA)];
  for (const camada of camadas.slice(0, -2)) camada.remove();
}

// O gate. `decode()` resolve quando o pixel existe, não quando o byte chega — é o que impede a
// camada nova de subir sobre nada.
async function revelar(camada) {
  const imagem = camada?.querySelector("img");
  if (imagem) {
    try {
      await imagem.decode();
    } catch {
      /* PNG ausente ou corrompido: revela assim mesmo, e a lente sozinha vira o piso visual */
    }
  }
  camada.addEventListener("transitionend", () => descartarAnteriores(camada), { once: true });
  camada.classList.add(CLASSE_VISIVEL);
}

// A anterior só sai depois que a nova chegou a opacity 1: em nenhum quadro as duas somam menos que
// uma imagem opaca.
function descartarAnteriores(camada) {
  for (const anterior of camada.parentElement.querySelectorAll(SELETOR_CAMADA)) {
    if (anterior !== camada) anterior.remove();
  }
}

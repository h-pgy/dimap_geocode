// Feedback visual do Enter na barra de busca (SPEC design/002): ao comitar, a lista de
// sugestões aparece/permanece por um instante com o 1º item da 1ª seção aceso como
// "selecionado" (classe .pos-commit no painel) e então se dispensa sozinha (.dismissing +
// limpeza do contêiner). Cobre o Enter rápido: se a lista ainda não chegou, o htmx:afterSwap
// das sugestões aplica o mesmo tratamento quando ela renderizar. Digitar de novo cancela tudo.
// §11 caso (1): callbacks de eventos HTMX + classes CSS — nenhuma regra de negócio.

const DURACAO_LISTA_POS_COMMIT_MS = 1500;
const DURACAO_FADE_MS = 500;

const inputBusca = document.getElementById("input_search");
const alvoSugestoes = document.getElementById("sugestoes-busca");

let posCommit = false;
let timers = [];

function painelSugestoes() {
  return alvoSugestoes.querySelector(".suggestion-panel");
}

function limparTimers() {
  timers.forEach(clearTimeout);
  timers = [];
}

function sairPosCommit() {
  posCommit = false;
  limparTimers();
  const painel = painelSugestoes();
  if (painel) painel.classList.remove("pos-commit", "dismissing");
}

function animarSelecaoEDispensar() {
  const painel = painelSugestoes();
  if (!painel) return; // Enter antes de a lista chegar: o afterSwap reaplica quando ela renderizar
  painel.classList.add("pos-commit");
  timers.push(setTimeout(() => {
    painel.classList.add("dismissing");
    timers.push(setTimeout(() => {
      if (alvoSugestoes.contains(painel)) alvoSugestoes.innerHTML = "";
      posCommit = false;
    }, DURACAO_FADE_MS));
  }, DURACAO_LISTA_POS_COMMIT_MS));
}

function aoTeclar(evt) {
  if (evt.key === "Enter") {
    posCommit = true;
    limparTimers();
    animarSelecaoEDispensar();
  } else if (posCommit) {
    sairPosCommit(); // voltou a digitar: a lista retoma o comportamento normal de sugestões
  }
}

function aoRenderizarSugestoes() {
  if (!posCommit) return;
  limparTimers(); // lista (re)chegou após o Enter: reinicia a coreografia sobre o painel novo
  animarSelecaoEDispensar();
}

if (inputBusca && alvoSugestoes) {
  htmx.on(inputBusca, "keyup", aoTeclar);
  htmx.on(alvoSugestoes, "htmx:afterSwap", aoRenderizarSugestoes);
}

// A torre de Ajustes da Animação (SPEC design/017). Ela não sabe simular nada: escreve em
// PARAMETROS, que o shader lê no quadro seguinte. Calibragem é preferência de quem olha, no mesmo
// regime do liga/desliga do fundo — localStorage, nunca o servidor (Caveats).
import { PADRAO, PARAMETROS, existe, ligar, desligar } from "./fundo_agua.js";
import { pintarTrilho } from "./trilho_onsen.js";

const CHAVE_LIGADA = "fundo-agua-ligada";
const CHAVE_AJUSTES = "fundo-agua-ajustes";

// A tabela é o ÚNICO lugar em que os ajustáveis são enumerados: a torre é montada dela, e
// parâmetro que não está aqui não se oferece a quem olha.
const AJUSTAVEIS = [
  { k: "ganho", rotulo: "Intensidade", min: 0, max: 0.6, passo: 0.005 },
  { k: "caustica", rotulo: "Cáustica", min: 0, max: 14, passo: 0.1 },
  { k: "piso", rotulo: "Achatamento do pico", min: 0.05, max: 0.8, passo: 0.005 },
  { k: "contraste", rotulo: "Contraste", min: 0.5, max: 2, passo: 0.01 },
  { k: "brilho", rotulo: "Glint", min: 0, max: 0.4, passo: 0.005 },
  { k: "escalaNormal", rotulo: "Relevo", min: 0, max: 14, passo: 0.1 },
  { k: "velocidadeDeriva", rotulo: "Velocidade da deriva", min: 0.15, max: 3, passo: 0.05 },
  { k: "forcaGota", rotulo: "Gotas ambientes", min: 0, max: 0.045, passo: 0.001 },
  { k: "amortecimento", rotulo: "Amortecimento", min: 0.985, max: 1, passo: 0.0005 },
  { k: "grao", rotulo: "Grão da água", min: 0, max: 0.06, passo: 0.002 },
];

function lembrar(chave, valor) {
  try {
    localStorage.setItem(chave, valor);
  } catch {
    /* modo privativo: a preferência não persiste, e a água segue no padrão */
  }
}

function lerAjustes() {
  try {
    return { ...PADRAO, ...JSON.parse(localStorage.getItem(CHAVE_AJUSTES) ?? "{}") };
  } catch {
    return { ...PADRAO };
  }
}

function lerLigada() {
  try {
    return localStorage.getItem(CHAVE_LIGADA) !== "0";
  } catch {
    return true;
  }
}

function ecoar(barra) {
  barra.closest(".torre-ajustes__linha").querySelector("[data-eco]").textContent = barra.value;
}

// Valor mudado por código não dispara `input`: o eco e o fio entintado do trilho são chamados aqui.
function refletir(barra) {
  barra.value = String(PARAMETROS[barra.dataset.ajuste]);
  ecoar(barra);
  pintarTrilho(barra);
}

function montarBarras() {
  const caixa = document.querySelector("[data-barras]");
  for (const ajuste of AJUSTAVEIS) {
    const linha = document.createElement("div");
    linha.className = "torre-ajustes__linha";
    linha.innerHTML = `
      <div class="torre-ajustes__linha-topo">
        <span class="text-overline">${ajuste.rotulo}</span>
        <span class="text-code text-[12px]" data-eco></span>
      </div>
      <input type="range" class="range-onsen" min="${ajuste.min}" max="${ajuste.max}"
             step="${ajuste.passo}" data-ajuste="${ajuste.k}" aria-label="${ajuste.rotulo}">`;
    caixa.appendChild(linha);
  }
  document.querySelectorAll("[data-ajuste]").forEach(refletir);
}

function aplicarLigada(valor) {
  document.querySelectorAll("[data-agua-ligada]").forEach((chave) => (chave.checked = valor));
  lembrar(CHAVE_LIGADA, valor ? "1" : "0");
  if (valor) ligar();
  else desligar();
}

function aplicarTorre(aberta) {
  const torre = document.querySelector(".torre-ajustes");
  const gatilho = document.querySelector("[data-ajustes]");
  if (!torre || !gatilho) return;
  torre.classList.toggle("torre-ajustes--fechada", !aberta);
  torre.classList.toggle("torre-ajustes--aberta", aberta);
  gatilho.classList.toggle("etched-inked", aberta);
  gatilho.setAttribute("aria-expanded", String(aberta));
}

const torreAberta = () =>
  document.querySelector(".torre-ajustes")?.classList.contains("torre-ajustes--aberta") ?? false;

// Sem água não há o que ajustar: a torre e a engrenagem saem do documento em vez de abrir vazias.
if (!existe()) {
  document.querySelector(".torre-ajustes")?.remove();
  document.querySelector("[data-ajustes]")?.remove();
} else {
  Object.assign(PARAMETROS, lerAjustes());
  montarBarras();
  aplicarLigada(lerLigada());

  document.addEventListener("input", (evento) => {
    const barra = evento.target.closest("[data-ajuste]");
    if (!barra) return;
    PARAMETROS[barra.dataset.ajuste] = Number(barra.value);
    ecoar(barra);
    lembrar(CHAVE_AJUSTES, JSON.stringify(PARAMETROS));
  });

  document.addEventListener("change", (evento) => {
    const chave = evento.target.closest("[data-agua-ligada]");
    if (chave) aplicarLigada(chave.checked);
  });

  document.addEventListener("click", (evento) => {
    if (evento.target.closest("[data-ajustes]")) {
      aplicarTorre(!torreAberta());
      return;
    }
    if (evento.target.closest("[data-padrao]")) {
      Object.assign(PARAMETROS, PADRAO);
      document.querySelectorAll("[data-ajuste]").forEach(refletir);
      return;
    }
    // A torre é um popover: sair dela é o gesto de fechá-la.
    if (!evento.target.closest(".torre-ajustes")) aplicarTorre(false);
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") aplicarTorre(false);
  });
}

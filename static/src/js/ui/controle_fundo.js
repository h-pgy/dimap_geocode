// Estado visual do controle de fundo (SPEC design/010, aprovado no mock — CLAUDE.md §7.2):
// liga/desliga e velocidade da deriva são preferência de quem olha, nunca do servidor (Caveats).
// Script clássico, não module, e incluído logo após o canvas: roda em ordem de parsing, antes do
// 1º quadro, para a preferência guardada não piscar errada.
const PERIODOS = ["300s", "220s", "150s", "90s", "50s"]; // o centro é o padrão
const NIVEL_PADRAO = 2;
const CHAVE_NIVEL = "fundo-admin-velocidade";
const CHAVE_LIGADO = "fundo-admin-ligado";

function lembrar(chave, valor) {
  try {
    localStorage.setItem(chave, valor);
  } catch {
    /* modo privativo: a preferência não persiste, e o fundo segue ligado no nível padrão */
  }
}

function lerNivel() {
  try {
    return Math.min(4, Math.max(0, Number(localStorage.getItem(CHAVE_NIVEL) ?? NIVEL_PADRAO)));
  } catch {
    return NIVEL_PADRAO;
  }
}

function lerLigado() {
  try {
    return localStorage.getItem(CHAVE_LIGADO) !== "0";
  } catch {
    return true;
  }
}

// O fio entintado do trilho é do trilho_onsen.js: aqui só o valor muda, e a varredura de boot
// daquele módulo pinta a barra logo em seguida.
function aplicarNivel(nivel) {
  document.documentElement.style.setProperty("--deriva-periodo", PERIODOS[nivel]);
  document.querySelectorAll("[data-nivel]").forEach((barra) => (barra.value = String(nivel)));
  lembrar(CHAVE_NIVEL, nivel);
}

// A classe fica no <html>, nunca no #fundo-ortofoto: o HTMX substitui esse elemento inteiro a
// cada rodízio, e uma classe presa nele se perderia no próximo swap.
function aplicarLigado(ligado) {
  document.documentElement.classList.toggle("fundo-desligado", !ligado);
  document.querySelectorAll("[data-fundo-ligado]").forEach((chave) => (chave.checked = ligado));
  // Recolhido não é o mesmo que ausente: `overflow: hidden` não tira do Tab (SPEC design/017).
  document.querySelectorAll("[data-trocar], [data-nivel]").forEach((alvo) => (alvo.disabled = !ligado));
  lembrar(CHAVE_LIGADO, ligado ? "1" : "0");
}

aplicarNivel(lerNivel());
aplicarLigado(lerLigado());

document.addEventListener("input", (evento) => {
  const barra = evento.target.closest("[data-nivel]");
  if (barra) aplicarNivel(Number(barra.value));
});

document.addEventListener("change", (evento) => {
  const chave = evento.target.closest("[data-fundo-ligado]");
  if (chave) aplicarLigado(chave.checked);
});

// Em telas estreitas (< xl), o .fundo-controle entra no fluxo como última linha. Para não ficar
// preso atrás da .admin-shell (z-10) nem sob as lentes (z-1), anexa-se ao final do container
// rolável da shell quando ela existir. Em xl: o CSS (xl:fixed) o projeta para o canto da viewport.
function ancorarNaShell() {
  const container = document.querySelector(".admin-shell > div");
  const controle = document.querySelector(".fundo-controle");
  if (container && controle && controle.parentElement !== container) {
    container.appendChild(controle);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", ancorarNaShell);
} else {
  ancorarNaShell();
}


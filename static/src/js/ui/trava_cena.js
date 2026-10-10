// Estado visual de um controle (SPEC design/021): enquanto há gaveta inferior, o que troca a cena
// não responde. A gaveta que está na tela quando a inferior abre foi renderizada antes dela — quem
// a trava é o navegador, lendo a marca que o servidor mandou.
const MARCA = "#contexto-acao[data-contexto-acao]";

function travar() {
  const travado = document.querySelector(MARCA) !== null;
  // `inert` tira o controle do ponteiro, do teclado e do leitor de tela de uma vez.
  document.querySelectorAll("[data-troca-cena]").forEach((peca) => { peca.inert = travado; });
}

// A cada resposta assentada: cobre a marca que chega, a que sai e o voltar que carrega depois.
export function inicializarTravaCena() {
  htmx.on("htmx:afterSettle", travar);
}

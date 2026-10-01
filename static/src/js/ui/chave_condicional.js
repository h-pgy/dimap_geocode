// Campos condicionais pela chave de duas posições (SPEC autorizacao/008): estado visual de um
// controle, autorizado pelo usuário — a alternativa em CSS puro (`.chave-onsen` + `has()` sobre
// seletor de atributo aninhado) esbarrou em limite do @tailwindcss/browser (CDN de dev), que
// truncava a variante e deixava os dois campos sempre visíveis. Nenhuma regra de negócio aqui: o
// valor concedido segue vindo só do <select> que fica visível, e é ele quem o formulário envia.

function aplicar(escopo) {
  const selecionado = escopo.querySelector('input[type="radio"]:checked');
  if (!selecionado) return;
  escopo.querySelectorAll("[data-mostra-se]").forEach((campo) => {
    campo.hidden = campo.dataset.mostraSe !== selecionado.value;
  });
}

export function aplicarChavesCondicionais() {
  document.querySelectorAll("[data-chave-condicional]").forEach(aplicar);
}

// DOMContentLoaded para a carga inicial, htmx:afterSwap para o modal reaberto por hx-get — o
// mesmo par de gatilhos de select_onsen.js.
document.addEventListener("DOMContentLoaded", aplicarChavesCondicionais);
document.addEventListener("htmx:afterSwap", aplicarChavesCondicionais);

// A chave é o primeiro grupo de rádios do escopo — o mesmo que aplicar() lê.
function ehDaChave(escopo, radio) {
  return escopo.querySelector('input[type="radio"]').name === radio.name;
}

// Controle com [data-padrao-se] volta ao padrão do lado escolhido a cada troca da chave; nada muda
// na carga, para a recusa 422 devolver o que a pessoa marcou.
function reporPadroes(escopo, valor) {
  escopo.querySelectorAll('input[type="checkbox"][data-padrao-se]').forEach((campo) => {
    campo.checked = campo.dataset.padraoSe === valor;
  });
}

// Delegação: um ouvinte só cobre qualquer chave condicional presente na página.
document.addEventListener("change", (evento) => {
  if (!(evento.target instanceof HTMLInputElement) || evento.target.type !== "radio") return;
  const escopo = evento.target.closest("[data-chave-condicional]");
  if (!escopo) return;
  aplicar(escopo);
  // Só a troca da chave repõe o padrão: escolher um texto não mexe no mapa.
  if (ehDaChave(escopo, evento.target)) reporPadroes(escopo, evento.target.value);
});

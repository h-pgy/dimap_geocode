// Sincroniza a chave-onsen-tripla de natureza do cargo em comissão (SPEC user_admin/029) com os
// dois campos reais que o servidor lê: o rótulo visível é ternário (assessoramento/chefia/alta
// administração), o model é dois booleanos (e_chefia, alta_administracao). Estado visual de um
// controle (CLAUDE.md §7.2), aprovado para este caso: a tripla é decorativa, os hidden é que valem.

function aplicar(escopo) {
  const selecionado = escopo.querySelector('input[type="radio"]:checked');
  if (!selecionado) return;
  const eChefia = escopo.querySelector("[data-campo-e-chefia]");
  const altaAdministracao = escopo.querySelector("[data-campo-alta-administracao]");
  if (eChefia) eChefia.value = selecionado.value === "assessoramento" ? "" : "on";
  if (altaAdministracao) {
    altaAdministracao.value = selecionado.value === "alta_administracao" ? "on" : "";
  }
}

export function aplicarNaturezaDoCargo() {
  document.querySelectorAll("[data-natureza-cargo]").forEach(aplicar);
}

// DOMContentLoaded para a carga inicial, htmx:afterSwap para o modal reaberto por hx-get — o mesmo
// par de gatilhos de chave_condicional.js.
document.addEventListener("DOMContentLoaded", aplicarNaturezaDoCargo);
document.addEventListener("htmx:afterSwap", aplicarNaturezaDoCargo);

// Delegação: um ouvinte só cobre qualquer chave de natureza presente na página.
document.addEventListener("change", (evento) => {
  if (!(evento.target instanceof HTMLInputElement) || evento.target.type !== "radio") return;
  const escopo = evento.target.closest("[data-natureza-cargo]");
  if (escopo) aplicar(escopo);
});

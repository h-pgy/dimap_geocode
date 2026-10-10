// Controle de exibição do botão de upload de documento (SPEC documentos_oficiais/010):
// o botão "Conferir documento" não aparece antes de um arquivo ser escolhido;
// aparece logo após a escolha de um arquivo.

function atualizarBotaoConferir(input) {
  const form = input.closest("form");
  if (!form) return;
  const botao = form.querySelector("[data-btn-conferir]");
  if (!botao) return;

  const temArquivo = Boolean(input.files && input.files.length > 0);
  botao.classList.toggle("hidden", !temArquivo);
}

// Delegação de evento: funciona na carga inicial e após qualquer swap HTMX sem re-bind
document.addEventListener("change", (evento) => {
  const target = evento.target;
  if (!(target instanceof HTMLInputElement) || target.type !== "file") return;
  if (target.matches("[data-arquivo-input]")) {
    atualizarBotaoConferir(target);
  }
});

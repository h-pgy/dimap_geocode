// Atalho Ctrl+K anunciado pela "dica" da barra de busca (core/home.html): foca o input de
// pesquisa sem precisar clicar nele, selecionando o texto já digitado para que a próxima
// digitação o substitua. preventDefault barra o atalho nativo do navegador (Ctrl+K abre a
// busca da barra de endereços). Aceita também Cmd+K (macOS), o equivalente usual do atalho.
// §11 caso (1): callback de evento via htmx.on — nenhuma regra de negócio.

const inputBusca = document.getElementById("input_search");

function aoAtalhoDeBusca(evt) {
  if (evt.key.toLowerCase() !== "k" || !(evt.ctrlKey || evt.metaKey)) return;
  evt.preventDefault();
  inputBusca.focus();
  inputBusca.select();
}

if (inputBusca) {
  htmx.on(document, "keydown", aoAtalhoDeBusca);
}

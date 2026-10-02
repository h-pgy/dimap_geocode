// Abre o link marcado com [data-janela-popup] numa janela à parte (SPEC street_view/001); bloqueada
// pelo navegador, pede ao servidor o aviso de [data-aviso-bloqueio].

const FEICOES = "popup,width=1100,height=720";
const ALVO_AVISO = "#resultado-busca";

function abrirJanela(link) {
  // Sem `noopener` nas feições: com ele o window.open devolve sempre null, e o bloqueio ficaria
  // indistinguível de uma janela aberta.
  const janela = window.open(link.href, "_blank", FEICOES);
  if (janela === null) {
    htmx.ajax("GET", link.dataset.avisoBloqueio, { target: ALVO_AVISO, swap: "innerHTML" });
    return;
  }
  // A página de destino não precisa alcançar a janela da plataforma.
  janela.opener = null;
}

// Delegado no body: a gaveta chega por swap do HTMX, depois da carga da página.
document.body.addEventListener("click", (evento) => {
  const link = evento.target.closest("a[data-janela-popup]");
  if (link === null) return;
  evento.preventDefault();
  abrirJanela(link);
});

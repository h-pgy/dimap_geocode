// Contexto de ação (SPEC localizacao_lote/003): a marca chega pelo OOB da resposta da ação, o CSS a
// lê para recolher a busca, e aqui ela só é apagada — quando o controle que ela aponta é desmarcado.
export function inicializarContextoAcao() {
  document.addEventListener("change", (evento) => {
    const slot = document.getElementById("contexto-acao");
    const encerraCom = slot?.dataset.encerraCom;
    if (!encerraCom || evento.target.checked || !evento.target.matches(encerraCom)) return;
    slot.removeAttribute("data-contexto-acao");
    slot.removeAttribute("data-desenho");
    slot.removeAttribute("data-encerra-com");
  });
}

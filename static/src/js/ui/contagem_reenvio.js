// Contagem regressiva do reenvio (SPEC autenticacao/003): estado visual de um controle, aprovado
// pelo usuário. Nenhum estado de domínio mora aqui — a espera chega pronta do servidor, e é a rota
// que recusa o envio dentro da janela; o botão indisponível só evita o clique que já seria negado.
function correr(painel) {
  const acionador = document.querySelector("[data-reenvio-acionador]");
  const relogio = painel.querySelector("[data-reenvio-relogio]");
  let restante = Number(painel.dataset.contagemReenvio);
  acionador.disabled = true;
  const passo = setInterval(() => {
    // O painel é trocado por HTMX a cada pedido: sem esta guarda o relógio antigo segue correndo
    // contra um nó solto e reabilita um botão que o painel novo já governava.
    if (!painel.isConnected) return clearInterval(passo);
    restante -= 1;
    relogio.textContent = `${restante} s`;
    if (restante > 0) return;
    clearInterval(passo);
    acionador.disabled = false;
  }, 1000);
}

// A marca de montagem é a mesma do olhinho: `htmx:afterSwap` também alcança painel já montado.
function montar() {
  document
    .querySelectorAll("[data-contagem-reenvio]:not([data-contagem-montada])")
    .forEach((painel) => {
      painel.dataset.contagemMontada = "true";
      correr(painel);
    });
}

document.addEventListener("DOMContentLoaded", montar);
document.addEventListener("htmx:afterSwap", montar);

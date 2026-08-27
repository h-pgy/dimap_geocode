// Checklist reativo de senha forte e correspondência de confirmação (SPEC autenticacao/002):
// estado visual de um controle — o servidor confere tudo de novo ao gravar, aqui é só feedback.
const CARACTERES_ESPECIAIS = "!@#$%^&*()_+-=[]{}|;:,.<>?";

function avaliarRegras(senha) {
  return {
    tamanho: senha.length >= 8,
    maiuscula: /[A-Z]/.test(senha),
    especial: Array.from(senha).some((caractere) => CARACTERES_ESPECIAIS.includes(caractere)),
  };
}

function atualizarChecklist(lista, senha) {
  const regras = avaliarRegras(senha);
  lista.querySelectorAll("[data-requisito]").forEach((item) => {
    item.classList.toggle("atendido", Boolean(regras[item.dataset.requisito]));
  });
}

function atualizarMatch(confirmacao, feedback, nova, digitouConfirmacao) {
  const coincide = nova === confirmacao.value;
  confirmacao.classList.toggle("campo-realce-erro", digitouConfirmacao && !coincide);
  if (!digitouConfirmacao) {
    feedback.innerHTML = "";
  } else if (coincide) {
    feedback.innerHTML =
      '<p class="text-xs text-success font-medium flex items-center gap-1 mt-1">✓ As senhas coincidem</p>';
  } else {
    feedback.innerHTML =
      '<p class="text-xs text-error font-medium flex items-center gap-1 mt-1">✕ As senhas não coincidem</p>';
  }
}

function montar(container) {
  const nova = container.querySelector("[data-checklist-alvo]");
  const confirmacao = container.querySelector("[data-checklist-confirmacao]");
  const lista = container.querySelector("[data-checklist-lista]");
  const feedback = container.querySelector("[data-checklist-feedback]");
  if (!nova || !confirmacao || !lista || !feedback) return;

  const aoDigitar = () => {
    atualizarChecklist(lista, nova.value);
    atualizarMatch(confirmacao, feedback, nova.value, confirmacao.value.length > 0);
  };

  nova.addEventListener("input", aoDigitar);
  confirmacao.addEventListener("input", aoDigitar);
}

// O atributo de montagem marca o que já foi feito: `htmx:load` também dispara no scan inicial da
// página (não só num swap real), e sem a marca o mesmo formulário ganhava dois ouvintes por campo.
function montarTodos() {
  document
    .querySelectorAll("[data-checklist-senha]:not([data-checklist-montado])")
    .forEach((container) => {
      container.dataset.checklistMontado = "true";
      montar(container);
    });
}

document.addEventListener("DOMContentLoaded", montarTodos);
document.addEventListener("htmx:afterSwap", montarTodos);

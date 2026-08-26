// Opt-in por [data-mascara], no padrão dos demais módulos de UI (SPEC autenticacao/001). O
// gabarito diz onde entram os separadores e, pela contagem dos seus slots, quantos dígitos o
// campo tem; [data-mascara-alvo] aponta o campo oculto que leva ao servidor só os dígitos.
const SLOT_DE_DIGITO = "0";

function contarDigitos(texto) {
  return texto.replace(/\D/g, "").length;
}

// O excesso não é truncado: sai formatado à direita do gabarito e acende o campo — engolir a
// tecla a mais esconderia da pessoa que ela digitou um RF errado.
function formatar(digitos, gabarito) {
  let saida = "";
  let lidos = 0;
  for (const marca of gabarito) {
    if (lidos >= digitos.length) return saida;
    if (marca === SLOT_DE_DIGITO) {
      saida += digitos[lidos];
      lidos += 1;
    } else {
      saida += marca;
    }
  }
  return saida + digitos.slice(lidos);
}

// Reformatar move o texto sob o cursor; o que o mantém no lugar é a contagem de dígitos à
// esquerda dele, que a máscara não altera.
function posicaoAposDigitos(texto, quantidade) {
  if (quantidade === 0) return 0;
  let vistos = 0;
  for (let i = 0; i < texto.length; i += 1) {
    if (!/\d/.test(texto[i])) continue;
    vistos += 1;
    if (vistos === quantidade) return i + 1;
  }
  return texto.length;
}

function aplicar(campo) {
  const gabarito = campo.dataset.mascara;
  const limite = contarDigitos(gabarito);
  const cursor = campo.selectionStart ?? campo.value.length;
  const digitosAEsquerda = contarDigitos(campo.value.slice(0, cursor));
  const digitos = campo.value.replace(/\D/g, "");

  campo.value = formatar(digitos, gabarito);
  if (document.activeElement === campo) {
    const posicao = posicaoAposDigitos(campo.value, digitosAEsquerda);
    campo.setSelectionRange(posicao, posicao);
  }

  const excede = digitos.length > limite;
  campo.classList.toggle("campo-realce-erro", excede);
  campo.setAttribute("aria-invalid", excede ? "true" : "false");
  campo.dataset.digitosCompletos = digitos.length === limite ? "sim" : "nao";

  const alvo = document.querySelector(campo.dataset.mascaraAlvo);
  if (alvo) alvo.value = digitos;
}

function montar(raiz) {
  raiz.querySelectorAll("[data-mascara]").forEach((campo) => {
    campo.addEventListener("input", () => aplicar(campo));
    aplicar(campo);
  });
}

document.addEventListener("DOMContentLoaded", () => montar(document));
// A recusa 422 devolve o formulário inteiro, e com ele um campo de RF que ainda não foi montado.
document.body.addEventListener("htmx:load", (evento) => montar(evento.detail.elt));

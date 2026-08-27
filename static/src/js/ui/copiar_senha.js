// Botão de copiar a senha do modal de desenvolvimento (SPEC criacao_usuarios/007). Terceiro caso
// do §7.2 do CLAUDE.md — estado visual de um controle, aprovado pelo usuário. Nenhum estado de
// domínio: a senha já está no DOM, e o botão só a move para o clipboard.

function trocarFace(botao, estado) {
  botao.dataset.estado = estado;
}

function ligarCopiaDeSenha(raiz) {
  const botao = raiz.querySelector("[data-copiar-senha]");
  if (botao === null) return;
  botao.addEventListener("click", async () => {
    // `navigator.clipboard` não existe fora de contexto seguro (HTTP em IP de rede) — o catch é
    // o caminho real, não defensivo, e por isso o botão precisa saber dizer que falhou.
    try {
      await navigator.clipboard.writeText(botao.dataset.copiarSenha);
      trocarFace(botao, "copiado");
    } catch {
      trocarFace(botao, "falhou");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => ligarCopiaDeSenha(document));
// O modal chega por oob depois do POST de cadastro: o botão dele nasce depois da carga inicial.
document.body.addEventListener("htmx:load", (evento) => ligarCopiaDeSenha(evento.detail.elt));

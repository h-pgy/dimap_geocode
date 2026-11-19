// Editor visual da resposta da FAQ (SPEC faq/002). Estado visual de um controle, aprovado na SPEC: o
// JS só espelha o markdown no <textarea> do <form>. Validação e gravação são do servidor.
import { Crepe } from "@milkdown/crepe";

const ROTULOS = {
  [Crepe.Feature.Placeholder]: {
    text: "Escreva a resposta. Digite / para inserir títulos, listas e tabelas.",
    mode: "block",
  },
  [Crepe.Feature.Toolbar]: {
    boldLabel: "Negrito",
    italicLabel: "Itálico",
    strikethroughLabel: "Riscado",
    codeLabel: "Código",
    linkLabel: "Link",
  },
  [Crepe.Feature.LinkTooltip]: { inputPlaceholder: "Cole o endereço: /faq/ ou https://…" },
  [Crepe.Feature.BlockEdit]: {
    textGroup: {
      label: "Texto",
      text: { label: "Parágrafo" },
      h1: { label: "Título 1" },
      h2: { label: "Título 2" },
      h3: { label: "Título 3" },
      h4: { label: "Título 4" },
      h5: { label: "Título 5" },
      h6: { label: "Título 6" },
      quote: { label: "Citação" },
      divider: { label: "Linha horizontal" },
    },
    listGroup: {
      label: "Listas",
      bulletList: { label: "Lista" },
      orderedList: { label: "Lista numerada" },
      taskList: { label: "Lista de tarefas" },
    },
    advancedGroup: {
      label: "Avançado",
      codeBlock: { label: "Bloco de código" },
      table: { label: "Tabela" },
    },
  },
};

function criarCrepe(alvo, campo, estado) {
  const crepe = new Crepe({
    root: alvo,
    defaultValue: campo.value,
    // Fora o que o renderizador de faq/001 não mostra: a fórmula, e o bloco de imagem do Crepe, que
    // aceitaria endereço externo (a imagem entra pelo fluxo de faq/004).
    features: { [Crepe.Feature.Latex]: false, [Crepe.Feature.ImageBlock]: false },
    featureConfigs: ROTULOS,
  });
  crepe.on((ouvinte) =>
    ouvinte.markdownUpdated((_ctx, markdown) => {
      campo.value = markdown;
      estado.emitido = markdown;
    }),
  );
  return crepe.create().then(() => crepe);
}

async function montarEditor(alvo) {
  alvo.dataset.editorMontado = "";
  const campo = document.getElementById(alvo.dataset.editorMarkdown);
  const estado = { emitido: campo.value };
  let crepe = await criarCrepe(alvo, campo, estado);
  // O que se digitou no modo Markdown volta ao Visual: o Crepe renasce do texto do campo.
  const abaVisual = alvo.closest("[role=tablist]").querySelector("[data-modo-visual]");
  abaVisual.addEventListener("change", async () => {
    if (campo.value === estado.emitido) return;
    await crepe.destroy();
    alvo.replaceChildren();
    estado.emitido = campo.value;
    crepe = await criarCrepe(alvo, campo, estado);
  });
}

// O formulário recusado volta inteiro por swap: o editor novo precisa nascer de novo.
function montarEditores() {
  document.querySelectorAll("[data-editor-markdown]:not([data-editor-montado])").forEach((alvo) => {
    montarEditor(alvo).catch(() => {
      // Sem o editor, o <textarea> do modo Markdown continua sendo o campo, e ele basta.
      alvo.closest("[role=tablist]").querySelector("input[value=markdown]").checked = true;
    });
  });
}

montarEditores();
document.addEventListener("htmx:afterSwap", montarEditores);

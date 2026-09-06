// Fundo da área administrativa, para os mocks (skill `mock`).
//
// Este módulo NÃO desenha fundo algum: ele busca as MESMAS peças que a aplicação usa —
// `templates/mapping/_mapa_admin.html` e os partials que ele inclui (`_glifos_fundo.html`,
// `_fundo_ortofoto.html`, `_camada_ortofoto.html`, `_controle_fundo.html`) — e as monta na página
// do mock. Trocar o fundo
// do produto passa a trocar o de todos os mocks de uma vez, que é o oposto de cada mock recriar o
// seu e envelhecer sozinho.
//
// Uso, no mock:
//   <script type="module">
//     import { montarFundoAdmin } from "/.claude/skills/mock/examples/fundo-admin.js";
//     montarFundoAdmin();
//   </script>
//
// Exige servidor com root na RAIZ do projeto (Live Server), como o resto do mock.

const PARTIAL_FUNDO = "/templates/mapping/_mapa_admin.html";
const PARTIAL_GLIFOS = "/templates/mapping/_glifos_fundo.html";
const PARTIAL_CASCA = "/templates/mapping/_fundo_ortofoto.html";
const PARTIAL_CAMADA = "/templates/mapping/_camada_ortofoto.html";
const PARTIAL_CONTROLE = "/templates/mapping/_controle_fundo.html";
const MODULO_CONTROLE = "/static/src/js/ui/controle_fundo.js";
const DIR_ORTOFOTOS = "/static/src/img/ortofotos_fundo/";

// Espelha as chaves de config/pontos_fundo.json: no mock não há Django para sortear no servidor,
// nem para resolver {% static %} — o `fetch` cru do template devolve a tag intacta.
const CHAVES_ORTOFOTO = [
  "anhangabau",
  "ibirapuera",
  "butanta",
  "itaquera",
  "anhembi",
  "cantareira",
  "jaragua",
  "interlagos",
];

const TAG_DE_TEMPLATE = /\{[{%#][\s\S]*?[}%#]\}/g;

function avisar(mensagem) {
  (document.body || document.documentElement).insertAdjacentHTML(
    "afterbegin",
    `<p style='padding:1rem;color:#b00;font-family:monospace'>${mensagem}</p>`,
  );
}

async function buscarPartial(caminho) {
  const resposta = await fetch(caminho);
  if (!resposta.ok) throw new Error(`${caminho} → ${resposta.status}`);
  return (await resposta.text()).replace(TAG_DE_TEMPLATE, "").trim();
}

// A casca é `{% include %}` e mais nada — sem Django, o fetch cru devolve um recipiente vazio, e a
// camada precisa ser aninhada aqui. O `{% static %}` do src some do mesmo jeito, e é a ortofoto
// sorteada que o repõe; o `{% if not entrando %}` cai deixando a classe que revela a camada, que é
// o certo: no mock não há JS de rodízio para acendê-la depois.
function montarCanvas(casca, camada, chave) {
  const molde = document.createElement("div");
  molde.innerHTML = casca;
  molde.firstElementChild.innerHTML = camada.replace(
    'src=""',
    `src="${DIR_ORTOFOTOS}${chave}.png"`,
  );
  return molde.innerHTML;
}

export async function montarFundoAdmin() {
  try {
    const chave = CHAVES_ORTOFOTO[Math.floor(Math.random() * CHAVES_ORTOFOTO.length)];
    const [molde, glifos, casca, camada, controle] = await Promise.all([
      buscarPartial(PARTIAL_FUNDO),
      buscarPartial(PARTIAL_GLIFOS),
      buscarPartial(PARTIAL_CASCA),
      buscarPartial(PARTIAL_CAMADA),
      buscarPartial(PARTIAL_CONTROLE),
    ]);
    const canvasPintado = montarCanvas(casca, camada, chave);
    // Ordem espelha _mapa_admin.html: glifos (invisível) → canvas (z-0) → lente (z-1, no molde
    // já sem o include) → controle (z-20).
    document.body.insertAdjacentHTML("afterbegin", glifos + canvasPintado + molde + controle);
    await import(MODULO_CONTROLE);
  } catch (erro) {
    avisar(`fundo administrativo não montou (${erro.message}) — sirva a RAIZ do projeto.`);
  }
}

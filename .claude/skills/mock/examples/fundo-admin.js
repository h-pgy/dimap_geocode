// Fundo da área administrativa, para os mocks (skill `mock`).
//
// Este módulo NÃO desenha fundo algum: ele busca as MESMAS peças que a aplicação usa —
// `templates/mapping/_mapa_admin.html` (as camadas da lente) e `static/src/js/mapa/fundo_admin.js`
// (o mapa, a ortofoto do GeoSampa e a deriva) — e as monta na página do mock. Trocar o fundo do
// produto passa a trocar o de todos os mocks de uma vez, que é o oposto de cada mock recriar o seu
// e envelhecer sozinho.
//
// Uso, no mock (o CDN do Leaflet precisa vir ANTES):
//   <script type="module">
//     import { montarFundoAdmin } from "/.claude/skills/mock/examples/fundo-admin.js";
//     montarFundoAdmin();
//   </script>
//
// Exige servidor com root na RAIZ do projeto (Live Server), como o resto do mock.

const PARTIAL_FUNDO = "/templates/mapping/_mapa_admin.html";
const MODULO_FUNDO = "/static/src/js/mapa/fundo_admin.js";

// Espelham config/settings.py: no mock não há Django para injetar o contexto. Se a base oficial
// mudar de URL ou de camada, é aqui que se acerta — em um lugar, não em cada mock.
const WMS = {
  url: "https://wms.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/ows",
  version: "1.3.0",
  bases: [
    {
      nome: "Ortofoto",
      layers: "geoportal:ORTO_RGB_2020",
      url: "http://raster.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wms",
    },
    { nome: "Mapa base", layers: "geoportal:MapaBase_Politico" },
  ],
};
const CONFIG_FUNDO = {
  centro: [-23.55, -46.63],
  zoom: 15,
};

const TAG_DE_TEMPLATE = /\{[{%#][\s\S]*?[}%#]\}/g;

function avisar(mensagem) {
  (document.body || document.documentElement).insertAdjacentHTML(
    "afterbegin",
    `<p style='padding:1rem;color:#b00;font-family:monospace'>${mensagem}</p>`,
  );
}

function inserirJson(id, dados) {
  const script = document.createElement("script");
  script.type = "application/json";
  script.id = id;
  script.textContent = JSON.stringify(dados);
  document.body.appendChild(script);
}

export async function montarFundoAdmin() {
  try {
    if (!window.L) throw new Error("Leaflet não carregou — o CDN dele vem antes deste módulo.");

    const resposta = await fetch(PARTIAL_FUNDO);
    if (!resposta.ok) throw new Error(`${PARTIAL_FUNDO} → ${resposta.status}`);
    const marcacao = (await resposta.text()).replace(TAG_DE_TEMPLATE, "").trim();
    document.body.insertAdjacentHTML("afterbegin", marcacao);

    // O que o `json_script` do Django entrega em produção.
    inserirJson("mapa-admin-wms", WMS);
    inserirJson("mapa-admin-config", CONFIG_FUNDO);

    await import(MODULO_FUNDO);
    // O módulo da aplicação monta no DOMContentLoaded, que aqui já passou: sem este disparo, ele
    // ficaria carregado e nunca chamado. Andaime do mock — a aplicação não precisa dele.
    document.dispatchEvent(new Event("DOMContentLoaded"));
  } catch (erro) {
    avisar(`fundo administrativo não montou (${erro.message}) — sirva a RAIZ do projeto.`);
  }
}

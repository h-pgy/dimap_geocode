---
spec: mapa/004
versao: v1
atualizado_em: 2026-07-06
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC mapa/004 — Voo suave anti-flicker ao reenquadrar o resultado

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como usuário que faz uma busca cujo resultado está longe da vista atual do mapa, quero que o
mapa **se desloque suavemente** (com um leve zoom-out → pan → zoom-in, estilo Google Earth) em vez
de saltar direto para o destino, para **não ver o flash branco** enquanto as tiles da ortofoto do
GeoSampa ainda estão sendo carregadas do servidor.

## Critérios de aceite
- [ ] Buscas cujo resultado está **longe** da vista atual reenquadram com uma animação de voo
      (zoom-out → deslocamento → zoom-in), não com salto instantâneo.
- [ ] Buscas cujo resultado está **perto** da vista atual continuam reenquadrando de forma direta
      (sem a animação de voo, que seria gratuita/irritante para deslocamentos curtos).
- [ ] Durante o voo, o trajeto passa por cima de imagem de zoom mais baixo (já em cache) em vez de
      área branca; ao chegar, as tiles do destino **entram por fade-in** em vez de "piscar".
- [ ] A camada base da ortofoto mantém um buffer de tiles maior ao redor da vista, reduzindo o
      descarte de imagem já carregada durante o deslocamento.
- [ ] O comportamento vale igualmente para os três tipos de resultado (ponto, linha, polígono).
- [ ] Nenhuma regressão no enquadramento final: o resultado continua cabendo na tela com o mesmo
      padding/`maxZoom` de hoje.

## Contexto e decisões de arquitetura

Mexe **exclusivamente na ponta de interface** — JS local ao objeto `map` do Leaflet, que é um dos
dois casos permitidos de JS no frontend (CLAUDE.md §11, caso 2: utilitário para falar com o `map`).
**Nenhuma** regra de negócio, DTO, view ou domínio é tocada. Não há mudança de servidor, de
persistência nem de contrato de dados.

**Por que só client-side.** A ortofoto (`geoportal:ORTO_RGB_2020`) vem do GeoServer de raster do
GeoSampa (`raster.geosampa.prefeitura.sp.gov.br`), que **renderiza cada tile ao vivo** por WMS. Foi
sondado se dava para acelerar a origem via tile cache (GeoWebCache/WMTS/WMS-C *tiled*) e **não dá**:
os endpoints `/gwc/service/wmts` e `/gwc/service/tms` respondem **403 Forbidden** (bloqueados por
proxy/WAF), o `GetCapabilities` do WMS **não anuncia** tiling WMS-C (sem bloco
`VendorSpecificCapabilities`/`TileSet`), e um `GetMap` com `TILED=true` volta PNG válido mas **sem
header `geowebcache-cache-result`** — ou seja, não cai em cache nenhum. Como a latência de origem é
inevitável, a solução é **mascará-la no cliente**: dar tempo ao WMS enquanto mostramos algo em vez
de branco.

**Como funciona a solução.** Três alavancas somadas:

1. **Voo condicional por distância.** Hoje o reenquadramento é um salto instantâneo
   (`fitBounds`/`setView`). Troca-se por uma decisão: se o alvo está **longe** da vista atual, usa
   `flyToBounds`/`flyTo` (o arco nativo do Leaflet: zoom-out → pan → zoom-in); se está **perto**,
   mantém o enquadramento direto. O arco resolve o grosso do flicker porque os frames intermediários
   (zoom mais baixo) cobrem área maior com tiles mais grosseiras — que carregam rápido ou já estão
   em cache — em vez de branco. A duração do voo é o "tempinho" proposital que cobre a latência de
   render do WMS no destino.

2. **Fade-in das tiles.** A animação de fade do `TileLayer` do Leaflet (ligada por padrão) precisa
   ser preservada: nada de desabilitar `fadeAnimation`. Assim, qualquer tile que ainda falte na
   chegada **entra em foco** em vez de piscar.

3. **`keepBuffer` maior na base WMS.** Aumentar o anel de tiles mantido ao redor do viewport reduz o
   descarte de imagem já carregada durante o deslocamento, dando material para o trajeto do voo.

**Limiar de distância.** A escolha "perto vs. longe" é uma constante em metros no topo do módulo
(`UPPER_CASE` conceitual em JS), comparando a distância geodésica entre o centro atual do mapa e o
centro do alvo. Constante única, fácil de calibrar.

## Peças de referência a compor
Reutilizar por composição — **não** recriar mapa, base nem camada de resultado:
- `@static/src/js/mapa/camada_resultado.js` → `adicionarResultado`: é aqui que hoje mora o
  reenquadramento final (`fitBounds`/`setView`). O voo condicional entra **substituindo esse trecho
  de reenquadramento** por um helper de "reenquadrar com voo quando longe".
- `@static/src/js/mapa/camada_base.js` → `adicionarBaseWms`: é aqui que a camada `L.tileLayer.wms` é
  construída. O `keepBuffer` (e a garantia de não desligar o fade) entra **nas opções dessa camada**.
- `@static/src/js/mapa/criar_mapa.js` → `criarMapa`: define `minZoom`/`maxZoom` do mapa; o arco do
  `flyTo` respeita esses limites (nada a mudar, apenas ciente de que o zoom-out do voo é limitado
  pelo `minZoom` atual).
- `@static/src/js/mapa/init.js` → `aplicarResultado`: continua sendo o disparador; não muda —
  `adicionarResultado` segue responsável por reenquadrar.

## Snippets sugeridos
```js
// static/src/js/mapa/camada_resultado.js — direção; adaptar sem violar §10/§11.

// Constantes locais ao módulo, logo no topo (após eventuais imports).
const DISTANCIA_VOO_METROS = 3000; // acima disso, faz o arco; abaixo, enquadra direto
const DURACAO_VOO_S = 2.2;         // "tempinho" que cobre a latência de render do WMS
const OPCOES_ENQUADRE = { maxZoom: 18, padding: [20, 20] };

// Reenquadra com voo (arco) quando o alvo está longe; direto quando está perto.
function reenquadrar(map, bounds) {
  const alvo = bounds.isValid() ? bounds.getCenter() : bounds; // bounds ou LatLng do ponto
  const longe = map.getCenter().distanceTo(alvo) > DISTANCIA_VOO_METROS;
  if (bounds.isValid()) {
    longe
      ? map.flyToBounds(bounds, { ...OPCOES_ENQUADRE, duration: DURACAO_VOO_S })
      : map.fitBounds(bounds, OPCOES_ENQUADRE);
  } else {
    longe
      ? map.flyTo(alvo, 17, { duration: DURACAO_VOO_S })
      : map.setView(alvo, 17);
  }
}

export function adicionarResultado(map, geometria, corPadrao) {
  const camada = L.geoJSON(geometria, { /* ...igual ao atual... */ }).addTo(map);
  reenquadrar(map, camada.getBounds());
  return camada;
}
```

```js
// static/src/js/mapa/camada_base.js — nas opções da L.tileLayer.wms:
const layer = L.tileLayer.wms(b.url || wms.url, {
  layers: b.layers,
  version: wms.version,
  format: "image/png",
  transparent: false,
  keepBuffer: 6,        // mantém mais tiles ao redor do viewport durante o deslocamento
  attribution: "GeoSampa — PMSP",
});
// NÃO desligar fadeAnimation do mapa (fade das tiles é o que evita o "pisca" na chegada).
```

## Fora de escopo
- **Qualquer otimização no servidor do GeoSampa** (WMTS/GWC/WMS-C *tiled*): comprovadamente
  indisponível (403 nos endpoints de cache; WMS não anuncia tiling). Documentado aqui só para não
  ser retentado.
- Camada WMS secundária fixa em zoom baixo como "rede de segurança" de cache: possível reforço
  futuro, deixado de fora por ser over-engineering enquanto `flyTo` + `keepBuffer` resolverem.
- Pré-carregamento offscreen/manual de tiles do destino antes de mover.
- Mudança nos limites de zoom do mapa, nas cores/estilos do resultado ou no popup/tooltip.
- Ajuste de comportamento do controle de camadas ou da troca de base (ortofoto ↔ mapa base).

## Notas de teste
Referência para quando os testes forem pedidos (não implementar agora) — e casos de borda para o
smoke test manual:
- **Longe:** buscar algo no extremo oposto da cidade partindo do centro default → deve animar o arco
  e não mostrar tela branca no meio do caminho.
- **Perto:** buscar algo dentro/junto do viewport atual → deve enquadrar direto, sem voo.
- **Ponto vs. linha vs. polígono:** os três reenquadram corretamente (bounds válido para linha e
  polígono; caminho de ponto para o `circleMarker`).
- **Resultados em sequência:** um segundo resultado logo após o primeiro remove a camada anterior e
  reenquadra a partir da nova posição (a decisão perto/longe usa o centro **corrente**).
- **Limiar:** calibrar `DISTANCIA_VOO_METROS` para que deslocamentos de poucos quarteirões não
  disparem o voo, mas travessias de bairro sim.

## Patches

_Nenhum patch registrado até o momento._

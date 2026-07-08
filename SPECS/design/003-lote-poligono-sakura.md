---
spec: design/003
versao: v1
atualizado_em: 2026-07-07
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC design/003 — Polígono de lote na escala sakura

- [x] **Implementada**

## User story
Como usuário da busca com a **ortofoto** de base, quero que o polígono do lote seja plotado num
rosa/magenta vivo (escala **sakura** do design system), para conseguir ler a geometria sobre o
raster — os tons de madeira somem em telhados e solo exposto.

## Critérios de aceite
- [ ] Buscar um lote plota o polígono com traço `sakura-500` (`#D84F7F`) e preenchimento na mesma
      cor com a opacidade padrão da camada de resultado (~35%).
- [ ] O lote **condominial** usa a variante mais funda da mesma família: `sakura-700` (`#97294F`).
- [ ] O badge `.badge-poligono` (sugestões, seleção de lote, home) exibe a pele sakura
      (borda/fundo/tinta), consistente com a cor plotada.
- [ ] O popup do lote no mapa usa a tinta `sakura-700` no identificador SQL (hoje `madeira-700`).
- [ ] O design system (skill `componentes-frontend`) reflete a troca: sakura assume o papel
      "geometria de polígono" e a madeira deixa de listá-lo (segue como tinta de títulos/acentos);
      styleguide, paleta JSON e SKILL.md coerentes entre si.
- [ ] `MAP_COR_POLIGONO` continua sobrescrevível por env var, sem mudança de contrato.

## Contexto e decisões de arquitetura

Puramente **apresentação** (tokens de cor + templates + default de settings): nenhum domínio,
model ou contrato muda. A cor viaja pelo mesmo caminho de hoje — settings → view do
`lote_geocoder` → `contexto_mapa` → JS da camada de resultado (que já aplica traço + fill a 0.35).

Decisões:
- A **fonte da verdade** volta a ser uma só: `geometrias.poligono` na paleta do design system passa
  a `#D84F7F` (sakura-500) e o settings volta a ler `_GEOMETRIAS["poligono"]`. Isso **supera o
  desvio do patch 001 da SPEC design/001** (que apontava `map_cor_poligono` para madeira-400 por
  falta de contraste na ortofoto — exatamente o problema que a escala sakura resolve na raiz).
- O condominial lê `_ESCALAS["sakura"]["700"]` (mesma família, tom mais fundo — regra atual).
- A pele do badge é a transposição direta da atual: `border-sakura-500/50 bg-sakura-400/15
  text-sakura-700`.
- Os popups de **segmento** e **endereço** mantêm `madeira-700`: ali a madeira é tinta de título,
  não cor de entidade lote.

## Peças de referência a compor
- Escala **sakura** já criada na paleta (skill `componentes-frontend` §3.1) — esta SPEC só troca
  papéis, não cria cor nova.
- `@config/paleta_ds.json` (espelho de `references/paleta.json` da skill) → `_GEOMETRIAS` /
  `_ESCALAS` lidos pelo settings — mecanismo existente de cor por geometria.
- Token `.badge-poligono` — definido nos quatro espelhos do design system (base.html, input.css,
  `references/design_system.css`, exemplos da skill); trocar a pele nos quatro.
- `@static/src/js/mapa/camada_resultado.js` → já aplica `color` + `fillColor` com `fillOpacity`
  0.35 a partir da cor única recebida — nada a mudar no JS.

## Snippets sugeridos
```python
# config/settings.py — direção
map_cor_poligono: str = Field(default=_GEOMETRIAS["poligono"], alias="MAP_COR_POLIGONO")
map_cor_poligono_condominio: str = Field(
    default=_ESCALAS["sakura"]["700"], alias="MAP_COR_POLIGONO_CONDOMINIO"
)
```
```css
/* pele sakura do badge de polígono (nos quatro espelhos) */
.badge-poligono { @apply border border-sakura-500/50 bg-sakura-400/15 text-sakura-700 font-medium; }
```

## Fora de escopo
- Cores de **linha** (logradouro) e **ponto** (endereço) — seguem `accent` e `agua-500`; se também
  perderem leitura sobre a ortofoto, é iteração futura (o caminho será a mesma escala sakura).
- Tinta dos popups de segmento/endereço (madeira-700 = título, mantém).
- Cor por base visível (madeira sobre mapa base / sakura sobre ortofoto) — descartado: uma cor
  única por geometria é mais simples e a sakura lê bem nas duas bases.
- Qualquer mudança em domínio, contratos ou no JS do mapa.

## Notas de teste
(Só quando explicitamente solicitado — CLAUDE.md §13.)
- Smoke test: buscar um SQL de lote comum e um condominial; conferir cor do polígono, badge nas
  sugestões e popup. Conferir override por env var `MAP_COR_POLIGONO`.

## Patches

_Nenhum patch registrado até o momento._

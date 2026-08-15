---
spec: autorizacao/006
versao: v2
atualizado_em: 2026-08-14
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
  - v2: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
    `specs`, com a justificativa toda concentrada em Caveats
---

# SPEC autorizacao/006 — Ícones das ações e renderização do menu

## 1 · User story
O servidor da DIMAP reconhece no menu, pelo glifo e pelo nome, as ações que pode executar sobre o que
tem na tela, para escolher o que fazer sem precisar ler tudo.

## 2 · Condições de pronto
- [ ] O ícone de uma ação é localizado **por convenção** a partir do slug e da variante — a mesma
      convenção que o system check da SPEC 001 cobra, sem segunda cópia do gabarito.
- [ ] O SVG é **inserido inline** e herda a cor do texto: o ícone acompanha hover, foco e a tinta do
      contexto.
- [ ] Ação sem o arquivo declarado **não quebra a tela**: cai num glifo genérico do design system.
- [ ] Ler o mesmo ícone várias vezes na mesma página **não relê o disco**.
- [ ] O menu renderiza a saída do router (SPEC 005) compondo **átomo → molécula → organismo**, sem
      marcação solta e sem token novo fora do design system.
- [ ] A mesma ação é renderizável em **duas formas** — linha compacta e cartão explicativo —, e quem
      escolhe é o menu, não a ação.
- [ ] Menu sem item liberado exibe **estado vazio**, não um painel quebrado.
- [ ] O design foi aprovado no **mock**, e as peças novas — `.icone-acao`, `.item-menu`, `.card-acao` e
      `.menu-acoes` — foram portadas para `static/src/tema-dimap.dev.css` e renderizadas no styleguide
      antes de qualquer template da aplicação usá-las.

## 3 · Domínio
Iteração de **interface e orquestração**: nenhum model novo, nenhuma migração, nenhum DTO de entrada —
o menu já chega resolvido. O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`MenuResolvido` e `ItemRenderizavel`](005-contrato-de-menu-e-router.md) — "o que este usuário pode
  executar, nesta ordem, com que nome e em que forma?"; o organismo desenha isso e não recalcula
  autorização.
- [`VarianteIcone`](001-catalogo-de-acoes-em-codigo.md) — "de que tamanho óptico é o glifo pedido?".
- [`GABARITO_CAMINHO_ICONE`](001-catalogo-de-acoes-em-codigo.md) — "onde mora o arquivo desta variante?";
  a convenção já existe em `checks.py` e é reusada, não redeclarada.

**Mock:** [006-mock-icones-e-menu.html](006-mock-icones-e-menu.html) — leia a skill `mock`.

## 4 · Fora de escopo
- A tela que consome o menu e a primeira ação registrada — SPEC 007.
- Gaveta da entidade territorial — épico de busca.
- Desenhar os glifos das ações — cada ação traz o seu; aqui nasce só o genérico do fallback.
- Ícone colorido ou com mais de duas variantes — sem dono ainda.
- Invalidação do cache de SVG sem reiniciar o processo — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/menus.py` (SPEC 005) → `MenuResolvido` e `ItemRenderizavel`: o que o organismo
  desenha.
- `@apps/competencias/checks.py` (SPEC 001) → `GABARITO_CAMINHO_ICONE`: a convenção de caminho.
- `django.contrib.staticfiles.finders` → `find()`: localiza o SVG honrando `STATICFILES_DIRS`.
- `@services/domain/warmup.py`: idioma de cache em memória aquecido no processo web.
- `@templates/partials/_filtros_gravacao.html`: os `defs` de gravação, já incluídos no `base.html`.
- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.card-well`, `.icon-glow`, `.icon-etched`,
  `.text-overline`, `.btn-glass`.
- Skills: `componentes-frontend`, `daisyui`, `mock`, `escrever-testes`.

## 6 · Snippets

**`apps/competencias/icones.py`** — slug + variante → markup, com o gabarito vindo de `checks.py`.
```python
class ResolvedorIcones:
    """Cacheado por processo: inline custa ler o arquivo no render, e é isso que paga o custo."""

    def __call__(self, slug: str, variante: VarianteIcone) -> str:
        # Arquivo ausente já é erro de system check no boot (SPEC 001). Em runtime, um glifo
        # genérico degrada melhor que um buraco no meio do menu.
        ...
```

**`templates/competencias/partials/_icone_acao.html`** — o átomo: normaliza a caixa e deixa a cor vir
de fora.
```html
{# `|safe` porque o conteúdo é o SVG do próprio projeto, lido de static/acoes/ pelo resolvedor. #}
<span class="icone-acao icone-acao-{{ variante }} icone-acao-acende">{{ svg|safe }}</span>
```

**`templates/competencias/partials/_item_menu.html`** e **`_card_acao.html`** — as duas formas do mesmo
item, compostas sobre o átomo. A linha usa o `nome_curto`; o cartão usa o `nome` e o `tooltip` como
descrição.

**`templates/competencias/partials/_menu_acoes.html`** — o organismo: escolhe a forma pelo item e
resolve o vazio como peça, não como ausência.
```html
{# O organismo não conhece perfil, cargo nem unidade: ele desenha o que o router devolveu. #}
{% for item in menu.itens %}
  {% include item.partial %}
{% empty %}
  <div class="menu-acoes-vazio">Nenhuma ação disponível para o seu cargo nesta unidade.</div>
{% endfor %}
```

**`static/src/tema-dimap.dev.css`** — o átomo não declara `color`: quem amarra o traço é o `stroke` do
SVG.
```css
/* Declarar cor aqui venceria por cascata a pele empilhada (.icon-glow é text-agua-600) e o brilho
   sumiria sem erro nenhum. */
.icone-acao svg { stroke: currentColor; }
```

## 7 · Caveats
**O SVG entra inline e é interpolado com `|safe`.** Com `<img src>` o desenho não herda `currentColor`
e o ícone deixaria de acompanhar o hover num design system inteiramente tokenizado. Custo: o markup de
`static/acoes/` passa a ser confiado pelo template, e um SVG com `<script>` colocado ali executaria na
página.

**Os ícones são cacheados em memória, por processo, sem invalidação.** É o que paga a leitura de disco
que o inline impõe, no mesmo idioma dos catálogos de `services/domain`. Custo: trocar o desenho de um
glifo só vale depois de reiniciar o processo web.

**O fallback em runtime duplica a defesa do system check.** O check cobra o arquivo no boot, então o
glifo genérico não deveria aparecer nunca. Custo: quando aparecer — `STATICFILES_DIRS` diferente entre
ambientes, arquivo removido a quente — a tela segue inteira e ninguém fica sabendo, porque o fallback é
silencioso.

**O cartão depende do `hover-3d` do daisyUI, e isso impõe três amarras.** O componente exige nove filhos
diretos, conteúdo não-interativo e não admite `display` declarado sobre ele — é `inline-grid` e posiciona
as zonas por `grid-area`. Custo: o clicável precisa ser o `<a>` de fora, o material do cartão não pode ser
vidro (`backdrop-filter` dentro de transform 3D reamostra o fundo errado), e uma atualização do daisyUI
pode quebrar a peça de um jeito que só aparece no hover.

**A SPEC vai do átomo ao organismo, e não só ao ícone.** Um glifo fora do lugar onde vive não é
aprovável, e o mock precisa mostrar a peça em uso. Custo: a iteração entrega três camadas de uma vez, e
uma correção de desenho no item mexe no que a SPEC 007 já vai estar compondo.

## 8 · Testes (TDD)
Rodam na suíte padrão. O resolvedor é o que tem comportamento a fixar; a aprovação do desenho é o mock,
não teste automatizado.

- `test_resolvedor_localiza_icone_por_convencao` — slug e variante produzem o caminho esperado e devolvem
  o markup do arquivo.
- `test_resolvedor_cai_no_glifo_generico_sem_arquivo` — variante sem arquivo devolve o fallback em vez de
  erro.
- `test_resolvedor_le_o_disco_uma_vez_por_icone` — a segunda leitura do mesmo ícone não toca o sistema de
  arquivos.
- `test_menu_vazio_renderiza_estado_vazio` — o partial do menu com `MenuResolvido` vazio devolve o estado
  vazio, não painel quebrado.

---
spec: user_admin/013
versao: v4
atualizado_em: 2026-08-06
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: gravação passa a filtro SVG (o recorte no texto não dava relevo); barra de rolagem vira
        elemento próprio com JavaScript; inventário do porte para o design system explicitado
  - v3: comando de servidores fictícios (criar e remover) — sem ele a listagem nasce vazia e não há
        como exercitá-la no sistema
  - v4: faixa de RF dos fictícios sobe para 999900-999919, longe de qualquer RF real
---

# SPEC user_admin/013 — Tabela de vidro, gravação no gelo e a listagem de servidores

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero ver os servidores cadastrados numa tabela que eu possa
filtrar por texto em cada coluna e ordenar, para encontrar uma pessoa entre dezenas sem sair da tela
e sem depender do admin do Django.

## Critérios de aceite

- [x] Existe o token **gravação no gelo** (`.etched`): o registro oposto ao `.icon-glow`, que acende.
      O relevo segue a **silhueta da própria forma** — sombra entrando pela borda de cima, lábio de
      luz na de baixo, a mesma leitura do `.card-well` — e a tinta é quase transparente, porque quem
      desenha a forma é a luz. Serve a qualquer caractere, em duas medidas (`.etched` e `.etched-lg`).
      Três restrições andam com ele: **nunca carrega informação**, só afordância; **só vale sobre
      vidro claro**; e quando o sulco precisa **nomear** algo, a tinta sobe (`.etched-rotulo`).
- [x] A **tabela inverte os materiais existentes**: corpo em poço rebaixado (`.card-well`) e
      cabeçalho em **placa de gelo espesso sobre ele**. A caixa rola por conta própria — a viewport
      nunca rola na horizontal — e o cabeçalho é grudento ao rolar.
- [x] A **barra de rolagem é a gravação em caixa**: trilho sulcado, polegar de água. Ela **começa
      abaixo do cabeçalho**, some quando não há o que rolar, e em repouso é só gravação — a água
      entra ao rolar e **escorre de volta** quando o gesto acaba.
- [x] O corpo separa as linhas **em luz** (aresta branca), **não tem zebra**, e o hover **acende** o
      gelo sem mudar de cor.
- [x] A **célula de cabeçalho filtrável afunda no poço** e revela o campo de texto. O estado é
      **"a coluna tem filtro"**, não "alguém clicou": a coluna continua afundada depois que o foco
      sai, e o relevo passa a indicar filtro ativo. O rótulo **permanece** na célula afundada.
- [x] A **régua abre inteira**: o campo de uma coluna abre o campo de todas, e o cabeçalho cresce
      como uma peça só. Afundar continua sendo só de quem tem filtro.
- [x] A coluna que **não responde** (situação, ações) **não tem peça**: o rótulo é gravado direto na
      bandeja. A ausência da peça é a mensagem — sem cinza de desabilitado nem cursor proibido.
- [x] A **ordenação é uma seta gravada** com alvo próprio, à direita da célula: ela **enche de água**
      quando a coluna passa a ordenar e gira 180° em `desc`. A semântica vai no `aria-sort` do `th`.
- [x] Existe o **botão gravado** (`.btn-etched`), a mesma gravação em corpo maior, usado no
      **limpar filtros** — que devolve todas as colunas ao repouso.
- [x] O **filtro casa texto pela normalização única do projeto**: `sant anna` acha `Sant'Anna` e
      `sao` acha `São`. Filtros de colunas diferentes **se somam**.
- [x] A **listagem de servidores é navegável** em `/gestao/servidores/`, com filtro e ordenação
      funcionando por HTMX. **A rota é aberta nesta iteração** — exceção declarada aqui nos termos do
      §3.5, com a proteção por perfil de administrador entrando na SPEC de autenticação.
- [x] Um **management command povoa 20 servidores fictícios** e os **remove**, para a listagem ser
      exercitável no sistema. Eles ocupam uma **faixa de RF reservada** (`999900`–`999919`), e a
      remoção apaga **essa faixa e só ela**. Criar é **idempotente**. Eles cobrem os dois valores de
      cada coluna que tem estado — com e sem impedimento vigente, com e sem cargo em comissão —
      espalhados pelas unidades e cargos que as seeds já criaram.
- [x] O design foi **aprovado no mock** que acompanha esta SPEC antes de qualquer código de
      aplicação.
- [x] Cada peça nova foi **portada para o design system** conforme o inventário abaixo — tema,
      styleguide e skill —, **e os templates da aplicação usam essas classes**, sem utilities soltas
      resolvendo pele.

## Contexto e decisões de arquitetura

Iteração de **interface + domínio de leitura**: tokens novos, partials, uma view de listagem e uma
função de domínio que filtra e ordena. Nenhum model novo, nenhuma migração.

**A inversão de material é a semântica, não o efeito.** Campo, neste design system, é sempre coisa
rebaixada (`.input-glass`, `.upload-well`). Pôr o corpo da tabela num poço e o cabeçalho numa placa
faz "clicar no cabeçalho para filtrar" virar um gesto material — a placa afunda e vira campo — em vez
de um comportamento que precisa ser aprendido. O custo é que o cabeçalho grudento tem de manter o
gelo opaco nos dois estados; translúcido, as linhas passariam por dentro dele ao rolar.

**A gravação vem de filtro SVG, não de recorte no texto.** `box-shadow: inset` só existe em caixa
retangular; para o relevo seguir a silhueta do glifo, a sombra interna é montada em duas passadas
sobre o alfa da forma (`#etched-onsen`). Os deslocamentos são px absolutos e não escalam com o
`font-size`, daí as duas medidas — acima de ~32px o sulco vira um fio.

**Afundado = tem filtro.** Fazendo o estado ser o *valor do campo*, o CSS o lê sozinho com
`:has(input:not(:placeholder-shown))` — a mesma saída da paleta da SPEC 005 e do modal por checkbox
da 012. Não há estado de UI em JavaScript, e o relevo ganha de graça o papel de indicador de filtro
ativo.

**A bandeja cresce sozinha porque nenhuma peça declara altura.** As peças têm a mesma altura por
construção (rótulo em uma linha, campo abrindo em todas ao mesmo tempo), então a mais alta é do
tamanho de qualquer outra e a linha da tabela acompanha. Esticar filho até a célula exigiria altura
fixa nela — que é o que travaria esse crescimento.

**A barra de rolagem é elemento, não `::-webkit-scrollbar`.** O pseudo não existe no Firefox, no
Chrome estilizá-lo troca a barra flutuante por uma clássica sempre visível, e em ambos ele ocupa a
altura inteira do rolador — correria ao lado da bandeja. Elemento começa onde mandarmos e desenha
igual nos dois. Descartada a alternativa de tirar o cabeçalho do rolador: só funciona com as larguras
declaradas em `<colgroup>`, e aí as colunas param de se negociar com o conteúdo.

**JavaScript entra, e só onde o CSS não alcança:** alternar `asc → desc → sem ordem` num alvo único,
preservar foco/caret na troca do corpo, e a barra gravada — medir a bandeja (altura de elemento não
se lê em CSS) e traduzir `scrollTop/scrollHeight` em posição de polegar. Rolar continua sendo do
navegador: roda, teclado e toque não passam pela peça. Autorizado pelo usuário para este organismo.

**O casamento textual fica no servidor.** O normalizador do projeto é um pipeline que descobre etapas
por convenção de nome e foi feito para crescer; uma cópia dele em JavaScript funciona hoje e diverge
na primeira etapa nova — o erro que o §6.1 nomeia. O filtro roda em `services/domain/`, sobre DTOs
(dezenas de registros, sem ORM no domínio), e por isso ganha teste barato sem banco.

**Servidores fictícios são andaime, não seed.** Seed é catálogo versionado de que a aplicação
depende para funcionar; servidor de mentira existe só para exercitar a tela enquanto gravar perfil
não existe. Por isso não entra em `data/seed/` nem no `seeds/` do app — é comando próprio, com a
mesma forma fina das seeds (lógica no app, porque mexe em models; comando só faz parsing e
feedback). A **faixa de RF reservada** é o que torna a remoção segura: apagar por faixa nunca vira
`Perfil.objects.all().delete()` executado no banco errado. Os perfis nascem **sem senha utilizável**
— dado de desenvolvimento não deve criar credencial que funcione —, e o comando **recusa rodar com
`DEBUG` desligado**.

**O swap HTMX é do `<tbody>`, nunca da tabela inteira.** Trocar o `<thead>` junto destruiria o campo
em que se está digitando a cada tecla. Ordenação e filtros viajam no mesmo pedido — um não pode
apagar o outro.

## O que entra no design system

Nada aqui é peça "da tabela": tudo abaixo é patrimônio do design system e nasce nele. O porte é
parte da entrega desta SPEC, não trabalho posterior.

### Camada de tokens → `static/src/tema-dimap.dev.css`, seção `TOKENS DE MATERIAL`

| Peça | Classes | O que é |
|---|---|---|
| Gravação no gelo | `.etched` `.etched-lg` `.etched-inked` `.etched-deeper` `.etched-rotulo` | o material: repouso, medida de display, entintado, hover, e a variante que nomeia |

**A gravação tem um ativo que não é CSS:** os dois `<filter>` (`#etched-onsen`, `#etched-onsen-lg`).
`filter: url(#…)` exige os `defs` no documento, então eles viram um partial incluído em
`base.html` — sem isso a classe existe e não desenha nada. É o item do porte que mais tem cara de
detalhe e mais quebra em silêncio.

### Camada de átomos → tema, seção `ÁTOMOS` + styleguide `2 · Átomos` + tabela de átomos da skill

| Peça | Classes | O que é |
|---|---|---|
| Seta de ordenação | `.sort-etched` | a gravação com alvo próprio e giro de 180° em `desc` |
| Botão gravado | `.btn-etched` | a gravação em corpo de botão; enche de água no hover |
| Ícone gravado em botão de vidro | `.icon-etched` | o glifo dentro de um `.btn-glass`, onde quem carrega a afordância é o botão |
| Ponto da unidade | `.dot-unidade` | o `.paint-well` em escala de marca; o hex chega em `--cor-unidade` |

### Camada de moléculas → tema, seção `MOLÉCULAS` + styleguide `3 · Moléculas` + §2.3 da skill

| Peça | Classes | O que é |
|---|---|---|
| Barra de rolagem gravada | `.scroll-etched` `.scroll-etched-thumb` `.scroll-etched-ativa` `.scroll-etched-ociosa` | serve a **qualquer** `.card-well` rolável, não só à tabela; par com `static/src/js/ui/scroll_etched.js` |
| Bandeja de cabeçalho | `.th-onsen-bandeja` | a superfície de vidro sob as peças de coluna, na forma fora-de-tabela |
| Célula de cabeçalho | `.th-onsen` `.th-onsen-campo` `.th-onsen-input` `.th-onsen-gravado` | a peça que afunda e vira campo, e a variante sem peça para coluna que não responde |
| Tabela de vidro | `.table-onsen` `.table-onsen-wrap` `.table-onsen-poco` | o poço que rola, a âncora da barra e a pele das linhas |

O módulo `scroll_etched.js` segue o padrão do `select_onsen.js`: opt-in por atributo no markup,
montado em todo poço marcado, redesenhado no `htmx:afterSwap` pelo mesmo observador de tamanho que
já trata o filtro.

### Camada de organismos → styleguide `4 · Organismos`

A listagem de servidores é partial Django, não classe: entra no styleguide como composição das
moléculas acima, do jeito que a gaveta de lote já está lá.

### Onde **não** portar

`references/design_system.css` da skill é espelho aposentado pela SPEC design/004 — a fonte única é
o `tema-dimap.dev.css`. Não duplicar lá.

## Peças de referência a compor

- `@static/src/tema-dimap.dev.css` → `.card-well`, `.glass-panel-thick`, `.icon-glow`,
  `.text-overline`, `.text-code`, `.btn-glass`, `.paint-well`: o poço, a placa, a tinta e o disco de
  cor já existem — a tabela é composição deles, não material novo.
- `@static/src/js/ui/select_onsen.js` → o padrão de módulo de UI opt-in por atributo, que a barra
  gravada repete.
- `@apps/mapping` → `contexto_fundo_admin`: o fundo à deriva da SPEC 007, igual ao das páginas de
  formulário.
- `@services/utils` → `normalize_text`: a normalização única do §6.1, na preparação **e** na consulta.
- `@apps/user_admin/models` → `Perfil`, `Unidade`, `CargoBase`, `CargoComissao`, e
  `Perfil.esta_impedido` / `Perfil.cor_unidade`: a situação e a cor da linha já são propriedades do
  model.
- `@apps/user_admin/seeds` → a forma do par comando fino + módulo no app, e as unidades e cargos que
  as seeds já gravam: os servidores fictícios se distribuem entre eles, não inventam catálogo.
- `@apps/user_admin/paleta.py` → `hex_da_cor`: a resolução slug → hex mora na borda do app; o ponto
  da unidade recebe o hex pronto em `--cor-unidade`, como `.avatar-glass` já faz.
- Esqueleto da página administrativa das SPECs 007/012 (casca, fundo, largura) — a listagem é a mesma
  moldura com outro conteúdo.

## Snippets sugeridos

```css
/* A sombra interna segue a silhueta do glifo: box-shadow: inset só existe em caixa retangular. */
.etched {
  filter: url(#etched-onsen);
  color: rgba(13, 27, 42, 0.14);
  @apply transition-all duration-300;
}
/* Os deslocamentos do filtro são px absolutos: acima de ~32px o sulco vira um fio. */
.etched-lg {
  filter: url(#etched-onsen-lg);
}
/* Afundado = tem filtro. O gelo segue opaco: cabeçalho grudento não pode deixar a linha passar. */
.th-onsen:focus-within,
.th-onsen:has(.th-onsen-input:not(:placeholder-shown)) {
  @apply bg-none bg-agua-100/45 border-white/45 translate-y-px;
  @apply shadow-[inset_0_3px_8px_rgba(7,58,84,0.28)];
}
/* A barra começa onde a bandeja termina; quem mede a bandeja é o JS. */
.scroll-etched {
  @apply absolute right-2 w-2.5 rounded-full pointer-events-none;
  top: calc(0.5rem + var(--altura-cabecalho, 0px));
  bottom: 0.5rem;
}
```

```python
class FiltroColuna(BaseModel):
    coluna: str
    termo: str


class ConsultaServidores(BaseModel):
    filtros: list[FiltroColuna] = []
    ordenar_por: str | None = None
    descendente: bool = False


class ListarServidores:
    """Filtra e ordena as linhas já materializadas — dezenas de registros, sem ORM no domínio."""

    def __call__(
        self,
        linhas: list[LinhaServidor],
        consulta: ConsultaServidores,
    ) -> list[LinhaServidor]: ...
```

## Fora de escopo

- **Autenticação e autorização.** A rota nasce aberta, declarada aqui nos termos do §3.5; restringir
  a listagem ao perfil de administrador é a SPEC de autenticação.
- **Gravar** servidor ou unidade — a listagem é só leitura.
- **Variante horizontal da barra gravada.** Desligar a barra nativa desligou os dois eixos: em tela
  estreita a tabela ainda rola de lado por toque e trackpad, mas sem barra visível. A peça vertical
  é a que a SPEC entrega; a gêmea horizontal entra se o uso mostrar que faz falta.
- **Clique no trilho da barra** para avançar uma página, como a barra nativa faz. Roda, teclado e
  arrasto do polegar cobrem a navegação.
- **Listagem de unidades e o componente de card** — SPEC 014.
- **Paginação, seleção múltipla, edição inline, exportação.** Dezenas de registros não pedem nada
  disso.
- **Colapsar a tabela em cards no mobile.** Em tela estreita ela rola na horizontal; colapsar
  inventaria dentro desta SPEC o componente que é o entregável da 014.

## Mock de validação

`SPECS/user_admin/013-mock-tabela-de-vidro.html` — organizado em Atomic Design (tokens → átomos →
moléculas → organismo), sobre o fundo administrativo à deriva. Mostra a gravação em repouso,
entintada e aprofundada, a inversão poço/placa, a bandeja com as peças nos três estados (repouso,
afundada com filtro, gravada sem peça), a barra de rolagem gravada num poço de conteúdo qualquer, e
a tabela viva de servidores com filtro por coluna, ordenação e estado vazio.

Referência visual da gravação: `.claude/skills/componentes-frontend/references/referencia_etched_glass.jpg`
— cristal gravado a ácido, onde o traço tem gradação interna em vez de contorno. Entra na lista do §9
da skill no porte. O mock traz também a escala em que o relevo deixa de ler (a seta da tabela é de
14px por isso, não de 11px).

No mock o filtro roda no navegador para a peça ser exercitável sem servidor — a duplicação da
normalização em JavaScript está ali marcada como artifício do mock e **não** vai para a aplicação.

Exige servidor com root na raiz do projeto (Live Server); via `file://` o fetch do tema é bloqueado.

## Testes (TDD)

Os três primeiros são domínio puro, sem banco. Os três últimos carregam o marker `banco` (nem a
listagem nem o comando existem sem Postgres) — declarado em `markers_obrigatorios`. O que é visual —
o relevo, a bandeja, o comportamento da barra — se valida no mock, não em teste.

- `test_filtro_casa_texto_normalizado` — `sant anna` acha `Sant'Anna` e `sao` acha `São`: o filtro usa
  a normalização única nas duas pontas.
- `test_filtros_de_colunas_diferentes_se_somam` — termo em nome **e** em unidade devolve só quem
  atende aos dois.
- `test_ordena_por_coluna_em_ambas_as_direcoes` — a mesma coluna asc e desc devolve a lista invertida.
- `test_listagem_htmx_devolve_apenas_o_corpo_da_tabela` *(marker `banco`)* — o pedido HTMX responde o
  partial do `<tbody>`, não a página; é o que protege o campo em foco.
- `test_filtro_sem_correspondencia_devolve_estado_vazio` *(marker `banco`)* — o corpo volta com a
  linha de vazio, não com uma tabela sem linhas.
- `test_remover_ficticios_poupa_os_servidores_reais` *(marker `banco`)* — a remoção apaga a faixa de
  RF reservada e **nada além dela**; é a borda que protege o banco de quem rodar o comando distraído.

## Patches

_Nenhum patch registrado até o momento._
</content>

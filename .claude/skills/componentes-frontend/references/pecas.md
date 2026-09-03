# Peças do design system — armadilhas de uso

O catálogo **visual** do que existe é a rota `/design_system` da aplicação. Este arquivo é o
complemento que a tela não mostra: como cada peça é acionada e o que já quebrou nela.
Consulte antes de mexer numa peça existente ou de compor uma nova com ela.

## Átomos

| Átomo | Classe do DS | Sobre |
|---|---|---|
| Botão de energia (CTA) | `.btn-onsen` | gradiente `agua-300→500`, tinta escura, glow ciano |
| Botão de vidro | `.btn-glass` | gelo fosco circular/pill; ações secundárias e ícones. `bg-white/40`, hover `white/60` — um degrau abaixo da placa espessa, senão o botão encosta nela e some como figura |
| Botão de criação inline | `.btn-criar-inline` | círculo de gelo com `+` em tinta ciana ao lado de um campo: "criar agora o que falta no catálogo" |
| Input de vidro | `.input-glass` | fundo `white/30` com o **poço em repouso** (`--sombra-poco`, SPEC design/006 — campo é coisa rebaixada); no foco o poço soma o anel ciano |
| Badges de geometria | `.badge-ponto` `.badge-linha` `.badge-poligono` | tipo do resultado/camada |
| Badges semânticos | `badge-{info,success,warning,error} badge-soft` | estado do sistema (daisyUI puro) |
| Ícone com brilho | `.icon-glow` | `agua-600` + drop-shadow ciano |
| Seta de ordenação | `.sort-etched` | a gravação com alvo próprio, à direita da célula; enche de água em `aria-sort` e gira 180° em `descending` |
| Botão gravado | `.btn-etched` | a gravação em corpo de botão (o "limpar filtros"); enche de água no hover |
| Ícone gravado em botão de vidro | `.icon-etched` | o glifo dentro de um `.btn-glass`, onde quem carrega a afordância é o botão |
| Ponto da unidade | `.dot-unidade` | o `.paint-well` em escala de marca; o hex chega em `--cor-unidade` |
| Toggle de vidro | `.toggle-onsen` | trilho = poço do `.card-well` em pílula; botão = disco `.etched` que enche de água ao ir para o lado (depende dos `defs`) |
| Fio gravado / entintado | `.etched-line` / `.etched-line-inked` | a gravação num traço; **só material** — não posicionam nem dimensionam. Pontas esmaecem 20% de cada lado, e nunca até o transparente |
| Lata de lixo gravada | `.lata-concessao` | `.etched` + `.etched-deeper` parado, sobe a `.etched-inked` no hover/foco; sem crachá de botão — a linha da tabela já carrega a afordância |
| Overline | `.text-overline` | rótulo 11px caps `rocha-700` |
| Código | `.text-code` | Roboto Mono `agua-700` (SQL, codlog) |

Para criar um átomo novo: (1) confira se um componente daisyUI já resolve o comportamento;
(2) crie **uma** classe `@apply` de utilities com a pele do DS; (3) registre-o no styleguide.

## Moléculas

**Campo de seleção de vidro** (`.select-onsen`, SPEC user_admin/011): opt-in por
`data-select-onsen` no `<select>` renderizado pelo servidor. O `<select>` continua sendo o campo
(valor, envio, `change` nativo); `static/src/js/ui/select_onsen.js` monta o gatilho
(`.select-onsen-trigger`, o `.select-glass` de hoje) e a lista (`.select-onsen-panel`, gelo espesso
na top layer via `popover`). Carregue o módulo na página que usa o marcador — marcar o campo não
basta. Filtro por texto a partir de seis opções.

**Campo com criação inline** (`.form-field-inline-action`, SPEC user_admin/012): o `.form-field`
com o controle e o `.btn-criar-inline` na mesma linha — o controle estica, o botão não. O gatilho é
um `<label for>` do modal, e o modal fica **fora** do formulário (formulário aninhado é HTML
inválido).

**Tabela de vidro** (`.table-onsen`, `.table-onsen-wrap`, `.table-onsen-poco`, SPEC
user_admin/013): a **inversão dos materiais** — corpo em poço rebaixado (`.card-well`) e cabeçalho
em placa de gelo sobre ele. A caixa rola por conta própria (a viewport nunca rola na horizontal) e o
cabeçalho é grudento; a folga do poço é padding do `.card-well`, **fora** do rolador — dentro dele o
recorte do overflow deixaria aparecer uma faixa de linha nítida acima da bandeja. Com cabeçalho, essa
folga existe só **embaixo** (`pb-2`): a bandeja encosta no topo e nas laterais do poço e **atravessa**
a coluna da barra (`--coluna-barra`), onde a linha para. Poço que só rola conteúdo mantém `p-2`.
Linhas separadas **em luz**, sem zebra, e hover que **acende** o gelo.

**Tabela de vidro simples** (`.tabela-onsen-simples`, SPEC autorizacao/008): a mesma `.table-onsen`
sem `<thead>` — só linha, para uma lista curta dentro de um cartão (ex.: quem exerce uma
atribuição). Composição: `.card-well.table-onsen-poco[data-scroll-etched]` >
`.table-onsen-wrap.tabela-onsen-simples[data-rolador]` > `table.table.table-onsen > tbody`, com a
barra gravada (`.scroll-etched` + `[data-barra]`/`[data-polegar]`) como na tabela completa —
`static/src/js/ui/scroll_etched.js` esconde a barra sozinho quando cabe tudo sem rolar.
`.tabela-onsen-simples` é só a altura do rolador: **3 linhas** (2,75rem cada, da folga `py-3` +
`text-sm` da célula) cabem antes de rolar. Uma coluna à direita para ação por linha (ex.:
`.lata-concessao`) empilha essas ações na mesma posição em todas as linhas.

**Bandeja e célula de cabeçalho** (`.th-onsen-bandeja`, `.th-onsen`, `.th-onsen-campo`,
`.th-onsen-input`, `.th-onsen-gravado`): o cabeçalho é **uma superfície** — o gelo mais denso do
sistema depois do modal, `94%→86%` sobre 56px de blur, porque é a única coisa entre ele e as linhas
que correm por trás — e cada coluna é uma peça assentada sobre ela — clicar a faz **afundar** e virar campo, porque campo aqui é sempre coisa
rebaixada. **Afundado = a coluna tem filtro**, não "alguém clicou": o CSS lê o valor com
`:has(input:not(:placeholder-shown))`, sem estado de UI em JavaScript. A régua **abre inteira** (o
campo de uma coluna abre o de todas). Coluna que não responde **não tem peça**: o rótulo é gravado
direto na bandeja — a ausência da peça é a mensagem, sem cinza de desabilitado.

**Imagem de perfil** (`.avatar-glass`): o disco com a foto ou o avatar de iniciais, recortado no
círculo. A unidade **não é um anel** — é **luz atrás do disco**: um aro de contato (`--halo-aro`,
3px, na mesma transparência da imagem) e, a partir dele, dois fades que se dissolvem. Anel sólido
com `outline`/`offset` é aresta desenhada fora da caixa que a caixa não reserva: pousava sobre o
vizinho. O hex chega em `--cor-unidade` e o alcance da luz em `--halo-escala` — o padrão serve de
`w-9` a `w-16`; disco maior abre o alcance **no include**, não no token (`w-28` usa `2`, o chip do
topo `0.5`). O volume vem do domo (`::after`): a mesma **óptica simulada** do mapa (§6) — só o aro
curva, o miolo até 78% do raio é a imagem crua, e nada se distorce geometricamente. A imagem cede
um pouco ao gelo (`opacity` no **filho**, nunca no `.avatar-glass`: no pai levaria junto o halo e o
domo, que são luz).

**Linha de pessoa, tarja de vínculo e calha da cobertura** (`.linha-pessoa`, `.tarja-vinculo`
(`-pendente`/`-critica`), `.calha-cobertura*`, SPEC user_admin/015): a tarja é **placa clara
assentada dentro de um poço** — não é `.card-well`, porque poço dentro de poço perde o degrau —, e
usa o raio `--radius-placa`. A calha é o afastamento inteiro como **bandeja funda**: ela nunca se
preenche, o que muda de estado é o **fio** no fundo dela, e a régua é o **calendário** —
`left`/`width` são a fração de dias de cada trecho, calculada na orquestração (`context.py`), nunca
no domínio. Prazo indeterminado **dissolve** a ponta (`.calha-cobertura-aberta`) em vez de desenhar
um fim que não existe. Sem cor semântica no fio: quem *nomeia* o buraco é o rótulo em âmbar.

**Linha pinçada** (`.table-flutuante-clone`, `.linha-pincada`, SPEC user_admin/021): escolhida uma
unidade, a linha dela sobe até o topo da tabela. Quem desliza é um **clone** em `.glass-panel-thick`
posicionado no `.table-onsen-poco` — `<tr>` não aceita `transform` sem desmontar a grade da tabela —
e a original **apaga no lugar** (`.linha-pincada`), sem sair do fluxo: removê-la faria a tabela
inteira pular sob o clone em movimento. Raio `--radius-placa`. Par com
`static/src/js/ui/sincronia_unidades.js`, que escreve **só medida** em custom properties
(`--topo-pincagem`, `--altura-pincagem`, `--duracao-pincagem`, `--largura-coluna`) — nenhuma
declaração de pele sai do JS.

**Barra de rolagem gravada** (`.scroll-etched`, `.scroll-etched-thumb`, `.scroll-etched-ativa`,
`.scroll-etched-ociosa`): trilho sulcado e polegar de água, para **qualquer** `.card-well` rolável.
Opt-in por `data-scroll-etched` no poço, com `[data-rolador]`, `[data-barra]`, `[data-polegar]` e
`[data-cabecalho]` (opcional) dentro dele; par com `static/src/js/ui/scroll_etched.js` — carregue o
módulo na página, marcar o markup não basta. É **elemento**, não `::-webkit-scrollbar`: o pseudo não
existe no Firefox, no Chrome troca a barra flutuante por uma clássica sempre visível, e em ambos
ocupa a altura inteira do rolador (correria ao lado da bandeja). Rolar continua sendo do navegador.

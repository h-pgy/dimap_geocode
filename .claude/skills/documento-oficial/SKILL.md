---
name: documento-oficial
description: Como escrever um documento oficial do DIMAP GeoCoder — o vocabulário de blocos, a composição da marcação/papel timbrado e a conferência da amostra em services/domain/documento_oficial/. Use SEMPRE que for criar um documento oficial novo (certidão, ofício, ...), acrescentar um tipo de bloco, um papel timbrado novo ou mexer no tema do documento.
---

# Documento oficial — blocos, papel timbrado e tema

`services/domain/documento_oficial/` gera PDF de ato administrativo: título, timbre da Secretaria,
marca d'água, numeração de página. Esta skill é o **como**; o **o quê** está na SPEC
[documentos_oficiais/003](../../../SPECS/documentos_oficiais/003-documento-oficial-timbrado.md), que
por sua vez compõe o motor de PDF genérico da SPEC
[documentos_oficiais/001](../../../SPECS/documentos_oficiais/001-motor-de-pdf.md) e o motor de
tabela da SPEC [documentos_oficiais/002](../../../SPECS/documentos_oficiais/002-motor-de-tabela.md).

## 1 · O vocabulário de blocos

Um documento é `ConteudoDocumento(titulo, nome_arquivo, blocos=(...))`. Cada bloco em
`models/blocos.py` é um subtipo de `BlocoDocumento`, discriminado por `tipo`:

| Bloco | Carrega | Observação |
|---|---|---|
| `Titulo` | `texto` | um por documento, tipicamente |
| `Subtitulo` | `texto`, `nivel` (1, 2 ou 3) | nível é ESCALA do mesmo bloco — muda o corpo da fonte, não a natureza |
| `Paragrafo` | `texto`, `recuado` (bool) | recuado é para transcrição/citação |
| `Lista` | `ordenada` (bool), `itens` | um bloco por lista inteira, não por item — a numeração é a posição |
| `Tabela` | `colunas`, `cabecalho` (opcional), `linhas` | ver §2 |
| `Imagem` | `caminho` (já resolvido), `largura_mm` | SVG vetorial, nunca raster (fora de escopo da SPEC 003) |
| `QrCode` | `conteudo`, `largura_mm` | o símbolo, não o desenho — ver §8 |

Texto de bloco **nunca** vira marcação do reportlab: `escritores.py` escapa via `html.escape` antes
de montar o `Paragraph`. Célula de tabela é escapada uma vez só, pelo motor da SPEC 002 — não
escape de novo no bloco.

**Bloco novo é subtipo novo em `models/blocos.py`** (entra na união `Bloco`) **+ escritor novo em
`escritores.py`**, registrado em `montar_escritores()`. Bloco sem escritor levanta `KeyError` na
montagem, de propósito — nunca some silenciosamente do documento.

## 2 · A tabela

Declare a tabela em **colunas e linhas de texto puro**, nunca em milímetros ou `TableStyle`:

```python
Tabela(
    colunas=(ColunaFixa(largura_mm=40.0), ColunaFluida(alinhamento=Alinhamento.DIREITA)),
    cabecalho=("Campo", "Valor"),
    linhas=(("Contribuinte", "123.456.7890-1"), ("Área", "312,00 m²")),
)
```

`ColunaFixa`, `ColunaFluida` e `Alinhamento` vêm de `services.utils.pdf` (motor da SPEC 002) — a
coluna só vira medida na página, o bloco não sabe disso. O visual (fonte, corpo, grade, respiro,
fundo do cabeçalho) é **sempre do tema** (`Tema.estilo_tabela`); o documento nunca escreve
`TableStyle` nem cor solta. Linha com número de células diferente das colunas não é recusada na
construção do bloco — só na montagem do flowable (`TabelaInput` da SPEC 002), então o erro aparece
ao chamar o escritor, não ao montar o `ConteudoDocumento`.

## 3 · Escrever um documento novo

Crie um módulo ao lado de `amostra.py` (ex.: `certidao_lancamento.py`), com um `Montar<Documento>`
callable que recebe o DTO de input do caso de uso e devolve `ConteudoDocumento`. Nenhum outro
código do sistema monta blocos "na mão" fora desse módulo.

Na orquestração (view ou management command), monte tema e marcação e chame o renderizador:

```python
tema = montar_tema(build_tema_config(settings))
marcacao = marcacao_fazenda_dimap(build_marcacao_config(settings), tema)
renderizado = RenderizarDocumentoOficial(tema)(
    RenderizarDocumentoInput(conteudo=montar_meu_documento(pedido), marcacao=marcacao)
)
# renderizado.pdf: bytes: persistir/responder é de quem chamou — o domínio nunca grava em disco.
```

`RenderizarDocumentoOficial` é criado com o `Tema` — não existe singleton nem tema-constante-de-
módulo, porque o tema vem do ambiente (§5). Montar tema e marcação é barato; ainda assim monte
**uma vez por emissão**, não uma vez por bloco.

## 4 · Escolher (ou criar) o papel timbrado

`marcacoes_concretas/` é um pacote com **um módulo por papel timbrado**. Hoje só existe
`fazenda_dimap.py`. Papel novo (outra secretaria, por exemplo) é **módulo novo ao lado**, que
compõe as marcas de `marcas.py` na ordem em que se empilham — nunca edite o módulo existente para
outro papel.

As marcas de `marcas.py`: `TimbreHorizontal`, `CabecalhoUnidade`, `RodapeEndereco`, `MarcaDagua`,
`NumeracaoPaginas`, `QrCodeRodape` e as compostas `CabecalhoTimbrado` (timbre à esquerda, unidade à
direita) e `RodapeComQr` (texto empilhado à esquerda, QR à direita — ver §8). Marcas na mesma
`Posicao` **somam altura**: duas no topo empilham, e é por isso que o cabeçalho da SF é uma
composta, não duas soltas. Toda `Marcacao` declara `margem_vertical_mm` — a borda que nem as marcas
ocupam; sem ela o rodapé sai na aresta da folha e a impressora o corta.

`MarcacaoDocumento` (motor da SPEC 001) aceita:

- `principal` — obrigatória, vale onde nenhuma outra reivindica a página;
- `primeira` / `ultima` — opcionais, para capa ou encerramento com marcação diferente;
- `marcacoes_especificas` — **keyword-only**, `dict[int, Marcacao]` por número de página 1-based.

Ordem de resolução por página: número específico vence extremo, extremo vence a principal. Num
documento de uma página só, `primeira` vence `ultima`. A **orientação** (retrato/paisagem) é
propriedade da `Marcacao`; marcações do mesmo `MarcacaoDocumento` com orientações divergentes são
recusadas na construção.

## 5 · Onde cada valor mora

| Valor | Default | Ambiente sobrepõe via |
|---|---|---|
| Unidade, endereço (texto institucional) | `models/conteudo.py` (`UNIDADE_PADRAO`, `ENDERECO_PADRAO`) | `build_marcacao_config(settings)` |
| Cor, fonte, corpo, entrelinha (tema) | `models/tema.py` (`PaletaDocumento`, `TipografiaDocumento`) | `build_tema_config(settings)` |
| Caminho dos logotipos | **sem default no domínio** — depende do `BASE_DIR` | `settings.DOCUMENTO_LOGO_HORIZONTAL` / `_VERTICAL`, já com fallback pro SVG comitado |

`build_marcacao_config` e `build_tema_config` (em `config.py`) só repassam o que o ambiente
**definiu de fato** — variável ausente deixa o default do domínio valer; não redeclare um default
em `config/settings.py` que já existe no model.

## 6 · A marca d'água: nunca clareie em tempo de emissão

O SVG que `MarcaDagua` carrega precisa já estar **claro** — a emissão só o carrega, nunca o
processa. Antes de usar um SVG novo como marca d'água:

1. **Pergunte ao usuário** onde está o SVG de origem e se ele **já foi esmaecido**.
2. Se não foi, rode **uma única vez**, à mão:
   ```bash
   uv run python manage.py esmaecer_svg <caminho/do/arquivo.svg> --forca 0.85
   ```
   Isso reescreve o arquivo **no lugar**, clareando cada cor contra o branco do papel (nunca por
   opacidade — alpha composto mancha traço sobreposto). Confira o resultado antes de seguir
   (§7) e **comite o SVG claro** — é o que o repositório guarda.
   Força acima de 0,90 some no papel: 0,85 é a que o `sec_fazenda_vertical.svg` usa. Como o
   comando é destrutivo, **acertar a força depois exige o SVG saturado de volta** —
   `git show <commit>:<caminho> > <caminho>` antes de reesmaecer, nunca clarear o já claro.
3. `esmaecer_svg` nunca é chamado por código de emissão (comando, view, domínio). Se você se pegar
   chamando `esmaecer_svg`/`EsmaecerSvgInput` fora de `apps/core/management/commands/esmaecer_svg.py`,
   pare — a preparação do ativo é separada do caminho de geração de propósito (SPEC 001).

## 7 · Conferir visualmente

Depois de montar ou alterar um documento (ou o tema, ou o papel timbrado), gere uma amostra e
confira o timbre, a marca d'água, a tabela e a numeração de página a olho:

```bash
uv run pytest -m artefato
```

O teste `test_amostra_para_conferencia` imprime o caminho do PDF gerado — abra-o num leitor.
`uv run python manage.py gerar_documento_amostra <caminho>` faz o mesmo fora da suíte de testes,
gravando com os logotipos e o tema do ambiente atual (útil para provar um `.env` específico).

## 8 · QR de verificação: bloco no corpo, marca no rodapé

`services/utils/qr_code/` gera o símbolo (SVG em bytes) a partir de um `QrCodeInput(conteudo=...)`
— sempre QR padrão (nunca Micro QR), com a zona de silêncio já contada em `modulos`.
`services/utils/pdf/qr_code.py` (`qr_code_pdf`) especializa esse símbolo para o papel: recebe o
`QrCodeSvg` e a largura pedida, e devolve o `VetorNomeado` que qualquer escritor/marca planta na
página pelo mesmo caminho de imagem do motor (`carregar_vetor`, `folha.vetor`).

O que recusa, e onde:

- **Conteúdo vazio** — `QrCodeInput`/bloco `QrCode` recusam na construção (`min_length=1`).
- **Conteúdo maior do que cabe** no maior símbolo — `gerar_qr_code` levanta `ValueError` dizendo o
  tamanho, em vez de truncar.
- **Largura que deixa o módulo abaixo de `MODULO_MINIMO_MM` (0,5 mm)** — `QrCodePdfInput` recusa na
  construção, antes de qualquer render; símbolo pequeno demais sai bonito no PDF e só falha no
  celular de quem confere.

No corpo, o bloco `QrCode(conteudo, largura_mm)` entra no registro de `escritores.py`
(`EscritorQrCode`) e sai como `VetorReferenciado` — centralizado, como qualquer outro bloco. No
rodapé, `QrCodeRodape(conteudo, largura_mm)` é uma `Marca` que se encosta na borda DIREITA da
faixa; `RodapeComQr(texto, qr_code, respiro_mm)` compõe o endereço e a paginação (agrupados por
`MarcasEmpilhadas`, de `services.utils.pdf`) à esquerda da mesma faixa — o espelho do
`CabecalhoTimbrado`. `marcacao_fazenda_dimap` recebe `qr_verificacao: str | None`: `None` mantém o
pé de sempre (duas marcas soltas); uma URL troca o pé inteiro pelo `RodapeComQr`. Conferir com o
celular: `uv run pytest -m artefato` grava a amostra com o QR no corpo e no rodapé — os dois
dizem a MESMA URL, montada uma vez por `url_de_conferencia()` em `amostra.py`.

O mesmo símbolo em posições/páginas diferentes é **um Form XObject só**: `VetorNomeado` carrega o
desenho e o NOME que o identifica no arquivo (`services/utils/pdf/forma.py`), e `DesenharForma`
escreve o form na primeira ocorrência e só referencia nas demais — mecanismo do motor, não do QR;
`qr_code_pdf` só deriva o nome do hash do SVG + largura, para que conteúdos diferentes (ou larguras
diferentes do mesmo conteúdo) nunca colidam no mesmo form.

## 9 · O que NÃO fazer

- ❌ Desenhar fora de um escritor — nenhum código monta `Paragraph`/`Table`/`Drawing` fora de
  `escritores.py` (ou do escritor de um bloco novo).
- ❌ Escrever cor hex, corpo em pt ou entrelinha fora de `Tema`/`TemaConfig` — se o valor não vem de
  `self._tema`, ele não pertence a um escritor nem a uma marca.
- ❌ Chamar `esmaecer_svg` em tempo de request ou de comando de emissão — é preparação de ativo,
  feita uma vez, fora do caminho de geração (§6).
- ❌ Persistir o PDF dentro do domínio — `RenderizarDocumentoOficial` devolve `bytes`; gravar é do
  comando (`escrever_atomico`) ou responder é da view (`Content-Disposition`), nunca do domínio.
- ❌ Editar `marcacoes_concretas/fazenda_dimap.py` para outro papel timbrado — módulo novo ao lado.
- ❌ Repetir a validação de linha×coluna da tabela no bloco — ela já existe no motor da SPEC 002.
- ❌ Guardar o SVG do QR pronto num bloco/marca — ele é DERIVADO do conteúdo a cada montagem
  (§8); persistir o desenho duplicaria o mesmo dado em dois lugares.
- ❌ Montar a URL de verificação em mais de um ponto de chamada — o bloco do corpo e a marca do
  rodapé precisam dizer exatamente a mesma coisa (§8).

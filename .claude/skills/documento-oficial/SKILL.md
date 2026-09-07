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
   uv run python manage.py esmaecer_svg <caminho/do/arquivo.svg> --forca 0.93
   ```
   Isso reescreve o arquivo **no lugar**, clareando cada cor contra o branco do papel (nunca por
   opacidade — alpha composto mancha traço sobreposto). Confira o resultado antes de seguir
   (§7) e **comite o SVG claro** — é o que o repositório guarda.
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

## 8 · O que NÃO fazer

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

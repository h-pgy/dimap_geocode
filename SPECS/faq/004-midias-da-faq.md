---
spec: faq/004
versao: v5
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: vídeos saem do escopo, e a SPEC fica só com imagens
  - v3: imagem só de endereço interno, e o reenvio mantém a legenda do primeiro envio
  - v4: caminhos seguem a estrutura de pacotes de faq/001
  - v5: imagem ligada a qualquer FAQ passa a ser de uso de todo administrador, como a FAQ em faq/002, e o portão de superusuário vem de apps/core
---

# SPEC faq/004 — Mídias da resposta: imagens

## 1 · User story
O administrador do sistema ilustra as respostas da FAQ com imagens e o leitor as vê na resposta, para
que fluxos visuais do sistema sejam compreendidos sem depender apenas de texto.

## 2 · Condições de pronto
- [ ] O design da seção de imagens (imagem na resposta, arrastar e soltar no editor e modal de
      metadados) foi aprovado no mock e as peças foram portadas para o tema e o styleguide antes de o
      template da aplicação usá-las.
- [ ] Imagens embutidas via markdown (`![legenda](/faq/midias/<id>/)`) aparecem formatadas dentro da
      largura da caixa de texto; SVG, `javascript:`, `data:` e `<script>` são recusados ou removidos, e
      imagem de endereço externo não é carregada.
- [ ] Arrastar e soltar (ou selecionar) imagem (PNG/JPEG/WebP) na edição abre o modal de metadados
      exigindo a legenda (e descrição opcional) antes de enviar; cancelar não envia nada, e arquivo ou
      legenda inválida devolve erro em português.
- [ ] Reenvio do mesmo arquivo (mesmo SHA-256) não duplica o binário no banco, inclui o administrador
      em `usuarios_upload` e mantém a legenda e a descrição do primeiro envio, que o editor mostra.
- [ ] Imagem ligada só a FAQ interna ou em rascunho dá 404 para quem não pode vê-la. Na edição, o
      administrador vê a prévia e vincula qualquer imagem já ligada a alguma FAQ; imagem que não está
      em FAQ alguma, só quem a enviou.
- [ ] Editar a resposta removendo uma imagem do markdown desvincula a imagem da FAQ automaticamente.

## 3 · Domínio

A ontologia da FAQ e da `Resposta` é a de [faq/001 §3](001-pagina-de-faq.md#3--domínio), já com
`anexos` de [faq/003 §3](003-anexos-da-faq.md#3--domínio). Esta SPEC acrescenta a imagem binária
(`MidiaFaq`) referenciada pelo markdown da resposta.

```python
class MidiaFaq(BaseModel):
    """Imagem ilustrativa guardada no sistema (PNG, JPEG ou WebP). A identidade do binário é o hash SHA-256."""
    id: int | None = None
    legenda: str = Field(min_length=3, max_length=200)
    descricao: str = Field(default="", max_length=500)
    content_type: str
    nome_arquivo: str
    hash_conteudo: str = Field(pattern=r"^[0-9a-f]{64}$")
    tamanho_bytes: int = Field(gt=0)
    usuarios_upload_ids: list[int] = []


# ALTERADO nesta SPEC: `Resposta` (faq/003) ganha `midias_referenciadas`.
class Resposta(BaseModel):
    markdown: str = Field(min_length=1)         # pode referenciar /faq/midias/<id>/
    links: list[LinkReferencia] = []
    anexos: list[int] = []

    @field_validator("markdown", mode="before")
    @classmethod
    def _nao_vazia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("A resposta não pode ficar em branco.")
        return valor

    @computed_field
    @property
    def midias_referenciadas(self) -> list[int]:
        return extrair_ids_midia_markdown(self.markdown)
```

**Mock:** [004-mock-midias-da-faq.html](004-mock-midias-da-faq.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Embeddings multimodais das imagens — faq/005.
- Contenção de imagens dentro do painel do widget flutuante — faq/006.
- Limpeza de imagens órfãs (enviadas e depois descartadas antes de salvar) — sem dono ainda.
- Vídeos na resposta (MP4 enviado ou importado do YouTube) — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/markdown` → `RenderizadorMarkdown` (faq/001): estendido no §6 para liberar `<img>`.
- `@services/domain/faq/leitura/visibilidade.py` → `eh_visivel` (faq/001): base da regra de visibilidade da imagem.
- `@apps/core/acesso.py` → `superusuario_requerido` (faq/002): portão da rota de envio.
- `@apps/faq/anexos/recebimento.py` → padrão de `bytea` deduplicado por SHA-256 (faq/003).
- `Pillow` (já é dependência) → conferência de integridade e formato real das imagens.
- Skills: `ontologia`, `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx-skill`,
  `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`services/domain/faq/arquivos/midia.py`** — validação pura da imagem e extração de referências (o limite vem
do app a partir de `FAQ_IMAGEM_TAMANHO_MAXIMO_BYTES`, padrão 5 MB).

```python
def validar_imagem(conteudo: bytes, limite_bytes: int) -> str:
    # Pillow `Image.open(...).verify()` confirma PNG/JPEG/WEBP; SVG e HTML são recusados (XSS).
    ...


def extrair_ids_midia_markdown(texto: str) -> list[int]:
    # Percorre tokens `image` do MarkdownIt: ignora blocos de código e texto corrido.
    ...
```

**`services/utils/markdown/renderizador.py`** — estende o renderizador de faq/001: `"img"` entra em
`TAGS_PERMITIDAS`, `{"src", "alt", "title"}` em `attributes["img"]`, e um `attribute_filter` do `nh3`
só deixa passar o `src` que aponta para imagem do próprio sistema. O padrão chega pelo construtor
(`RenderizadorMarkdown(src_imagem=...)`), porque o utilitário não conhece a FAQ; sem ele, `<img>`
continua fora, como em faq/001. O filtro `markdown` do template passa `PADRAO_SRC_IMAGEM`.

```python
PADRAO_SRC_IMAGEM = re.compile(r"^/faq/midias/\d+/$")     # apps/faq/midias/urls.py: o endereço de `faq:midia_exibir`


def _filtrar_atributo(self, tag: str, atributo: str, valor: str) -> str | None:
    # Imagem externa sai sem `src`: a página não carrega nada de fora (rastreio do leitor, conteúdo
    # trocado depois da revisão).
    if tag == "img" and atributo == "src" and not self._src_imagem.fullmatch(valor):
        return None
    return valor
```

**`services/domain/faq/leitura/visibilidade.py`** e **`services/domain/faq/edicao/autoria.py`** —
estendem os dois módulos de faq/001 e faq/002. Todo administrador edita toda FAQ (faq/002), então a
imagem já ligada a uma FAQ, de qualquer situação, é de uso de todos; a que não está em FAQ alguma
(enviada numa edição não salva) é só de quem a enviou.

```python
def midia_eh_visivel(faqs_da_midia: list[Faq], leitor: Leitor) -> bool:
    return any(eh_visivel(f, leitor) for f in faqs_da_midia)


def pode_usar_midia(midia: MidiaFaq, faqs_ligadas: list[Faq], editor: Editor) -> bool:
    # `faqs_ligadas` inclui as excluídas: a restauração devolve a FAQ com a imagem.
    return editor.perfil_id in midia.usuarios_upload_ids or bool(faqs_ligadas)
```

**`apps/faq/models/arquivos.py`**

```python
class MidiaFaq(models.Model):
    legenda = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, default="")
    content_type = models.CharField(max_length=40)
    nome_arquivo = models.CharField(max_length=255)
    arquivo = models.BinaryField()
    hash_conteudo = models.CharField(max_length=64, unique=True)
    tamanho_bytes = models.PositiveIntegerField()
    usuarios_upload = models.ManyToManyField("user_admin.Perfil", blank=True, related_name="midias_faq")
    enviado_em = models.DateTimeField(auto_now_add=True)

# `Faq` (apps/faq/models/conteudo.py) ganha:
# midias = models.ManyToManyField("faq.MidiaFaq", blank=True, related_name="faqs")
```

**`apps/faq/midias/recebimento.py`** — `receber_midia` valida a imagem com `validar_imagem` e deduplica por
`hash_conteudo`, adicionando `editor.perfil_id` em `usuarios_upload` quando o arquivo já existe. No
reenvio, a legenda e a descrição digitadas no modal são descartadas, como o título do anexo reenviado
em faq/003, e o partial devolve a legenda que ficou, que é a que o editor insere no `![...]`.
`gravar_faq` (`apps/faq/conteudo/cadastro.py`) e `regravar_faq` (`apps/faq/gestao/cadastro.py`) passam a validar `pode_usar_midia` e a sincronizar
`registro.midias` com `resposta.midias_referenciadas`.

**Rotas e interface (`apps/faq/midias/urls.py` e `views.py` + `static/src/js/editor_markdown.js`):**

| Rota | Acesso | Comportamento |
|---|---|---|
| `faq:midia_exibir` | aberta / preview admin | checa `midia_eh_visivel` (ou `pode_usar_midia` para superusuário) e responde a imagem com o `content_type` gravado |
| `faq:admin_midia_enviar` | `superusuario_requerido` | recebe arquivo + `legenda` + `descricao` do modal de arrastar e soltar; devolve partial HTML com `data-midia-url` e `data-midia-legenda` para o Milkdown |

O arrastar e soltar é a única entrada de imagem no editor: o bloco de imagem do próprio Crepe, que
aceitaria endereço externo, está desligado desde faq/002.

## 7 · Caveats

**Imagens ficam em `bytea` no Postgres.** Guardar na linha segue o padrão de documentos e anexos e
evita operar storage externo na escala do sistema. O custo é cada exibição ler a imagem inteira do
banco, limitada por `FAQ_IMAGEM_TAMANHO_MAXIMO_BYTES`.

**A imagem enviada e depois removida do texto, ou enviada numa edição que não foi salva, fica órfã no
banco.** Não há rotina de coleta de lixo ainda. Ela segue inacessível ao público (`midia_eh_visivel`
exige FAQ visível vinculada) até existir limpeza.

**Quem reenvia o mesmo arquivo passa a poder usar a imagem, mesmo que ela ainda não esteja em FAQ
alguma.** Ele já tem os bytes, então o que se revela é só a legenda do primeiro envio. Não
há rota que altere a imagem depois de enviada, e por isso estar em `usuarios_upload` dá direito de uso,
não de edição. Quem esperava outra legenda no reenvio não consegue trocá-la; renomear fica sem dono.

**O arrastar e soltar segura o `File` no navegador durante o modal e lê `data-midia-*` do partial
HTML.** Navegadores não permitem preencher `<input type="file">` por script após um drop, e retornar
HTML em vez de JSON preserva o HATEOAS do CLAUDE.md §3.1.

## 8 · Testes (TDD)
- `test_markdown_permite_imagem_e_barra_xss_e_svg` — `![legenda](/faq/midias/1/)` gera `<img>`,
  `![x](https://externo.com/x.png)` sai sem `src`, e `<script>`, `onerror=`, `javascript:`, `data:` e
  upload de SVG são recusados.
- `test_validacao_imagem_pelos_bytes` — Pillow aceita PNG/JPEG/WebP e recusa falso positivo e arquivo
  acima do limite.
- `test_extrair_ids_midia_ignora_blocos_de_codigo` — links `/faq/midias/<id>/` dentro de cercas de
  código markdown não entram em `midias_referenciadas`.
- `test_midia_respeita_visibilidade` — imagem ligada só a interna ou rascunho dá 404 para anônimo;
  ligada a FAQ pública publicada é entregue com o `content_type` gravado. *(marker `banco`)*
- `test_upload_drag_and_drop_exige_legenda_deduplica_e_isola_orfa` — envio sem `legenda` devolve
  erro em português; reenvio do mesmo arquivo com outra legenda inclui o segundo admin em
  `usuarios_upload` e devolve a legenda do primeiro envio; imagem do rascunho de outro admin é aceita
  na gravação, e imagem que não está em FAQ alguma, enviada por outro, é recusada. *(marker `banco`)*
- `test_editar_resposta_atualiza_vinculos_de_imagens` — remover imagem do markdown desvincula
  `Faq.midias`. *(marker `banco`)*

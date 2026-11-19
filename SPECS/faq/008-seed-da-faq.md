---
spec: faq/008
versao: v2
atualizado_em: 2026-11-19
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a FAQ da seed guarda o próprio id_seed e, sendo do sistema, não é excluível
---

# SPEC faq/008 — Seed da FAQ

> **Esta SPEC começa por uma conversa.** O conteúdo da seed (quais FAQs, as respostas, as capturas de
> tela) não é decidido pelo agente sozinho: segue o roteiro do [§9](#9--roteiro-do-conteúdo).

## 1 · User story
O servidor da DIMAP, ou o cidadão sem login, encontra a FAQ já povoada com as dúvidas básicas, e
ilustrada com as telas do sistema, desde a primeira subida, sem esperar que o administrador escreva
tudo do zero.

## 2 · Condições de pronto
- [ ] A lista de FAQs da seed, as respostas e as capturas de tela foram definidas em conversa com o
      usuário e revisadas por ele antes de entrar em `data/seed/`.
- [ ] Nenhuma captura da seed mostra dado pessoal real (nome ou CPF de contribuinte, nome de servidor).
- [ ] `seed_faq` carrega os temas, as FAQs, as imagens e os vínculos de tela de `data/seed/` e, rodado
      de novo, não duplica nem altera nada.
- [ ] A imagem da seed aparece na resposta igual a uma enviada pelo editor, com a legenda como texto
      alternativo. Uma imagem idêntica já enviada por um administrador não é duplicada.
- [ ] Uma FAQ da seed que o administrador editou ou despublicou não é sobrescrita nem republicada pela
      carga seguinte, e uma FAQ nova do JSON cuja pergunta já está em uso é pulada com aviso, sem
      derrubar a carga.
- [ ] Um arquivo inválido (subtema de subtema, imagem inexistente, tela não declarada) aborta a carga
      com a mensagem do erro, e nada é gravado.
- [ ] Cada FAQ da seed é encontrada pelo fallback textual da busca a partir de cada uma das suas
      variações.
- [ ] Subir o container carrega a FAQ da seed, depois do administrador do sistema.

## 3 · Domínio

A ontologia da FAQ é a de [faq/001](001-pagina-de-faq.md#3--domínio), com `Resposta` estendida por
[faq/003](003-anexos-da-faq.md#3--domínio) e [faq/004](004-midias-da-faq.md#3--domínio) e `Faq.telas`
de [faq/006](006-faq-da-tela.md#3--domínio). Esta SPEC pergunta a ela como uma FAQ do sistema
(`autor_id = None`, editável e não excluível por [faq/002](002-edicao-de-faq.md#3--domínio)) nasce a
partir de um arquivo versionado. O arquivo tem modelo próprio: a FAQ é
identificada por um slug estável, e as imagens, as relacionadas e o tema são referências por nome,
resolvidas na carga.

```python
class TemaSeed(BaseModel):
    """Chave natural: (nome, pai)."""
    nome: str = Field(min_length=2, max_length=80)
    pai: str | None = None
    ordem: int = 0


class ImagemSeed(BaseModel):
    """Captura de tela versionada em data/seed/faq_imagens/."""
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    arquivo: str                                   # relativo a data/seed/faq_imagens/
    legenda: str = Field(min_length=3, max_length=200)
    descricao: str = Field(default="", max_length=500)


class FaqSeed(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")       # slug estável, nunca reaproveitado
    tema: list[str] = Field(min_length=1, max_length=2)   # [tema] ou [tema, subtema]
    pergunta: str
    variacoes: list[str] = []
    palavras_chave: list[str] = []
    visibilidade: Visibilidade = Visibilidade.PUBLICA
    resposta: str                                  # markdown; imagem como ![](midia:<id da ImagemSeed>)
    links: list[LinkReferencia] = []
    relacionadas: list[str] = []                   # ids de outras FaqSeed
    telas: list[str] = []                          # nome_rota (faq/006)


class ArquivoSeedFaq(BaseModel):
    temas: list[TemaSeed]
    imagens: list[ImagemSeed] = []
    faqs: list[FaqSeed]

    @model_validator(mode="after")
    def _referencias_fechadas(self) -> Self:
        # ids únicos; todo tema, relacionada e `midia:` citado existe no próprio arquivo; e todo
        # `midia:` do markdown está na forma ![](midia:<id>).
        ...
```

## 4 · Fora de escopo
- Anexos (PDF/DOCX) nas FAQs da seed — sem dono ainda; entra nesta SPEC, com versão nova, se a conversa
  do §9 pedir.
- Atualizar no banco uma FAQ da seed já carregada a partir do JSON — sem dono; a mudança é feita pela
  edição de faq/002.
- Retirar do sistema uma FAQ da seed que ficou obsoleta — sem dono; hoje ela só é despublicada.

## 5 · Peças de referência a compor
- `@apps/faq/cadastro.py` → `gravar_faq` (faq/001, estendida em faq/004 e faq/006): a única porta de escrita.
- `@services/domain/faq/midia.py` → `validar_imagem` (faq/004): formato e tamanho das capturas.
- `@apps/faq/telas.py` → `telas_declaradas` (faq/006) e `@services/domain/faq/telas.py` → `conferir_telas`.
- `@services/domain/faq/busca_textual.py` → fallback textual e `LIMIAR_SCORE_FUZZY` (faq/007).
- `@apps/cargos/seeds` → padrão de carga, contagem e `dry_run` do projeto.
- `@docker/run_seeds.sh` → a ordem das seeds na subida.
- Skills: `seeds`, `management-commands`, `escrever-testes`, `claude-in-chrome` (capturas do §9).

## 6 · Snippets

> O comentário didático destes blocos existe só aqui e **não é portado** (CLAUDE.md §7.2).

**`apps/faq/models.py`** — `Faq` ganha o slug da seed. A FAQ do sistema nunca é excluída (faq/002),
então a linha que carrega o `id_seed` existe para sempre.

```python
# Faq ganha:
id_seed = models.CharField(max_length=60, unique=True, null=True, blank=True)

# e, em Meta.constraints, a FAQ do sistema passa a ter definição no banco:
models.CheckConstraint(
    # Sem autor ⇔ veio da seed. Nenhuma FAQ do administrador fica sem autor, e nenhuma da seed ganha um.
    condition=Q(autor__isnull=True, id_seed__isnull=False) | Q(autor__isnull=False, id_seed__isnull=True),
    name="faq_do_sistema_vem_da_seed",
)
```

**`data/seed/faq.json`** + **`data/seed/faq_imagens/`** — as FAQs da seed nascem `publicada`, com
`autor_id = None`. O conteúdo real sai da conversa do §9; o bloco abaixo só mostra a forma.

```json
{
  "temas": [
    {"nome": "Busca", "ordem": 1},
    {"nome": "Endereço", "pai": "Busca", "ordem": 1}
  ],
  "imagens": [
    {
      "id": "busca-endereco-sugestoes",
      "arquivo": "busca-endereco-sugestoes.webp",
      "legenda": "Sugestões de endereço abaixo da barra de busca"
    }
  ],
  "faqs": [
    {
      "id": "busca-endereco",
      "tema": ["Busca", "Endereço"],
      "pergunta": "Como busco um endereço?",
      "variacoes": ["Onde digito o endereço para localizar no mapa?"],
      "palavras_chave": ["endereço", "número", "geocodificação"],
      "visibilidade": "publica",
      "resposta": "Digite o logradouro e o número na **barra de busca**...\n\n![](midia:busca-endereco-sugestoes)",
      "links": [],
      "relacionadas": ["busca-codlog"],
      "telas": ["search:busca"]
    }
  ]
}
```

**Inventário da seed** — preenchido na conversa do §9. Preenchida a tabela, a SPEC sobe de versão.

| id | Tema / subtema | Pergunta | Visibilidade | Telas | Capturas |
|---|---|---|---|---|---|
| _a definir com o usuário_ | | | | | |

**`apps/faq/seeds/faq.py`** — segue a skill `seeds`, com um desvio: a FAQ da seed é editável pelo
administrador (faq/002), inclusive a pergunta, então "já existe" é decidido pelo `id_seed`, e não pela
busca da pergunta no banco.

```python
REFERENCIA_IMAGEM = re.compile(r"!\[\]\(midia:(?P<id>[a-z0-9-]+)\)")


def _carregar_faqs(arquivo: ArquivoSeedFaq, aviso: Callable[[str], None]) -> dict[str, int]:
    ja_carregadas = set(FaqModel.objects.filter(id_seed__isnull=False).values_list("id_seed", flat=True))
    declaradas = telas_declaradas()
    imagens = {i.id: i for i in arquivo.imagens}
    criadas: dict[str, int] = {}
    for item in arquivo.faqs:
        if item.id in ja_carregadas:
            continue                     # editada ou despublicada depois da carga: o banco manda
        if _alguma_formulacao_ocupada(item):
            # Pular, e não abortar: a carga roda a cada subida, e uma FAQ do admin não pode derrubá-la.
            aviso(f"FAQ '{item.id}' pulada: a pergunta ou uma variação já é de outra FAQ.")
            continue
        conferir_telas(item.telas, declaradas)        # tela fora do código aborta a carga inteira
        markdown = _resolver_imagens(item.resposta, imagens)
        # editor=None: carga do sistema. Dispensa `pode_usar_midia`, porque a imagem veio do próprio
        # arquivo, nesta transação (Caveats).
        criadas[item.id] = gravar_faq(
            _como_dto(item, markdown, _temas_de(item)),
            editor=None,
            id_seed=item.id,
        )
    return criadas


def _resolver_imagens(markdown: str, imagens: dict[str, ImagemSeed]) -> str:
    def _trocar(achado: re.Match[str]) -> str:
        midia = _midia_persistida(imagens[achado["id"]])
        # A legenda é a da MidiaFaq gravada: se o binário já existia, vale a do primeiro envio (faq/004).
        return f"![{midia.legenda}]({reverse('faq:midia_exibir', args=[midia.pk])})"
    return REFERENCIA_IMAGEM.sub(_trocar, markdown)


def _midia_persistida(imagem: ImagemSeed) -> MidiaFaqModel:
    # Lê o arquivo, passa por `validar_imagem` (faq/004) e deduplica pelo SHA-256. A MidiaFaq criada
    # aqui não tem `usuarios_upload`: é do sistema, como a FAQ.
    ...
```

Os temas e as imagens são criados só quando uma FAQ nova da carga precisa deles; os temas em duas
passadas (raiz, depois subtema). As relacionadas são ligadas pelo `id` do JSON, **só entre as FAQs
criadas nesta carga**. Tudo roda num único `transaction.atomic()`. O `seed_faq` entra no
`docker/run_seeds.sh`, depois do `seed_admin`. As FAQs carregadas entram no índice semântico pelo
ciclo normal do indexador de faq/005.

## 7 · Caveats

**A seed reconhece a FAQ pelo `id_seed` gravado nela, e não pela chave natural.** Pela pergunta, uma FAQ
da seed com a pergunta trocada seria recriada e bateria no UNIQUE da antiga, que virou variação. O
custo: uma FAQ da seed apagada direto no banco volta na carga seguinte, e a FAQ pulada por pergunta
ocupada só deixa rastro no aviso do stdout.

**As FAQs e as imagens da seed não têm autor.** Elas são bootstrap do sistema, e nenhum superusuário
existe com certeza no momento da carga. Toda FAQ do sistema é editável por qualquer superusuário e
excluível por nenhum (faq/002), e toda imagem dela, utilizável por qualquer um.

**A seed grava pela porta única com `editor=None` e `id_seed`, o que dispensa `pode_usar_midia`.** A regra de faq/004
protege a imagem de outro administrador, e a imagem da seed nasce na mesma transação, do próprio
arquivo. Qualquer chamada futura a `gravar_faq` com `editor=None` passa sem essa conferência, e só a
seed pode fazê-lo.

**As capturas de tela são binários versionados no git e envelhecem com a interface.** A ajuda visual
precisa existir desde a primeira subida, e o repositório é o único lugar versionado de onde a seed lê.
O repositório cresce alguns MB, e uma tela redesenhada deixa a captura desatualizada; editar o JSON não
propaga ao banco já carregado, e a troca é feita pela edição de faq/002.

**O teste de conteúdo amarra o JSON ao código.** Ele confere telas declaradas, imagens válidas e o
fallback textual sobre o arquivo real. Renomear uma rota, apertar `LIMIAR_SCORE_FUZZY` ou trocar a
normalização quebra a suíte até o JSON ser ajustado.

## 8 · Testes (TDD)
- `test_seed_faq_cria_e_nao_toca_o_que_existe` — carrega hierarquia de temas, formulações, links,
  relacionadas e telas; recarregar com o JSON alterado não duplica nem reescreve. *(marker `banco`)*
- `test_seed_faq_grava_imagem_e_troca_a_referencia` — `![](midia:x)` sai como
  `![<legenda>](/faq/midias/<id>/)`, a MidiaFaq fica ligada à FAQ sem `usuarios_upload` e é entregue ao
  anônimo; com o mesmo binário já enviado por um administrador, a carga reaproveita a MidiaFaq e a
  legenda dela. *(marker `banco`)*
- `test_seed_faq_respeita_edicao_do_admin` — com uma FAQ da seed de pergunta trocada (a antiga virou
  variação) e outra despublicada, a carga seguinte não recria, não reescreve e não republica nenhuma
  das duas, e não aborta. Uma FAQ nova do JSON com pergunta já usada por FAQ do administrador é pulada
  com aviso, e as demais entram. *(marker `banco`)*
- `test_seed_faq_invalida_aborta_sem_gravar` — parametrizado: subtema de subtema, `midia:` sem
  imagem, arquivo de imagem ausente e tela não declarada abortam a carga, e nenhum tema, imagem nem FAQ
  persiste; `dry_run=True` também não persiste nada. *(marker `banco`)*
- `test_seed_real_eh_coerente` — sobre o `data/seed/faq.json` real: o arquivo valida, toda tela está
  em `telas_declaradas()`, toda imagem existe e passa por `validar_imagem`, e cada variação acha a
  própria FAQ no fallback textual de faq/007.

## 9 · Roteiro do conteúdo

O mecanismo (§6) é aprovado com a SPEC; o conteúdo é decidido com o usuário, nesta ordem:

1. **Inventário.** O agente levanta, a partir do que as SPECs marcam como `implementado: true`, as
   telas declaradas (faq/006) e as ações do painel, uma lista candidata de temas e perguntas, e a
   apresenta ao usuário. Nada é escrito no JSON antes da conversa.
2. **Conversa.** Usuário e agente decidem, FAQ por FAQ: se entra, tema e subtema, visibilidade
   (pública ou interna), variações, telas vinculadas, relacionadas, e quais respostas pedem captura de
   tela — de qual tela, em qual estado (gaveta aberta, desenho selecionado, zoom) e com qual dado de
   exemplo. O resultado preenche o inventário do §6, e a SPEC sobe de versão.
3. **Capturas.** Para cada captura, o agente descreve o que ela deve mostrar. A forma de capturar é
   combinada na conversa: o agente pelo navegador (skill `claude-in-chrome`, com o app local e dados
   de exemplo) ou o usuário, que salva o arquivo em `data/seed/faq_imagens/`. Regras: WebP ou PNG,
   dentro de `FAQ_IMAGEM_TAMANHO_MAXIMO_BYTES`, sem dado pessoal real, com a legenda escrita junto.
4. **Redação.** O agente escreve as respostas em `data/seed/faq.json`, já com as referências
   `![](midia:<id>)`.
5. **Revisão.** O usuário revisa respostas e capturas; só então o `test_seed_real_eh_coerente` vale
   como prova de pronto.

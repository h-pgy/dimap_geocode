---
spec: documentos_oficiais/006
versao: v1
atualizado_em: 2026-09-07
testes_tdd: false
implementado: false
markers_obrigatorios: [artefato]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/006 — Selo de integridade do PDF

## 1 · User story
**Requisito não-funcional** — todo PDF emitido carrega um selo que denuncia a alteração de um único
byte, e que se confere **só com o arquivo**, sem consultar banco nem rede.

## 2 · Condições de pronto
- [ ] Selar um PDF devolve outro PDF, de mesmo tamanho em bytes, que abre em qualquer leitor com o
      mesmo conteúdo visível.
- [ ] Conferir um PDF selado, **sem nada além do arquivo e do segredo**, devolve selo íntegro.
- [ ] Virar **um único byte** em qualquer ponto do arquivo — texto, imagem ou envelope — faz a
      conferência acusar selo violado.
- [ ] Conferir com segredo diferente do que selou acusa selo violado.
- [ ] PDF que nunca foi selado é acusado como **sem selo**, e não confundido com selo violado.
- [ ] O envelope volta da conferência com os mesmos valores que entraram, acentuação incluída.
- [ ] A conferência devolve **apenas os campos declarados públicos**; o envelope inteiro só sai para
      quem o pede explicitamente.
- [ ] Selar um documento que **já traz selo** é recusado.
- [ ] Dados que trazem a chave `tag` são recusados na construção do pedido.

## 3 · Domínio
`services/utils/assinatura/` não modela domínio: é o vocabulário do **selo** — os bytes de um PDF, um
mapa de dados opaco e a marca que prova que os dois não mudaram desde a emissão. Ele não sabe o que é
ação, ato ou certidão; quem dá sentido aos dados é a SPEC [documentos_oficiais/007](007-envelope-do-ato-e-selo-no-papel.md).

**`services/utils/assinatura/models.py`**
```python
class EstadoSelo(StrEnum):
    """Os três estados que o ARQUIVO sozinho consegue distinguir. Saber se o documento existe, ou se
    ainda vale, exige o acervo — e é da SPEC 008."""

    INTEGRO = "integro"
    VIOLADO = "violado"
    SEM_SELO = "sem_selo"


class SelarInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf: bytes
    # Opaco de propósito: o utilitário sela o que lhe derem, e não conhece a forma do que sela.
    dados: dict[str, Any]
    # Os nomes das chaves de `dados` que a conferência devolve. O que fica de fora não é secreto —
    # continua legível no arquivo (Caveats); é só o que a tela não mostra.
    campos_publicos: tuple[str, ...] = ()
    # `SecretStr` para o segredo não vazar em repr, log de exceção nem traceback.
    segredo: SecretStr
    id_chave: str

    @field_validator("dados")
    @classmethod
    def _sem_chave_reservada(cls, valor: dict[str, Any]) -> dict[str, Any]:
        if CHAVE_TAG in valor:
            raise ValueError(f"`{CHAVE_TAG}` é do mecanismo do selo e não pode vir nos dados.")
        return valor


class DocumentoSelado(BaseModel):
    """O arquivo pronto e o que ficou escrito dentro dele. `tag` sai junto para quem quiser guardá-la
    ao lado do arquivo — o selo, porém, se confere pelo arquivo, nunca pela cópia."""

    model_config = ConfigDict(frozen=True)

    pdf: bytes
    envelope: dict[str, Any]
    tag: str


class ConferirInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf: bytes
    segredo: SecretStr


class ResultadoConferencia(BaseModel):
    """`envelope` e `publicos` vêm nulos quando não há selo: sem envelope não há o que devolver.
    Quando o selo está VIOLADO os dois vêm preenchidos — o que está escrito ali é justamente o que
    permite localizar o original."""

    model_config = ConfigDict(frozen=True)

    estado: EstadoSelo
    envelope: dict[str, Any] | None = None
    publicos: dict[str, Any] | None = None
```

## 4 · Fora de escopo
- O envelope do ato administrativo — o que as chaves significam é da SPEC
  [documentos_oficiais/007](007-envelope-do-ato-e-selo-no-papel.md).
- O quadro impresso no papel — SPEC [documentos_oficiais/007](007-envelope-do-ato-e-selo-no-papel.md).
- O acervo, a segunda via e a tela de conferência — SPEC
  [documentos_oficiais/008](008-acervo-e-conferencia.md).
- Revogação do documento emitido — sem dono ainda.
- Mais de um segredo vivo ao mesmo tempo: `id_chave` fica escrito no envelope, mas a conferência usa
  o único segredo configurado — sem dono ainda.
- Assinatura assimétrica, PAdES e ICP-Brasil — sem dono ainda.
- Selar formato que não seja PDF — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/pdf/documento.py` → `gerar_pdf`: os bytes que entram no selo.
- `@services/utils/qr_code/gerador.py` → `GerarQrCode`: a forma de um callable de utilitário —
  `__call__` fino, `pipeline` orquestrando os passos.
- `@tests/conftest.py` → `publicar_artefato`: grava o artefato fora do repositório e imprime o caminho.
- Skills: `ontologia`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/utils/assinatura/constants.py`**
```python
# O envelope inteiro cabe numa chave do dicionário `/Info` do PDF.
CHAVE_METADADO = "/DimapAssinatura"
CHAVE_TAG = "tag"
ALGORITMO = "HMAC-SHA256"
# A tag é o hexdigest do SHA-256: 64 caracteres, sempre.
TAMANHO_TAG = 64
# Sessenta e quatro zeros. O que o arquivo carrega ENQUANTO a tag está sendo calculada — e o que
# volta ao lugar dela para a conferência refazer a conta.
PLACEHOLDER = "0" * TAMANHO_TAG
```

**`services/utils/assinatura/envelope.py`** — a costura com o PDF, e o único ponto do projeto que
conhece `pypdf`. Guardar em `/Info`, e não em stream próprio, é o que faz o envelope sobreviver a
leitura por qualquer biblioteca.
```python
class EmbutirEnvelope:
    """Callable: bytes + envelope → bytes com o envelope no `/Info`."""

    def __call__(self, pdf: bytes, envelope: dict[str, Any]) -> bytes:
        return self.pipeline(pdf, envelope)

    def pipeline(self, pdf: bytes, envelope: dict[str, Any]) -> bytes:
        escritor = PdfWriter()
        escritor.append_pages_from_reader(PdfReader(BytesIO(pdf)))
        escritor.add_metadata({CHAVE_METADADO: self._serializar(envelope)})
        buffer = BytesIO()
        escritor.write(buffer)
        return buffer.getvalue()

    def _serializar(self, envelope: dict[str, Any]) -> str:
        # `ensure_ascii=True` mantém o envelope em ASCII puro mesmo com acento no nome do servidor:
        # é o que garante que os 64 dígitos da tag entrem no arquivo como texto simples, e não
        # dentro de uma string reencodada. `sort_keys` deixa o envelope legível e estável no diff.
        return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def ler_envelope(pdf: bytes) -> dict[str, Any] | None:
    metadados = PdfReader(BytesIO(pdf)).metadata
    if metadados is None or CHAVE_METADADO not in metadados:
        return None
    return json.loads(metadados[CHAVE_METADADO])
```

**`services/utils/assinatura/selo.py`** — o mecanismo. A tag mora **dentro** do arquivo que ela
assina; o placeholder é o que desfaz essa circularidade.
```python
class SelarDocumento:
    """Callable: um PDF entra, o mesmo PDF selado sai. A tag cobre o arquivo INTEIRO — texto,
    fontes, imagens e o próprio envelope —, e não o texto extraído: mapa e brasão também precisam
    estar cobertos."""

    def __call__(self, pedido: SelarInput) -> DocumentoSelado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SelarInput) -> DocumentoSelado:
        self._recusar_se_ja_selado(pedido.pdf)
        envelope = self._envelope(pedido)
        # 1. o arquivo fechado, com a tag ainda em branco;
        base = embutir_envelope(pedido.pdf, envelope)
        posicao = localizar_unica(base, PLACEHOLDER)
        # 2. a tag calculada sobre ESSE arquivo;
        tag = calcular_tag(base, pedido.segredo)
        # 3. a tag no lugar do placeholder, sem mudar um byte de tamanho — o que faz a conferência
        #    poder desfazer o passo e chegar de volta em `base`.
        return DocumentoSelado(
            pdf=trocar(base, posicao, tag),
            envelope={**envelope, CHAVE_TAG: tag},
            tag=tag,
        )

    def _envelope(self, pedido: SelarInput) -> dict[str, Any]:
        return {
            **pedido.dados,
            "alg": ALGORITMO,
            "id_chave": pedido.id_chave,
            "campos_publicos": list(pedido.campos_publicos),
            CHAVE_TAG: PLACEHOLDER,
        }

    def _recusar_se_ja_selado(self, pdf: bytes) -> None:
        # Selar duas vezes deixaria duas tags no arquivo e nenhuma conferível: a segunda cobriria
        # bytes que a primeira já alterou.
        if ler_envelope(pdf) is not None:
            raise ValueError("Este PDF já traz selo: sele o documento recém-gerado, não o selado.")


class ConferirSelo:
    """Callable: bytes → o que o arquivo sozinho consegue afirmar. Não consulta banco, rede nem
    relógio: é isso que faz o selo valer com o acervo fora do ar."""

    def __call__(self, pedido: ConferirInput) -> ResultadoConferencia:
        return self.pipeline(pedido)

    def pipeline(self, pedido: ConferirInput) -> ResultadoConferencia:
        envelope = ler_envelope(pedido.pdf)
        if envelope is None or CHAVE_TAG not in envelope:
            return ResultadoConferencia(estado=EstadoSelo.SEM_SELO)
        return ResultadoConferencia(
            estado=self._estado(pedido, envelope),
            envelope=envelope,
            publicos=self._publicos(envelope),
        )

    def _estado(self, pedido: ConferirInput, envelope: dict[str, Any]) -> EstadoSelo:
        tag = envelope[CHAVE_TAG]
        base = trocar(pedido.pdf, localizar_unica(pedido.pdf, tag), PLACEHOLDER)
        # `compare_digest`, e não `==`: comparação que sai no primeiro byte diferente mede o quanto
        # a tag tentada acertou.
        if not hmac.compare_digest(calcular_tag(base, pedido.segredo), tag):
            return EstadoSelo.VIOLADO
        return EstadoSelo.INTEGRO

    def _publicos(self, envelope: dict[str, Any]) -> dict[str, Any]:
        declarados = envelope.get("campos_publicos", [])
        return {chave: envelope[chave] for chave in declarados if chave in envelope}


def calcular_tag(pdf: bytes, segredo: SecretStr) -> str:
    # HMAC, e não `sha256(segredo + bytes)`: SHA-256 é Merkle–Damgård e o hash com prefixo secreto
    # admite extensão de mensagem sem conhecer o segredo.
    return hmac.new(
        segredo.get_secret_value().encode(),
        pdf,
        hashlib.sha256,
    ).hexdigest()


def localizar_unica(pdf: bytes, agulha: str) -> int:
    """Onde estão, no arquivo, os 64 caracteres da tag. Procurar os bytes, em vez de gravar o
    deslocamento: gravá-lo mudaria o arquivo e, com ele, o próprio deslocamento."""
    bytes_agulha = agulha.encode()
    ocorrencias = pdf.count(bytes_agulha)
    # Uma ocorrência é o contrato do mecanismo. Zero ou duas viram erro AQUI, na emissão, e não um
    # selo que só deixa de conferir meses depois, na mão de quem recebeu o documento.
    if ocorrencias != 1:
        raise ValueError(
            f"Esperava 1 ocorrência da marca do selo no arquivo, encontrei {ocorrencias}."
        )
    return pdf.find(bytes_agulha)


def trocar(pdf: bytes, posicao: int, conteudo: str) -> bytes:
    return pdf[:posicao] + conteudo.encode() + pdf[posicao + TAMANHO_TAG :]
```

**`services/utils/assinatura/__init__.py`** — só reexporta (CLAUDE.md §7.2).
```python
from .models import ConferirInput, DocumentoSelado, EstadoSelo, ResultadoConferencia, SelarInput
from .selo import ConferirSelo, SelarDocumento, conferir_selo, selar_documento
```

**`pyproject.toml`** — `pypdf` deixa de ser dependência de teste. O reportlab não expõe chave
arbitrária no `/Info`, e a conferência precisa ler o envelope de um arquivo que chega pela web.
```toml
dependencies = [
    # ... as que já existem
    "pypdf>=5.1",
]
```

## 7 · Caveats
O selo é HMAC com chave simétrica, não assinatura assimétrica. Quem confere é o próprio sistema, e um
par de chaves só se pagaria se um terceiro precisasse conferir sem nós. O custo é que o vazamento do
segredo permite forjar todo o acervo retroativamente, e `id_chave` no envelope é o único preparo para
trocar o segredo sem invalidar o que já saiu.

A região assinada se localiza **procurando a tag nos bytes** do arquivo. Gravar o deslocamento
mudaria o arquivo e o deslocamento junto, e a alternativa seria reservar espaço fixo no `/Info` a cada
gravação. O custo é depender de o `pypdf` escrever os 64 dígitos hexadecimais sem escapá-los — ele
escapa pontuação em octal e deixa dígito em claro —, e a recusa por ocorrência diferente de uma é o
que transforma essa dependência em erro de emissão, e não em selo que não confere.

O selo cobre o arquivo inteiro, então qualquer regravação por outro programa — Acrobat, "imprimir
para PDF", gateway de e-mail que recomprime — derruba o selo mesmo sem má-fé. É o preço de cobrir a
imagem e o mapa, que um hash do texto extraído não cobriria. O custo é que documento honesto
regravado acusa selo violado, e só a SPEC 008 dá o que fazer depois disso.

O envelope é legível por qualquer um que abra o PDF: `campos_publicos` governa o que a conferência
devolve, não o que está escrito no arquivo. O custo é que nada sigiloso pode entrar no envelope, e
nada no código impede o chamador de pôr — a regra vive na SPEC.

`pypdf` sobe de dependência de teste para dependência de runtime. O custo é uma biblioteca a mais no
processo web, para uma capacidade que o reportlab, já na árvore, não oferece.

O segredo entra pelo DTO a cada chamada, em vez de ser lido de settings pelo módulo. É o que mantém
`services/utils/` sem Django e o singleton sem estado. O custo é que toda orquestração que sela ou
confere precisa carregar o segredo até aqui.

## 8 · Testes (TDD)
- `test_documento_selado_confere_consigo_mesmo` — selar e conferir com o mesmo segredo devolve
  `INTEGRO`, e o PDF resultante tem o mesmo tamanho em bytes do que entrou no `/Info`.
- `test_um_byte_virado_no_conteudo_derruba_o_selo` — virar um bit dentro do stream comprimido da
  página, longe do envelope, devolve `VIOLADO`.
- `test_alteracao_no_envelope_derruba_o_selo` — trocar o identificador do alvo escrito no envelope
  devolve `VIOLADO`, e o envelope adulterado volta no resultado.
- `test_segredo_diferente_derruba_o_selo` — conferir com outro segredo devolve `VIOLADO`.
- `test_documento_sem_selo_eh_distinguido_de_selo_violado` — PDF nunca selado devolve `SEM_SELO`, com
  envelope e públicos nulos.
- `test_envelope_volta_com_acentuacao_intacta` — nome com acento entra e volta idêntico da
  conferência.
- `test_conferencia_devolve_so_os_campos_publicos` — chave fora de `campos_publicos` não aparece em
  `publicos`, e continua presente no envelope.
- `test_selar_documento_ja_selado_eh_recusado` — selar duas vezes levanta na segunda.
- `test_dados_com_chave_reservada_sao_recusados` — `dados` contendo `tag` levanta na construção do
  `SelarInput`.
- `test_amostra_selada_para_conferencia` — grava o documento de amostra selado e imprime o caminho,
  para abrir num leitor e ver que o conteúdo permanece. *(marker `artefato`)*

---
spec: documentos_oficiais/008
versao: v6
atualizado_em: 2026-09-08
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a conferência devolve a ficha do ato — quem assinou, com que cargo e quando — e a home ganha o atalho para a tela de conferência
  - v3: o código alegado é lido do `ResultadoConferencia` inteiro, e não do dicionário do envelope solto
  - v4: o §5 explicita que quem recalcula o HMAC é o `ConferirSelo` da SPEC 006, e que esta SPEC só o consome
  - v5: a tela do código separa "está no acervo" de "o arquivo confere", e oferece os dois caminhos — conferir os bytes, aberto, e o original guardado, só a quem está logado
  - v6: testes da §8 escritos (`tests/apps/documentos/`, `tests/services/domain/documento_selado/test_conferencia.py`) e implementação completa — `testes_tdd: true`, `implementado: true`
---

# SPEC documentos_oficiais/008 — Acervo e conferência do documento emitido

## 1 · User story
Quem recebeu um documento emitido pela DIMAP abre o endereço impresso no selo, ou sobe o arquivo na
tela de conferência, no contexto de desconfiar da via que tem em mãos, para saber se o arquivo confere
e quem o assinou.

## 2 · Condições de pronto
- [ ] Todo documento emitido é guardado **inteiro** — os bytes, o envelope e o código — no mesmo ato
      da emissão.
- [ ] A tela do **código** afirma que o documento **está no acervo** — nunca que a via em mãos
      confere, porque sem os bytes não há o que recalcular — e mostra, **sem login**, quem
      assinou, com cargo e unidade, quando assinou, e os campos públicos do ato.
- [ ] A tela do código oferece os **dois caminhos**: conferir os bytes do arquivo, **aberto a
      todos**, e baixar o original guardado, que **só aparece a quem está logado**.
- [ ] O **arquivo enviado** é que recebe o veredito de confere ou não confere, e só o que confere
      afirma quem assinou.
- [ ] Código inexistente responde "documento não localizado", sem dizer se já existiu.
- [ ] Subir um arquivo devolve **um de quatro** resultados: confere, não confere, sem selo, ou selo
      íntegro de código desconhecido.
- [ ] Selo íntegro cujo código **não está no acervo** é apresentado como alerta, e nunca como
      documento válido.
- [ ] Arquivo cujo selo não confere, mas cujo código existe, oferece **o original guardado**.
- [ ] A segunda via **exige login** e devolve os **mesmos bytes** guardados na emissão, cujo selo
      confere.
- [ ] Arquivo acima do tamanho máximo é recusado com mensagem em português, sem ser lido inteiro.
- [ ] A home leva à conferência por um atalho no canto inferior direito, e o mapa não exibe mais os
      botões de zoom.
- [ ] O design da tela de conferência e do atalho na home foi aprovado no mock, e as peças portadas
      para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O acervo guarda o **documento emitido**: os bytes, o envelope que a SPEC
[documentos_oficiais/007](007-envelope-do-ato-e-selo-no-papel.md) selou, e o código que o selo imprime.
A pergunta que esta SPEC faz ao selo da SPEC [documentos_oficiais/006](006-selo-de-integridade.md) é o
que o arquivo afirma sozinho; o acervo responde a outra, que o arquivo não alcança — se esse documento
**existe**.

O envelope é o retrato congelado do ato; a linha do acervo é o índice consultável dele; e
`ExecucaoAcao` (épico `autorizacao`) é o registro vivo. A conferência recalcula sempre a partir dos
bytes do arquivo, nunca da coluna — mas o que a tela **afirma** sobre o ato sai da coluna, que é o
que o acervo escreveu.

**`services/domain/documento_selado/models.py`** — os modelos da conferência, ao lado do envelope.
```python
class EstadoDocumento(StrEnum):
    """O que o arquivo E o acervo, juntos, conseguem afirmar. `EstadoSelo` (SPEC 006) é o que o
    arquivo diz sozinho; estes quatro são o que a tela mostra."""

    CONFERE = "confere"
    NAO_CONFERE = "nao_confere"
    SEM_SELO = "sem_selo"
    # Selo íntegro de código que o acervo não conhece. Não é documento adulterado: ou o segredo
    # vazou, ou o documento saiu de uma base que não é esta.
    DESCONHECIDO = "desconhecido"


class RegistroDocumento(BaseModel):
    """A linha do acervo como o domínio a enxerga — sem `Model`, sem `QuerySet`. Quem a monta é a
    view, que é quem pode tocar no banco."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    emitido_em: AwareDatetime
    # O envelope guardado, achatado como a selagem o escreveu: na página do código não há arquivo
    # para conferir, e é daqui que sai a ficha.
    envelope: dict[str, Any]


class FichaDoAto(BaseModel):
    """O que a tela afirma sobre o ato quando ele confere. Envelopa o `AutorDoAto` da SPEC 007 em vez
    de recopiar nome, cargo e unidade."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    autor: AutorDoAto
    assinado_em: AwareDatetime
    # Os nomes que a ação declarou públicos, já resolvidos em valores.
    publicos: dict[str, Any]


class ConferenciaInput(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    # O que o arquivo afirmou sozinho, inteiro — não os campos dele soltos.
    resultado_selo: ResultadoConferencia
    # E só então o que é do processo: `None` quando o código não está no acervo.
    registro: RegistroDocumento | None = None


class ConferenciaOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    estado: EstadoDocumento
    # O que o arquivo diz chamar-se, mesmo quando não confere: é por ele que se acha o original.
    codigo: str | None = None
    # Preenchida só no estado CONFERE: fora dele, dizer quem assinou é repetir o que o arquivo alega.
    ficha: FichaDoAto | None = None
    # Se existe original guardado para oferecer a quem estiver logado.
    tem_original: bool = False


class TamanhoDoUpload(BaseModel):
    """A porta do upload em rota aberta. Só o tamanho: ele vem do cabeçalho do multipart, e é o que
    permite recusar o arquivo antes de os bytes irem para a memória."""

    model_config = ConfigDict(frozen=True)

    tamanho: int

    @field_validator("tamanho")
    @classmethod
    def cabe_no_limite(cls, valor: int) -> int:
        if valor <= 0:
            raise ValueError("Escolha o arquivo PDF a conferir.")
        if valor > TAMANHO_MAXIMO_BYTES:
            raise ValueError(f"O arquivo passa de {TAMANHO_MAXIMO_MB} MB.")
        return valor
```

**Mock:** [008-mock-acervo-e-conferencia.html](008-mock-acervo-e-conferencia.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **Revogação** do documento emitido — o acervo não diz se o ato ainda vale, só se ele existiu. SPEC
  própria, sem dono ainda.
- A ação de emitir certidão de lançamento, que é a primeira a alimentar o acervo — SPEC própria, sem
  dono ainda.
- Listagem e busca de documentos emitidos por unidade, autor ou período — sem dono ainda.
- Política de retenção e expurgo do acervo — sem dono ainda.
- Mais de um segredo vivo, e reconferência do acervo depois de trocar o segredo — sem dono ainda.
- Conferência de documento emitido por outro órgão — sem dono ainda.
- Prévia local do arquivo escolhido e realce de arraste no poço de upload — exigem JS de estado; sem
  dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/assinatura` → `ConferirSelo`, `ResultadoConferencia`: quem **recalcula o HMAC**
  sobre os bytes do arquivo e devolve o `EstadoSelo`, e o DTO em que esse veredito chega ao
  domínio. Esta SPEC **não reimplementa a conferência criptográfica** — só a consome, e o que ela
  acrescenta ao assunto é de onde vem o segredo (§6, `settings`).
- `@services/domain/documento_selado/models.py` → `EnvelopeAto`, `AutorDoAto`: o ato que a ficha mostra.
- `@services/domain/documento_selado/codigo.py` → `gerar_codigo`: o identificador do documento.
- `@services/domain/documento_selado/datas.py` → `por_extenso`: a data do ato como ela sai impressa.
- `@apps/competencias/models/execucao.py` → `ExecucaoAcao`: o registro vivo do ato, que a linha do
  acervo referencia em vez de recopiar.
- `@apps/core/middleware.py` → `PydanticValidationMiddleware`: o `ValidationError` virando resposta,
  sem `try/except` na view.
- `@services/domain/autorizacao` → a máquina de proteção de rota, para a única rota logada desta SPEC.
- `@templates/user_admin/partials/_campo_upload_foto.html` → `.upload-well`: o campo de upload em poço
  rebaixado, que o formulário de conferência compõe.
- Skills: `ontologia`, `mock`, `componentes-frontend`, `escrever-testes`, `pydantic-validation-errors`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/documentos/models.py`** — a linha do acervo. Só persistência: nenhuma regra aqui.
```python
class DocumentoEmitido(models.Model):
    codigo = models.CharField(max_length=TAMANHO_CODIGO, unique=True, editable=False)
    # `BinaryField` é `bytea`: o PDF vive na linha. Na escala do sistema — dezenas de usuários — um
    # arquivo, uma linha e uma transação valem mais que um storage a operar (Caveats).
    arquivo = models.BinaryField(editable=False)
    # O envelope também está DENTRO do arquivo. Esta cópia é índice consultável e fonte da ficha,
    # nunca a fonte da conferência (Caveats).
    envelope = models.JSONField(editable=False)
    campos_publicos = models.JSONField(default=list, editable=False)
    # Nulo enquanto houver emissão que não venha de ação inscrita — a amostra, por exemplo.
    execucao = models.ForeignKey(
        "competencias.ExecucaoAcao",
        on_delete=models.PROTECT,
        related_name="documentos",
        null=True,
        blank=True,
    )
    emitido_em = models.DateTimeField(editable=False)

    class Meta:
        # A conferência entra sempre pelo código, e a listagem futura, pela data.
        indexes = [models.Index(fields=["-emitido_em"])]
```

**`apps/documentos/acervo.py`** — a persistência do documento, ao lado do model, como
`registro_execucao.py` faz para o rastro do ato. A view chama; a regra não mora aqui.
```python
def guardar_documento(
    selado: DocumentoSelado,
    ato: EnvelopeAto,
    execucao: ExecucaoAcao | None,
) -> DocumentoEmitido:
    return DocumentoEmitido.objects.create(
        codigo=ato.codigo,
        arquivo=selado.pdf,
        envelope=selado.envelope,
        campos_publicos=list(ato.campos_publicos),
        execucao=execucao,
        emitido_em=ato.emitido_em,
    )


def buscar_registro(codigo: str) -> RegistroDocumento | None:
    # `only`: a conferência precisa do envelope e da data, não do PDF inteiro — que é o que faz esta
    # consulta rodar em toda conferência sem carregar megabytes do banco.
    linha = (
        DocumentoEmitido.objects.filter(codigo=codigo)
        .only("codigo", "emitido_em", "envelope")
        .first()
    )
    if linha is None:
        return None
    return RegistroDocumento(
        codigo=linha.codigo,
        emitido_em=linha.emitido_em,
        envelope=linha.envelope,
    )
```

**`services/utils/assinatura/publicos.py`** — a extração que hoje é privada do `ConferirSelo`, exposta
para ter **um** lugar só: o resultado do selo e a ficha do acervo leem os mesmos nomes do mesmo jeito.
`ConferirSelo._publicos` passa a delegar aqui.
```python
def extrair_publicos(envelope: dict[str, Any]) -> dict[str, Any]:
    declarados = envelope.get("campos_publicos", [])
    # `campos_publicos` também vem do arquivo: o que não for lista de nomes não declara nada.
    if not isinstance(declarados, list):
        return {}
    return {
        chave: envelope[chave]
        for chave in declarados
        if isinstance(chave, str) and chave in envelope
    }
```

**`services/domain/documento_selado/ficha.py`** — o envelope guardado virando o que a tela afirma.
Uma peça, dois chamadores: a página do código e o resultado do upload dizem o mesmo sobre o mesmo ato.
```python
def codigo_alegado(resultado: ResultadoConferencia) -> str | None:
    """O resultado do selo INTEIRO, e não o dicionário do envelope solto: é o DTO que atravessa a
    fronteira. O envelope de um arquivo forjado põe o que quiser em `codigo` — inclusive nada, ou um
    número. A rota é aberta: o que não for texto não é código, e não vira consulta ao acervo."""
    envelope = resultado.envelope
    if envelope is None:
        return None
    codigo = envelope.get("codigo")
    return codigo if isinstance(codigo, str) else None


class LerFichaDoAto:
    """Callable: o envelope GUARDADO → a ficha. `model_validate` sem defesa porque a entrada é o que
    esta aplicação escreveu na emissão, e não o que chegou pelo formulário."""

    def __call__(self, envelope: dict[str, Any]) -> FichaDoAto:
        ato = EnvelopeAto.model_validate(envelope)
        return FichaDoAto(
            codigo=ato.codigo,
            # O autor inteiro: cargo de comissão e substituição fazem parte de quem assinou.
            autor=ato.autor,
            assinado_em=ato.emitido_em,
            # A selagem achatou os extras junto do núcleo, então o nome declarado público acha o
            # valor no dicionário inteiro — e não só nos campos do `EnvelopeAto`.
            publicos=extrair_publicos(envelope),
        )
```

**`services/domain/documento_selado/conferencia.py`** — a regra: cruzar o que o arquivo diz com o que
o acervo sabe. É o domínio inteiro desta SPEC, e roda sem Django.
```python
class ClassificarConferencia:
    """Callable: o veredito do selo + a existência no acervo → o que a tela mostra."""

    def __call__(self, pedido: ConferenciaInput) -> ConferenciaOutput:
        return self.pipeline(pedido)

    def pipeline(self, pedido: ConferenciaInput) -> ConferenciaOutput:
        estado = self._estado(pedido)
        return ConferenciaOutput(
            estado=estado,
            codigo=codigo_alegado(pedido.resultado_selo),
            ficha=self._ficha(estado, pedido.registro),
            # Só há original a oferecer se o documento existe no acervo.
            tem_original=pedido.registro is not None,
        )

    def _estado(self, pedido: ConferenciaInput) -> EstadoDocumento:
        selo = pedido.resultado_selo.estado
        if selo is EstadoSelo.SEM_SELO:
            return EstadoDocumento.SEM_SELO
        if selo is EstadoSelo.VIOLADO:
            # Violado com código conhecido continua NAO_CONFERE: quem decide o que fazer com o
            # original é a tela, pelo `tem_original`.
            return EstadoDocumento.NAO_CONFERE
        # Íntegro é o caso que se bifurca: selo que fecha com um código que o acervo nunca emitiu
        # não é documento bom — é sinal de que o segredo saiu daqui.
        if pedido.registro is None:
            return EstadoDocumento.DESCONHECIDO
        return EstadoDocumento.CONFERE

    def _ficha(
        self,
        estado: EstadoDocumento,
        registro: RegistroDocumento | None,
    ) -> FichaDoAto | None:
        # A ficha é uma AFIRMAÇÃO sobre o ato, e só o selo que fecha contra o acervo autoriza fazê-la.
        # Nos outros três estados o que existe é a alegação do arquivo, que a tela não repete como
        # se fosse fato. E ela sai do envelope guardado, nunca do que veio dentro do arquivo.
        if estado is not EstadoDocumento.CONFERE or registro is None:
            return None
        return ler_ficha_do_ato(registro.envelope)
```

**`apps/documentos/views.py`** — quatro rotas finas. A validação do upload constrói o DTO e deixa o
middleware interceptar; nenhum `try/except` aqui.
```python
def pagina_conferencia(request: HttpRequest) -> HttpResponse:
    """Rota ABERTA: a porta de quem tem o arquivo e não tem — ou não consegue ler — o código
    impresso. É para cá que o atalho da home aponta."""
    return render(request, "documentos/conferencia.html")


def conferir_por_codigo(request: HttpRequest, codigo: str) -> HttpResponse:
    """Rota ABERTA (exceção declarada, CLAUDE.md §3.5): é o endereço que o QR do selo abre, e quem
    recebe o documento não tem login."""
    registro = buscar_registro(codigo)
    # A mesma resposta para código inexistente e para código malformado: dizer "existiu e não
    # existe mais" já é informação sobre o acervo.
    if registro is None:
        return render(request, "documentos/partials/_nao_localizado.html", status=404)
    # A ficha, e não a linha: a tela do código e a do upload mostram a mesma coisa.
    return render(
        request,
        "documentos/conferencia_por_codigo.html",
        {"ficha": ler_ficha_do_ato(registro.envelope)},
    )


@require_POST
def conferir_arquivo(request: HttpRequest) -> HttpResponse:
    """Rota ABERTA: conferir um arquivo que o próprio remetente já tem em mãos não revela nada que
    ele não possua."""
    enviado = request.FILES.get("arquivo")
    # `size` vem do cabeçalho do multipart: o arquivo grande — e o formulário vazio — são recusados
    # aqui, antes de os bytes irem para a memória. O `ValidationError` vira 422 no middleware.
    TamanhoDoUpload(tamanho=enviado.size if enviado else 0)
    # O ramo vazio é inalcançável: o DTO acima não deixa passar tamanho zero.
    pdf = enviado.read() if enviado else b""
    selo = conferir_selo(ConferirInput(pdf=pdf, segredo=SEGREDO))
    codigo = codigo_alegado(selo)
    resultado = classificar_conferencia(
        ConferenciaInput(
            resultado_selo=selo,
            registro=buscar_registro(codigo) if codigo else None,
        )
    )
    return render(request, "documentos/partials/_resultado.html", {"resultado": resultado})


@login_required
def segunda_via(request: HttpRequest, codigo: str) -> HttpResponse:
    """Rota PROTEGIDA, ao contrário das três acima: o código está impresso no canto do papel, e
    quem o fotografa de longe não pode com isso baixar o documento inteiro."""
    documento = get_object_or_404(DocumentoEmitido, codigo=codigo)
    # Os MESMOS bytes guardados na emissão. Renderizar de novo daria outro arquivo, com outro selo,
    # e dois documentos diferentes para o mesmo ato.
    return HttpResponse(bytes(documento.arquivo), content_type="application/pdf")
```

**`templates/documentos/conferencia_por_codigo.html`** — os dois caminhos da tela do código. O
partial da oferta do original é o **mesmo** da tela do upload; o que muda é quem o inclui.
```html
{# Aberto a todos: é a conferência forte — a única que recalcula o HMAC sobre os bytes. #}
<a href="{% url 'documentos:pagina' %}" class="btn btn-glass w-full gap-2">Tenho o arquivo — conferir os bytes</a>

{# Só para quem está logado: o destinatário externo não vê botão que não pode percorrer. Esconder é
   UX; a autorização de verdade continua no `@login_required` da rota (CLAUDE.md §3.5). #}
{% if request.user.is_authenticated %}
  {% include "documentos/partials/_oferta_original.html" with codigo=ficha.codigo %}
{% endif %}
```

**`apps/documentos/urls.py`** — a rota de uma letra da SPEC 007 vira também a pasta do formulário:
quem digita o endereço impresso errado cai na tela de conferência em vez de num 404.
```python
app_name = "documentos"

urlpatterns = [
    path(f"{ROTA_CONFERENCIA}/", pagina_conferencia, name="pagina"),
    # Antes da rota do código, que casaria com qualquer texto — e "conferir" não é código válido de
    # todo jeito: o alfabeto da SPEC 007 não tem minúscula.
    path(f"{ROTA_CONFERENCIA}/conferir", conferir_arquivo, name="conferir_arquivo"),
    path(f"{ROTA_CONFERENCIA}/<str:codigo>", conferir_por_codigo, name="conferir"),
    path(f"{ROTA_CONFERENCIA}/<str:codigo>/original", segunda_via, name="segunda_via"),
]
```

**`static/src/js/mapa/criar_mapa.js`** e **`templates/core/home.html`** — o canto inferior direito do
mapa deixa de ser dos botões de zoom e passa a ser do atalho.
```javascript
// A linha `L.control.zoom({ position: "bottomright" }).addTo(mapa)` sai; `zoomControl: false` já
// estava na criação do mapa, então nada mais precisa mudar aqui.
```
```html
{# fica na página: o mapa é singleton da home, e o atalho vive sobre ele. A pele é do mock. #}
<a href="{% url 'documentos:pagina' %}" class="…">Validar documento</a>
```

**`config/settings.py`** e **`.env.example`** — o segredo do selo e a identificação da chave, que a
orquestração lê e passa ao domínio.
```python
ASSINATURA_SEGREDO = env("ASSINATURA_SEGREDO")
ASSINATURA_ID_CHAVE = env("ASSINATURA_ID_CHAVE", default="k1")
```

## 7 · Caveats
As três rotas de conferência são **abertas**, exceção ao CLAUDE.md §3.5, que exige rota protegida por
padrão. O selo existe para quem recebeu o documento e não tem login: uma conferência protegida
tornaria o QR impresso inútil justamente para o destinatário. O custo é uma superfície pública nova, e
o que a torna aceitável é o código de ~60 bits da SPEC 007 — varrer o acervo por tentativa é inviável.

A ficha mostra quem assinou, com cargo e unidade, sem login. Nome e cargo já saem impressos no quadro
de fecho do papel de onde o código veio, e conferência que não os repete não deixa comparar o papel
com o acervo. O custo é que quem obtém um código válido passa a saber a lotação de quem assinou.

Baixar o original exige login, enquanto conferir não. O código está impresso no canto do papel, e sem
essa assimetria quem fotografasse só o selo levaria o documento inteiro. O custo é que o destinatário
externo vê a ficha mas não obtém segunda via, que passa a depender de um servidor — e o que torna
isso aceitável é o outro caminho ser o forte: subir o arquivo recalcula o HMAC byte a byte, enquanto
baixar o original e comparar dois PDFs a olho não prova nada. O download serve para obter uma via
boa, não para conferir.

Na tela do código o botão do original **não aparece** para o anônimo, em vez de aparecer levando ao
login. Botão que a maioria dos visitantes daquela tela não consegue percorrer ensina a ignorar a
interface. O custo é que o destinatário externo não fica sabendo que existe original guardado — e a
tela do upload, onde o arquivo não confere, continua dizendo isso a quem precisa.

O PDF é gravado cru em `bytea`, sem compressão. Medido sobre o documento de amostra, `gzip` economiza
19,5% de 290 KB, e o TOAST do Postgres já comprime valores grandes por conta própria — uma camada de
compressão e descompressão não se paga, e cada passo a mais é uma chance de os bytes voltarem
diferentes do que entraram. O custo é que o dump do banco cresce junto com o acervo.

O envelope existe em dois lugares que podem divergir: dentro do arquivo e na coluna `envelope`. A
coluna é o que torna o acervo consultável e é de onde sai a ficha; o arquivo é o que se confere. O
custo é a duplicação, e a regra que a sustenta — a conferência nunca lê a coluna para decidir o
estado — vive nesta SPEC, não no código.

`emitido_em` é coluna e também está no envelope, pelo mesmo motivo e com o mesmo custo: sem ela, a
ordenação e o índice por data exigiriam varrer JSON.

O documento emitido não pode ser cancelado nesta iteração: quem confere uma certidão anulada continua
lendo "confere". O acervo já traz a linha onde a revogação vai morar — fora do selo, porque payload
assinado não pode conter nada mutável —, mas a SPEC que a implementa não tem dono ainda.

O upload é lido inteiro em memória depois de passar pelo teto de tamanho, numa rota aberta. Conferir
exige o arquivo completo, porque o selo cobre todos os bytes. O custo é que a rota segue exposta a
quem repetir o envio no limite.

Uma SPEC do épico `documentos_oficiais` mexe na home e no mapa, que são de outro épico — o atalho e a
saída dos botões de zoom, com o aval do usuário exigido pelo CLAUDE.md §3.4 para peça já implementada.
A tela de conferência sem porta de entrada só serve a quem já tem o endereço impresso, e a porta é
justamente a home. O custo é que o dono do canto inferior direito do mapa passa a ser esta SPEC.

O mapa perde os botões de zoom e fica só com a roda do mouse, o gesto de pinça e o teclado do próprio
Leaflet. O canto que eles ocupavam é o único lugar livre da tela para o atalho, e o zoom por botão
duplica o que os outros três já fazem. O custo cai sobre quem navega em desktop sem roda de rolagem.

## 8 · Testes (TDD)
- `test_documento_emitido_eh_guardado_inteiro` — depois da emissão, a linha traz os bytes, o
  envelope e o código, e os bytes guardados conferem contra o selo. *(marker `banco`)*
- `test_conferencia_por_codigo_mostra_a_ficha_do_ato` — a página do código traz assinante, cargo,
  unidade, data e os campos declarados públicos, e nenhum campo fora da lista. *(marker `banco`)*
- `test_codigo_inexistente_responde_nao_localizado` — devolve 404 com o partial de não localizado, e
  o corpo não distingue "nunca existiu" de "não está mais lá". *(marker `banco`)*
- `test_arquivo_integro_e_conhecido_confere` — arquivo recém-emitido devolve `CONFERE` com o código
  do envelope e a ficha montada a partir do envelope guardado. *(marker `banco`)*
- `test_arquivo_alterado_com_codigo_conhecido_nao_confere_e_oferece_original` — um byte virado
  devolve `NAO_CONFERE` com `tem_original=True` e sem ficha. *(marker `banco`)*
- `test_selo_integro_de_codigo_ausente_eh_desconhecido` — selo que fecha com o segredo mas cujo
  código não está no acervo devolve `DESCONHECIDO`, sem ficha, e não `CONFERE`.
- `test_arquivo_sem_selo_eh_sem_selo` — PDF nunca selado devolve `SEM_SELO`, sem código e sem ficha.
- `test_tela_do_codigo_esconde_o_original_do_anonimo` — a mesma página traz o link da segunda via
  para o logado e não o traz para o anônimo, e os dois veem o caminho de conferir os bytes.
  *(marker `banco`)*
- `test_segunda_via_devolve_os_mesmos_bytes_e_exige_login` — anônimo é redirecionado ao login; o
  logado recebe bytes idênticos aos guardados na emissão. *(marker `banco`)*
- `test_upload_vazio_ou_acima_do_limite_eh_recusado` — formulário sem arquivo e upload maior que o
  teto respondem 422 com mensagem em português, e os bytes não são lidos.
- `test_home_oferece_atalho_para_a_conferencia` — a home renderiza o link para a tela de conferência.

---
spec: documentos_oficiais/008
versao: v1
atualizado_em: 2026-09-07
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/008 — Acervo e conferência do documento emitido

## 1 · User story
Quem recebeu um documento emitido pela DIMAP abre o endereço impresso no selo, no contexto de
desconfiar da via que tem em mãos, para ver os dados públicos do ato e saber se o arquivo confere.

## 2 · Condições de pronto
- [ ] Todo documento emitido é guardado **inteiro** — os bytes, o envelope e o código — no mesmo ato
      da emissão.
- [ ] O endereço impresso no selo mostra, **sem login**, os campos públicos do ato e a data de
      emissão.
- [ ] Código inexistente responde "documento não localizado", sem dizer se já existiu.
- [ ] Subir um arquivo devolve **um de quatro** resultados: confere, não confere, sem selo, ou selo
      íntegro de código desconhecido.
- [ ] Selo íntegro cujo código **não está no acervo** é apresentado como alerta, e nunca como
      documento válido.
- [ ] Arquivo cujo selo não confere, mas cujo código existe, oferece **o original guardado**.
- [ ] Baixar o original **exige login**; conferir, não.
- [ ] A segunda via devolve os **mesmos bytes** guardados na emissão, cujo selo confere.
- [ ] Arquivo acima do tamanho máximo é recusado com mensagem em português, sem ser lido inteiro.
- [ ] O design da tela de conferência foi aprovado no mock, e as peças portadas para o tema e o
      styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O acervo guarda o **documento emitido**: os bytes, o envelope que a SPEC
[documentos_oficiais/007](007-envelope-do-ato-e-selo-no-papel.md) selou, e o código que o selo imprime.
A pergunta que esta SPEC faz ao selo da SPEC [documentos_oficiais/006](006-selo-de-integridade.md) é o
que o arquivo afirma sozinho; o acervo responde a outra, que o arquivo não alcança — se esse documento
**existe**.

O envelope é o retrato congelado do ato; a linha do acervo é o índice consultável dele; e
`ExecucaoAcao` (épico `autorizacao`) é o registro vivo. A conferência recalcula sempre a partir dos
bytes do arquivo, nunca da coluna.

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


class ConferenciaInput(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    # O que o arquivo afirmou sozinho, inteiro — não os campos dele soltos.
    resultado_selo: ResultadoConferencia
    # E só então o que é do processo: `None` quando o código não está no acervo.
    registro: RegistroDocumento | None = None


class ConferenciaOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    estado: EstadoDocumento
    codigo: str | None = None
    publicos: dict[str, Any] | None = None
    # Se existe original guardado para oferecer a quem estiver logado.
    tem_original: bool = False


class ArquivoConferido(BaseModel):
    """O que chega pelo formulário. O limite é do processo — arquivo é upload em rota aberta."""

    model_config = ConfigDict(frozen=True)

    conteudo: bytes = Field(max_length=TAMANHO_MAXIMO_BYTES)
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

## 5 · Peças de referência a compor
- `@services/utils/assinatura` → `ConferirSelo`: o que o arquivo afirma sozinho.
- `@services/domain/documento_selado/codigo.py` → `gerar_codigo`: o identificador do documento.
- `@apps/competencias/models/execucao.py` → `ExecucaoAcao`: o registro vivo do ato, que a linha do
  acervo referencia em vez de recopiar.
- `@apps/competencias/registro_execucao.py` → o módulo de app que grava o rastro: a forma de uma
  camada de persistência fina, chamada pela orquestração.
- `@apps/core/middleware.py` → `PydanticValidationMiddleware`: o `ValidationError` virando resposta,
  sem `try/except` na view.
- `@services/domain/autorizacao` → a máquina de proteção de rota, para a única rota logada desta SPEC.
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
    # O envelope também está DENTRO do arquivo. Esta cópia é índice consultável, nunca a fonte da
    # conferência (Caveats).
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
    # `only`: a conferência precisa saber se o documento existe, não carregar o PDF inteiro do banco
    # para descobrir isso.
    linha = DocumentoEmitido.objects.filter(codigo=codigo).only("codigo", "emitido_em").first()
    if linha is None:
        return None
    return RegistroDocumento(codigo=linha.codigo, emitido_em=linha.emitido_em)
```

**`services/domain/documento_selado/conferencia.py`** — a regra: cruzar o que o arquivo diz com o que
o acervo sabe. É o domínio inteiro desta SPEC, e roda sem Django.
```python
class ClassificarConferencia:
    """Callable: o veredito do selo + a existência no acervo → o que a tela mostra."""

    def __call__(self, pedido: ConferenciaInput) -> ConferenciaOutput:
        return self.pipeline(pedido)

    def pipeline(self, pedido: ConferenciaInput) -> ConferenciaOutput:
        return ConferenciaOutput(
            estado=self._estado(pedido),
            codigo=self._codigo(pedido),
            publicos=pedido.resultado_selo.publicos,
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

    def _codigo(self, pedido: ConferenciaInput) -> str | None:
        envelope = pedido.resultado_selo.envelope
        return envelope.get("codigo") if envelope else None
```

**`apps/documentos/views.py`** — três rotas finas. A validação do upload constrói o DTO e deixa o
middleware interceptar; nenhum `try/except` aqui.
```python
def conferir_por_codigo(request: HttpRequest, codigo: str) -> HttpResponse:
    """Rota ABERTA (exceção declarada, CLAUDE.md §3.5): é o endereço que o QR do selo abre, e quem
    recebe o documento não tem login."""
    registro = buscar_registro(codigo)
    # A mesma resposta para código inexistente e para código malformado: dizer "existiu e não
    # existe mais" já é informação sobre o acervo.
    if registro is None:
        return render(request, "documentos/_nao_localizado.html", status=404)
    return render(request, "documentos/_conferencia.html", {...})


@require_POST
def conferir_arquivo(request: HttpRequest) -> HttpResponse:
    """Rota ABERTA: conferir um arquivo que o próprio remetente já tem em mãos não revela nada que
    ele não possua."""
    enviado = ArquivoConferido(conteudo=request.FILES["arquivo"].read())
    selo = conferir_selo(ConferirInput(pdf=enviado.conteudo, segredo=SEGREDO))
    resultado = classificar_conferencia(
        ConferenciaInput(
            resultado_selo=selo,
            registro=buscar_registro(selo.envelope["codigo"]) if selo.envelope else None,
        )
    )
    return render(request, "documentos/_resultado.html", {"resultado": resultado})


@login_required
def segunda_via(request: HttpRequest, codigo: str) -> HttpResponse:
    """Rota PROTEGIDA, ao contrário das duas acima: o código está impresso no canto do papel, e
    quem o fotografa de longe não pode com isso baixar o documento inteiro."""
    documento = get_object_or_404(DocumentoEmitido, codigo=codigo)
    # Os MESMOS bytes guardados na emissão. Renderizar de novo daria outro arquivo, com outro selo,
    # e dois documentos diferentes para o mesmo ato.
    return HttpResponse(bytes(documento.arquivo), content_type="application/pdf")
```

**`config/settings.py`** e **`.env.example`** — o segredo do selo e a identificação da chave, que a
orquestração lê e passa ao domínio.
```python
ASSINATURA_SEGREDO = env("ASSINATURA_SEGREDO")
ASSINATURA_ID_CHAVE = env("ASSINATURA_ID_CHAVE", default="k1")
```

## 7 · Caveats
As duas rotas de conferência são **abertas**, exceção ao CLAUDE.md §3.5, que exige rota protegida por
padrão. O selo existe para quem recebeu o documento e não tem login: uma conferência protegida
tornaria o QR impresso inútil justamente para o destinatário. O custo é uma superfície pública nova, e
o que a torna aceitável é o código de ~60 bits da SPEC 007 — varrer o acervo por tentativa é inviável.

Baixar o original exige login, enquanto conferir não. O código está impresso no canto do papel, e sem
essa assimetria quem fotografasse só o selo levaria o documento inteiro. O custo é que o destinatário
externo vê os campos públicos mas não obtém segunda via, que passa a depender de um servidor.

O PDF é gravado cru em `bytea`, sem compressão. Medido sobre o documento de amostra, `gzip` economiza
19,5% de 290 KB, e o TOAST do Postgres já comprime valores grandes por conta própria — uma camada de
compressão e descompressão não se paga, e cada passo a mais é uma chance de os bytes voltarem
diferentes do que entraram. O custo é que o dump do banco cresce junto com o acervo.

O envelope existe em dois lugares que podem divergir: dentro do arquivo e na coluna `envelope`. A
coluna é o que torna o acervo consultável; o arquivo é o que se confere. O custo é a duplicação, e a
regra que a sustenta — a conferência nunca lê a coluna — vive nesta SPEC, não no código.

`emitido_em` é coluna e também está no envelope, pelo mesmo motivo e com o mesmo custo: sem ela, a
ordenação e o índice por data exigiriam varrer JSON.

O documento emitido não pode ser cancelado nesta iteração: quem confere uma certidão anulada continua
lendo "confere". O acervo já traz a linha onde a revogação vai morar — fora do selo, porque payload
assinado não pode conter nada mutável —, mas a SPEC que a implementa não tem dono ainda.

O upload é lido inteiro em memória para ser conferido, numa rota aberta. Conferir exige o arquivo
completo, porque o selo cobre todos os bytes. O custo é limitado pelo teto de tamanho do DTO, e a
rota segue exposta a quem repetir o envio no limite.

## 8 · Testes (TDD)
- `test_documento_emitido_eh_guardado_inteiro` — depois da emissão, a linha traz os bytes, o
  envelope e o código, e os bytes guardados conferem contra o selo. *(marker `banco`)*
- `test_codigo_repetido_nao_entra_no_acervo` — gravar dois documentos com o mesmo código levanta na
  segunda inserção. *(marker `banco`)*
- `test_conferencia_por_codigo_mostra_so_os_campos_publicos` — a página do código traz os campos
  declarados públicos e a data, e nenhum campo fora da lista. *(marker `banco`)*
- `test_codigo_inexistente_responde_nao_localizado` — devolve 404 com o partial de não localizado, e
  o corpo não distingue "nunca existiu" de "não está mais lá". *(marker `banco`)*
- `test_arquivo_integro_e_conhecido_confere` — arquivo recém-emitido devolve `CONFERE` com o código
  do envelope. *(marker `banco`)*
- `test_arquivo_alterado_com_codigo_conhecido_nao_confere_e_oferece_original` — um byte virado
  devolve `NAO_CONFERE` com `tem_original=True`. *(marker `banco`)*
- `test_selo_integro_de_codigo_ausente_eh_desconhecido` — selo que fecha com o segredo mas cujo
  código não está no acervo devolve `DESCONHECIDO`, e não `CONFERE`.
- `test_arquivo_sem_selo_eh_sem_selo` — PDF nunca selado devolve `SEM_SELO`, sem código e sem
  públicos.
- `test_segunda_via_devolve_os_mesmos_bytes_e_exige_login` — anônimo é redirecionado ao login; o
  logado recebe bytes idênticos aos guardados na emissão. *(marker `banco`)*
- `test_arquivo_acima_do_limite_eh_recusado` — upload maior que o teto responde erro de validação em
  português, e o documento não é lido.

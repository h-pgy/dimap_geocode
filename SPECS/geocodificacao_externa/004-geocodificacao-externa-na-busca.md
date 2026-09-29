---
spec: geocodificacao_externa/004
versao: v1
atualizado_em: 2026-09-27
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC geocodificacao_externa/004 — Geocodificação externa na busca

## 1 · User story
O servidor logado na plataforma digita um endereço por nome e recebe a geocodificação externa como
última opção da lista e como último recurso do Enter, no contexto de endereços que a base oficial não
resolve, para localizá-los sem gastar cota quando a base oficial resolve.

## 2 · Condições de pronto
- [ ] Para quem está logado, endereço por nome com número (`rua augusta, 100`) traz nas sugestões,
      **sempre por último**, a opção de geocodificação externa; digitar **não** chama o provedor.
- [ ] Clicar na opção geocodifica pelo provedor externo mesmo quando a base oficial resolve o endereço.
- [ ] Endereço por codlog (`12345, 100`), logradouro sem número e "sem número" (`rua x, s/n`) **não**
      trazem a opção.
- [ ] Enter com a base oficial resolvendo o endereço usa a base oficial e não chama o provedor.
- [ ] Enter com o logradouro fora da base oficial, sem segmento ou com número fora da faixa
      geocodifica pelo provedor externo e mostra, junto do resultado, um **aviso** dizendo o que a base
      oficial não encontrou e que o resultado veio do serviço externo.
- [ ] Enter em que o provedor externo também falha responde um aviso com o que a base oficial não
      encontrou e o que aconteceu no serviço externo.
- [ ] Clicar numa sugestão da base oficial que falha continua respondendo o aviso de hoje, sem cair no
      externo.
- [ ] **Sem login**, ou sem geocodificador externo configurado, a opção não aparece e o Enter responde o
      aviso do que a base oficial não encontrou, sem chamar o provedor.
- [ ] O design da opção nas sugestões e do aviso junto do resultado foi aprovado no mock e as peças
      novas portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O resultado externo e a sua renderização são os da SPEC [003](003-endereco-externo-no-mapa-e-na-gaveta.md);
a pergunta que esta SPEC faz a eles é "e se a base oficial não resolveu?". O roteador é o da SPEC
[roteamento_busca/001](../roteamento_busca/001-roteador-entrada.md): a opção externa entra nele como
mais um candidato, reconhecido pela mesma regra do endereço por nome.

**`services/domain/roteamento_busca/models.py`** — `TipoEntrada` e `Candidato` inteiros.

```python
class TipoEntrada(StrEnum):
    CONTRIBUINTE = "contribuinte"
    CODLOG = "codlog"
    LOGRADOURO = "logradouro"
    ENDERECO = "endereco"
    ENDERECO_CODLOG = "endereco_codlog"
    ENDERECO_LOTE = "endereco_lote"
    GEOCODIFICACAO_EXTERNA = "geocodificacao_externa"  # ALTERADO nesta SPEC: valor novo


class GeocodificacaoExternaParse(BaseModel):  # ALTERADO nesta SPEC: parse novo
    tipo: Literal[TipoEntrada.GEOCODIFICACAO_EXTERNA] = TipoEntrada.GEOCODIFICACAO_EXTERNA
    texto: str  # a entrada inteira, como digitada: é o que vai ao provedor


Candidato = Annotated[
    ContribuinteParse
    | CodlogParse
    | LogradouroParse
    | EnderecoParse
    | EnderecoCodlogParse
    | EnderecoLoteParse
    | GeocodificacaoExternaParse,  # ALTERADO nesta SPEC
    Field(discriminator="tipo"),
]
```

**`services/domain/roteamento_busca/router.py`** — `PRIORIDADE_TIPOS` inteira.

```python
PRIORIDADE_TIPOS: tuple[TipoEntrada, ...] = (
    TipoEntrada.CONTRIBUINTE,
    TipoEntrada.ENDERECO_LOTE,
    TipoEntrada.ENDERECO_CODLOG,
    TipoEntrada.ENDERECO,
    TipoEntrada.CODLOG,
    TipoEntrada.LOGRADOURO,
    TipoEntrada.GEOCODIFICACAO_EXTERNA,  # ALTERADO nesta SPEC: sempre a última
)
```

**`apps/search/tentativas.py`** — o que o Enter carrega de um candidato para o seguinte.

```python
class FalhaBaseOficial(BaseModel):
    motivo: str  # o que a base oficial não encontrou, pronto para o aviso
```

**Mock:** [004-mock-geocodificacao-externa-na-busca.html](004-mock-geocodificacao-externa-na-busca.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Entrada sem número (nome de lugar, ponto de interesse) na geocodificação externa — sem dono ainda.
- Cache de resultados externos por texto — sem dono ainda.
- Limite de chamadas ao provedor por sessão ou por usuário — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/roteamento_busca/endereco.py` → `EnderecoIdentifier`: a regra de "endereço por nome", composta pelo identifier novo.
- `@apps/geocodificacao_externa/views.py` → `geocodificador_externo`, `geocodificar_externo`, `ROTULO_PROVEDOR` (SPEC 003).
- `@apps/search/views.py` → `REGISTRO_SECOES`, `comitar`, `_acionar_candidato`: o registro de seções e o laço do Enter.
- `@apps/search/secoes.py` → `SecaoResultado`.
- `@apps/address_geocoder/views.py` → `MSG_SEM_SEGMENTO`, `MSG_SEM_NUMERACAO`: os motivos de hoje, reaproveitados no aviso.
- `@templates/address_geocoder/partials/resultados_endereco_nome.html` → o item de sugestão clicável, molde do novo.
- `@templates/mapping/_aviso.html` → o aviso de hoje.
- Skills: `mock`, `componentes-frontend`, `htmx`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/roteamento_busca/geocodificacao_externa.py`** — só lê o texto, como os outros
identifiers: nenhum I/O, nenhuma chamada ao provedor.

```python
class GeocodificacaoExternaIdentifier:
    def __init__(self, endereco: EnderecoIdentifier | None = None) -> None:
        self._endereco = endereco or EnderecoIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> GeocodificacaoExternaParse | None:
        # mesma regra do endereço por nome: codlog, sem número e "s/n" ficam de fora sozinhos
        if self._endereco(texto, finished_typing) is None:
            return None
        return GeocodificacaoExternaParse(texto=texto.strip())
```

**`apps/geocodificacao_externa/secoes.py`** — a opção nas sugestões é só um item clicável: montá-la
não chama o provedor.

```python
TITULO_GEOCODIFICACAO_EXTERNA = "Geocodificação externa"


def secao_geocodificacao_externa(candidato: GeocodificacaoExternaParse) -> SecaoResultado | None:
    geocodificador = geocodificador_externo()
    if geocodificador is None:
        return None  # sem provedor configurado, não se oferece o que não se pode cumprir
    html = render_to_string(
        "geocodificacao_externa/partials/_sugestao_externa.html",
        {"texto": candidato.texto, "provedor": ROTULO_PROVEDOR[geocodificador.provedor]},
    )
    return SecaoResultado(titulo=TITULO_GEOCODIFICACAO_EXTERNA, html=html)
```

**`templates/geocodificacao_externa/partials/_sugestao_externa.html`** — `escapejs`: o texto é livre
e vai dentro de JSON.

```html
<li class="suggestion-item"
    hx-post="{% url 'geocodificacao_externa:selecionar' %}"
    hx-vals='{"texto": "{{ texto|escapejs }}"}'
    hx-target="#resultado-busca"
    hx-swap="innerHTML">
  ...
</li>
```

**`apps/address_geocoder/views.py`** — a resolução se separa da renderização; o clique segue igual.

```python
def resolver_endereco(codlog: str, numero: object) -> EnderecoFeature | FalhaBaseOficial:
    entrada = AddressGeocodInput.model_validate({...})  # como hoje
    geocoder = AddressGeocoder(LogradouroGeocoder(build_fetcher(settings)))
    try:
        return geocoder(entrada)
    except SegmentoNaoEncontradoError:
        return FalhaBaseOficial(motivo=MSG_SEM_SEGMENTO)
    except NumeracaoNaoEncontradaError:
        return FalhaBaseOficial(motivo=MSG_SEM_NUMERACAO)


def geocodificar_endereco(request: HttpRequest, codlog: str, numero: object, score: float | None = None) -> HttpResponse:
    resolvido = resolver_endereco(codlog, numero)
    if isinstance(resolvido, FalhaBaseOficial):
        # o clique numa sugestão oficial é escolha explícita: falha vira aviso, sem fallback
        return render(request, "mapping/_aviso.html", contexto_aviso(resolvido.motivo))
    return renderizar_endereco(request, resolvido, score)
```

**`apps/search/views.py`** — o laço do Enter carrega a falha da base oficial até o candidato externo.

```python
MSG_LOGRADOURO_FORA_DA_BASE = "O logradouro não foi encontrado na base oficial."

REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    ...,
    TipoEntrada.GEOCODIFICACAO_EXTERNA: secao_geocodificacao_externa,
}

# resposta pronta · a base oficial falhou dizendo por quê · o candidato não casou com nada
Tentativa = HttpResponse | FalhaBaseOficial | None


def _candidatos_liberados(request: HttpRequest, candidatos: list[Candidato]) -> list[Candidato]:
    # autorização é orquestração: o roteador segue só lendo o texto, e a view tira o que custa cota
    if request.user.is_authenticated:
        return candidatos
    return [c for c in candidatos if c.tipo is not TipoEntrada.GEOCODIFICACAO_EXTERNA]


@require_POST
def rotear_busca(request: HttpRequest) -> HttpResponse:
    query = RoteamentoQuery(...)  # como hoje
    secoes = [
        secao
        for candidato in _candidatos_liberados(request, rotear_entrada(query).candidatos)
        if (render_secao := REGISTRO_SECOES.get(candidato.tipo)) is not None
        and (secao := render_secao(candidato)) is not None
    ]
    return render(request, "search/partials/_sugestoes.html", {"secoes": secoes})


@require_POST
def comitar(request: HttpRequest) -> HttpResponse:
    query = RoteamentoQuery(texto=request.POST.get("termo_pesquisa", ""), finished_typing=True)
    falha: FalhaBaseOficial | None = None
    for candidato in _candidatos_liberados(request, rotear_entrada(query).candidatos):
        tentativa = _acionar_candidato(request, candidato, falha)
        if isinstance(tentativa, HttpResponse):
            return tentativa
        if isinstance(tentativa, FalhaBaseOficial):
            falha = tentativa
    mensagem = falha.motivo if falha is not None else MSG_SEM_RESULTADO_COMMIT
    return render(request, "mapping/_aviso.html", contexto_aviso(mensagem))


def _acionar_candidato(
    request: HttpRequest,
    candidato: Candidato,
    falha: FalhaBaseOficial | None,
) -> Tentativa:
    ...  # demais ramos como hoje

    if isinstance(candidato, EnderecoParse):
        item = _primeiro(resolver_logradouro(ResolucaoLogradouroQuery(...)).itens)
        if item is None:
            return FalhaBaseOficial(motivo=MSG_LOGRADOURO_FORA_DA_BASE)
        codlog = f"{item.logradouro.codlog}{item.logradouro.dv}"
        resolvido = resolver_endereco(codlog, candidato.numero)
        if isinstance(resolvido, FalhaBaseOficial):
            return resolvido  # no Enter a falha não bloqueia: segue para o externo
        return renderizar_endereco(request, resolvido)

    if isinstance(candidato, GeocodificacaoExternaParse):
        geocodificador = geocodificador_externo()
        if geocodificador is None:
            return None  # sem provedor, o laço termina no aviso da base oficial
        return geocodificar_externo(request, geocodificador, candidato.texto, falha)

    return None
```

**`apps/geocodificacao_externa/views.py`** — `geocodificar_externo` da SPEC 003 inteiro: ganha a falha
que o trouxe até ali.

```python
MSG_FALLBACK = "{motivo} O resultado veio do serviço externo ({provedor}), fora da base oficial."


def geocodificar_externo(
    request: HttpRequest,
    geocodificador: GeocodificadorExterno,
    texto: str,
    falha: FalhaBaseOficial | None = None,  # ALTERADO nesta SPEC
) -> HttpResponse:
    entrada = GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto=texto),
        output_crs=MAP_OUTPUT_CRS,
    )
    try:
        endereco = geocodificador(entrada)
    except ProvedorIndisponivelError:
        return _aviso(request, MSG_INDISPONIVEL, falha)
    except SemResultadoAceitoError:
        return _aviso(request, MSG_SEM_RESULTADO, falha)
    contexto = _contexto_externo(endereco) | {"aviso_fallback": _aviso_fallback(falha, endereco)}
    return render(request, TEMPLATE_RESULTADO_EXTERNO, contexto)


def _aviso(request: HttpRequest, mensagem: str, falha: FalhaBaseOficial | None) -> HttpResponse:
    # no Enter, o aviso diz primeiro o que a base oficial não encontrou
    texto = mensagem if falha is None else f"{falha.motivo} {mensagem}"
    return render(request, "mapping/_aviso.html", contexto_aviso(texto))


def _aviso_fallback(falha: FalhaBaseOficial | None, endereco: EnderecoExternoFeature) -> str | None:
    if falha is None:
        return None  # veio do clique: a pessoa escolheu o externo, não há o que avisar
    provedor = ROTULO_PROVEDOR[endereco.attributes.provedor]
    return MSG_FALLBACK.format(motivo=falha.motivo, provedor=provedor)
```

## 7 · Caveats
`GEOCODIFICACAO_EXTERNA` entra como `TipoEntrada`, embora não seja uma forma de entrada e sim uma
estratégia de resolução do endereço por nome. É o que a faz caber no registro de seções e no laço do
Enter sem caso especial. O custo é que todo endereço por nome passa a ter ao menos dois candidatos, e
`RoteamentoResult.status` deixa de ser `UNICO` para eles; hoje ninguém lê `status` nem `match`.

O Enter e o clique tratam a mesma falha da base oficial de formas diferentes. O Enter é "o melhor que
der" e o clique numa sugestão oficial é escolha explícita. O custo é que número fora da faixa cai no
externo por um caminho e vira aviso pelo outro.

A opção externa aparece em toda busca de endereço por nome, mesmo quando a base oficial resolve. Ela
é o override da pessoa, e montá-la não gasta cota. O custo é uma linha a mais na lista de sugestões de
todo endereço.

Com o geocodificador externo desligado, o Enter em logradouro fora da base passa a responder "O
logradouro não foi encontrado na base oficial." no lugar do aviso genérico. O motivo precisa existir
para o aviso do fallback, e o mesmo texto serve aos dois casos. O custo é uma mudança de texto visível
num caminho que não tem nada de externo.

Os testes de `tests/services/domain/roteamento_busca/test_router.py` que comparam a lista exata de
tipos de um endereço por nome (`[ENDERECO_LOTE, ENDERECO]`) passam a incluir `GEOCODIFICACAO_EXTERNA`
no fim. O candidato novo muda a saída do roteador para essas entradas. O custo é editar testes de uma
SPEC já entregue.

## 8 · Testes (TDD)
Salvo quando o teste diz o contrário, o cliente dos testes de view está logado.

- `test_identifier_emite_geocodificacao_externa_com_o_texto_inteiro` — `rua augusta, 100 - consolação`
  gera o candidato com o texto como digitado, na última posição dos candidatos.
- `test_identifier_nao_emite_para_codlog_nem_sem_numero` — parametrizado: `12345, 100`, `rua augusta`
  e `rua x, s/n` não geram o candidato.
- `test_sugestoes_trazem_a_opcao_externa_por_ultimo_sem_chamar_o_provedor` — com um geocodificador
  dublê que falha se for chamado, o partial de sugestões traz a seção externa como a última.
- `test_sugestoes_omitem_a_opcao_sem_login_ou_sem_configuracao` — parametrizado: cliente anônimo, e
  cliente logado com a factory devolvendo `None`, recebem o partial sem a seção externa.
- `test_enter_resolvido_pela_base_oficial_nao_chama_o_provedor` — endereço que a interpolação resolve
  responde o ponto oficial, e o geocodificador dublê não é chamado.
- `test_enter_com_numero_fora_da_faixa_cai_no_externo_com_o_aviso` — a interpolação levanta
  `NumeracaoNaoEncontradaError`: a resposta é o resultado externo com o aviso trazendo
  `MSG_SEM_NUMERACAO` e o provedor.
- `test_enter_com_logradouro_fora_da_base_cai_no_externo_com_o_aviso` — o resolvedor não acha o
  logradouro: resultado externo com `MSG_LOGRADOURO_FORA_DA_BASE` no aviso.
- `test_enter_com_falha_tambem_no_externo_responde_os_dois_motivos` — base oficial sem segmento e
  `SemResultadoAceitoError` no externo: o aviso traz `MSG_SEM_SEGMENTO` seguido de `MSG_SEM_RESULTADO`.
- `test_enter_sem_login_ou_sem_configuracao_responde_o_motivo_da_base_oficial` — parametrizado:
  cliente anônimo, e cliente logado com a factory devolvendo `None`, com número fora da faixa,
  recebem o aviso com `MSG_SEM_NUMERACAO`, e o geocodificador dublê não é chamado.
- `test_clique_em_sugestao_oficial_que_falha_mantem_o_aviso` — POST em `address_geocoder:selecionar`
  com número fora da faixa responde `MSG_SEM_NUMERACAO`, e o geocodificador dublê não é chamado.

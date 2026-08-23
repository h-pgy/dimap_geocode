---
spec: criacao_usuarios/005
versao: v4
atualizado_em: 2026-08-22
testes_tdd: true
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a recusa passa pelo contrato de erros de formulário — mensagem em português, controle em
    realce e o lápis do campo recusado já aberto
  - v3: o valor do Resumo ganha átomo próprio e passa a quebrar dentro da célula
  - v4: o valor lido do `.campo-onsen` quebra junto, por alteração do átomo
---

# SPEC criacao_usuarios/005 — Editar servidor: o cadastro alterado por quem responde pela unidade

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP corrige o cadastro de um servidor no modal da
página dele — identificação, e-mail, lotação, cargos e foto —, para que a competência administrativa
de quem trabalha ali reflita a realidade sem passar pelo admin do Django.

## 2 · Condições de pronto
- [ ] **Editar servidor** é ação **estrutural** inscrita no catálogo, com abertura e gravação em rotas
      protegidas: quem responde pela direção a exerce sem concessão gravada, e quem não dirige unidade
      alguma recebe **403**.
- [ ] A unidade conferida é a **de lotação do servidor editado**, derivada no servidor: abrir ou gravar
      o cadastro de quem está fora do alcance é recusado com 403 e fica registrado, e mandar a própria
      unidade no request não muda isso.
- [ ] **Mover para fora do alcance é recusado**: a unidade de **destino** é conferida junto com a de
      origem, com 403 antes de a view rodar.
- [ ] O **botão de editar** só aparece a quem tem a competência **e** o alcance sobre aquele servidor.
- [ ] A gravação altera identificação, e-mail, lotação, cargos e foto **num ato só**, e o que não foi
      tocado permanece como estava — inclusive a foto, quando nenhuma nova é enviada.
- [ ] **Toda** recusa — campo obrigatório em branco, e-mail torto, RF ou e-mail já usado por outro,
      titular com cargo incompatível com a unidade de destino — volta no **modal, que segue aberto**,
      com o motivo em português na tarja e o **controle recusado em realce**; o que foi digitado
      permanece nos campos e nada é gravado.
- [ ] O **lápis do controle recusado chega aberto**: no padrão `.campo-onsen` o input fica escondido
      atrás do toggle, e realçar um campo que ninguém vê não corrige nada.
- [ ] Gravado, o **modal fecha** e a página do servidor passa a mostrar o cadastro novo **sem
      recarregar**, com cada valor do Resumo contido na **própria célula**: e-mail longo, que é um
      token sem espaço, quebra em vez de invadir o rótulo e o valor vizinhos, em uma coluna ou em
      duas. O **lado lido do modal**, que mostra o mesmo cadastro, cabe do mesmo jeito.
- [ ] Editar é **ato registrado** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)),
      com a operação e o RF do servidor como alvo, distinguível de criar.
- [ ] O sistema **sobe** com a ação declarada, cuja rota recebe o id do servidor no caminho: o
      system check do catálogo confere que o **nome da rota existe**, e não que ela monte URL sem
      argumento.
- [ ] O design foi aprovado no **mock**, e peça nova foi portada para `static/src/tema-dimap.dev.css` e
      renderizada no styleguide antes de qualquer template da aplicação usá-la.
- [ ] **Duas peças novas e um átomo alterado**: a molécula `_tarja_recusa.html`, **extraída** da que
      já existe em `_formulario_servidor.html` e composta dos átomos `.tarja-vinculo` +
      `.tarja-vinculo-critica`; o átomo `.valor-leitura`, o valor de um par rótulo/valor em leitura,
      par do `.text-overline` que já existe; e o `.campo-onsen-valor`, que passa a quebrar — peça
      implementada, alterada com aval explícito do usuário (§3.4). Os `.campo-realce-*` do tema (SPEC
      [formularios/001](../formularios/001-erros-de-formulario.md)) são consumidos como estão.

## 3 · Domínio
Nenhum model novo: o cadastro é o da SPEC [004](004-criar-servidor.md), aqui alterado em vez de criado.
O que muda de modelagem é o **alcance**, que passa a poder nomear mais de um alvo e a nomeá-los por
pessoa: editar alguém incide sobre a unidade em que ele está e sobre aquela para a qual vai.

**`services/domain/autorizacao/contratos.py`**
```python
class TipoAlcance(BaseModel):
    """O que todo alcance é: até onde a ação pode incidir, e os parâmetros do request que carregam
    os alvos. Abstrato — cada alcance concreto é um subtipo, nunca uma instância desta classe."""

    model_config = ConfigDict(frozen=True)

    # ALTERADO nesta SPEC: era `parametro_id_unidade_alvo: str`. São os NOMES dos parâmetros na
    # assinatura da view/formulário, e não ids reais. Viram tupla porque um ato pode incidir sobre
    # mais de uma unidade, e todas precisam cair no alcance; e perdem o "id_unidade" do nome porque
    # o parâmetro nem sempre carrega uma unidade — pode carregar quem está lotado nela.
    parametros_alvo: tuple[str, ...]


class UnidadesSubordinadas(TipoAlcance):
    """O alcance de quem dirige: as unidades que o perfil dirige e todas abaixo delas. O parâmetro
    carrega o id da unidade-alvo."""

    parametros_alvo: tuple[str, ...] = ("unidade",)


class LotacaoAtualEDestino(TipoAlcance):
    """ALTERADO nesta SPEC: subtipo novo. O mesmo alcance, com dois alvos — a unidade em que o
    servidor está, lida da lotação dele, e a unidade para a qual o formulário o manda."""

    parametros_alvo: tuple[str, ...] = ("servidor", "unidade")
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Perfil` com `email`](004-criar-servidor.md) — o cadastro que este ato altera.
- [`acao_protegida` e `registrar_ato`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  a rota protegida, os alvos conferidos contra o alcance e o rastro do ato.
- [`alcance_do_perfil`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — "quais unidades
  este perfil alcança?"; é contra este conjunto que origem e destino são conferidas.
- [`has_perm`](../autorizacao/003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta ação
  estrutural?"; quem lê a direção da unidade é o backend, não esta tela.
- [`Perfil.clean` e `cargo_titulariza`](../user_admin/014-titular-da-unidade.md) — "este cargo
  titulariza a unidade de destino?"; a recusa é do model, e esta SPEC só a leva ao modal.
- [`contexto_modal_perfil`](../user_admin/017-pagina-do-servidor.md) — o modal já montado e preenchido,
  que aqui ganha destino de submit.
- [`FORMULARIO_SERVIDOR` e `LeitorDeFormulario`](../formularios/001-erros-de-formulario.md) — "como
  esta recusa se diz, e qual controle ela realça?"; o catálogo é o **mesmo** da criação, porque os
  controles são os mesmos — só o DTO lido muda.

**Mock:** [005-mock-editar-servidor.html](005-mock-editar-servidor.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Avisar por e-mail a troca de endereço ou de RF — sem dono ainda.
- Exonerar servidor e reativar exonerado — sem dono ainda.
- Remover a foto sem enviar outra — sem dono ainda.
- Marcar titular, designar substituto e registrar impedimento — SPECs `user_admin/014` e `015`, que já
  os entregam na própria página do servidor.
- Histórico de alterações do cadastro, campo a campo: o que fica é a execução registrada (SPEC
  `autorizacao/004`) — sem dono ainda.
- Alcance com **regra de pertencimento** diferente de unidades subordinadas — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/protecao.py` → `acao_protegida`, `conferir_alvo`, `registrar_ato`: a barreira, a
  conferência do alvo e o rastro.
- `@apps/competencias/consulta.py` → `alcance_do_perfil`: as unidades alcançadas, em conjunto de ids.
- `@apps/competencias/utils.py` → `instanciar_acao`; `@apps/competencias/registro.py` →
  `_construir_registro`: onde a ação nova se inscreve.
- `@apps/user_admin/cadastro.py` (SPEC 004) → `DesfechoCadastro`, `criar_servidor` e o tratamento de
  recusa do model: o molde do ato irmão, do formulário cru ao desfecho.
- `@apps/user_admin/schemas.py` (SPEC 004) → `NovoServidor` e `CargoOpcional`: o DTO irmão e o select
  vazio como ausência.
- `@apps/user_admin/formularios.py` (SPEC 004) → `FORMULARIO_SERVIDOR` e `traduzir_recusa`: o catálogo
  **reusado como está** — mesmos sete controles, mesmos rótulos.
- `@services/utils/erros_formulario` (SPEC [formularios/001](../formularios/001-erros-de-formulario.md))
  → `LeitorDeFormulario`, `RecusaDeFormulario`; e `@apps/core/erros_formulario.py` →
  `de_validation_error`: a ponte do `ValidationError` do model.
- `@apps/user_admin/context.py` → `contexto_modal_perfil`, `contexto_pagina_perfil`,
  `_valores_do_formulario` (SPEC 004): a conversão dos ids que o `selected` do select compara.
- `@templates/user_admin/partials/_modal_editar_perfil.html` → o modal preenchido, com os campos que
  só viram campo ao abrir o lápis.
- `@templates/user_admin/partials/_formulario_servidor.html` → a tarja de recusa, hoje inline, que
  esta SPEC extrai para partial e as duas telas passam a incluir.
- `@static/src/tema-dimap.dev.css` → `.campo-realce-erro` e irmãos, o átomo do controle em realce, já
  portado e no styleguide; `.tarja-vinculo` + `.tarja-vinculo-critica`, os da tarja; `.text-overline`
  e `.text-code`, os do par rótulo/valor do Resumo.
- Skills: `erros-de-formulario` (o padrão desta tela; `pydantic-validation-errors` cobre o caso
  contrário — rota que não é formulário), `componentes-frontend`, `daisyui`, `htmx`, `mock`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/user_admin/acoes_declaradas.py`** — a ação, ao lado da de criar.
```python
ACAO_EDITAR_SERVIDOR = instanciar_acao(
    slug="user_admin.editar_servidor",
    nome="Editar cadastro de servidor",
    nome_curto="Editar servidor",
    tooltip="Altera identificação, lotação, cargos e foto de um servidor.",
    url_name="user_admin:editar_perfil",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    # Duas incidências, não uma: o ato tira alguém de uma unidade e o põe em outra, e as duas
    # precisam estar no alcance de quem assina. Os nomes dos parâmetros já são o default do alcance
    # — `servidor` vem do caminho da rota, `unidade` vem do formulário.
    alcance=LotacaoAtualEDestino(),
)
```

**`apps/competencias/protecao.py`** — a conferência passa a percorrer os alvos declarados, e o
dispatch responde "como este parâmetro vira unidade".
```python
def conferir_alvo(
    request: HttpRequest,
    perfil: Perfil,
    acao: AcaoDominio,
    kwargs_da_rota: Mapping[str, object],
) -> None:
    if acao.alcance is None:
        return
    valores = _valores_dos_alvos(request, acao.alcance, kwargs_da_rota)
    # Leitura sem alvo escolhido: a tela abre e escolhe depois. Em requisição que altera estado a
    # ausência já virou 400 lá dentro.
    if not valores:
        return
    # Uma passagem só pela árvore, e não uma por alvo: o alcance é o mesmo para os dois.
    alcance = alcance_do_perfil(perfil)
    if not all(unidade in alcance for unidade in _unidades_alvo(acao.alcance, valores)):
        raise PermissionDenied


def _valores_dos_alvos(
    request: HttpRequest,
    alcance: TipoAlcance,
    kwargs_da_rota: Mapping[str, object],
) -> dict[str, int]:
    """Cada parâmetro declarado, procurado no caminho da rota, no corpo e na query string. Ausência
    tem duas leituras, e é aqui que elas se separam: em leitura é a tela ainda sem alvo escolhido;
    em requisição que altera estado é alvo faltando, e sem este ramo um POST que omitisse o
    parâmetro escaparia da conferência inteira."""
    valores: dict[str, int] = {}
    for parametro in alcance.parametros_alvo:
        id_bruto = _valor_do_parametro(request, parametro, kwargs_da_rota)
        if id_bruto is None:
            if request.method in METODOS_QUE_ALTERAM:
                raise BadRequest(f"Parâmetro obrigatório ausente: '{parametro}'.")
            continue
        if not id_bruto.isdigit():
            # Id malformado é 400, não 500: o valor vem do cliente e nunca chega ao `int()` sem
            # passar por aqui.
            raise BadRequest(f"Id malformado para '{parametro}': '{id_bruto}'.")
        id_alvo = int(id_bruto)
        valores[parametro] = id_alvo
    return valores


def _unidades_alvo(alcance: TipoAlcance, valores: Mapping[str, int]) -> tuple[int, ...]:
    """Despacha pelo subtipo concreto: é ele que sabe se o número é uma unidade ou a pessoa lotada
    nela. A regra de pertencimento é a mesma para todos e fica escrita uma vez só, em
    `conferir_alvo`; alcance novo sem ramo aqui estoura em vez de passar batido."""
    if isinstance(alcance, UnidadesSubordinadas):
        return (valores["unidade"],)
    if isinstance(alcance, LotacaoAtualEDestino):
        # A origem é lida no banco, nunca recebida do cliente: aceitá-la do request deixaria
        # qualquer um editar quem quisesse, bastando mandar a própria unidade.
        origem = _lotacao_de(valores["servidor"])
        destino = valores.get("unidade")
        return (origem,) if destino is None else (origem, destino)
    raise NotImplementedError(f"alcance sem conferência: {type(alcance).__name__}")


def _lotacao_de(id_servidor: int) -> int:
    """Servidor inexistente não tem lotação e por isso não está no alcance de ninguém: 403, e não
    404 — a rota protegida não confirma quem existe."""
    lotacao = Perfil.objects.filter(pk=id_servidor).values_list("unidade_id", flat=True).first()
    if lotacao is None:
        raise PermissionDenied
    return lotacao


def pode_executar(
    usuario: Perfil | AnonymousUser,
    acao: AcaoImplementada,
    id_unidade_alvo: int | None = None,
) -> bool:
    """A mesma dupla conferência do decorator, na forma de que a TELA precisa: responde em vez de
    levantar. O router filtra e a rota decide (§3.5) — esconder o botão é UX, e a barreira segue
    sendo o `acao_protegida`."""
    if not usuario.has_perm(acao.acao.slug):
        return False
    if acao.acao.alcance is None or id_unidade_alvo is None:
        return True
    return id_unidade_alvo in alcance_do_perfil(usuario)
```

**`apps/competencias/checks.py`** — o check do `url_name` passa a perguntar pelo nome da rota.
```python
def _rota_existe(url_name: str) -> bool:
    """`reverse` cru só resolve rota SEM parâmetro, e ação que incide sobre um objeto tem o id no
    caminho. O que o check precisa provar é que o nome existe — montar a URL é da view, que tem o
    argumento em mãos."""
    namespace, _, nome = url_name.rpartition(":")
    resolver = get_resolver()
    if namespace:
        try:
            resolver = resolver.namespace_dict[namespace][1]
        except KeyError:
            return False
    return nome in resolver.reverse_dict
```

**`apps/user_admin/urls.py`** — o nome do parâmetro é o que o contrato da ação declara.
```python
urlpatterns = [
    ...,
    path("servidores/<int:pk>/", views.pagina_perfil, name="pagina_perfil"),
    # `servidor`, e não `pk`: é o parâmetro que o alcance da ação nomeia.
    path("servidores/<int:servidor>/editar/", views.editar_perfil, name="editar_perfil"),
    path("servidores/<int:servidor>/gravar/", views.gravar_edicao, name="gravar_edicao"),
]
```

**`apps/user_admin/schemas.py`** — o DTO do ato, ao lado do `NovoServidor`.
```python
class EdicaoServidor(BaseModel):
    """ALTERADO na v2: quem o constrói é o `LeitorDeFormulario`, e não a view — construí-lo aqui
    entregaria a recusa ao `PydanticValidationMiddleware`, cuja resposta o HTMX troca no alvo da
    requisição, que é o poço do modal (SPEC formularios/001, Caveats). Sem `url_acesso`: editar não
    manda e-mail nenhum."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    rf: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=1, max_length=100)
    sobrenome: str = Field(min_length=1, max_length=150)
    email: EmailStr
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
```

**`apps/user_admin/formularios.py`** — o leitor da edição, ao lado do da criação. O catálogo **não é
declarado de novo**.
```python
# Mesmos sete controles, mesmos rótulos, mesmas frases: o que muda entre criar e editar é o DTO
# lido, não como a recusa se diz. Um catálogo irmão seria a mesma tabela com outro nome.
ler_edicao_servidor = LeitorDeFormulario(EdicaoServidor, FORMULARIO_SERVIDOR)
```

**`apps/user_admin/cadastro.py`** — o ato, no mesmo módulo do cadastro e com o mesmo desfecho.
```python
def editar_servidor(
    valores: Mapping[str, Any],
    foto: UploadedFile | None = None,
) -> DesfechoCadastro:
    """Um ato só: ou o cadastro inteiro passa pela validação do model, ou nada muda.

    ALTERADO na v2: recebe o formulário cru e delega a leitura ao `LeitorDeFormulario`, como o
    `criar_servidor`. O `try` mora aqui, e não na view, pelo mesmo motivo: é este módulo que sabe o
    que a recusa significa para o cadastro."""
    leitura = ler_edicao_servidor(valores)
    edicao = leitura.dto
    if edicao is None:
        # O `or` é só o que o tipo pede, não um caso real.
        return DesfechoCadastro(perfil=None, recusa=leitura.recusa or RecusaDeFormulario())
    perfil = get_object_or_404(Perfil, pk=edicao.servidor_id)
    _aplicar(perfil, edicao, foto)
    try:
        perfil.full_clean(exclude=["password"])
        perfil.save()
    except ValidationError as recusa:
        # RF e e-mail já usados por outro, e o titular cujo cargo não titulariza a unidade de
        # destino: as três recusas são do model, e chegam juntas por aqui. A ponte de `apps/core`
        # preserva o `code`, que é o que faz o RF e o e-mail realçarem o controle certo; a do
        # titular nomeia `e_titular`, que não é controle desta tela, e por isso cai na tarja.
        return DesfechoCadastro(perfil=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCadastro(perfil=perfil)


def _aplicar(perfil: Perfil, edicao: EdicaoServidor, foto: UploadedFile | None) -> None:
    """Foto sem arquivo novo é campo não tocado, não foto apagada: o formulário manda o `input`
    vazio a cada gravação, e sobrescrever com ele limparia o que já está lá."""
    perfil.rf = edicao.rf
    perfil.nome = edicao.nome
    perfil.sobrenome = edicao.sobrenome
    perfil.email = edicao.email
    perfil.unidade_id = edicao.unidade_id
    perfil.cargo_base_id = edicao.cargo_base_id
    perfil.cargo_comissao_id = edicao.cargo_comissao_id
    if foto is not None:
        perfil.foto = foto
```

**`apps/user_admin/context.py`** — o modal passa a separar o que se **lê** do que se **digita**.
```python
def contexto_modal_perfil(perfil: Perfil, valores: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """ALTERADO na v2: ganha `valores`. O modal tem duas faces do mesmo servidor — o lado LIDO do
    `.campo-onsen`, que mostra o que está gravado, e o input atrás do lápis, que mostra o que a
    pessoa digitou. Na abertura os dois coincidem e `valores` sai do próprio perfil; na recusa eles
    divergem, e é essa divergência que deixa a pessoa comparar o que tentou com o que vale.

    Por isso `perfil` continua sendo o model, e não um dicionário como no formulário de criação: o
    lado lido pede `unidade.sigla`, `cargo_base.nome`, o avatar e a tarja de titular."""
    return (
        _catalogos_de_lotacao()
        | _contexto_do_modal_de_unidade()
        | {
            "perfil": perfil,
            "valores": valores if valores is not None else _valores_do_perfil(perfil),
            "imagem": _imagem_do_perfil(perfil),
            "cor_unidade_hex": hex_da_cor(perfil.cor_unidade),
        }
    )


def _valores_do_perfil(perfil: Perfil) -> dict[str, Any]:
    """A abertura do modal, dita na mesma língua da recusa: os ids já como inteiros, que é o que o
    `selected` do select compara."""
    return {
        "rf": perfil.rf,
        "nome": perfil.nome,
        "sobrenome": perfil.sobrenome,
        "email": perfil.email,
        "unidade_id": perfil.unidade_id,
        "cargo_base_id": perfil.cargo_base_id,
        "cargo_comissao_id": perfil.cargo_comissao_id,
    }


def contexto_edicao_recusada(
    perfil: Perfil,
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    # `perfil` vem do banco INTOCADO: `editar_servidor` altera a instância dele em memória antes do
    # `full_clean`, e reaproveitá-la mostraria no lado lido o valor que a recusa impediu de gravar.
    return contexto_modal_perfil(perfil, _valores_do_formulario(valores)) | {
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }
```

**`apps/user_admin/views.py`** — a view chega com competência, origem e destino já conferidos.
```python
@acao_protegida(ACAO_EDITAR_SERVIDOR)
def editar_perfil(request: HttpRequest, servidor: int) -> HttpResponse:
    """Só o partial do modal: a página de leitura não o carrega, e os catálogos dos selects só são
    consultados quando alguém abre o lápis."""
    # Nenhuma conferência de lotação escrita aqui: o contrato da ação declara o alcance pela pessoa,
    # e o decorator já resolveu a unidade dela.
    return render(request, TEMPLATE_MODAL_PERFIL, contexto_modal_perfil(_perfil(servidor)))


@acao_protegida(ACAO_EDITAR_SERVIDOR)
@require_POST
def gravar_edicao(request: HttpRequest, servidor: int) -> HttpResponse:
    # ALTERADO na v2: a view traduz nome de controle em nome de campo e NÃO constrói o DTO — quem o
    # constrói é o ato. `.get(..., "")` porque só `unidade` tem rede (o decorator devolve 400 quando
    # ela falta); nos demais, chave ausente daria 500 na rota que existe para transformar entrada
    # ruim em recusa na tela.
    valores = {
        # Do caminho da rota, nunca do corpo: é o mesmo id que o decorator conferiu.
        "servidor_id": servidor,
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
    }
    desfecho = editar_servidor(valores, foto=request.FILES.get("foto"))
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_MODAL_PERFIL,
            contexto_edicao_recusada(_perfil(servidor), valores, desfecho.recusa),
            status=422,
        )
    registrar_ato(
        request,
        operacao="editar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    # O poço volta vazio — é assim que o modal fecha — e a página se atualiza pelo swap fora de
    # banda que o partial carrega.
    return render(request, TEMPLATE_EDICAO_CONCLUIDA, contexto_pagina_perfil(desfecho.perfil))


def pagina_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    """Rota aberta de leitura (SPEC user_admin/017). O que a autorização decide aqui é um botão."""
    perfil = _perfil(pk)
    return render(
        request,
        TEMPLATE_PAGINA_PERFIL,
        contexto_pagina_perfil(perfil)
        | {"pode_editar": pode_executar(request.user, ACAO_EDITAR_SERVIDOR, perfil.unidade_id)},
    )
```

**`templates/user_admin/partials/_tarja_recusa.html`** — a molécula extraída do que já existe inline
em `_formulario_servidor.html`; as duas telas passam a incluí-la, e ela não inventa átomo nenhum.
```html
{# Composta de `.tarja-vinculo` + `.tarja-vinculo-critica`, que já estão no tema. Lê `erros`, que é #}
{# sempre `recusa.mensagens` — inclusive as gerais, que não realçam controle algum.                #}
{% if erros %}
  <div class="tarja-vinculo tarja-vinculo-critica flex items-start gap-2">
    ...
    <ul class="text-[13px] text-base-content/80 list-disc list-inside mt-0.5">
      {% for erro in erros %}<li>{{ erro }}</li>{% endfor %}
    </ul>
  </div>
{% endif %}
```

**`templates/user_admin/partials/_modal_editar_perfil.html`** — o modal ganha destino, e o alvo é o
próprio poço: a recusa o remonta aberto, o sucesso o esvazia.
```html
{# hx-encoding: sem isto a foto não sobe — o HTMX manda urlencoded por padrão. #}
<form hx-post="{% url 'user_admin:gravar_edicao' perfil.pk %}"
      hx-encoding="multipart/form-data"
      hx-target="#poco-modal"
      hx-swap="innerHTML">
  {% include "user_admin/partials/_tarja_recusa.html" %}
```

E cada `.campo-onsen` passa a ler três coisas: o valor gravado no lado lido, o digitado no input, e o
realce — que também **abre o lápis**.
```html
{# O toggle chega marcado quando o controle foi recusado: o input do `.campo-onsen` fica escondido #}
{# atrás dele, e realçar um campo que ninguém vê não corrige nada. Sem recusa, `realce.rf` é       #}
{# string vazia e o `{% if %}` não marca — o modal abre como sempre abriu.                         #}
<input type="checkbox" id="editar-campo-rf" class="campo-onsen-toggle"{% if realce.rf %} checked{% endif %} />
...
{# O lado LIDO segue no perfil gravado; só o input recebe o digitado. #}
<p class="campo-onsen-valor text-code">{{ perfil.rf }}</p>
<input type="text" name="rf" class="input input-glass {{ realce.rf }}" value="{{ valores.rf }}" />
```

**`templates/user_admin/partials/_edicao_concluida.html`** — a resposta do sucesso: nada para o poço,
e a página trocada fora de banda.
```html
{# O poço fica vazio (este partial não escreve nada nele), e é isso que fecha o modal: o toggle sai #}
{# do documento junto com a caixa. O painel de leitura entra pelo hx-swap-oob, no lugar dele.       #}
<div id="painel-servidor" hx-swap-oob="outerHTML">
  {% include "user_admin/partials/_identidade_perfil.html" %}
  {% include "user_admin/partials/_secao_resumo_perfil.html" %}
</div>
```

**`static/src/tema-dimap.dev.css`** — o átomo do valor em leitura, par do `.text-overline`.
```css
/* O Resumo repete `text-[15px] ... mt-0.5` em seis células e nenhuma delas quebra: o e-mail é um
   token sem espaço, estoura a coluna do grid e passa por cima do rótulo vizinho. `wrap-anywhere`
   quebra DENTRO da palavra — `break-words` só quebra onde já há oportunidade, e aqui não há.
   Sem cor: o Resumo tem três (valor presente, valor ausente e o RF em monoespaçada), e embuti-las
   aqui exigiria um modificador por cor ou faria o átomo vencer o `.text-code` que já existe. */
.valor-leitura { @apply text-[15px] mt-0.5 wrap-anywhere; }

/* ALTERAÇÃO (SPEC criacao_usuarios/005): o mesmo e-mail no lado lido do campo que se abre. Aqui o
   `min-w-0` já deixava a célula encolher, e era só isso que faltava para o texto acompanhar. */
.campo-onsen-valor { @apply flex-1 min-w-0 text-[15px] text-base-content/90 py-1.5 wrap-anywhere; }
```

**`templates/user_admin/partials/_secao_resumo_perfil.html`** — cada célula compõe o átomo e mantém
a cor que já declara.
```html
{# `min-w-0` na célula deixa a coluna do grid encolher; sem o átomo no valor, quem encolhe é a #}
{# coluna e o texto continua saindo dela.                                                      #}
<div class="min-w-0">
  <p class="text-overline">E-mail</p>
  <p class="valor-leitura {% if perfil.email %}text-base-content/90{% else %}text-base-content/40{% endif %}">
    {{ perfil.email|default:"— sem e-mail cadastrado —" }}
  </p>
</div>
```

## 7 · Caveats
**O alcance passa a nomear uma tupla de alvos, e o subtipo é quem sabe convertê-los em unidade.** Sem
o segundo alvo, mover alguém para fora do próprio ramo passaria pela barreira — a origem estaria no
alcance e o destino ninguém conferiria; sem a conversão no subtipo, a origem teria de vir do request,
e mandar a própria unidade abriria a edição de qualquer servidor. Custo: o snippet da SPEC
`autorizacao/004` mostra um campo que o código não tem mais, e `conferir_alvo` cresceu de uma
conferência para um laço com dispatch.

**O check do catálogo passa a provar que o nome da rota existe, não que ela monte URL.** Ação que
incide sobre um objeto tem o id no caminho, e `reverse` sem argumento não resolve rota assim. Custo:
o check deixa de pegar o `url_name` que existe mas está declarado com a assinatura errada — um nome
que exija dois argumentos passa aqui e só quebra quando o menu tentar montar o link.

**A conferência lê o banco a cada requisição protegida, e servidor inexistente recebe 403 em vez de
404.** O decorator roda antes da view, e uma pk sem linha não está no alcance de ninguém. Custo: mais
uma consulta por abertura de modal e por gravação, somada à árvore que `alcance_do_perfil` refaz, e um
id errado deixa linha de negativa sem a tela distinguir "não existe" de "não é seu".

**Mover de unidade é editar, e não ato próprio.** A lotação é campo do cadastro como os outros, e
separá-la exigiria uma segunda ação, com sua tela, para trocar um `ForeignKey`. Custo: quem edita
também remove, dentro do ramo, e o histórico não distingue uma correção de nome de uma transferência
— só a operação `editar` fica gravada, com o RF.

**Trocar o e-mail ou o RF não avisa ninguém.** O e-mail novo passa a valer sem confirmação, e o RF é a
credencial de entrada. Custo: um erro de digitação em qualquer dos dois deixa a pessoa sem como
entrar e sem como ser avisada, e o conserto é outra edição.

**A foto só é substituída quando um arquivo novo sobe.** O `input` de arquivo viaja vazio a cada
gravação, e tratá-lo como valor apagaria a foto de quem editasse o nome. Custo: não existe caminho
para remover a foto e voltar ao avatar de iniciais.

**`DesfechoCadastro` serve aos dois atos.** Criar e editar têm o mesmo desfecho — o perfil, ou a
`RecusaDeFormulario` que diz o motivo e o controle —, e um tipo por ato seria a mesma estrutura com
dois nomes. Custo: o nome fala de cadastro e é usado também na alteração, e um dos dois atos ganhando
desfecho próprio quebra o outro.

**O modal precisa de duas leituras do mesmo servidor, e por isso não repopula como o formulário de
criação.** Lá o contexto troca o `perfil` por um dicionário do que foi digitado; aqui o lado lido do
`.campo-onsen` pede `unidade.sigla`, `cargo_base.nome`, o avatar e a tarja de titular, que só o model
tem. Então `perfil` continua sendo o model e o digitado entra por `valores`. Custo: o template lê de
duas fontes e é possível trocá-las por engano, mostrando no lado lido o que a recusa impediu de
gravar — e o `perfil` da recusa tem de vir de uma consulta nova, porque o do ato já foi alterado em
memória antes do `full_clean`.

**A recusa do titular cai na tarja, sem realçar nada.** O `clean()` a levanta nomeando `e_titular`,
que não é controle desta tela — o que precisa mudar é o cargo em comissão ou a unidade de destino, e
o contrato não adivinha qual dos dois. Custo: a única recusa do model que não realça campo algum é
justamente a mais difícil de entender, e quem a recebe lê a frase e procura o campo sozinho.

**O átomo do valor em leitura carrega tipo e quebra, não cor.** O Resumo tem três cores de valor — o
presente, o ausente e o RF em monoespaçada —, e nenhuma delas cabe num átomo só sem um modificador por
cor ou sem sobrescrever o `.text-code`. Custo: célula nova pode nascer com o átomo e sem cor alguma,
herdando a do contêiner sem que nada acuse.

**O `.campo-onsen-valor` é alterado, e não composto.** Envolver o valor lido numa peça nova só para
quebrar duplicaria o átomo que já existe, e a alteração tem aval explícito do usuário (§3.4). Custo: a
quebra chega junto ao modal da página da unidade, que compõe o mesmo átomo e não foi olhado nesta
iteração.

**Recusa que só nomeia `servidor_id` sai muda.** O campo não tem input, então o tradutor o manda para
`gerais` — e ali descarta erro sem mensagem, que é o caso de todo erro do Pydantic. Risco baixo: o id
vem do caminho da rota, já convertido pelo `<int:...>` e conferido pelo decorator. Custo: existe uma
recusa possível que não se explica em tela, a mesma da `url_acesso` na SPEC 004.

## 8 · Testes (TDD)
Dois grupos. O **comportamento** obedece ao teto de 10; a **bateria de segurança** da skill
`acao-administrativa` vem além dele. Quase todos exigem `Perfil` gravado e carregam o marker `banco`;
o do system check é puro.

A tradução em si — regra declarada, tom, sufixo `_id`, ponte do Django — já é fixada pelos testes da
SPEC [formularios/001](../formularios/001-erros-de-formulario.md); os daqui param no modal.

**Comportamento**

- `test_gravacao_altera_o_cadastro_num_ato_so` — identificação, e-mail, lotação e cargos mudam juntos;
  a foto de quem não enviou arquivo novo permanece. *(marker `banco`)*
- `test_recusa_volta_no_modal_realcada_sem_gravar` — RF ou e-mail já usado por outro devolvem o modal
  com o motivo em português, `campo-realce-erro` no controle repetido e **o lápis dele aberto**; o
  digitado permanece no input e o lado lido segue mostrando o que está gravado. Campo em branco e
  e-mail torto fazem o mesmo caminho, e nada é gravado em nenhum dos casos. *(marker `banco`)*
- `test_recusa_do_titular_vai_para_a_tarja` — cargo incompatível com a unidade de destino devolve o
  motivo na tarja e não realça controle algum, porque o campo que a recusa nomeia não é um deles.
  *(marker `banco`)*
- `test_sucesso_fecha_o_modal_e_atualiza_a_pagina` — a resposta não devolve modal algum e traz o painel
  do servidor em swap fora de banda, com os dados novos. *(marker `banco`)*
- `test_botao_de_editar_so_aparece_para_quem_pode` — a página do servidor do próprio ramo traz o botão;
  a de servidor de outro ramo, não. *(marker `banco`)*
- `test_check_aceita_rota_com_argumento` — ação cujo `url_name` exige o id no caminho passa no system
  check; nome inexistente e namespace inexistente seguem reprovando.

**Segurança da ação** — bateria da skill `acao-administrativa`, fora do teto.

- `test_anonimo_vai_para_o_login_sem_deixar_linha` — o anônimo é redirecionado, não recebe 403 e não
  gera execução. *(marker `banco`)*
- `test_autenticado_sem_competencia_recebe_403_registrado` — perfil logado sem a ação recebe 403 ao
  abrir o modal e ao gravar, e as duas tentativas ficam gravadas. *(marker `banco`)*
- `test_estrutural_libera_quem_dirige_sem_concessao` — quem responde pela direção abre o modal sem
  concessão gravada; quem não dirige e não tem concessão, não. *(marker `banco`)*
- `test_concessao_em_outra_unidade_nao_libera` — a ação concedida ao cargo noutra unidade não abre o
  cadastro de quem está fora dela. *(marker `banco`)*
- `test_perfil_fora_de_exercicio_nao_exerce` — impedido e exonerado recebem 403, ainda que dirijam a
  unidade no papel. *(marker `banco`)*
- `test_alcance_vem_da_lotacao_do_servidor` — o servidor do próprio ramo abre; o de outro ramo recebe
  403 e deixa linha, com o id do caminho como única origem do alvo. *(marker `banco`)*
- `test_unidade_forjada_no_request_nao_abre_servidor_alheio` — mandar a própria unidade no POST não
  contorna a lotação lida no banco: segue 403. *(marker `banco`)*
- `test_mover_para_fora_do_alcance_e_recusado` — POST cuja unidade de **destino** é de outro ramo
  recebe 403 antes de a view rodar, e o cadastro segue como estava. *(marker `banco`)*
- `test_gravar_sem_o_parametro_do_alvo_e_400` — POST que omite `unidade` é recusado antes de a view
  rodar, e a recusa não vira linha de negativa. *(marker `banco`)*
- `test_acao_inativa_nao_libera_ninguem` — com a projeção marcada inativa, a concessão gravada deixa de
  abrir a rota. *(marker `banco`)*
- `test_execucao_registrada_com_a_lotacao_do_momento` — a gravação autorizada guarda unidade e cargos
  vigentes no ato, com a operação `editar` e o RF como alvo, distinguível da criação do mesmo servidor.
  *(marker `banco`)*
- `test_ato_em_substituicao_diz_por_quem_responde` — o substituto que age pela competência do afastado
  deixa gravado quem cobria; quem age por competência própria deixa o campo vazio. *(marker `banco`)*
- `test_abrir_o_modal_nao_vira_registro` — o GET autorizado do modal não gera linha; o mesmo GET negado
  gera. *(marker `banco`)*
- `test_gravacao_so_por_post` — GET na rota de escrita é recusado, e o cadastro não muda.
  *(marker `banco`)*

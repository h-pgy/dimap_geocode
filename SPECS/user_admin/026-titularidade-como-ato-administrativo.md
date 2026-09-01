---
spec: user_admin/026
versao: v1
atualizado_em: 2026-08-31
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/026 — Titularidade como ato administrativo: definir, trocar e destituir titular de unidade

## 1 · User story
Quem responde pela direção de uma unidade superior da DIMAP (ou quem administra o sistema) nomeia,
troca e destitui o titular de uma unidade subordinada, na página da própria unidade ou pelo card no
Painel de Ações, para manter formalmente designada a autoridade responsável pela unidade e por suas
canetas estruturais.

## 2 · Condições de pronto
- [x] **Definir titular** é ação **estrutural** inscrita no catálogo (`unidades.definir_titular`),
      com as rotas protegidas: quem dirige a unidade superior a exerce sem concessão prévia gravada;
      quem não dirige unidade superior ou tenta praticar o ato sobre a própria unidade recebe **403**.
- [x] O alcance é **estritamente subordinado** (`UnidadesEstritamenteSubordinadas`): incide sobre a
      unidade-alvo, que precisa estar no ramo abaixo de quem assina — assinar sobre a própria unidade
      dirigida ou sobre outro ramo é recusado com **403 registrado**.
- [x] O **superusuário alcança todo o organograma**: define, troca e destitui titulares de qualquer
      unidade (inclusive da unidade raiz), sem restrição de alcance.
- [x] **Nomear titular** em unidade sem titular marca o servidor escolhido como titular da unidade
      (`e_titular=True`), conferindo-lhe a caneta de direção da unidade.
- [x] **Trocar titular** destitui o titular anterior e marca o novo na **mesma transação atômica**,
      inclusive se o anterior estiver afastado — nunca restando dois titulares nem uma janela com
      a vaga aberta.
- [x] **Destituir titular** abre a vaga na unidade, e a mesma transação **encerra as delegações
      estruturais vigentes** feitas por ele naquela unidade (com data fim em hoje e cancelando as
      futuras) e **encerra as substituições daquela titularidade**.
- [x] O servidor escolhido precisa estar **lotado na unidade**, possuir cargo em comissão de chefia
      compatível com o tipo da unidade (`cargo_titulariza`) e estar **em exercício** — servidor
      incompatível ou fora de exercício é recusado na validação com tarja de erro no modal.
- [x] A **página da unidade** só renderiza os botões e modais de titularidade para quem tem a
      competência e o alcance sobre ela; a gravação via HTMX fecha o modal e atualiza a seção de
      direção sem recarregar a tela.
- [x] O **modal de rota direta (standalone)** no Painel de Ações (`unidades:modal_definir_titular`)
      permite escolher a unidade — recortada ao alcance estrito de quem abre — e atualiza a face
      conforme o estado dela: titular atual com opção de troca/destituição, vaga aberta com lista de
      candidatos, ou aviso de falta quando não há servidores aptos.
- [x] A ação ganha card no **Painel de Ações** (aba *Estrutura Administrativa*, grupo *Organograma*)
      declarado com `partial=PARTIAL_CARTAO_MODAL` e ícones SVG nas variantes declaradas (pequeno e
      grande), satisfazendo os checks `painel.E002`, `painel.E003` e `painel.E004`.
- [x] Os atos são **registrados** (SPEC autorizacao/004), distinguíveis pela operação (`definir`,
      `trocar` e `destituir`), com a sigla da unidade como alvo.
- [x] O design foi aprovado no **mock** ([026-mock-titularidade.html](026-mock-titularidade.html)) e
      as peças foram portadas antes do uso pela aplicação.

## 3 · Domínio
Esta SPEC adiciona o tipo de alcance `UnidadesEstritamenteSubordinadas` ao domínio de autorização,
inscreve a ação administrativa de titularidade, expõe seu card no painel de ações e estende a rotina
de destituição para encerrar em cascata delegações estruturais e substituições vigentes.

```python
class UnidadesEstritamenteSubordinadas(TipoAlcance):
    """O ramo, menos as unidades de onde ele parte: o alvo precisa estar estritamente ABAIXO de
    quem se dirige ou de quem se recebeu por delegação."""

    parametros_alvo: tuple[str, ...] = ("unidade",)


class AtoDefinirTitular(BaseModel):
    """Entrada para definir ou trocar o titular de uma unidade."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    titular_id: int


class AtoDestituirTitular(BaseModel):
    """Entrada para destituir o titular e abrir a vaga."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
```

- [`Unidade` e `TipoUnidade`](001-models-perfil-cargos-unidade.md) — a unidade e seu tipo.
- [`cargo_titulariza`](014-titular-da-unidade.md) — "este perfil pode titularizar esta unidade?".
- [`definir_titular` e `destituir_titular`](014-titular-da-unidade.md) — as operações de escrita no
  banco.
- [`EstadoDaDirecao` e `avaliar_direcao`](014-titular-da-unidade.md) — "quem dirige a unidade hoje?".
- [`Delegacao`](../autorizacao/009-delegacao-de-competencia-estrutural.md) — delegações nominais da
  unidade a encerrar na destituição.
- [`Substituicao`](015-exercicio-e-substituicao.md) — substituições vinculadas ao titular a encerrar.
- [`PAINEL` e `ItemAcao`](../painel/001-painel-de-acoes-por-abas.md) — exposição da ação no painel.

**Mock:** [026-mock-titularidade.html](026-mock-titularidade.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Exoneração ou destituição de cargo em comissão do servidor — SPEC `user_admin/005`.
- Histórico detalhado de titulares anteriores com datas de exercício — sem dono ainda.
- Indicação de titulares em lote para múltiplas unidades simultaneamente — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/protecao.py` → `acao_protegida`, `conferir_alvo`, `pode_executar`, `registrar_ato`:
  barreira, conferência do alvo e registro de execução.
- `@apps/competencias/utils.py` → `instanciar_acao`: construção do contrato da ação.
- `@apps/competencias/consulta.py` → `alcance_do_perfil`, `unidades_dirigidas`: unidades alcançadas.
- `@apps/painel/abas_declaradas.py` → `ABA_ESTRUTURA`, `PARTIAL_CARTAO_MODAL`: declaração do card no painel.
- `@apps/unidades/titularidade.py` → `definir_titular`, `destituir_titular`, `candidatos_a_titular`:
  atos em transação e filtro de servidores aptos.
- `@apps/unidades/context.py` → `contexto_unidade`: montagem de contexto da página da unidade.
- Skills: `acao-administrativa`, `painel`, `specs`, `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`services/domain/autorizacao/contratos.py`**
```python
class UnidadesEstritamenteSubordinadas(TipoAlcance):
    """O ramo, menos as unidades de onde ele parte: o alvo precisa estar estritamente ABAIXO de
    quem se dirige ou de quem se recebeu por delegação."""

    parametros_alvo: tuple[str, ...] = ("unidade",)
```

**`apps/competencias/protecao.py`**
```python
def _unidades_alvo(alcance: TipoAlcance, valores: Mapping[str, int]) -> tuple[int, ...]:
    if isinstance(alcance, UnidadesSubordinadas):
        return tuple(valores[parametro] for parametro in alcance.parametros_alvo if parametro in valores)
    if isinstance(alcance, UnidadesEstritamenteSubordinadas):
        return tuple(valores[parametro] for parametro in alcance.parametros_alvo if parametro in valores)
    if isinstance(alcance, LotacaoDoServidor):
        return (_lotacao_de(valores["servidor"]),)
    if isinstance(alcance, LotacaoAtualEDestino):
        origem = _lotacao_de(valores["servidor"])
        destino = valores.get("unidade")
        return (origem,) if destino is None else (origem, destino)
    raise NotImplementedError(f"alcance sem conferência: {type(alcance).__name__}")


def conferir_alvo(
    request: HttpRequest,
    perfil: Perfil,
    acao: AcaoDominio,
    kwargs_da_rota: Mapping[str, object],
) -> None:
    if acao.alcance is None or perfil.is_superuser:
        return
    valores = _valores_dos_alvos(request, acao.alcance, kwargs_da_rota)
    if not valores:
        return
    if isinstance(acao.alcance, UnidadesEstritamenteSubordinadas):
        alcance_permitido = alcance_do_perfil(perfil) - unidades_dirigidas(perfil)
    else:
        alcance_permitido = alcance_do_perfil(perfil)
    if not all(unidade in alcance_permitido for unidade in _unidades_alvo(acao.alcance, valores)):
        raise PermissionDenied
```

**`apps/unidades/acoes_declaradas.py`**
```python
ACAO_DEFINIR_TITULAR = instanciar_acao(
    slug="unidades.definir_titular",
    nome="Definir titular de unidade",
    nome_curto="Titularidade",
    tooltip="Nomeia, troca ou destitui o titular de uma unidade subordinada.",
    url_name="unidades:modal_definir_titular",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    alcance=UnidadesEstritamenteSubordinadas(),
)
```

**`apps/painel/abas_declaradas.py`**
```python
ABA_ESTRUTURA = Aba(
    slug="painel.estrutura_administrativa",
    rotulo="Estrutura Administrativa",
    titulo="Estrutura Administrativa",
    descricao=(
        "A forma da DIMAP: as unidades que a compõem, como se subordinam, os cargos em comissão que "
        "existem e quem responde pela direção de cada uma."
    ),
    grupos=(
        Grupo(
            rotulo="Organograma",
            itens=(
                ItemLivre(
                    slug="painel.lista_unidades",
                    nome="Ver o organograma",
                    tooltip="A árvore de unidades e a tabela filtrável que a acompanha.",
                    url_name="unidades:listar_unidades",
                ),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE_RAIZ),
                ItemAcao(acao=ACAO_DEFINIR_TITULAR, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
        Grupo(rotulo="Cargos em Comissão", itens=()),
    ),
)
```

**`apps/unidades/titularidade.py`**
```python
def definir_titular(perfil: Perfil) -> None:
    """Destitui o anterior (com encerramentos) e marca o novo na mesma transação atômica."""
    with transaction.atomic():
        _destituir(perfil.unidade, exceto=perfil)
        perfil.e_titular = True
        perfil.full_clean()
        perfil.save(update_fields=["e_titular"])


def destituir_titular(unidade: Unidade) -> None:
    """Abre a vaga na unidade e encerra delegações estruturais e substituições vigentes."""
    with transaction.atomic():
        _destituir(unidade)


def _destituir(unidade: Unidade, exceto: Perfil | None = None) -> None:
    hoje = timezone.localdate()
    titulares = Perfil.objects.filter(unidade=unidade, e_titular=True)
    if exceto is not None and exceto.pk is not None:
        titulares = titulares.exclude(pk=exceto.pk)
    for titular in titulares:
        _encerrar_substituicoes_de_titularidade(titular, hoje)
    _encerrar_delegacoes_da_unidade(unidade, hoje)
    titulares.update(e_titular=False)


def _encerrar_delegacoes_da_unidade(unidade: Unidade, hoje: date) -> None:
    from apps.competencias.models.delegacao import Delegacao
    vigentes = Delegacao.objects.filter(unidade=unidade, data_inicio__lte=hoje).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gt=hoje)
    )
    vigentes.update(data_fim=hoje)
    Delegacao.objects.filter(unidade=unidade, data_inicio__gt=hoje).delete()


def _encerrar_substituicoes_de_titularidade(titular: Perfil, hoje: date) -> None:
    from apps.user_admin.models import Substituicao
    vigentes = Substituicao.objects.filter(
        impedimento__perfil=titular,
        data_inicio__lte=hoje,
    ).filter(Q(data_fim__isnull=True) | Q(data_fim__gt=hoje))
    vigentes.update(data_fim=hoje)
    Substituicao.objects.filter(
        impedimento__perfil=titular,
        data_inicio__gt=hoje,
    ).delete()
```

**`apps/unidades/views.py`**
```python
TEMPLATE_MODAL_TITULARIDADE = "unidades/partials/_modal_definir_titular_standalone.html"
TEMPLATE_FACE_TITULARIDADE = "unidades/partials/_face_titularidade.html"


@acao_protegida(ACAO_DEFINIR_TITULAR)
def modal_definir_titular(request: HttpRequest) -> HttpResponse:
    """Rota direta do painel / menu: abre o modal com o seletor de unidades do alcance."""
    autor = cast(Perfil, request.user)
    alcance = (
        Unidade.objects.all()
        if autor.is_superuser
        else Unidade.objects.filter(pk__in=(alcance_do_perfil(autor) - unidades_dirigidas(autor)))
    )
    return render(
        request,
        TEMPLATE_MODAL_TITULARIDADE,
        {"unidades": alcance},
    )


@acao_protegida(ACAO_DEFINIR_TITULAR)
def face_titularidade(request: HttpRequest) -> HttpResponse:
    """Atualiza a face do modal conforme a unidade escolhida no select."""
    unidade_id = request.GET.get("unidade", "")
    if not unidade_id.isdigit():
        return HttpResponse("")
    unidade = get_object_or_404(Unidade, pk=int(unidade_id))
    return render(
        request,
        TEMPLATE_FACE_TITULARIDADE,
        contexto_unidade(unidade),
    )


@acao_protegida(ACAO_DEFINIR_TITULAR)
@require_POST
def gravar_definir_titular(request: HttpRequest) -> HttpResponse:
    unidade_id = request.POST.get("unidade", "")
    titular_id = request.POST.get("titular", "")
    if not unidade_id.isdigit() or not titular_id.isdigit():
        return HttpResponse(status=400)
    unidade_obj = get_object_or_404(Unidade, pk=int(unidade_id))
    novo_titular = get_object_or_404(Perfil, pk=int(titular_id))
    if novo_titular.unidade_id != unidade_obj.id or not novo_titular.em_exercicio:
        return HttpResponse(status=422)
    operacao = "trocar" if unidade_obj.titular is not None else "definir"
    definir_titular(novo_titular)
    registrar_ato(
        request,
        operacao=operacao,
        alvo_tipo="unidade",
        alvo_identificador=unidade_obj.sigla,
    )
    return render(
        request,
        "unidades/partials/_secao_direcao.html",
        contexto_secao_direcao(unidade_obj, request.user),
    )


@acao_protegida(ACAO_DEFINIR_TITULAR)
@require_POST
def gravar_destituir_titular(request: HttpRequest) -> HttpResponse:
    unidade_id = request.POST.get("unidade", "")
    if not unidade_id.isdigit():
        return HttpResponse(status=400)
    unidade_obj = get_object_or_404(Unidade, pk=int(unidade_id))
    destituir_titular(unidade_obj)
    registrar_ato(
        request,
        operacao="destituir",
        alvo_tipo="unidade",
        alvo_identificador=unidade_obj.sigla,
    )
    return render(
        request,
        "unidades/partials/_secao_direcao.html",
        contexto_secao_direcao(unidade_obj, request.user),
    )
```

## 7 · Caveats
- Encerramento de substituições pelo término da titularidade fixa a vigência em `hoje`, preservando
  o histórico de dias exercidos pelo substituto até a data do ato.
- A unidade raiz não possui unidade superior, de modo que a definição ou destituição de sua
  titularidade só é exercida pelo superusuário.

## 8 · Testes (TDD)
- `test_definir_titular_em_unidade_sem_titular` — marca titular em unidade vaga e atualiza estado da direção *(marker `banco`)*
- `test_trocar_titular_destitui_anterior_e_marca_novo_em_transacao` — substituição atômica de titularidade *(marker `banco`)*
- `test_destituir_titular_abre_vaga_e_encerra_delegacoes_vigentes` — delegações ativas da unidade encerram em hoje e futuras são apagadas *(marker `banco`)*
- `test_destituir_titular_encerra_substituicoes_vigentes_do_afastado` — coberturas de direção do ex-titular encerram em hoje *(marker `banco`)*
- `test_definir_titular_com_servidor_de_outra_unidade_ou_sem_cargo_recusa_422` — validação de lotação e cargo compatível *(marker `banco`)*
- `test_definir_titular_com_servidor_impedido_recusa_422` — servidor fora de exercício não pode assumir titularidade *(marker `banco`)*
- `test_modal_direto_lista_apenas_unidades_do_alcance_estrito` — rota direta filtra pelo alcance *(marker `banco`)*
- `test_card_titularidade_presente_no_painel_para_quem_tem_competencia` — card do painel visível via `ItemAcao` *(marker `banco`)*

**Bateria de segurança da ação administrativa (`acao-administrativa`):**
- `test_definir_titular_anonimo_redireciona_login` *(marker `banco`)*
- `test_definir_titular_sem_competencia_retorna_403_e_registra_negativa` *(marker `banco`)*
- `test_definir_titular_fora_do_alcance_estrito_retorna_403_registrado` *(marker `banco`)*
- `test_titular_nao_pode_definir_ou_destituir_a_propria_titularidade` *(marker `banco`)*
- `test_superusuario_alcanca_qualquer_unidade_inclusive_raiz` *(marker `banco`)*
- `test_ato_autorizado_registra_operacao_e_alvo` *(marker `banco`)*

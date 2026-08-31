"""
Testes de apps/user_admin/views.py — `modal_administrador`, `opcoes_administrador` e
`gravar_administrador` (SPEC user_admin/022): ato próprio, exclusivo do superusuário — mesmo
regime de `unidades.criar_unidade_raiz` (SPEC user_admin/020, v3). Não é estrutural (dirigir
unidade não dá esta caneta) nem concessão (que ela recusa mesmo gravada), e por isso não entra em
`slugs_liberados` de ninguém além do superusuário. A rota não tem alcance: o ato não incide sobre
unidade, e o superusuário alcança o organograma inteiro.

O comportamento do ato em si (o que `mudar_administrador` grava) é
`tests/apps/user_admin/test_administrador.py`; aqui fica a bateria de segurança da skill
`acao-administrativa` e o contrato HTTP das três rotas.

Todos levam o marker `banco`.
"""

from django.conf import settings as django_settings
from bs4 import BeautifulSoup
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.models import CargoBase, CargoComissao, Perfil

banco = pytest.mark.banco

SLUG_ACAO = "user_admin.tornar_administrador"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Rota Administrador",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Rota Administrador", "sigla": "CGRA"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Rota Administrador",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _dirigente(unidade: Unidade, rf: str, nome: str = "Dirigente") -> Perfil:
    """Titular em exercício: basta para exercer `criar_servidor`/`editar_servidor` (estruturais),
    mas NUNCA basta para `tornar_administrador` — é o contraste que os testes 8 e 12 fixam."""
    perfil = _perfil(unidade, rf, nome, cargo_comissao=_cargo_chefia(f"Diretor {rf}"))
    definir_titular(perfil)
    return perfil


def _superusuario(rf: str, unidade: Unidade | None = None) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=unidade or _unidade(f"ADM-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _conceder(unidade: Unidade, cargo_base: CargoBase) -> Acao:
    # Ação NÃO estrutural — projeta como o contrato a declara: a exclusividade não é projetada, e
    # a concessão gravada existe só para provar que ela não basta.
    acao, _ = Acao.objects.get_or_create(
        slug=SLUG_ACAO,
        defaults={"nome": "Tornar administrador", "tooltip": "tt", "estrutural": False},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    return acao


def _fresco(perfil: Perfil) -> Perfil:
    # O cache de `has_perm` é do objeto Python: cada requisição simulada precisa ver o efeito de
    # uma mudança de estado como uma requisição nova veria.
    return Perfil.objects.get(pk=perfil.pk)


def _url_opcoes() -> str:
    return reverse("user_admin:opcoes_administrador")


def _url_gravar(servidor_id: int) -> str:
    return reverse("user_admin:gravar_administrador", kwargs={"servidor": servidor_id})


# ---------------------------------------------------------------------------
# O botão só existe na tela para quem já é administrador
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_poco_de_plenos_poderes_so_aparece_para_administrador(client: Client) -> None:
    unidade = _unidade("ADM-POCO")
    superusuario = _superusuario("9501900", unidade)
    dirigente = _dirigente(unidade, "9501910", "Dirigente Poço")
    alvo = _perfil(unidade, "9501920", "Alvo Poço")

    client.force_login(superusuario)
    formulario = client.get(reverse("user_admin:criar_perfil")).content.decode()
    modal = client.get(
        reverse("user_admin:editar_perfil", kwargs={"servidor": alvo.pk})
    ).content.decode()
    assert "Tornar administrador" in formulario
    assert "Tornar administrador" in modal

    # Cadastra e edita servidor, mas não é administrador: o poço não aparece em tela alguma.
    client.force_login(_fresco(dirigente))
    formulario = client.get(reverse("user_admin:criar_perfil")).content.decode()
    modal = client.get(
        reverse("user_admin:editar_perfil", kwargs={"servidor": alvo.pk})
    ).content.decode()
    assert "Tornar administrador" not in formulario
    assert "Tornar administrador" not in modal


# ---------------------------------------------------------------------------
# O modal da rota direta lista só quem está lotado na unidade escolhida
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_direto_lista_servidores_da_unidade_escolhida(client: Client) -> None:
    superusuario = _superusuario("9501000")
    unidade = _unidade("ADM-OPC")
    outra = _unidade("ADM-OPC-OUTRA")
    dentro = _perfil(unidade, "9501010", "Dentro Opções")
    fora = _perfil(outra, "9501020", "Fora Opções")

    client.force_login(superusuario)
    resposta = client.get(_url_opcoes(), {"unidade": str(unidade.pk)})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert dentro.rf in html
    assert fora.rf not in html


# ---------------------------------------------------------------------------
# A gravação devolve o botão no estado novo
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_botao_reflete_o_estado_gravado(client: Client) -> None:
    superusuario = _superusuario("9501100")
    alvo = _perfil(_unidade("ADM-BOTAO"), "9501110", "Alvo Botão")

    client.force_login(superusuario)
    concedido = client.post(_url_gravar(alvo.pk), {"tornar": "1"})
    assert concedido.status_code == 200
    assert "botao-aura-ligado" in concedido.content.decode()
    assert _fresco(alvo).is_superuser is True

    revogado = client.post(_url_gravar(alvo.pk), {"tornar": "0"})
    assert revogado.status_code == 200
    assert "botao-aura-ligado" not in revogado.content.decode()
    assert _fresco(alvo).is_superuser is False


# ---------------------------------------------------------------------------
# Barreira de autenticação e de competência — exclusiva mesmo com concessão gravada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    alvo = _perfil(_unidade("ADM-ANON"), "9501200", "Alvo Anônimo")

    resposta = client.post(_url_gravar(alvo.pk), {"tornar": "1"})

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0
    assert _fresco(alvo).is_superuser is False


@banco
@pytest.mark.django_db
def test_nao_superusuario_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("ADM-403")
    perfil = _perfil(unidade, "9501300", "Sem Caneta")
    alvo = _perfil(_unidade("ADM-403-ALVO"), "9501310", "Alvo 403")

    client.force_login(perfil)
    resposta = client.post(_url_gravar(alvo.pk), {"tornar": "1"})

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False
    assert _fresco(alvo).is_superuser is False


@banco
@pytest.mark.django_db
def test_concessao_gravada_nao_libera_acao_exclusiva(client: Client) -> None:
    unidade = _unidade("ADM-CONC")
    cargo = _cargo_base(nome="Cargo Concessão Administrador", sigla="CCAD")
    perfil = _perfil(unidade, "9501400", "Concessão Administrador", cargo_base=cargo)
    _conceder(unidade, cargo)
    alvo = _perfil(unidade, "9501410", "Alvo Concessão")

    client.force_login(_fresco(perfil))
    assert _fresco(perfil).has_perm(SLUG_ACAO) is False
    resposta = client.post(_url_gravar(alvo.pk), {"tornar": "1"})

    assert resposta.status_code == 403
    assert _fresco(alvo).is_superuser is False


@banco
@pytest.mark.django_db
def test_exonerado_chega_como_anonimo(client: Client) -> None:
    superusuario = _superusuario("9501500")
    superusuario.is_active = False
    superusuario.exonerado_em = timezone.localdate()
    superusuario.save(update_fields=["is_active", "exonerado_em"])
    alvo = _perfil(_unidade("ADM-EXON"), "9501510", "Alvo Exonerado")

    client.force_login(superusuario)
    resposta = client.post(_url_gravar(alvo.pk), {"tornar": "1"})

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0


# ---------------------------------------------------------------------------
# O que fica registrado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_ato_grava_quem_cargo_unidade_operacao_e_alvo(client: Client) -> None:
    unidade_autor = _unidade("ADM-REG-AUTOR")
    outra = _unidade("ADM-REG-OUTRA")
    superusuario = _superusuario("9501600", unidade_autor)
    alvo = _perfil(_unidade("ADM-REG-ALVO"), "9501610", "Alvo Registro")

    client.force_login(superusuario)
    resposta = client.post(_url_gravar(alvo.pk), {"tornar": "1"})
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == superusuario.pk
    assert execucao.unidade_id == unidade_autor.pk
    assert execucao.cargo_base_id == superusuario.cargo_base_id
    assert execucao.alvo_tipo == "servidor"
    assert execucao.alvo_identificador == alvo.rf

    # Mudar a lotação depois não reescreve a linha.
    superusuario.unidade = outra
    superusuario.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade_autor.pk


@banco
@pytest.mark.django_db
def test_conceder_e_revogar_sao_distinguiveis_no_historico(client: Client) -> None:
    superusuario = _superusuario("9501700")
    alvo = _perfil(_unidade("ADM-HIST"), "9501710", "Alvo Histórico")

    client.force_login(superusuario)
    client.post(_url_gravar(alvo.pk), {"tornar": "1"})
    client.post(_url_gravar(alvo.pk), {"tornar": "0"})

    operacoes = set(ExecucaoAcao.objects.values_list("operacao", flat=True))
    assert operacoes == {"tornar", "revogar"}


# ---------------------------------------------------------------------------
# Gravação só por POST
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_escrita_so_por_post(client: Client) -> None:
    superusuario = _superusuario("9501800")
    alvo = _perfil(_unidade("ADM-SOPOST"), "9501810", "Alvo SóPost")

    client.force_login(superusuario)
    resposta = client.get(_url_gravar(alvo.pk), {"tornar": "1"})

    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
    assert _fresco(alvo).is_superuser is False


# ---------------------------------------------------------------------------
# A marca viaja com o formulário de edição (SPEC user_admin/022 v3)
# ---------------------------------------------------------------------------


def _url_editar(servidor_id: int) -> str:
    return reverse("user_admin:gravar_edicao", kwargs={"servidor": servidor_id})


def _payload_edicao(perfil: Perfil, rf: str, **overrides: str) -> dict[str, str]:
    payload = {
        "rf": rf,
        "nome": perfil.nome,
        "sobrenome": perfil.sobrenome,
        "email": f"{rf}@prefeitura.sp.gov.br",
        "unidade": str(perfil.unidade_id),
        "cargo_base": str(perfil.cargo_base_id),
        "cargo_comissao": "",
    }
    payload.update(overrides)
    return payload


@banco
@pytest.mark.django_db
def test_edicao_recusada_nao_torna_administrador(client: Client) -> None:
    """A garantia da v3: a marca é gravada pelo ato que grava o resto, então cadastro recusado não
    dá caneta a ninguém."""
    unidade = _unidade("ADM-EDREC")
    superusuario = _superusuario("9502000", unidade)
    alvo = _perfil(unidade, "9502010", "Alvo Recusa")

    client.force_login(superusuario)
    resposta = client.post(
        _url_editar(alvo.pk),
        _payload_edicao(alvo, "952010", administrador="1"),
    )

    assert resposta.status_code == 422
    assert _fresco(alvo).is_superuser is False


@banco
@pytest.mark.django_db
def test_edicao_valida_grava_a_marca_e_registra_operacao_propria(client: Client) -> None:
    unidade = _unidade("ADM-EDOK")
    superusuario = _superusuario("9502100", unidade)
    alvo = _perfil(unidade, "9502110", "Alvo Edição")

    client.force_login(superusuario)
    resposta = client.post(
        _url_editar(alvo.pk),
        _payload_edicao(alvo, "9502110", administrador="1"),
    )

    assert resposta.status_code == 200
    assert _fresco(alvo).is_superuser is True
    assert ExecucaoAcao.objects.filter(operacao="editar_administrador").count() == 1


@banco
@pytest.mark.django_db
def test_edicao_de_quem_nao_tem_caneta_nao_revoga_a_marca(client: Client) -> None:
    """Sem o controle na tela o POST não manda a marca: ler essa ausência como "revogar" tiraria a
    caneta do alvo a cada edição feita por quem apenas edita servidor."""
    unidade = _unidade("ADM-EDSEM")
    dirigente = _dirigente(unidade, "9502200", "Dirigente Edição")
    alvo = _perfil(unidade, "9502210", "Alvo Preservado", is_superuser=True)

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_editar(alvo.pk), _payload_edicao(alvo, "9502210"))

    assert resposta.status_code == 200
    assert _fresco(alvo).is_superuser is True


@banco
@pytest.mark.django_db
def test_edicao_nao_revoga_a_si_mesmo(client: Client) -> None:
    unidade = _unidade("ADM-EDAUTO")
    superusuario = _superusuario("9502300", unidade)

    client.force_login(superusuario)
    resposta = client.post(
        _url_editar(superusuario.pk),
        _payload_edicao(superusuario, "9502300", administrador="0"),
    )

    assert resposta.status_code == 422
    assert _fresco(superusuario).is_superuser is True
    # Nada é gravado: a recusa da marca derruba a edição inteira.
    assert _fresco(superusuario).email == ""


@banco
@pytest.mark.django_db
def test_aviso_de_confirmacao_nasce_fora_do_modal_box(client: Client) -> None:
    """`backdrop-filter` no `.modal-box` o torna containing block de descendente `fixed`: a placa
    presa lá dentro nasce ancorada no topo do formulário, longe de quem rolou até o botão."""
    unidade = _unidade("ADM-AVISO")
    superusuario = _superusuario("9502400", unidade)
    alvo = _perfil(unidade, "9502410", "Alvo Aviso")

    client.force_login(superusuario)
    html = client.get(
        reverse("user_admin:editar_perfil", kwargs={"servidor": alvo.pk})
    ).content.decode()

    sopa = BeautifulSoup(html, "html.parser")
    aviso = sopa.select_one(".botao-aura-aviso")
    assert aviso is not None
    assert aviso.find_parent(class_="modal-box") is None

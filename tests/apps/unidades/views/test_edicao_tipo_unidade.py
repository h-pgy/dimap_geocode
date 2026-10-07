"""
Testes de apps/unidades/views.py — `gravar_edicao_tipo_unidade` (SPEC user_admin/031): a trava de
estrutura vive no servidor, não na tela. Nível, permissão de raiz, requisito de titular e tipos
filhos vedados de tipo com unidades no organograma só são recusados pelo caminho do ato; o nome
segue editável mesmo em tipo com unidades ou extinto.

`ACAO_EDITAR_TIPO_UNIDADE` é exclusiva do superusuário — o contrato de segurança da ação (anônimo,
sem competência, concessão gravada) está em test_seguranca_tipos_unidade.py, comum às quatro ações.
Todos levam o marker `banco`.
"""

from datetime import date

from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.models import CargoBase
from apps.unidades.extincao_tipo import extinguir_tipo_unidade
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {"nome": nome, "nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1}
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, tipo: TipoUnidade | None = None, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": tipo or _tipo_unidade(f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Base Edição Tipo", "sigla": "CGBEDT"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _superusuario(rf: str) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=_unidade(f"TIPO-ED-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _payload(tipo: TipoUnidade, **mudancas: object) -> dict[str, object]:
    """O formulário como a tela o manda com o tipo intocado, mais o que o teste muda: checkbox
    desmarcado não posta a chave, e o nível mínimo some quando o requisito é alta administração."""
    campos: dict[str, object] = {
        "nome": tipo.nome,
        "nivel": str(tipo.nivel),
        "pode_ser_raiz": tipo.pode_ser_raiz,
        "exige_alta_administracao": tipo.exige_alta_administracao,
        "nivel_minimo_titular": tipo.nivel_minimo_titular,
        "tipos_filhos_vedados": [str(pk) for pk in tipo.tipos_filhos_vedados.values_list("pk", flat=True)],
    }
    campos.update(mudancas)
    payload: dict[str, object] = {
        "nome": campos["nome"],
        "nivel": campos["nivel"],
        "nivel_minimo_titular": "" if campos["nivel_minimo_titular"] is None else str(campos["nivel_minimo_titular"]),
        "tipos_filhos_vedados": campos["tipos_filhos_vedados"],
    }
    if campos["pode_ser_raiz"]:
        payload["pode_ser_raiz"] = "on"
    if campos["exige_alta_administracao"]:
        payload["exige_alta_administracao"] = "on"
    return payload


def _url_gravar(tipo_pk: int) -> str:
    return reverse("unidades:gravar_edicao_tipo_unidade", kwargs={"tipo": tipo_pk})


# ---------------------------------------------------------------------------
# Estrutura travada quando há unidade no organograma
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_edicao_recusa_nivel_raiz_e_titular_de_tipo_com_unidades(client: Client) -> None:
    superusuario = _superusuario("9610100")
    outro = _tipo_unidade("Tipo Vedável", nivel=5, pode_ser_raiz=False)
    tipo = _tipo_unidade("Tipo Em Uso", nivel=10, pode_ser_raiz=True, nivel_minimo_titular=1)
    _unidade("TIPO-EM-USO", tipo)

    client.force_login(superusuario)
    mudancas_estruturais: tuple[dict[str, object], ...] = (
        {"nivel": "12"},
        {"pode_ser_raiz": False},
        {"exige_alta_administracao": True, "nivel_minimo_titular": None},
        {"nivel_minimo_titular": 2},
        {"tipos_filhos_vedados": [str(outro.pk)]},
    )
    for mudanca in mudancas_estruturais:
        resposta = client.post(_url_gravar(tipo.pk), _payload(tipo, **mudanca))
        assert resposta.status_code == 422, mudanca

    tipo.refresh_from_db()
    assert tipo.nivel == 10
    assert tipo.pode_ser_raiz is True
    assert tipo.exige_alta_administracao is False
    assert tipo.nivel_minimo_titular == 1
    assert not tipo.tipos_filhos_vedados.exists()


@banco
@pytest.mark.django_db
def test_edicao_altera_nome_de_tipo_com_unidades_e_extinto(client: Client) -> None:
    superusuario = _superusuario("9610200")
    em_uso = _tipo_unidade("Tipo Nome Em Uso")
    _unidade("TIPO-NOME-USO", em_uso)
    extinto = _tipo_unidade("Tipo Nome Extinto")
    extinguir_tipo_unidade(extinto, date(2026, 10, 7))

    client.force_login(superusuario)

    resposta_em_uso = client.post(_url_gravar(em_uso.pk), _payload(em_uso, nome="Tipo Renomeado Em Uso"))
    assert resposta_em_uso.status_code == 200
    em_uso.refresh_from_db()
    assert em_uso.nome == "Tipo Renomeado Em Uso"

    resposta_extinto = client.post(_url_gravar(extinto.pk), _payload(extinto, nome="Tipo Renomeado Extinto"))
    assert resposta_extinto.status_code == 200
    extinto.refresh_from_db()
    assert extinto.nome == "Tipo Renomeado Extinto"
    assert extinto.extinto_em is not None


@banco
@pytest.mark.django_db
def test_edicao_livre_quando_nenhuma_unidade_utiliza_o_tipo(client: Client) -> None:
    superusuario = _superusuario("9610300")
    outro = _tipo_unidade("Tipo Vedável Livre", nivel=5, pode_ser_raiz=False)
    tipo = _tipo_unidade("Tipo Edição Livre", nivel=10, pode_ser_raiz=True, nivel_minimo_titular=1)

    client.force_login(superusuario)
    resposta = client.post(
        _url_gravar(tipo.pk),
        _payload(
            tipo,
            nivel="12",
            pode_ser_raiz=False,
            exige_alta_administracao=True,
            nivel_minimo_titular=None,
            tipos_filhos_vedados=[str(outro.pk)],
        ),
    )

    assert resposta.status_code == 200
    tipo.refresh_from_db()
    assert tipo.nivel == 12
    assert tipo.pode_ser_raiz is False
    assert tipo.exige_alta_administracao is True
    assert tipo.nivel_minimo_titular is None
    assert set(tipo.tipos_filhos_vedados.values_list("pk", flat=True)) == {outro.pk}

"""
Testes da página da unidade (SPEC user_admin/016): o contrato HTTP/partial da rota de leitura —
quem dirige a unidade hoje, o resumo com o cargo mínimo em padrão de cargo, o modal de edição
pré-preenchido e sem destino de escrita, os candidatos a titular restritos por `cargo_titulariza` e
o alarme de unidade sem direção refletido na página do servidor (SPEC 015). O que é visual (a
bandeja `.stats-onsen`, o campo `.campo-onsen`) se valida no mock da SPEC, não aqui.

Todos levam o marker `banco`: a página monta resumo, direção e candidatos a partir das tabelas.
"""

from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil, TipoImpedimento
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.unidades.titularidade import definir_titular

banco = pytest.mark.banco


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Página Unidade",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 4,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(
    sigla: str, tipo: TipoUnidade | None = None, **overrides: object
) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Divisão {sigla}",
        "sigla": sigla,
        "tipo": tipo or _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(
        nome="Cargo Página Unidade", defaults={"sigla": "CGPU"}
    )
    return cargo


def _cargo_chefia(nome: str, nivel: int) -> CargoComissao:
    return CargoComissao.objects.create(
        nome=nome,
        sigla="CDA",
        nivel=nivel,
        e_chefia=True,
    )


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Página Unidade",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _url_unidade(unidade: Unidade) -> str:
    return reverse("unidades:pagina_unidade", kwargs={"pk": unidade.pk})


# ---------------------------------------------------------------------------
# Resumo e direção
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pagina_da_unidade_traz_o_resumo_e_quem_dirige(client: Client) -> None:
    superior = _unidade(
        "DECAD",
        tipo=_tipo_unidade(
            nome="Departamento Página Unidade",
            nivel=20,
            exige_alta_administracao=True,
            nivel_minimo_titular=None,
        ),
    )
    tipo = _tipo_unidade(nome="Divisão Resumo", nivel=10, nivel_minimo_titular=4)
    unidade = _unidade("DIMAP-R", tipo=tipo, pai=superior)
    # Cargo de chefia no nível mínimo do tipo: é dele que sai "CDA-IV" no resumo.
    cargo_minimo = _cargo_chefia("Diretor de Divisão Resumo", nivel=4)
    titular = _perfil(unidade, "700700", "Helena", cargo_comissao=cargo_minimo)
    definir_titular(titular)
    _perfil(unidade, "700701", "Marcos")
    _perfil(unidade, "700702", "Renata")

    resposta = client.get(_url_unidade(unidade))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert unidade.nome in html
    assert unidade.sigla in html
    assert tipo.nome in html
    assert "CDA-IV" in html
    assert superior.sigla in html
    assert "Servidores lotados" in html
    assert ">3<" in html
    assert f"{titular.nome} {titular.sobrenome}" in html
    assert "Em exercício" in html


@banco
@pytest.mark.django_db
def test_pagina_distingue_as_duas_faltas(client: Client) -> None:
    tipo_impedimento = TipoImpedimento.objects.create(nome="Férias Página Unidade")
    hoje = timezone.localdate()
    inicio_afastamento = hoje - timedelta(days=1)

    # Vaga: nenhum titular.
    unidade_vaga = _unidade("VAGA-R")
    html_vaga = client.get(_url_unidade(unidade_vaga)).content.decode()
    assert f"A {unidade_vaga.sigla} está sem titular" in html_vaga
    assert "está sem quem responda por ela" not in html_vaga

    # Titular afastado, sem substituto: sem direção.
    tipo = _tipo_unidade(nome="Divisão Duas Faltas", nivel_minimo_titular=1)
    unidade_sem_direcao = _unidade("SDIR-R", tipo=tipo)
    titular = _perfil(
        unidade_sem_direcao,
        "700710",
        "Titular",
        cargo_comissao=_cargo_chefia("Diretor Sem Direção", nivel=1),
    )
    definir_titular(titular)
    registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=tipo_impedimento.pk, data_inicio=inicio_afastamento, data_fim=None
        ),
    )
    html_sem_direcao = client.get(_url_unidade(unidade_sem_direcao)).content.decode()
    assert (
        f"A {unidade_sem_direcao.sigla} está sem quem responda por ela"
        in html_sem_direcao
    )
    assert "está sem titular" not in html_sem_direcao

    # O mesmo titular afastado, agora com substituto vigente: nenhuma das duas.
    substituto = _perfil(unidade_sem_direcao, "700711", "Substituto")
    designar_substituto(
        titular.impedimentos.get(),
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )
    html_coberta = client.get(_url_unidade(unidade_sem_direcao)).content.decode()
    assert "está sem titular" not in html_coberta
    assert "está sem quem responda por ela" not in html_coberta


# ---------------------------------------------------------------------------
# Modal de edição da unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_de_edicao_vem_preenchido_e_com_destino(client: Client) -> None:
    """SPEC user_admin/020: editar unidade passa a ser ato registrado — o modal só existe atrás da
    rota protegida (`unidades:editar_unidade`), e não mais estático na página para qualquer
    visitante (ver `test_botao_de_editar_so_aparece_para_quem_alcanca_a_unidade`)."""
    pai = _unidade(
        "PAI-R", tipo=_tipo_unidade(nome="Departamento Modal Edição", nivel=20)
    )
    tipo = _tipo_unidade(nome="Divisão Modal Edição", nivel=10)
    unidade = _unidade("FILHA-R", tipo=tipo, pai=pai)
    dirigente = _perfil(
        pai,
        "700760",
        "Dirigente Modal Edição",
        cargo_comissao=_cargo_chefia("Diretor Modal Edição", 4),
    )
    definir_titular(dirigente)

    client.force_login(dirigente)
    html = client.get(
        reverse("unidades:editar_unidade", kwargs={"unidade": unidade.pk})
    ).content.decode()

    assert f'value="{unidade.nome}"' in html
    assert f'value="{unidade.sigla}"' in html
    assert f'<option value="{tipo.pk}" selected>{tipo.nome}</option>' in html
    assert (
        f'<option value="{pai.pk}" selected>{pai.sigla} · {pai.nome}</option>' in html
    )
    # O modal É a rota de gravação agora — a SPEC 016 renderizava o mesmo HTML sem destino.
    assert "hx-post" in html


# ---------------------------------------------------------------------------
# Candidatos a titular
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_lista_so_quem_pode_titularizar(client: Client) -> None:
    tipo = _tipo_unidade(nome="Seção Candidatos", nivel=5, nivel_minimo_titular=3)
    unidade = _unidade("CAND-R", tipo=tipo)
    outra_unidade = _unidade("OUTRA-R")

    elegivel = _perfil(
        unidade,
        "700720",
        "Elegível",
        cargo_comissao=_cargo_chefia("Chefe de Seção Elegível", nivel=3),
    )
    assessor_alto = _perfil(
        unidade,
        "700721",
        "AssessorAlto",
        cargo_comissao=CargoComissao.objects.create(
            nome="Assessor Alto Candidatos",
            sigla="ASS",
            nivel=6,
            e_chefia=False,
        ),
    )
    sem_cargo = _perfil(unidade, "700722", "SemCargo")
    de_outra_unidade = _perfil(
        outra_unidade,
        "700723",
        "DeOutraUnidade",
        cargo_comissao=_cargo_chefia("Chefe de Seção Outra Unidade", nivel=6),
    )

    html = client.get(_url_unidade(unidade)).content.decode()

    assert f'value="{elegivel.pk}"' in html
    assert f'value="{assessor_alto.pk}"' not in html
    assert f'value="{sem_cargo.pk}"' not in html
    assert f'value="{de_outra_unidade.pk}"' not in html

    # Sem nenhum candidato, o modal diz o que falta em vez de abrir um campo vazio.
    tipo_sem_candidato = _tipo_unidade(
        nome="Seção Sem Candidato", nivel=5, nivel_minimo_titular=6
    )
    unidade_sem_candidato = _unidade("SEMCAND-R", tipo=tipo_sem_candidato)
    _perfil(
        unidade_sem_candidato,
        "700730",
        "AbaixoDoMinimo",
        cargo_comissao=_cargo_chefia("Chefe Abaixo do Mínimo", nivel=3),
    )
    _perfil(unidade_sem_candidato, "700731", "SemCargoComissao")

    html_sem_candidato = client.get(
        _url_unidade(unidade_sem_candidato)
    ).content.decode()

    assert (
        f"Nenhum servidor da {unidade_sem_candidato.sigla} pode titularizar"
        in html_sem_candidato
    )
    assert '<select name="titular"' not in html_sem_candidato


# ---------------------------------------------------------------------------
# O botão de editar só aparece a quem tem a competência e o alcance (SPEC user_admin/020)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_botao_de_editar_so_aparece_para_quem_alcanca_a_unidade(client: Client) -> None:
    unidade = _unidade("BOTAO-R")
    outro_ramo = _unidade("BOTAO-FORA-R")
    dirigente = _perfil(
        unidade,
        "700750",
        "Dirigente Botão",
        cargo_comissao=_cargo_chefia("Diretor Botão", nivel=4),
    )
    definir_titular(dirigente)
    sem_direcao = _perfil(outro_ramo, "700751", "Sem Direção Botão")
    url_editar = reverse("unidades:editar_unidade", kwargs={"unidade": unidade.pk})

    client.force_login(dirigente)
    html = client.get(_url_unidade(unidade)).content.decode()
    assert "Editar unidade" in html
    assert url_editar in html

    client.force_login(sem_direcao)
    html_sem = client.get(_url_unidade(unidade)).content.decode()
    assert "Editar unidade" not in html_sem
    assert url_editar not in html_sem


# ---------------------------------------------------------------------------
# Reflexo na página do servidor (SPEC 015)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_secao_do_servidor_acusa_unidade_sem_direcao(client: Client) -> None:
    tipo_impedimento = TipoImpedimento.objects.create(nome="Férias Secao Servidor")
    tipo = _tipo_unidade(nome="Divisão Secao Servidor", nivel_minimo_titular=1)
    unidade = _unidade("SECSRV-R", tipo=tipo)
    hoje = timezone.localdate()
    titular = _perfil(
        unidade,
        "700740",
        "TitularAfastado",
        cargo_comissao=_cargo_chefia("Diretor Secao Servidor", nivel=1),
    )
    definir_titular(titular)
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=tipo_impedimento.pk,
            data_inicio=hoje - timedelta(days=1),
            data_fim=None,
        ),
    )

    # A seção de exercício mora na página de leitura do servidor, não no modal de edição
    # (SPEC user_admin/017).
    html_sem_substituto = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": titular.pk})
    ).content.decode()
    assert f"A {unidade.sigla} está sem quem responda por ela" in html_sem_substituto

    substituto = _perfil(unidade, "700741", "Substituto")
    designar_substituto(
        impedimento,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )

    html_com_substituto = client.get(
        reverse("user_admin:pagina_perfil", kwargs={"pk": titular.pk})
    ).content.decode()
    assert "está sem quem responda por ela" not in html_com_substituto

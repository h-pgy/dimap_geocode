"""
Testes dos atos de exercício e substituição (SPEC user_admin/015): registrar impedimento, designar
substituto, encerrar, trocar e voltar ao exercício — os cinco atos em transação que a tela e o
andaime exercitam pela mesma porta —, mais as duas leituras que compõem a direção da unidade
(SPEC 014): quem cobre um perfil hoje e quem ele está cobrindo.

Marker `banco`: os atos escrevem em Impedimento, Substituicao e Perfil.
"""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

import pytest

from apps.user_admin.exercicio import (
    designar_substituto,
    encerrar_substituicao,
    registrar_impedimento,
    retornar_ao_exercicio,
    substituicao_vigente,
    substituicoes_do_impedimento,
    trocar_substituto,
)
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    Substituicao,
    TipoImpedimento,
    TipoUnidade,
    Unidade,
)
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento, TrocaDeSubstituto
from apps.user_admin.titularidade import definir_titular
from services.domain.titularidade import Direcao, EstadoDaDirecao, avaliar_direcao

banco = pytest.mark.banco


def _unidade(**overrides: object) -> Unidade:
    tipo, _ = TipoUnidade.objects.get_or_create(
        nome="Divisão Exercício",
        defaults={"nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1},
    )
    dados: dict[str, object] = {
        "nome": "Divisão Exercício",
        "sigla": "DIVEX",
        "tipo": tipo,
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_comissao(**overrides: object) -> CargoComissao:
    dados: dict[str, object] = {
        "sigla": "CDA",
        "nivel": 1,
        "e_chefia": True,
        "nome": "Diretor de Divisão Exercício",
    }
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, **overrides: object) -> Perfil:
    cargo_base, _ = CargoBase.objects.get_or_create(
        nome="Cargo Exercício", sigla="CGEX"
    )
    dados: dict[str, object] = {
        "rf": "700500",
        "nome": "Fulano",
        "sobrenome": "Exercício",
        "cargo_base": cargo_base,
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _tipo_impedimento(**overrides: object) -> TipoImpedimento:
    dados: dict[str, object] = {"nome": "Férias Ato"}
    dados.update(overrides)
    return TipoImpedimento.objects.create(**dados)  # type: ignore[arg-type]


def _impedir(
    perfil: Perfil,
    tipo: TipoImpedimento,
    data_inicio: date,
    data_fim: date | None = None,
) -> Impedimento:
    assert tipo.pk is not None
    return registrar_impedimento(
        perfil,
        NovoImpedimento(tipo=tipo.pk, data_inicio=data_inicio, data_fim=data_fim),
    )


def _designar(
    impedimento: Impedimento,
    substituto: Perfil,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> Substituicao:
    assert substituto.pk is not None
    return designar_substituto(
        impedimento,
        NovaSubstituicao(
            substituto=substituto.pk, data_inicio=data_inicio, data_fim=data_fim
        ),
    )


# ---------------------------------------------------------------------------
# designar_substituto — a lacuna proposta em branco, e o estreitamento validado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_substituicao_nasce_na_lacuna_do_afastamento_e_so_estreita() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    tipo = _tipo_impedimento()

    # Em branco e é a primeira: fica com as datas do impedimento inteiro, fim nulo inclusive.
    afastado_indeterminado = _perfil(
        unidade, rf="700510", cargo_comissao=_cargo_comissao()
    )
    impedimento_indeterminado = _impedir(afastado_indeterminado, tipo, hoje)
    substituto_1 = _perfil(unidade, rf="700511", nome="Substituta Um")
    primeira = _designar(impedimento_indeterminado, substituto_1)
    assert primeira.data_inicio == hoje
    assert primeira.data_fim is None

    # Em branco e já há uma cobrindo o início: fica com a lacuna restante.
    afastado_com_lacuna = _perfil(
        unidade,
        rf="700512",
        nome="Afastado Lacuna",
        cargo_comissao=_cargo_comissao(sigla="CDB", nome="Diretor Lacuna"),
    )
    fim = hoje + timedelta(days=29)
    impedimento_com_lacuna = _impedir(afastado_com_lacuna, tipo, hoje, fim)
    substituto_2 = _perfil(unidade, rf="700513", nome="Substituta Dois")
    _designar(impedimento_com_lacuna, substituto_2, hoje, hoje + timedelta(days=9))
    substituto_3 = _perfil(unidade, rf="700514", nome="Substituto Três")
    segunda = _designar(impedimento_com_lacuna, substituto_3)
    assert segunda.data_inicio == hoje + timedelta(days=10)
    assert segunda.data_fim == fim

    # Informada mais estreita que o impedimento: aceita. Começando antes ou terminando depois:
    # recusada.
    afastado_estreita = _perfil(
        unidade,
        rf="700515",
        nome="Afastado Estreita",
        cargo_comissao=_cargo_comissao(sigla="CDC", nome="Diretor Estreita"),
    )
    impedimento_estreito = _impedir(
        afastado_estreita, tipo, hoje, hoje + timedelta(days=19)
    )
    substituto_4 = _perfil(unidade, rf="700516", nome="Substituto Quatro")
    mais_estreita = _designar(
        impedimento_estreito,
        substituto_4,
        hoje + timedelta(days=1),
        hoje + timedelta(days=10),
    )
    assert mais_estreita.pk is not None

    substituto_5 = _perfil(unidade, rf="700517", nome="Substituto Cinco")
    with pytest.raises(ValidationError):
        _designar(
            impedimento_estreito,
            substituto_5,
            hoje - timedelta(days=1),
            hoje + timedelta(days=5),
        )

    substituto_6 = _perfil(unidade, rf="700518", nome="Substituto Seis")
    with pytest.raises(ValidationError):
        _designar(
            impedimento_estreito,
            substituto_6,
            hoje + timedelta(days=11),
            hoje + timedelta(days=25),
        )


@banco
@pytest.mark.django_db
def test_um_afastamento_aceita_substitutos_em_sequencia() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    afastado = _perfil(unidade, rf="700520", cargo_comissao=_cargo_comissao())
    tipo = _tipo_impedimento()
    impedimento = _impedir(
        afastado, tipo, hoje - timedelta(days=10), hoje + timedelta(days=20)
    )

    primeiro = _perfil(unidade, rf="700521", nome="Primeiro")
    segundo = _perfil(unidade, rf="700522", nome="Segundo")
    _designar(impedimento, primeiro, hoje - timedelta(days=10), hoje)
    _designar(impedimento, segundo, hoje + timedelta(days=1), hoje + timedelta(days=20))

    assert substituicoes_do_impedimento(impedimento).count() == 2
    # Cada uma vigora no seu tempo: só a que contém hoje responde por "vigente agora".
    vigente = substituicao_vigente(afastado)
    assert vigente is not None
    assert vigente.substituto == primeiro

    # A que cruzaria as duas é recusada.
    terceiro = _perfil(unidade, rf="700523", nome="Terceiro")
    with pytest.raises(ValidationError):
        _designar(
            impedimento, terceiro, hoje - timedelta(days=1), hoje + timedelta(days=5)
        )


@banco
@pytest.mark.django_db
def test_afastado_pode_ficar_sem_substituto_vigente() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    tipo = _tipo_impedimento()

    # A substituição ainda não começou: sem vigência, mesmo com o vínculo gravado.
    afastado_futuro = _perfil(unidade, rf="700530", cargo_comissao=_cargo_comissao())
    impedimento_futuro = _impedir(
        afastado_futuro, tipo, hoje - timedelta(days=5), hoje + timedelta(days=30)
    )
    substituto_futuro = _perfil(unidade, rf="700531", nome="Substituto Futuro")
    _designar(
        impedimento_futuro,
        substituto_futuro,
        hoje + timedelta(days=10),
        hoje + timedelta(days=20),
    )
    assert substituicao_vigente(afastado_futuro) is None
    assert afastado_futuro.em_exercicio is False

    # A substituição já terminou: mesma ausência de vigência.
    afastado_passado = _perfil(
        unidade,
        rf="700532",
        nome="Afastado Passado",
        cargo_comissao=_cargo_comissao(sigla="CDD", nome="Diretor Passado"),
    )
    impedimento_passado = _impedir(
        afastado_passado, tipo, hoje - timedelta(days=30), hoje + timedelta(days=30)
    )
    substituto_passado = _perfil(unidade, rf="700533", nome="Substituto Passado")
    _designar(
        impedimento_passado,
        substituto_passado,
        hoje - timedelta(days=30),
        hoje - timedelta(days=10),
    )
    assert substituicao_vigente(afastado_passado) is None

    # No dia em que uma delas vale, a mesma leitura responde certo — a resposta não vem da
    # existência da linha.
    afastado_coberto = _perfil(
        unidade,
        rf="700534",
        nome="Afastado Coberto",
        cargo_comissao=_cargo_comissao(sigla="CDE", nome="Diretor Coberto"),
    )
    impedimento_coberto = _impedir(
        afastado_coberto, tipo, hoje - timedelta(days=5), hoje + timedelta(days=5)
    )
    substituto_coberto = _perfil(unidade, rf="700535", nome="Substituto Coberto")
    designacao_vigente = _designar(
        impedimento_coberto,
        substituto_coberto,
        hoje - timedelta(days=5),
        hoje + timedelta(days=5),
    )
    assert substituicao_vigente(afastado_coberto) == designacao_vigente


# ---------------------------------------------------------------------------
# encerrar_substituicao / trocar_substituto — o histórico vem da lista, sem tabela nova
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_encerrar_substituicao_registra_ou_apaga() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    tipo = _tipo_impedimento()
    afastado = _perfil(unidade, rf="700540", cargo_comissao=_cargo_comissao())
    impedimento = _impedir(
        afastado, tipo, hoje - timedelta(days=10), hoje + timedelta(days=30)
    )

    em_curso_substituto = _perfil(unidade, rf="700541", nome="Em Curso")
    em_curso = _designar(
        impedimento,
        em_curso_substituto,
        hoje - timedelta(days=10),
        hoje + timedelta(days=10),
    )
    encerrar_substituicao(em_curso)
    em_curso.refresh_from_db()
    assert em_curso.data_fim == hoje
    assert substituicoes_do_impedimento(impedimento).filter(pk=em_curso.pk).exists()

    futuro_substituto = _perfil(unidade, rf="700542", nome="Futuro")
    futura = _designar(
        impedimento,
        futuro_substituto,
        hoje + timedelta(days=11),
        hoje + timedelta(days=30),
    )
    encerrar_substituicao(futura)
    assert not substituicoes_do_impedimento(impedimento).filter(pk=futura.pk).exists()


@banco
@pytest.mark.django_db
def test_trocar_substituto_encerra_a_anterior_na_vespera() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    tipo = _tipo_impedimento()
    afastado = _perfil(unidade, rf="700550", cargo_comissao=_cargo_comissao())
    impedimento = _impedir(
        afastado, tipo, hoje - timedelta(days=10), hoje + timedelta(days=30)
    )

    anterior_substituto = _perfil(unidade, rf="700551", nome="Anterior")
    anterior = _designar(
        impedimento,
        anterior_substituto,
        hoje - timedelta(days=10),
        hoje + timedelta(days=30),
    )

    novo_substituto = _perfil(unidade, rf="700552", nome="Novo")
    dia_que_assume = hoje + timedelta(days=5)
    nova = trocar_substituto(
        anterior,
        TrocaDeSubstituto(
            substituto=novo_substituto.pk,
            data_inicio=dia_que_assume,
            data_fim=hoje + timedelta(days=30),
        ),
    )

    anterior.refresh_from_db()
    assert anterior.data_fim == dia_que_assume - timedelta(days=1)
    assert nova.data_inicio == dia_que_assume
    assert substituicoes_do_impedimento(impedimento).count() == 2
    # Sem dia com dois vigentes e sem lacuna entre elas.
    assert substituicao_vigente(afastado) is not None


# ---------------------------------------------------------------------------
# retornar_ao_exercicio — o único retorno antecipado, e acerta as substituições na mesma transação
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_voltar_ao_exercicio_encerra_impedimentos_e_acerta_substituicoes() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    afastado = _perfil(unidade, rf="700560", cargo_comissao=_cargo_comissao())
    impedimento_1 = _impedir(
        afastado,
        _tipo_impedimento(),
        hoje - timedelta(days=10),
        hoje + timedelta(days=30),
    )
    impedimento_2 = _impedir(
        afastado,
        _tipo_impedimento(nome="Licença Retorno"),
        hoje - timedelta(days=5),
        None,
    )

    em_curso_substituto = _perfil(unidade, rf="700561", nome="Em Curso Retorno")
    em_curso = _designar(
        impedimento_1,
        em_curso_substituto,
        hoje - timedelta(days=10),
        hoje + timedelta(days=30),
    )
    futuro_substituto = _perfil(unidade, rf="700562", nome="Futuro Retorno")
    # Depois do fim da que está em curso: os dois impedimentos se sobrepõem, e o substituído nunca
    # tem duas substituições que se cruzem — venham do mesmo afastamento ou de outro.
    futura = _designar(impedimento_2, futuro_substituto, hoje + timedelta(days=31), None)

    retornar_ao_exercicio(afastado)

    afastado.refresh_from_db()
    assert afastado.em_exercicio is True
    impedimento_1.refresh_from_db()
    impedimento_2.refresh_from_db()
    # Na véspera, e não hoje: o período é inclusivo no fim, então afastamento que termina hoje ainda
    # vale hoje — e quem volta ao exercício volta agora, não amanhã.
    assert impedimento_1.data_fim == hoje - timedelta(days=1)
    assert impedimento_2.data_fim == hoje - timedelta(days=1)
    em_curso.refresh_from_db()
    assert em_curso.data_fim == hoje - timedelta(days=1)
    assert not Substituicao.objects.filter(pk=futura.pk).exists()


# ---------------------------------------------------------------------------
# A designação não mexe na titularidade (SPEC 014): o vínculo continua com o afastado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_designar_substituto_nao_mexe_na_titularidade() -> None:
    unidade = _unidade()
    hoje = timezone.localdate()
    titular = _perfil(unidade, rf="700570", cargo_comissao=_cargo_comissao())
    definir_titular(titular)
    impedimento = _impedir(
        titular, _tipo_impedimento(), hoje, hoje + timedelta(days=10)
    )
    substituto = _perfil(unidade, rf="700571", nome="Substituto Titularidade")
    _designar(impedimento, substituto, hoje, hoje + timedelta(days=10))

    titular.refresh_from_db()
    substituto.refresh_from_db()
    assert titular.e_titular is True
    assert substituto.e_titular is False

    estado = EstadoDaDirecao(
        tem_titular=True,
        titular_em_exercicio=titular.em_exercicio,
        substituto_do_titular_em_exercicio=substituicao_vigente(titular) is not None,
    )
    assert avaliar_direcao(estado) == Direcao.SUBSTITUTO

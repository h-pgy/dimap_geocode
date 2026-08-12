"""
Testes de avaliar_titularidade (SPEC user_admin/014): cargo compatível com o porte da unidade —
chefia é obrigatória, alta administração satisfaz qualquer tipo, e fora dela o nível do cargo
precisa alcançar o mínimo do tipo. Domínio puro, sem Django.
"""

from services.domain.titularidade import RequisitoTitularidade, avaliar_titularidade

# Escala do cargo em comissão (CargoComissao.nivel): 1..6 — ver apps/user_admin/models/cargos.py.
NIVEL_MAXIMO_DO_CARGO = 6


def _requisito(**overrides: object) -> RequisitoTitularidade:
    dados: dict[str, object] = {
        "e_chefia": True,
        "alta_administracao": False,
        "nivel_cargo": 4,
        "tipo_exige_alta_administracao": False,
        "nivel_minimo_do_tipo": 4,
    }
    dados.update(overrides)
    return RequisitoTitularidade(**dados)  # type: ignore[arg-type]


def test_adequacao_exige_chefia_e_nivel_suficiente() -> None:
    # Diretor de Divisão (chefia, nível 4) titulariza a Divisão, cujo mínimo é 4.
    diretor_de_divisao = _requisito(nivel_cargo=4, nivel_minimo_do_tipo=4)
    assert avaliar_titularidade(diretor_de_divisao) is True

    # Chefe de Seção (chefia, nível 3) não titulariza Coordenadoria, cujo mínimo é 6.
    chefe_de_secao = _requisito(nivel_cargo=3, nivel_minimo_do_tipo=6)
    assert avaliar_titularidade(chefe_de_secao) is False

    # Assessor VI é CDA-VI — nível máximo da escala — mas não é chefia: não titulariza nada.
    assessor_vi = _requisito(
        e_chefia=False,
        nivel_cargo=NIVEL_MAXIMO_DO_CARGO,
        nivel_minimo_do_tipo=1,
    )
    assert avaliar_titularidade(assessor_vi) is False


def test_tipo_que_exige_alta_administracao_recusa_qualquer_nivel() -> None:
    tipo_alta_administracao: dict[str, object] = {
        "tipo_exige_alta_administracao": True,
        "nivel_minimo_do_tipo": None,
    }

    subsecretario = _requisito(
        alta_administracao=True,
        nivel_cargo=None,
        **tipo_alta_administracao,
    )
    assert avaliar_titularidade(subsecretario) is True

    # Nível máximo da escala do cargo em comissão não alcança: o tipo exige estar acima dela.
    no_topo_da_escala = _requisito(
        nivel_cargo=NIVEL_MAXIMO_DO_CARGO,
        **tipo_alta_administracao,
    )
    assert avaliar_titularidade(no_topo_da_escala) is False

"""
Ponte entre a adequação de titularidade (`services/domain/titularidade/`) e os models — o que
`Perfil.clean()` e `Unidade.clean()` chamam (SPEC user_admin/014). Importa só o catálogo de cargos,
por isso não fecha ciclo com `user.py` nem com `unidade.py`.
"""

from services.domain.titularidade import RequisitoTitularidade, avaliar_titularidade

from .cargos import CargoComissao


def cargo_titulariza(
    cargo: CargoComissao | None,
    exige_alta_administracao: bool,
    nivel_minimo: int | None,
) -> bool:
    # Sem cargo em comissão não há chefia, e o avaliador recusa na primeira guarda.
    requisito = RequisitoTitularidade(
        e_chefia=bool(cargo and cargo.e_chefia),
        alta_administracao=bool(cargo and cargo.alta_administracao),
        nivel_cargo=cargo.nivel if cargo else None,
        tipo_exige_alta_administracao=exige_alta_administracao,
        nivel_minimo_do_tipo=nivel_minimo,
    )
    return avaliar_titularidade(requisito)

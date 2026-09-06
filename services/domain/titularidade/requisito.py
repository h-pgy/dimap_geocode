"""
Cargo compatível com o porte da unidade (SPEC user_admin/014): a adequação que o `clean()` do
`Perfil` e da `Unidade` chamam, e que o teste fixa sem Django.
"""

from services.domain.titularidade.models import RequisitoTitularidade


class AvaliadorTitularidade:
    """Cargo compatível com o porte da unidade. Sem Django: a regra é a mesma no clean, na view
    e no teste."""

    def __call__(self, requisito: RequisitoTitularidade) -> bool:
        # Nível sem chefia não basta: Assessor VI é CDA-VI e não dirige nada.
        if not requisito.e_chefia:
            return False
        if requisito.alta_administracao:
            return True
        return self._satisfaz_o_minimo(requisito)

    def _satisfaz_o_minimo(self, requisito: RequisitoTitularidade) -> bool:
        # O tipo exige estar acima da escala, e quem chegou aqui está dentro dela.
        if requisito.tipo_exige_alta_administracao:
            return False
        # Fora dessa exigência os dois níveis existem; o None só sobra por defesa de tipo.
        if requisito.nivel_minimo_do_tipo is None or requisito.nivel_cargo is None:
            return False
        return requisito.nivel_cargo >= requisito.nivel_minimo_do_tipo


def avaliar_titularidade(requisito: RequisitoTitularidade) -> bool:
    return AvaliadorTitularidade()(requisito)

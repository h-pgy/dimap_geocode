class NenhumLoteProximoError(Exception):
    """Nenhum lote do codlog informado dentro do raio consultado."""


class DesenhoInvalidoError(Exception):
    """O polígono não é uma geometria válida — o laço que se cruza, por exemplo."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        # O GEOS anexa a coordenada do defeito entre colchetes, em metros UTM: ruído para quem lê.
        causa = motivo.split("[")[0]
        super().__init__(
            f"O polígono não é válido para a busca de lotes ({causa}): corrija o traço e tente de novo."
        )


class DesenhoGrandeDemaisError(Exception):
    """O polígono passa da área máxima que a busca de lotes aceita."""

    def __init__(self, area_m2: float, area_maxima_m2: float) -> None:
        self.area_m2 = area_m2
        self.area_maxima_m2 = area_maxima_m2
        super().__init__(
            f"O polígono tem {_m2(area_m2)} m², acima da área máxima de {_m2(area_maxima_m2)} m² "
            "para a busca de lotes: desenhe uma área menor."
        )


def _m2(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")

"""
A borda do app que conhece o design system (SPEC user_admin/005 e 007): o banco guarda o slug do
token (`agua-700`), nunca o valor — se a escala for reajustada, todas as unidades acompanham sem
migração de dados. É aqui que o slug vira hex, e o hex sai daqui para dois destinos: o DTO do
gerador de avatar (o domínio recebe cor já resolvida) e a CSS var do template — classe montada no
template (`ring-{{ cor }}`) o Tailwind não enxerga no `@source` e sumiria no build de produção.
"""

from apps.user_admin.models import CorUnidade

# base-100 do tema: a tinta clara, legível sobre os oito tons oferecidos abaixo (SPEC 005).
TINTA_AVATAR = "#F2F8FB"

HEX_POR_COR: dict[str, str] = {
    CorUnidade.AGUA_700: "#0077B6",
    CorUnidade.AGUA_800: "#023E8A",
    CorUnidade.ROCHA_700: "#415A77",
    CorUnidade.ROCHA_900: "#1B263B",
    CorUnidade.MADEIRA_600: "#7F5539",
    CorUnidade.MADEIRA_700: "#5E412F",
    CorUnidade.SAKURA_600: "#BC3A67",
    CorUnidade.SAKURA_700: "#97294F",
}


def hex_da_cor(cor: str) -> str:
    # Slug fora da paleta não chega aqui: o `choices` do model o recusa antes de gravar.
    return HEX_POR_COR[cor]

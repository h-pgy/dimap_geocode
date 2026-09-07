from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .conteudo import ENDERECO_PADRAO, UNIDADE_PADRAO


class MarcacaoConfig(BaseModel):
    """O que distingue um papel timbrado de outro. Os caminhos não têm default: eles dependem da
    raiz do projeto, que o domínio não conhece."""

    model_config = ConfigDict(frozen=True)

    logo_horizontal: Path
    # O SVG da marca d'água já é o claro no repositório: a marca não clareia nada.
    logo_vertical: Path
    # Um nível por item, e não uma linha só: é a marca que decide se empilha ou junta.
    unidade: tuple[str, ...] = UNIDADE_PADRAO
    endereco: tuple[str, ...] = ENDERECO_PADRAO
    largura_timbre_mm: float = 58.0
    largura_marca_dagua_mm: float = 105.0
    margem_lateral_mm: float = 25.0
    respiro_mm: float = 8.0

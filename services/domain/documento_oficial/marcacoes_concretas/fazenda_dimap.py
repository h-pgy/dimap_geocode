from services.utils.pdf import Marcacao, MarcacaoDocumento

from ..marcas import (
    CabecalhoTimbrado,
    CabecalhoUnidade,
    MarcaDagua,
    NumeracaoPaginas,
    RodapeEndereco,
    TimbreHorizontal,
)
from ..models import MarcacaoConfig, Tema


def marcacao_fazenda_dimap(config: MarcacaoConfig, tema: Tema) -> MarcacaoDocumento:
    """A composição das marcas na ordem em que se empilham. Trocar de papel timbrado é escrever
    outro módulo ao lado deste; trocar de unidade é trocar a config."""
    # Só a principal: o papel da SF é o mesmo em toda página. Primeira, última e página nomeada
    # existem no motor (SPEC 001) e entram quando um documento pedir capa própria.
    return MarcacaoDocumento(
        principal=Marcacao(
            marcas=(
                CabecalhoTimbrado(
                    TimbreHorizontal(config.logo_horizontal, config.largura_timbre_mm),
                    CabecalhoUnidade(
                        config.unidade,
                        tema.estilo_cabecalho_marca,
                        tema.entrelinha_marca_mm,
                    ),
                    config.respiro_mm,
                ),
                MarcaDagua(config.logo_vertical, config.largura_marca_dagua_mm),
                RodapeEndereco(
                    config.endereco,
                    tema.estilo_rodape_marca,
                    tema.entrelinha_marca_mm,
                ),
                NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            ),
            margem_lateral_mm=config.margem_lateral_mm,
            margem_vertical_mm=config.margem_vertical_mm,
            respiro_mm=config.respiro_mm,
        )
    )

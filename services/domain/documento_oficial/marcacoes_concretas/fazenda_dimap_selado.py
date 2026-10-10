from services.domain.documento_selado import SeloImpresso
from services.utils.pdf import (
    Marcacao,
    MarcacaoDocumento,
    MarcasEmpilhadas,
    MarcasLadoALado,
    Posicao,
)

from ..marcas import (
    CabecalhoTimbrado,
    CabecalhoUnidade,
    MarcaDagua,
    NumeracaoPaginas,
    RodapeEndereco,
    SeloCompacto,
    TimbreHorizontal,
)
from ..models import MarcacaoConfig, QuadroSeloConfig, Tema


def marcacao_fazenda_dimap_selado(
    config: MarcacaoConfig,
    tema: Tema,
    selo: SeloImpresso,
    quadro: QuadroSeloConfig,
) -> MarcacaoDocumento:
    """O papel timbrado da SF com selo, ao lado do que já existe. Trocar de papel timbrado é
    escrever outro módulo: `fazenda_dimap` não muda, e o QR genérico do pé some porque o do selo o
    substitui."""
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
                # Endereço e paginação empilhados à esquerda; o quadro compacto à direita, com
                # largura declarada. Quem não declara largura — a coluna de texto — fica com a sobra.
                MarcasLadoALado(
                    (
                        MarcasEmpilhadas(
                            (
                                RodapeEndereco(
                                    config.endereco,
                                    tema.estilo_rodape_marca,
                                    tema.entrelinha_marca_mm,
                                ),
                                NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
                            ),
                            Posicao.INFERIOR,
                        ),
                        SeloCompacto(selo, quadro, tema),
                    ),
                    Posicao.INFERIOR,
                    config.respiro_mm,
                ),
            ),
            margem_lateral_mm=config.margem_lateral_mm,
            margem_vertical_mm=config.margem_vertical_mm,
            respiro_mm=config.respiro_mm,
        )
    )

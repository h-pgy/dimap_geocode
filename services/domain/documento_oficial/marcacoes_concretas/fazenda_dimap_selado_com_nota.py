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
    NotaDeRodape,
    NumeracaoPaginas,
    RodapeEndereco,
    SeloCompacto,
    TimbreHorizontal,
)
from ..models import MarcacaoConfig, QuadroSeloConfig, Tema


def marcacao_fazenda_dimap_selado_com_nota(
    config: MarcacaoConfig,
    tema: Tema,
    selo: SeloImpresso,
    quadro: QuadroSeloConfig,
    *,
    nota: tuple[str, ...],
) -> MarcacaoDocumento:
    rodape = MarcasEmpilhadas(
        (
            NotaDeRodape(nota, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            RodapeEndereco(config.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
        ),
        Posicao.INFERIOR,
    )
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
                MarcasLadoALado(
                    (
                        rodape,
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

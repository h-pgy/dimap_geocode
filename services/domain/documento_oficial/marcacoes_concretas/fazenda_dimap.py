from services.utils.pdf import Marca, Marcacao, MarcacaoDocumento, MarcasEmpilhadas, Posicao

from ..marcas import (
    CabecalhoTimbrado,
    CabecalhoUnidade,
    MarcaDagua,
    NumeracaoPaginas,
    QrCodeRodape,
    RodapeComQr,
    RodapeEndereco,
    TimbreHorizontal,
)
from ..models import MarcacaoConfig, Tema


def marcacao_fazenda_dimap(
    config: MarcacaoConfig,
    tema: Tema,
    qr_verificacao: str | None = None,
) -> MarcacaoDocumento:
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
                *_rodape(config, tema, qr_verificacao),
            ),
            margem_lateral_mm=config.margem_lateral_mm,
            margem_vertical_mm=config.margem_vertical_mm,
            respiro_mm=config.respiro_mm,
        )
    )


def _rodape(config: MarcacaoConfig, tema: Tema, qr_verificacao: str | None) -> tuple[Marca, ...]:
    # `None` é o documento SEM verificação, e não um QR vazio: a maioria dos atos não tem código a
    # conferir, e um símbolo em branco no pé seria pior que símbolo nenhum. Sem ele o pé é o de
    # sempre — duas marcas soltas, cada uma na sua faixa.
    texto = (
        RodapeEndereco(config.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
        NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
    )
    if qr_verificacao is None:
        return texto
    return (
        RodapeComQr(
            MarcasEmpilhadas(texto, Posicao.INFERIOR),
            QrCodeRodape(qr_verificacao, config.largura_qr_rodape_mm),
            config.respiro_mm,
        ),
    )

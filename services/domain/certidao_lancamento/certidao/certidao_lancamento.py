from services.domain.documento_oficial import (
    DocumentoRenderizado,
    MarcacaoConfig,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    SeloConfig,
    Tema,
)
from services.domain.documento_oficial.marcacoes_concretas.fazenda_dimap_selado_com_nota import (
    marcacao_fazenda_dimap_selado_com_nota,
)
from services.domain.documento_selado import (
    SeloImpressoInput,
    montar_selo_impresso,
)

from ..models import CertidaoLancamentoInput
from .certidao_builder import MontarCertidaoLancamento, MontarCertidaoLancamentoInput


class CertidaoLancamento:
    """O tipo: conteúdo + papel selado com nota de rodapé + tema. Quem emite só preenche o DTO."""

    def __init__(
        self,
        tema: Tema,
        config: MarcacaoConfig,
        selo_config: SeloConfig,
    ) -> None:
        self._montar = MontarCertidaoLancamento()
        self._tema = tema
        self._config = config
        self._selo_config = selo_config
        self._renderizar = RenderizarDocumentoOficial(tema)

    def __call__(self, pedido: CertidaoLancamentoInput) -> DocumentoRenderizado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: CertidaoLancamentoInput) -> DocumentoRenderizado:
        selo = montar_selo_impresso(
            SeloImpressoInput(
                envelope=pedido.envelope,
                base_url=pedido.base_url,
            )
        )
        conteudo = self._montar(
            MontarCertidaoLancamentoInput(
                certidao=pedido,
                selo=selo,
                quadro=self._selo_config.fecho,
            )
        )
        marcacao = marcacao_fazenda_dimap_selado_com_nota(
            self._config,
            self._tema,
            selo,
            self._selo_config.compacto,
            nota=self._nota(pedido),
        )
        return self._renderizar(
            RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)
        )

    def _nota(self, pedido: CertidaoLancamentoInput) -> tuple[str, ...]:
        momento = pedido.consultado_em
        # Cada item é UMA linha da faixa: numa frase só o rodapé estoura e quebra no meio.
        return (
            "Certidão emitida de forma automatizada",
            f"Dados cadastrais consultados no GeoSampa em {momento:%d/%m/%Y} às {momento:%H:%M}",
        )

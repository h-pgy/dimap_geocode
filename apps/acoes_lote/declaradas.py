from apps.certidao_lancamento.acoes_declaradas import ACAO_EMITIR_CERTIDAO_LANCAMENTO
from .estrutura import AcaoDeLote, ContratoAcoesLote

ACOES_LOTE = ContratoAcoesLote(
    itens=(
        AcaoDeLote(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal"),
    )
)

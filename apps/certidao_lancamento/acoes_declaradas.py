from apps.competencias.utils import instanciar_acao
from services.domain.autorizacao import VarianteIcone

ACAO_EMITIR_CERTIDAO_LANCAMENTO = instanciar_acao(
    slug="certidao_lancamento.emitir",
    nome="Emitir certidão de existência de lançamento",
    nome_curto="Certidão de lançamento",
    tooltip="Emite o PDF selado que atesta o lançamento do IPTU do lote.",
    url_name="certidao_lancamento:modal",
    variantes_icone=frozenset({VarianteIcone.PEQUENO}),
    estrutural=False,
    alcance=None,
)

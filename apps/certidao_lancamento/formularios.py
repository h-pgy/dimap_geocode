from services.domain.certidao_lancamento.models import PedidoCertidao
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    RegraDeErro,
    TradutorDeRecusa,
)

FORMULARIO_CERTIDAO = Formulario(
    campos=(
        CampoDeFormulario(
            controle="processo",
            rotulo="Processo SEI",
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="O número do processo SEI não está no formato padrão (NNNN.AAAA/NNNNNNN-D)."
                ),
            },
        ),
        CampoDeFormulario(
            controle="interessado",
            rotulo="Nome do interessado",
            regras={
                "string_too_short": RegraDeErro(
                    mensagem="Informe o nome completo ou razão social do interessado."
                ),
            },
        ),
    ),
)

ler_pedido_certidao = LeitorDeFormulario(PedidoCertidao, FORMULARIO_CERTIDAO)
traduzir_recusa_certidao = TradutorDeRecusa(FORMULARIO_CERTIDAO)

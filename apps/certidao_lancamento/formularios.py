from services.domain.certidao_lancamento.models import PedidoCertidao
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    RegraDeErro,
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
        CampoDeFormulario(
            controle="cpf_cnpj",
            rotulo="CPF/CNPJ",
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="O CPF deve ter 11 dígitos e o CNPJ, 14. Deixe em branco se não constar do processo."
                ),
            },
        ),
        CampoDeFormulario(
            controle="tipo_despacho",
            rotulo="Tipo de despacho",
            regras={"enum": RegraDeErro(mensagem="Escolha um dos textos de despacho.")},
        ),
        CampoDeFormulario(
            controle="sentido",
            rotulo="Despacho",
            regras={
                "enum": RegraDeErro(
                    mensagem="Escolha se o despacho defere ou indefere."
                )
            },
        ),
        CampoDeFormulario(controle="observacoes", rotulo="Observações"),
    ),
)

ler_pedido_certidao = LeitorDeFormulario(PedidoCertidao, FORMULARIO_CERTIDAO)

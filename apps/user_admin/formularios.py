"""
Catálogo do formulário de servidor (SPEC criacao_usuarios/004, sobre o contrato de
formularios/001): quais controles a tela tem e como cada recusa se diz para quem preencheu. Editar
(SPEC criacao_usuarios/005) reusa o mesmo catálogo — os controles são os mesmos, só o DTO lido muda.
"""

from apps.user_admin.schemas import (
    ERRO_FIM_ANTES_DO_INICIO,
    ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO,
    EdicaoServidor,
    NovaSubstituicao,
    NovoImpedimento,
    NovoServidor,
    TrocaDeSubstituto,
)
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    RegraDeErro,
    TradutorDeRecusa,
)

FORMULARIO_SERVIDOR = Formulario(
    campos=(
        CampoDeFormulario(
            controle="rf",
            rotulo="RF",
            # `string_pattern_mismatch` é um tipo só para todos os campos com formato: é aqui, por
            # controle, que ele vira a frase que ensina o formato daquele campo.
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="RF: sete dígitos, com ou sem pontuação (812.345-6)."
                )
            },
        ),
        CampoDeFormulario(
            controle="nome",
            rotulo="Nome",
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="Nome: só letras, espaço, hífen e apóstrofo."
                )
            },
        ),
        CampoDeFormulario(
            controle="sobrenome",
            rotulo="Sobrenome",
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="Sobrenome: só letras, espaço, hífen e apóstrofo."
                )
            },
        ),
        CampoDeFormulario(
            controle="email",
            rotulo="E-mail",
            regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.")},
        ),
        CampoDeFormulario(controle="unidade", rotulo="Unidade"),
        CampoDeFormulario(controle="cargo_base", rotulo="Cargo base"),
        CampoDeFormulario(controle="cargo_comissao", rotulo="Cargo em comissão"),
        # A foto não vinha no catálogo porque nada a recusava; agora tamanho e formato recusam.
        CampoDeFormulario(controle="foto", rotulo="Foto"),
        # SPEC user_admin/022: a mensagem já vem escrita da fonte (`ERRO_SEM_CANETA`,
        # `ERRO_AUTO_REVOGACAO`) — o catálogo existe aqui só para o controle ser reconhecido e
        # realçado, não para fornecer frase.
        CampoDeFormulario(controle="administrador", rotulo="Administrador do Sistema"),
    )
)

ler_novo_servidor = LeitorDeFormulario(NovoServidor, FORMULARIO_SERVIDOR)
traduzir_recusa = TradutorDeRecusa(FORMULARIO_SERVIDOR)
# Mesmos controles, mesmos rótulos, mesmas frases: o que muda entre criar e editar é o DTO lido,
# não como a recusa se diz. Um catálogo irmão seria a mesma tabela com outro nome.
ler_edicao_servidor = LeitorDeFormulario(EdicaoServidor, FORMULARIO_SERVIDOR)

# SPEC user_admin/023: catálogo irmão do do servidor — três controles, os mesmos `name=` do modal.
FORMULARIO_IMPEDIMENTO = Formulario(
    campos=(
        CampoDeFormulario(controle="tipo", rotulo="Tipo"),
        CampoDeFormulario(controle="data_inicio", rotulo="Início"),
        CampoDeFormulario(
            controle="data_fim",
            rotulo="Fim",
            # A frase já vem escrita da fonte; o catálogo existe para o controle ser reconhecido e
            # o realce cair no campo certo.
            regras={"fim_antes_do_inicio": RegraDeErro(mensagem=ERRO_FIM_ANTES_DO_INICIO)},
        ),
    ),
)

ler_novo_impedimento = LeitorDeFormulario(NovoImpedimento, FORMULARIO_IMPEDIMENTO)
traduzir_recusa_impedimento = TradutorDeRecusa(FORMULARIO_IMPEDIMENTO)

# SPEC user_admin/024: catálogo irmão do do impedimento — três controles.
FORMULARIO_SUBSTITUICAO = Formulario(
    campos=(
        CampoDeFormulario(controle="substituto", rotulo="Servidor"),
        CampoDeFormulario(controle="data_inicio", rotulo="Início da substituição"),
        CampoDeFormulario(
            controle="data_fim",
            rotulo="Fim da substituição",
            regras={
                "fim_antes_do_inicio": RegraDeErro(
                    mensagem=ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO
                )
            },
        ),
    ),
)

ler_nova_substituicao = LeitorDeFormulario(NovaSubstituicao, FORMULARIO_SUBSTITUICAO)
ler_troca_de_substituto = LeitorDeFormulario(TrocaDeSubstituto, FORMULARIO_SUBSTITUICAO)
traduzir_recusa_substituicao = TradutorDeRecusa(FORMULARIO_SUBSTITUICAO)


"""
Catálogo do formulário de servidor (SPEC criacao_usuarios/004, sobre o contrato de
formularios/001): quais controles a tela tem e como cada recusa se diz para quem preencheu. Editar
(SPEC criacao_usuarios/005) reusa o mesmo catálogo — os controles são os mesmos, só o DTO lido muda.
"""

from apps.user_admin.schemas import EdicaoServidor, NovoServidor
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    RegraDeErro,
    TradutorDeRecusa,
)

FORMULARIO_SERVIDOR = Formulario(
    campos=(
        CampoDeFormulario(controle="rf", rotulo="RF"),
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sobrenome", rotulo="Sobrenome"),
        CampoDeFormulario(
            controle="email",
            rotulo="E-mail",
            # A única regra particular desta tela: as demais recusas se dizem bem com as padrão.
            regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.")},
        ),
        CampoDeFormulario(controle="unidade", rotulo="Unidade"),
        CampoDeFormulario(controle="cargo_base", rotulo="Cargo base"),
        CampoDeFormulario(controle="cargo_comissao", rotulo="Cargo em comissão"),
    )
)

ler_novo_servidor = LeitorDeFormulario(NovoServidor, FORMULARIO_SERVIDOR)
traduzir_recusa = TradutorDeRecusa(FORMULARIO_SERVIDOR)
# Mesmos sete controles, mesmos rótulos, mesmas frases: o que muda entre criar e editar é o DTO
# lido, não como a recusa se diz. Um catálogo irmão seria a mesma tabela com outro nome.
ler_edicao_servidor = LeitorDeFormulario(EdicaoServidor, FORMULARIO_SERVIDOR)

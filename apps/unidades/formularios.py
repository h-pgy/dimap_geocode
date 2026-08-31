"""
Catálogo do formulário de unidade (SPEC user_admin/020, sobre o contrato de formularios/001): quais
controles a tela tem e como cada recusa se diz para quem preencheu. Criar e editar reusam o mesmo
catálogo — os controles são os mesmos, só o DTO lido muda.
"""

from apps.unidades.schemas import AtoDeUnidade, EdicaoUnidade, NovaUnidade
from services.utils.erros_formulario import (
    CampoDeFormulario,
    ErroBruto,
    Formulario,
    LeitorDeFormulario,
    RecusaDeFormulario,
    RegraDeErro,
    TomDeRealce,
    TradutorDeRecusa,
)

ERRO_NAO_VIRA_RAIZ = "Unidade com superior não vira raiz: escolha a unidade à qual ela passa a responder."
AVISO_TRANSFERENCIA = (
    "Transferir {sigla}: ela e todas as unidades abaixo dela passam a responder a {destino}. "
    "Se o destino estiver fora do seu alcance, você deixa de administrá-la. Confirme para gravar."
)

FORMULARIO_UNIDADE = Formulario(
    campos=(
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sigla", rotulo="Sigla"),
        CampoDeFormulario(controle="tipo", rotulo="Tipo"),
        CampoDeFormulario(
            controle="pai",
            rotulo="Unidade superior",
            # O tom vem da regra; a frase vem escrita do ato, com as siglas. `transferencia` fica
            # fora das REGRAS_PADRAO de propósito: nada mais no sistema o levanta.
            regras={
                "transferencia": RegraDeErro(
                    mensagem=AVISO_TRANSFERENCIA,
                    tom=TomDeRealce.ALERTA,
                )
            },
        ),
        CampoDeFormulario(controle="cor", rotulo="Cor"),
        # SPEC user_admin/025: o alvo do modal de extinguir/reativar. `veredito` fica fora das
        # REGRAS_PADRAO pelo mesmo motivo que `transferencia` — nada mais no sistema o levanta.
        CampoDeFormulario(
            controle="unidade",
            rotulo="Unidade",
            regras={"veredito": RegraDeErro(mensagem="{motivo}", tom=TomDeRealce.ERRO)},
        ),
    )
)

ler_nova_unidade = LeitorDeFormulario(NovaUnidade, FORMULARIO_UNIDADE)
ler_edicao_unidade = LeitorDeFormulario(EdicaoUnidade, FORMULARIO_UNIDADE)
ler_ato_de_unidade = LeitorDeFormulario(AtoDeUnidade, FORMULARIO_UNIDADE)
traduzir_recusa = TradutorDeRecusa(FORMULARIO_UNIDADE)


def recusa_do_veredito(motivo: str) -> RecusaDeFormulario:
    """O `motivo` do avaliador já chega em português e pronto para a tela (SPEC user_admin/025): o
    catálogo não o reescreve, só o põe no controle certo."""
    return traduzir_recusa(
        (ErroBruto(controle="unidade", tipo="veredito", mensagem=motivo),)
    )

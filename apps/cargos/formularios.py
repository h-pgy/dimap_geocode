"""
Catálogo dos formulários dos dois catálogos de cargo (SPECs user_admin/029 e 030, sobre o contrato
de formularios/001): quais controles cada tela tem e como cada recusa se diz para quem preencheu.
Criar e editar reusam o mesmo catálogo — os controles são os mesmos, só o DTO lido muda.
"""

from apps.cargos.schemas import EdicaoCargo, EdicaoCargoBase, NovaCargo, NovaCargoBase
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

FORMULARIO_CARGO = Formulario(
    campos=(
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sigla", rotulo="Sigla"),
        # A trava de natureza (SPEC, §7) recai sobre o nível: é o controle que a tela destaca
        # quando a edição tenta mudar nível, chefia ou alta administração de cargo ocupado.
        CampoDeFormulario(
            controle="nivel",
            rotulo="Nível",
            regras={
                "trava_natureza": RegraDeErro(mensagem="{motivo}", tom=TomDeRealce.ALERTA)
            },
        ),
        CampoDeFormulario(controle="e_chefia", rotulo="Natureza"),
        CampoDeFormulario(controle="alta_administracao", rotulo="Alta administração"),
        # SPEC user_admin/029: o alvo do modal de extinguir/reativar.
        CampoDeFormulario(
            controle="cargo",
            rotulo="Cargo",
            regras={"veredito": RegraDeErro(mensagem="{motivo}", tom=TomDeRealce.ERRO)},
        ),
    )
)

# Cargo base não tem nível nem natureza (SPEC user_admin/030): só identificação, e o mesmo alvo de
# extinguir/reativar do outro catálogo.
FORMULARIO_CARGO_BASE = Formulario(
    campos=(
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sigla", rotulo="Sigla"),
        CampoDeFormulario(
            controle="cargo",
            rotulo="Cargo",
            regras={"veredito": RegraDeErro(mensagem="{motivo}", tom=TomDeRealce.ERRO)},
        ),
    )
)

ler_nova_cargo = LeitorDeFormulario(NovaCargo, FORMULARIO_CARGO)
ler_edicao_cargo = LeitorDeFormulario(EdicaoCargo, FORMULARIO_CARGO)
traduzir_recusa = TradutorDeRecusa(FORMULARIO_CARGO)

ler_nova_cargo_base = LeitorDeFormulario(NovaCargoBase, FORMULARIO_CARGO_BASE)
ler_edicao_cargo_base = LeitorDeFormulario(EdicaoCargoBase, FORMULARIO_CARGO_BASE)
traduzir_recusa_base = TradutorDeRecusa(FORMULARIO_CARGO_BASE)


def recusa_de_natureza(motivo: str) -> RecusaDeFormulario:
    return traduzir_recusa(
        (ErroBruto(controle="nivel", tipo="trava_natureza", mensagem=motivo),)
    )


def recusa_do_veredito(motivo: str) -> RecusaDeFormulario:
    """O `motivo` do avaliador já chega em português e pronto para a tela: o catálogo não o
    reescreve, só o põe no controle certo."""
    return traduzir_recusa(
        (ErroBruto(controle="cargo", tipo="veredito", mensagem=motivo),)
    )


def recusa_do_veredito_base(motivo: str) -> RecusaDeFormulario:
    return traduzir_recusa_base(
        (ErroBruto(controle="cargo", tipo="veredito", mensagem=motivo),)
    )

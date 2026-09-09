from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    TradutorDeRecusa,
)

FORMULARIO_CODIGO = Formulario(
    campos=(
        CampoDeFormulario(controle="codigo", rotulo="Código do documento"),
    )
)

traduzir_recusa_codigo = TradutorDeRecusa(FORMULARIO_CODIGO)

from collections.abc import Mapping

from .models import RegraDeErro

# O Pydantic classifica por tipo; é aqui que cada tipo vira frase. Formulário nenhum precisa
# redeclarar "preencha o campo" — só o que for particular dele.
REGRAS_PADRAO: Mapping[str, RegraDeErro] = {
    "missing": RegraDeErro(mensagem="Preencha o campo {rotulo}."),
    "string_too_short": RegraDeErro(
        mensagem="Preencha o campo {rotulo} com a quantidade mínima de caracteres."
    ),
    "string_too_long": RegraDeErro(mensagem="{rotulo}: texto longo demais."),
    # Campo com BeforeValidator sai da validação de string do Pydantic e erra por comprimento
    # genérico: sem estes dois, "preencha o RF" vira "valor inválido" quando o campo ganha
    # normalização.
    "too_short": RegraDeErro(mensagem="Preencha o campo {rotulo}."),
    "too_long": RegraDeErro(mensagem="{rotulo}: texto longo demais."),
    "int_parsing": RegraDeErro(mensagem="{rotulo}: escolha uma opção da lista."),
    "value_error": RegraDeErro(mensagem="{rotulo}: valor inválido."),
}
REGRA_DESCONHECIDA = RegraDeErro(mensagem="{rotulo}: valor inválido.")

from .models import Botao, ConteudoEmail, Destaque, EmailAcessoInput, Otp, Paragrafo, Titulo

ASSUNTO_ACESSO = "DIMAP GeoCoder — seu acesso"


class MontarEmailAcesso:
    """Callable: o pedido vira o que o e-mail vai dizer."""

    def __call__(self, pedido: EmailAcessoInput) -> ConteudoEmail:
        return ConteudoEmail(
            assunto=ASSUNTO_ACESSO,
            blocos=(
                Titulo(texto="Sua conta no DIMAP GeoCoder já existe"),
                Paragrafo(texto=f"{pedido.nome}, entre com o seu RF e a senha temporária abaixo."),
                Destaque(rotulo="RF", valor=pedido.rf, monoespacado=True),
                # `get_secret_value` no último ponto antes do corpo: o SecretStr protege quem passa
                # o pedido adiante, não a mensagem — que existe para entregar a senha.
                Otp(
                    rotulo="Senha temporária",
                    valor=pedido.senha_temporaria.get_secret_value(),
                ),
                Paragrafo(texto="Troque a senha assim que entrar."),
                Botao(rotulo="Acessar o DIMAP GeoCoder", url=pedido.url_acesso),
            ),
            rodape="Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
        )


montar_email_acesso = MontarEmailAcesso()

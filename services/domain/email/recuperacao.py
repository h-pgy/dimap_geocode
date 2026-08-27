from .models import Botao, ConteudoEmail, Divisor, EmailRecuperacaoInput, Paragrafo, Titulo

ASSUNTO_RECUPERACAO = "DIMAP GeoCoder — redefinição de senha"


class MontarEmailRecuperacao:
    """Callable: o pedido vira o que o e-mail vai dizer."""

    def __call__(self, pedido: EmailRecuperacaoInput) -> ConteudoEmail:
        return ConteudoEmail(
            assunto=ASSUNTO_RECUPERACAO,
            blocos=(
                Titulo(texto="Redefinição de senha"),
                Paragrafo(
                    texto=(
                        f"{pedido.nome}, foi solicitada a redefinição da senha da sua conta no "
                        "DIMAP GeoCoder."
                    )
                ),
                Botao(rotulo="Definir uma nova senha", url=pedido.url_recuperacao),
                Paragrafo(
                    texto=(
                        "O link é de uso único e vale por "
                        f"{pedido.validade_horas} hora(s): depois de aberto uma vez, ele deixa de "
                        "funcionar."
                    )
                ),
                Divisor(),
                Paragrafo(
                    texto=(
                        "Se não foi você quem pediu, ignore esta mensagem: sua senha continua a "
                        "mesma."
                    )
                ),
            ),
            rodape="Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
        )


montar_email_recuperacao = MontarEmailRecuperacao()

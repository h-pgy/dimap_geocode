from .models import ConteudoEmail, Destaque, EmailTesteInput, Paragrafo, Titulo

ASSUNTO = "DIMAP GeoCoder — e-mail de teste"


class MontarEmailTeste:
    """Callable: o pedido de teste vira o que o e-mail vai dizer."""

    def __call__(self, pedido: EmailTesteInput) -> ConteudoEmail:
        return ConteudoEmail(
            assunto=ASSUNTO,
            blocos=(
                Titulo(texto="O envio de e-mail está funcionando"),
                Paragrafo(
                    texto="Esta mensagem foi disparada para provar a configuração de envio do "
                    "DIMAP GeoCoder."
                ),
                # O destaque carrega o que identifica ESTE envio: sem isso, dois testes seguidos
                # são indistinguíveis na caixa de entrada.
                Destaque(
                    rotulo="Ambiente e momento do disparo",
                    valor=f"{pedido.ambiente} · {pedido.momento:%d/%m/%Y %H:%M:%S}",
                    monoespacado=True,
                ),
            ),
            rodape="Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
        )


montar_email_teste = MontarEmailTeste()

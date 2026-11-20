from services.domain.faq.conteudo import Faq, Situacao, Visibilidade

from .models import Leitor


def visibilidades_para(leitor: Leitor) -> frozenset[Visibilidade]:
    if leitor.eh_interno:
        return frozenset({Visibilidade.PUBLICA, Visibilidade.INTERNA})
    return frozenset({Visibilidade.PUBLICA})


def eh_visivel(faq: Faq, leitor: Leitor) -> bool:
    # Rascunho não é "interno": não aparece para ninguém na página.
    return (
        faq.situacao is Situacao.PUBLICADA
        and faq.visibilidade in visibilidades_para(leitor)
    )


def anexo_eh_baixavel(faqs_do_anexo: list[Faq], leitor: Leitor) -> bool:
    # O anexo não tem visibilidade própria: herda a da FAQ mais aberta a que está ligado.
    return any(eh_visivel(f, leitor) for f in faqs_do_anexo)

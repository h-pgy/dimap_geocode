from services.domain.faq.conteudo import Faq


def pode_excluir(faq: Faq) -> bool:
    # A seed (faq/008) conta com a FAQ do sistema: editável por todos, excluível por ninguém.
    return not faq.eh_do_sistema

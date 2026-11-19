from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.faq.conteudo import carregar_faqs
from apps.faq.leitor import leitor_de
from services.domain.faq import MontagemIndiceInput, MontarIndice, visibilidades_para

montar_indice = MontarIndice()


def pagina_faq(request: HttpRequest) -> HttpResponse:
    # Rota aberta de propósito (SPEC faq/001, Caveats): a FAQ pública existe para quem não tem login.
    leitor = leitor_de(request)
    faqs = carregar_faqs(visibilidades_para(leitor))
    indice = montar_indice(MontagemIndiceInput(faqs=faqs, leitor=leitor))
    return render(request, "faq/pagina.html", {"indice": indice, "leitor": leitor})

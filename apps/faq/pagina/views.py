from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.faq.anexos.consulta import anexos_da_lista
from apps.faq.conteudo import carregar_faqs
from apps.faq.leitor import leitor_de
from apps.faq.models import Anexo as AnexoModel
from services.domain.faq import (
    Faq,
    MontagemIndiceInput,
    MontarIndice,
    visibilidades_para,
)

montar_indice = MontarIndice()


def pagina_faq(request: HttpRequest) -> HttpResponse:
    # Rota aberta de propósito (SPEC faq/001, Caveats): a FAQ pública existe para quem não tem login.
    leitor = leitor_de(request)
    faqs = carregar_faqs(visibilidades_para(leitor))
    indice = montar_indice(MontagemIndiceInput(faqs=faqs, leitor=leitor))
    return render(
        request,
        "faq/pagina.html",
        {"indice": indice, "leitor": leitor, "anexos_por_faq": _anexos_por_faq(faqs)},
    )


def _anexos_por_faq(faqs: list[Faq]) -> dict[int, list[AnexoModel]]:
    ids = [anexo_id for faq in faqs for anexo_id in faq.resposta.anexos]
    por_id = {anexo.pk: anexo for anexo in anexos_da_lista(ids)}
    return {
        faq.id: [por_id[i] for i in faq.resposta.anexos if i in por_id]
        for faq in faqs
        if faq.id is not None
    }

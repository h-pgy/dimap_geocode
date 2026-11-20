from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel

from apps.core.acesso import superusuario_requerido
from apps.faq.gestao.formularios import (
    CONTROLE_ANEXO,
    CONTROLE_NOVOS_ANEXOS,
    envios_dos_arquivos,
)
from apps.faq.leitor import leitor_de
from services.utils.extracao_texto import TipoDocumento

from .consulta import anexo_baixavel, anexo_com_texto, anexos_da_lista, buscar_anexos
from .recebimento import conferir_anexos

TEMPLATE_CONFERENCIA = "faq/partials/anexos/_conferencia.html"
TEMPLATE_RESULTADO_BUSCA = "faq/partials/anexos/_resultado_busca.html"
TEMPLATE_LISTA = "faq/partials/gestao/_lista_anexos.html"
TEMPLATE_MODAL_TEXTO = "faq/partials/anexos/_modal_texto.html"
TIPOS_DE_CONTEUDO: dict[str, str] = {
    TipoDocumento.PDF: "application/pdf",
    TipoDocumento.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    TipoDocumento.ODT: "application/vnd.oasis.opendocument.text",
}


class PedidoBuscaAnexo(BaseModel):
    q: str = ""


class PedidoBlocoAnexos(BaseModel):
    adicionar: int | None = None
    remover: int | None = None


@require_GET
def baixar(request: HttpRequest, anexo_id: int) -> HttpResponse:
    # Rota aberta (SPEC faq/003): o anexo herda a visibilidade das FAQs a que está ligado.
    registro = anexo_baixavel(anexo_id, leitor_de(request))
    resposta = HttpResponse(
        bytes(registro.arquivo), content_type=TIPOS_DE_CONTEUDO[registro.tipo]
    )
    # Nome com acento sai no `filename*` (RFC 6266), que o cabeçalho cru não comporta.
    resposta["Content-Disposition"] = content_disposition_header(
        as_attachment=True, filename=registro.nome_arquivo
    )
    return resposta


@superusuario_requerido
@require_POST
def conferir(request: HttpRequest) -> HttpResponse:
    envios = envios_dos_arquivos(request.FILES.getlist(CONTROLE_NOVOS_ANEXOS))
    return render(
        request, TEMPLATE_CONFERENCIA, {"conferencias": conferir_anexos(envios)}
    )


@superusuario_requerido
@require_GET
def buscar(request: HttpRequest) -> HttpResponse:
    pedido = PedidoBuscaAnexo.model_validate(request.GET.dict())
    return render(
        request,
        TEMPLATE_RESULTADO_BUSCA,
        {"anexos": buscar_anexos(pedido.q, _ids_da_lista(request)), "termo": pedido.q},
    )


@superusuario_requerido
@require_GET
def bloco_anexos(request: HttpRequest) -> HttpResponse:
    pedido = PedidoBlocoAnexos.model_validate(
        {
            "adicionar": request.GET.get("adicionar") or None,
            "remover": request.GET.get("remover") or None,
        }
    )
    ids = [i for i in _ids_da_lista(request) if i != pedido.remover]
    if pedido.adicionar is not None and pedido.adicionar not in ids:
        ids.append(pedido.adicionar)
    return render(
        request,
        TEMPLATE_LISTA,
        {
            "anexos_ligados": anexos_da_lista(ids),
            "limpar_busca": pedido.adicionar is not None,
        },
    )


@superusuario_requerido
@require_GET
def texto(request: HttpRequest, anexo_id: int) -> HttpResponse:
    anexo = anexo_com_texto(anexo_id)
    return render(
        request,
        TEMPLATE_MODAL_TEXTO,
        {"anexo": anexo, "caracteres": len(anexo.texto)},
    )


def _ids_da_lista(request: HttpRequest) -> list[int]:
    return [int(i) for i in request.GET.getlist(CONTROLE_ANEXO) if i.isdigit()]

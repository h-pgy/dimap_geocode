from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_fundo_admin
from services.domain.documento_selado import (
    ConferenciaInput,
    TamanhoDoUpload,
    classificar_conferencia,
    codigo_alegado,
    ler_ficha_do_ato,
)
from services.domain.documento_selado.constants import TAMANHO_MAXIMO_MB
from services.utils.assinatura import ConferirInput, conferir_selo

from .acervo import buscar_registro
from .models import DocumentoEmitido

SEGREDO = settings.ASSINATURA_SEGREDO


def pagina_conferencia(request: HttpRequest) -> HttpResponse:
    """Rota ABERTA: a porta de quem tem o arquivo e não tem — ou não consegue ler — o código
    impresso. É para cá que o atalho da home aponta."""
    contexto = {"tamanho_maximo_mb": TAMANHO_MAXIMO_MB, **contexto_fundo_admin()}
    return render(request, "documentos/conferencia.html", contexto)


def conferir_por_codigo(request: HttpRequest, codigo: str) -> HttpResponse:
    """Rota ABERTA (exceção declarada, CLAUDE.md §3.5): é o endereço que o QR do selo abre, e quem
    recebe o documento não tem login."""
    registro = buscar_registro(codigo)
    # A mesma resposta para código inexistente e para código malformado: dizer "existiu e não
    # existe mais" já é informação sobre o acervo.
    if registro is None:
        return render(request, "documentos/partials/_nao_localizado.html", status=404)
    # A ficha, e não a linha: a tela do código e a do upload mostram a mesma coisa.
    contexto = {"ficha": ler_ficha_do_ato(registro.envelope), **contexto_fundo_admin()}
    return render(request, "documentos/conferencia_por_codigo.html", contexto)


@require_POST
def conferir_arquivo(request: HttpRequest) -> HttpResponse:
    """Rota ABERTA: conferir um arquivo que o próprio remetente já tem em mãos não revela nada que
    ele não possua."""
    enviado = request.FILES.get("arquivo")
    # `size` vem do cabeçalho do multipart: o arquivo grande — e o formulário vazio — são
    # recusados aqui, antes de os bytes irem para a memória. O `ValidationError` vira 422 no
    # middleware.
    TamanhoDoUpload(tamanho=(enviado.size or 0) if enviado else 0)
    pdf = enviado.read() if enviado else b""
    selo = conferir_selo(ConferirInput(pdf=pdf, segredo=SEGREDO))
    codigo = codigo_alegado(selo)
    resultado = classificar_conferencia(
        ConferenciaInput(
            resultado_selo=selo,
            registro=buscar_registro(codigo) if codigo else None,
        )
    )
    return render(request, "documentos/partials/_resultado.html", {"resultado": resultado})


@login_required
def segunda_via(request: HttpRequest, codigo: str) -> HttpResponse:
    """Rota PROTEGIDA, ao contrário das três acima: o código está impresso no canto do papel, e
    quem o fotografa de longe não pode com isso baixar o documento inteiro."""
    documento = get_object_or_404(DocumentoEmitido, codigo=codigo)
    # Os MESMOS bytes guardados na emissão. Renderizar de novo daria outro arquivo, com outro
    # selo, e dois documentos diferentes para o mesmo ato.
    return HttpResponse(bytes(documento.arquivo), content_type="application/pdf")

from typing import Any

from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.core.acesso import superusuario_requerido
from apps.faq.gestao.context import opcoes_de_tema, opcoes_de_tema_raiz, rotulo_do_tema
from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Tema as TemaModel
from services.domain.faq import PROFUNDIDADE_PALAVRA_CHAVE

from .formularios import (
    CONTROLE_RELACIONADA,
    criar_palavra_chave,
    criar_tema,
    renomear_palavra_do_modal,
    renomear_tema_do_modal,
)
from .palavras_chave import (
    caminho_de,
    colunas_ate,
    marcadas_do_formulario,
    opcoes_de_palavra,
    opcoes_de_pai,
)

TEMPLATE_COLUNAS = "faq/partials/taxonomia/_resposta_colunas.html"
TEMPLATE_MARCADAS = "faq/partials/taxonomia/_resposta_marcadas.html"
TEMPLATE_MODAL_PALAVRA = "faq/partials/taxonomia/_modal_palavra_chave.html"
TEMPLATE_RELACIONADAS_PALAVRA = "faq/partials/taxonomia/_relacionadas_palavra.html"
TEMPLATE_MODAL_TEMA = "faq/partials/taxonomia/_modal_tema.html"
TEMPLATE_TEMA_CONCLUIDO = "faq/partials/taxonomia/_tema_concluido.html"
TEMPLATE_PALAVRA_CONCLUIDA = "faq/partials/taxonomia/_palavra_concluida.html"
PARAMETRO_MARCADA = "palavra_chave"


@superusuario_requerido
def coluna(request: HttpRequest) -> HttpResponse:
    # Sem `pai`, as raízes. Com ele, as filhas dele; as colunas acima voltam com o ramo aberto.
    pai_id = _id(request.GET.get("pai"))
    return render(
        request, TEMPLATE_COLUNAS, _contexto_colunas(pai_id, _marcadas(request.GET))
    )


@superusuario_requerido
def marcadas(request: HttpRequest) -> HttpResponse:
    # A lista de marcadas, e não as colunas, é que leva os ids ao formulário: trocar de ramo
    # descarta colunas, nunca marcação.
    ids = _marcadas(request.GET)
    alternar = _id(request.GET.get("alternar"))
    if alternar is not None:
        ids ^= {alternar}
    alternada = (
        PalavraChaveModel.objects.filter(pk=alternar).first()
        if alternar is not None
        else None
    )
    return render(
        request,
        TEMPLATE_MARCADAS,
        {
            "marcadas": marcadas_do_formulario(ids),
            "alternada": alternada,
            "marcada": alternar in ids,
        },
    )


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def palavra_chave_nova(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        pai_id = _id(request.GET.get("pai"))
        return render(
            request, TEMPLATE_MODAL_PALAVRA, _contexto_modal_palavra({"pai": pai_id})
        )
    desfecho = criar_palavra_chave(request.POST)
    if not isinstance(desfecho, int):
        return render(
            request,
            TEMPLATE_MODAL_PALAVRA,
            _contexto_modal_palavra(_valores_modal(request.POST), recusa=desfecho),
            status=422,
        )
    pai_id = _id(request.POST.get("pai"))
    return render(
        request,
        TEMPLATE_PALAVRA_CONCLUIDA,
        _contexto_colunas(pai_id, _marcadas(request.POST)),
    )


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def palavra_chave_renomear(request: HttpRequest, palavra_id: int) -> HttpResponse:
    palavra = get_object_or_404(
        PalavraChaveModel.objects.select_related("pai__pai"), pk=palavra_id
    )
    if request.method == "GET":
        return render(
            request,
            TEMPLATE_MODAL_PALAVRA,
            _contexto_modal_palavra({"nome": palavra.nome}, palavra=palavra),
        )
    recusa = renomear_palavra_do_modal(palavra_id, request.POST)
    if recusa is not None:
        return render(
            request,
            TEMPLATE_MODAL_PALAVRA,
            _contexto_modal_palavra(
                _valores_modal(request.POST), palavra=palavra, recusa=recusa
            ),
            status=422,
        )
    ids = _marcadas(request.POST)
    return render(
        request,
        TEMPLATE_PALAVRA_CONCLUIDA,
        _contexto_colunas(palavra.pai_id, ids)
        | {"marcadas": marcadas_do_formulario(ids), "renomeada": True},
    )


@superusuario_requerido
def relacionadas_palavra(request: HttpRequest) -> HttpResponse:
    ids = [
        i
        for i in _ids(request.GET.getlist(CONTROLE_RELACIONADA))
        if str(i) != request.GET.get("desrelacionar")
    ]
    relacionar = _id(request.GET.get("relacionar"))
    if relacionar is not None and relacionar not in ids:
        ids.append(relacionar)
    return render(
        request, TEMPLATE_RELACIONADAS_PALAVRA, _contexto_relacionadas_palavra(ids)
    )


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def tema_novo(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, TEMPLATE_MODAL_TEMA, _contexto_modal_tema({}))
    desfecho = criar_tema(request.POST)
    if not isinstance(desfecho, int):
        return render(
            request,
            TEMPLATE_MODAL_TEMA,
            _contexto_modal_tema(_valores_modal(request.POST), recusa=desfecho),
            status=422,
        )
    return render(
        request,
        TEMPLATE_TEMA_CONCLUIDO,
        {"temas": opcoes_de_tema(), "tema_escolhido": desfecho},
    )


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def tema_renomear(request: HttpRequest) -> HttpResponse:
    dados = request.GET if request.method == "GET" else request.POST
    tema = get_object_or_404(
        TemaModel.objects.select_related("pai"), pk=_id(dados.get("tema"))
    )
    if request.method == "GET":
        return render(
            request,
            TEMPLATE_MODAL_TEMA,
            _contexto_modal_tema({"nome": tema.nome}, tema=tema),
        )
    recusa = renomear_tema_do_modal(tema.pk, request.POST)
    if recusa is not None:
        return render(
            request,
            TEMPLATE_MODAL_TEMA,
            _contexto_modal_tema(
                _valores_modal(request.POST), tema=tema, recusa=recusa
            ),
            status=422,
        )
    return render(
        request,
        TEMPLATE_TEMA_CONCLUIDO,
        {"temas": opcoes_de_tema(), "tema_escolhido": tema.pk},
    )


def _contexto_colunas(pai_id: int | None, ids: set[int]) -> dict[str, Any]:
    colunas = colunas_ate(pai_id, ids)
    return {
        "principal": colunas[-1],
        "anteriores": colunas[:-1],
        "vazios": range(len(colunas), PROFUNDIDADE_PALAVRA_CHAVE),
    }


def _contexto_modal_palavra(
    valores: dict[str, Any],
    palavra: PalavraChaveModel | None = None,
    recusa: Any = None,
) -> dict[str, Any]:
    pais = opcoes_de_pai()
    return {
        "valores": valores,
        "palavra": palavra,
        "caminho": caminho_de(palavra) if palavra is not None else "",
        "pais": pais,
        "pai_fora": _fora_das_opcoes(valores.get("pai"), pais, opcoes_de_palavra()),
        "recusa": recusa,
        "realce": recusa.realce if recusa is not None else {},
    } | _contexto_relacionadas_palavra(valores.get("relacionadas", []))


def _contexto_relacionadas_palavra(ids: list[int]) -> dict[str, Any]:
    opcoes = opcoes_de_palavra()
    return {
        "relacionadas": [opcao for opcao in opcoes if opcao[0] in ids],
        "candidatas": [opcao for opcao in opcoes if opcao[0] not in ids],
    }


def _contexto_modal_tema(
    valores: dict[str, Any],
    tema: TemaModel | None = None,
    recusa: Any = None,
) -> dict[str, Any]:
    raizes = opcoes_de_tema_raiz()
    return {
        "valores": valores,
        "tema": tema,
        "rotulo_tema": rotulo_do_tema(tema) if tema is not None else "",
        "raizes": raizes,
        "pai_fora": _fora_das_opcoes(valores.get("pai"), raizes, opcoes_de_tema()),
        "recusa": recusa,
        "realce": recusa.realce if recusa is not None else {},
    }


def _fora_das_opcoes(
    pai_id: int | None,
    oferecidas: list[tuple[int, str]],
    todas: list[tuple[int, str]],
) -> tuple[int, str] | None:
    if pai_id is None or any(pk == pai_id for pk, _ in oferecidas):
        return None
    return next((opcao for opcao in todas if opcao[0] == pai_id), None)


def _valores_modal(post: QueryDict) -> dict[str, Any]:
    return {
        "nome": post.get("nome", ""),
        "pai": _id(post.get("pai")),
        "relacionadas": _ids(post.getlist(CONTROLE_RELACIONADA)),
    }


def _marcadas(dados: QueryDict) -> set[int]:
    return set(_ids(dados.getlist(PARAMETRO_MARCADA)))


def _id(valor: str | None) -> int | None:
    return int(valor) if valor and valor.isdigit() else None


def _ids(valores: list[str]) -> list[int]:
    return [int(v) for v in valores if v.isdigit()]

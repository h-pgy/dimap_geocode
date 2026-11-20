from django.db.models import QuerySet
from django.http import Http404

from apps.faq.conteudo import faq_do_registro
from apps.faq.models import Anexo as AnexoModel
from services.domain.faq import Leitor, anexo_eh_baixavel
from services.utils.normalization import normalize_text

# A lista e a busca mostram o anexo sem carregar o arquivo nem o texto.
CAMPOS_DA_LISTA = ("pk", "titulo", "tipo", "tamanho_bytes", "origem_texto")
LIMITE_DA_BUSCA = 20


def anexos_da_lista(ids: list[int]) -> list[AnexoModel]:
    return list(_leves().filter(pk__in=ids).order_by("titulo"))


def anexo_com_texto(anexo_id: int) -> AnexoModel:
    registro = AnexoModel.objects.defer("arquivo").filter(pk=anexo_id).first()
    if registro is None:
        raise Http404
    return registro


def buscar_anexos(termo: str, marcados: list[int]) -> list[AnexoModel]:
    # Título normalizado em Python: `normalize_text` não tem equivalente em SQL, e o acervo é pequeno.
    chave = normalize_text(termo)
    if not chave:
        return []
    candidatos = _leves().exclude(pk__in=marcados).order_by("titulo")
    return [a for a in candidatos if chave in normalize_text(a.titulo)][
        :LIMITE_DA_BUSCA
    ]


def anexo_baixavel(anexo_id: int, leitor: Leitor) -> AnexoModel:
    # 404 também para o que existe mas o leitor não vê: a rota não confirma que o anexo existe.
    registro = AnexoModel.objects.filter(pk=anexo_id).first()
    if registro is None:
        raise Http404
    ligadas = registro.faqs.select_related("tema__pai").prefetch_related(
        "perguntas", "links", "relacionadas", "palavras_chave__pai__pai"
    )
    faqs = [faq_do_registro(f) for f in ligadas]
    if not anexo_eh_baixavel([f for f in faqs if f is not None], leitor):
        raise Http404
    return registro


def _leves() -> QuerySet[AnexoModel]:
    return AnexoModel.objects.only(*CAMPOS_DA_LISTA)

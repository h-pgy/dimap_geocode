from collections.abc import Iterable

from django.db.models import Prefetch

from apps.faq.models import Anexo as AnexoModel
from apps.faq.models import Faq as FaqModel
from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Tema as TemaModel
from services.domain.faq import (
    Faq,
    LinkReferencia,
    PalavraChave,
    Pergunta,
    Resposta,
    Situacao,
    Tema,
    Visibilidade,
    destino_gravado,
)


def carregar_faqs(visibilidades: Iterable[Visibilidade]) -> list[Faq]:
    registros = (
        FaqModel.objects.filter(
            situacao=Situacao.PUBLICADA,
            visibilidade__in=[v.value for v in visibilidades],
        )
        .select_related("tema__pai")
        .prefetch_related(
            "perguntas",
            "links",
            "relacionadas",
            # Só o id: o arquivo e o texto de cada anexo não entram na leitura da FAQ.
            Prefetch("anexos", queryset=AnexoModel.objects.only("pk")),
            "palavras_chave__pai__pai",
        )
        .order_by("id")
    )
    faqs = [faq_do_registro(registro) for registro in registros]
    return [faq for faq in faqs if faq is not None]


def faq_do_registro(registro: FaqModel) -> Faq | None:
    perguntas = sorted(registro.perguntas.all(), key=lambda p: p.pk)
    principal = next((p for p in perguntas if p.eh_principal), None)
    if principal is None:
        # Escrita direta no ORM, fora de `gravar_faq` (Caveats da SPEC): sem pergunta, não há o que exibir.
        return None
    return Faq(
        id=registro.pk,
        pergunta=Pergunta(texto=principal.texto),
        variacoes=[Pergunta(texto=p.texto) for p in perguntas if not p.eh_principal],
        resposta=Resposta(
            markdown=registro.resposta_markdown,
            links=[
                LinkReferencia(titulo=link.titulo, destino=destino_gravado(link.url))
                for link in sorted(registro.links.all(), key=lambda link: link.ordem)
            ],
            anexos=[anexo.pk for anexo in registro.anexos.all()],
        ),
        tema=_tema(registro.tema),
        palavras_chave=[_palavra_chave(p) for p in registro.palavras_chave.all()],
        visibilidade=Visibilidade(registro.visibilidade),
        situacao=Situacao(registro.situacao),
        autor_id=registro.autor_id,
        relacionadas=[r.pk for r in registro.relacionadas.all()],
    )


def _tema(registro: TemaModel) -> Tema:
    pai = _tema(registro.pai) if registro.pai is not None else None
    return Tema(nome=registro.nome, pai=pai, ordem=registro.ordem)


def _palavra_chave(registro: PalavraChaveModel) -> PalavraChave:
    pai = _palavra_chave(registro.pai) if registro.pai is not None else None
    return PalavraChave(id=registro.pk, nome=registro.nome, pai=pai)

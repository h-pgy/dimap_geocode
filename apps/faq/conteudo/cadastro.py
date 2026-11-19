from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.faq.models import Faq as FaqModel
from apps.faq.models import LinkReferencia as LinkReferenciaModel
from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Pergunta as PerguntaModel
from apps.faq.models import Tema as TemaModel
from apps.faq.taxonomia import gravar_palavra_chave
from services.domain.faq import (
    Faq,
    PalavraChave,
    Pergunta,
    PerguntaJaRespondida,
    PerguntaOcupada,
    Situacao,
    Tema,
)


def gravar_faq(faq: Faq) -> int:
    if faq.situacao is Situacao.EXCLUIDA:
        raise ValueError("A exclusão é feita pelo botão de excluir.")
    perguntas = [faq.pergunta, *faq.variacoes]
    # O DTO já recusou pergunta repetida DENTRO da FAQ. Aqui se confere ENTRE FAQs, antes de gravar,
    # para a recusa dizer qual FAQ é a dona.
    conferir_perguntas_livres(perguntas, faq_id=faq.id)
    try:
        return _criar(faq)
    except IntegrityError:
        # Corrida: outra gravação ocupou a pergunta entre a conferência e o INSERT. Conferir de novo
        # transforma a colisão em PerguntaJaRespondida; se a violação foi outra, o erro original sobe.
        conferir_perguntas_livres(perguntas, faq_id=faq.id)
        raise


def conferir_perguntas_livres(perguntas: list[Pergunta], faq_id: int | None) -> None:
    por_chave = {p.chave: p for p in perguntas}
    candidatas = PerguntaModel.objects.filter(chave__in=por_chave)
    if faq_id is not None:
        # Na regravação, as perguntas da própria FAQ não contam como ocupadas.
        candidatas = candidatas.exclude(faq_id=faq_id)
    donas = list(candidatas.values_list("chave", "faq_id"))
    if donas:
        raise PerguntaJaRespondida(
            [
                PerguntaOcupada(pergunta=por_chave[chave], faq_id=dona)
                for chave, dona in donas
                if chave is not None
            ],
        )


@transaction.atomic
def _criar(faq: Faq) -> int:
    # Transação própria (savepoint, se o chamador já abriu uma): o IntegrityError desfaz só esta FAQ,
    # e a conferência de `gravar_faq` ainda consegue consultar o banco depois dele.
    registro = FaqModel.objects.create(
        resposta_markdown=faq.resposta.markdown,
        tema=tema_persistido(faq.tema),
        visibilidade=faq.visibilidade,
        situacao=faq.situacao,
        autor_id=faq.autor_id,
        # A FAQ recém-criada nasce com o próprio autor como último editor (faq/002).
        editado_por_id=faq.autor_id,
        editado_em=timezone.now() if faq.autor_id is not None else None,
    )
    PerguntaModel.objects.create(
        faq=registro,
        texto=faq.pergunta.texto,
        chave=faq.pergunta.chave,
        eh_principal=True,
    )
    PerguntaModel.objects.bulk_create(
        PerguntaModel(faq=registro, texto=v.texto, chave=v.chave) for v in faq.variacoes
    )
    LinkReferenciaModel.objects.bulk_create(
        LinkReferenciaModel(
            faq=registro, titulo=link.titulo, url=link.destino.href, ordem=i
        )
        for i, link in enumerate(faq.resposta.links)
    )
    registro.palavras_chave.set(palavras_chave_persistidas(faq.palavras_chave))
    registro.relacionadas.set(faq.relacionadas)
    return registro.pk


def tema_persistido(tema: Tema) -> TemaModel:
    pai = tema_persistido(tema.pai) if tema.pai is not None else None
    existente = TemaModel.objects.filter(nome__iexact=tema.nome, pai=pai).first()
    if existente is not None:
        return existente
    return TemaModel.objects.create(nome=tema.nome, pai=pai, ordem=tema.ordem)


def palavras_chave_persistidas(
    palavras: list[PalavraChave],
) -> list[PalavraChaveModel]:
    # Grava-se só a marcada, nunca os ancestrais, que a busca deriva pelo `caminho`.
    return [_palavra_pelo_caminho(palavra) for palavra in palavras]


def _palavra_pelo_caminho(palavra: PalavraChave) -> PalavraChaveModel:
    pai_dto: PalavraChave | None = None
    pai_registro: PalavraChaveModel | None = None
    ultimo_indice = len(palavra.caminho) - 1
    for indice, nome in enumerate(palavra.caminho):
        registro = PalavraChaveModel.objects.filter(
            nome__iexact=nome, pai=pai_registro
        ).first()
        if registro is None:
            nova = PalavraChave(
                nome=nome,
                pai=pai_dto,
                relacionadas=palavra.relacionadas if indice == ultimo_indice else [],
            )
            registro = PalavraChaveModel.objects.get(pk=gravar_palavra_chave(nova))
        pai_dto = PalavraChave(id=registro.pk, nome=registro.nome, pai=pai_dto)
        pai_registro = registro
    assert pai_registro is not None
    return pai_registro

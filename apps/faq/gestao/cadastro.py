from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.faq.conteudo import (
    conferir_perguntas_livres,
    faq_do_registro,
    palavras_chave_persistidas,
    tema_persistido,
)
from apps.faq.models import Faq as FaqModel
from apps.faq.models import LinkReferencia as LinkReferenciaModel
from apps.faq.models import Pergunta as PerguntaModel
from services.domain.faq import (
    Edicao,
    Editor,
    Faq,
    LinkReferencia,
    Pergunta,
    Situacao,
    pode_excluir,
)
from services.utils.normalization import normalize_text

from .consulta import SITUACOES_ATIVAS, faq_editavel
from .edicao import marcar_edicao


@transaction.atomic
def regravar_faq(edicao: Edicao) -> None:
    assert edicao.faq.id is not None
    registro = faq_editavel(edicao.faq.id)
    conferir_perguntas_livres(
        [edicao.faq.pergunta, *edicao.faq.variacoes], faq_id=edicao.faq.id
    )
    # As antigas saem antes de as novas entrarem: promover uma variação não colide com ela mesma.
    registro.perguntas.all().delete()
    registro.links.all().delete()
    _aplicar_campos(registro, edicao.faq)
    _gravar_perguntas(registro, edicao.faq)
    _gravar_links(registro, edicao.faq.resposta.links)
    registro.anexos.set(edicao.faq.resposta.anexos)
    registro.relacionadas.set(
        _relacionadas_regravadas(registro, edicao.faq.relacionadas)
    )
    marcar_edicao(registro, edicao.editor)


@transaction.atomic
def alterar_situacao(faq_id: int, situacao: Situacao, editor: Editor) -> None:
    if situacao not in SITUACOES_ATIVAS:
        raise ValueError("A exclusão é feita pelo botão de excluir.")
    registro = faq_editavel(faq_id)
    registro.situacao = situacao
    registro.save(update_fields=["situacao", "atualizado_em"])
    marcar_edicao(registro, editor)


@transaction.atomic
def excluir_faq(faq_id: int, editor: Editor) -> None:
    registro = faq_editavel(faq_id)
    faq = faq_do_registro(registro)
    if faq is None or not pode_excluir(faq):
        raise PermissionDenied
    registro.situacao = Situacao.EXCLUIDA
    registro.save(update_fields=["situacao", "atualizado_em"])
    # Chave nula libera a pergunta no UNIQUE; o texto fica para a restauração recalcular.
    registro.perguntas.update(chave=None)
    marcar_edicao(registro, editor)


@transaction.atomic
def restaurar_faq(faq_id: int, editor: Editor) -> None:
    registro = faq_editavel(faq_id, situacoes=frozenset({Situacao.EXCLUIDA}))
    linhas = list(registro.perguntas.all())
    conferir_perguntas_livres(
        [Pergunta(texto=linha.texto) for linha in linhas], faq_id=registro.pk
    )
    for linha in linhas:
        linha.chave = normalize_text(linha.texto)
    PerguntaModel.objects.bulk_update(linhas, ["chave"])
    # Volta fora da página: republicar é decisão do administrador.
    registro.situacao = Situacao.RASCUNHO
    registro.save(update_fields=["situacao", "atualizado_em"])
    marcar_edicao(registro, editor)


def _aplicar_campos(registro: FaqModel, faq: Faq) -> None:
    registro.resposta_markdown = faq.resposta.markdown
    registro.tema = tema_persistido(faq.tema)
    registro.visibilidade = faq.visibilidade
    registro.situacao = faq.situacao
    registro.save()
    registro.palavras_chave.set(palavras_chave_persistidas(faq.palavras_chave))


def _gravar_perguntas(registro: FaqModel, faq: Faq) -> None:
    PerguntaModel.objects.bulk_create(
        [
            PerguntaModel(
                faq=registro,
                texto=faq.pergunta.texto,
                chave=faq.pergunta.chave,
                eh_principal=True,
            ),
            *(
                PerguntaModel(faq=registro, texto=v.texto, chave=v.chave)
                for v in faq.variacoes
            ),
        ],
    )


def _gravar_links(registro: FaqModel, links: list[LinkReferencia]) -> None:
    LinkReferenciaModel.objects.bulk_create(
        LinkReferenciaModel(
            faq=registro, titulo=link.titulo, url=link.destino.href, ordem=i
        )
        for i, link in enumerate(links)
    )


def _relacionadas_regravadas(registro: FaqModel, pedidas: list[int]) -> set[int]:
    # A relacionada excluída é inerte e não vem no formulário: sem preservá-la aqui, salvar apagaria o
    # vínculo e a restauração não teria o que devolver. Excluída pedida sem vínculo (id forjado) cai.
    excluidas = set(
        registro.relacionadas.filter(situacao=Situacao.EXCLUIDA).values_list(
            "pk", flat=True
        ),
    )
    ativas = set(
        FaqModel.objects.filter(pk__in=pedidas, situacao__in=SITUACOES_ATIVAS)
        .exclude(pk=registro.pk)
        .values_list("pk", flat=True),
    )
    return ativas | excluidas

from collections.abc import Mapping
from typing import Any

from apps.core.tabela import colunas_da_tabela, marca_descendente
from apps.faq.anexos.consulta import anexos_da_lista
from apps.faq.anexos.recebimento import FAQ_ANEXO_TAMANHO_MAXIMO_BYTES
from apps.faq.conteudo import faq_do_registro
from apps.faq.models import Faq as FaqModel
from apps.faq.models import Tema as TemaModel
from apps.faq.taxonomia.palavras_chave import colunas_ate, marcadas_do_formulario
from services.domain.faq import (
    PROFUNDIDADE_PALAVRA_CHAVE,
    Situacao,
    Visibilidade,
    pode_excluir,
)
from services.domain.listagem_gestao import (
    ColunaFaq,
    ConsultaFaqs,
    LinhaFaq,
    listar_faqs,
)
from services.utils.erros_formulario import RecusaDeFormulario

from .consulta import SITUACOES_ATIVAS, SITUACOES_COM_EXCLUIDAS, faqs_editaveis
from .formularios import CONTROLE_NOVOS_ANEXOS, ValoresFaq

ROTULOS_COLUNAS: Mapping[ColunaFaq, str] = {
    ColunaFaq.PERGUNTA: "Pergunta",
    ColunaFaq.TEMA: "Tema",
    ColunaFaq.SITUACAO: "Situação",
    ColunaFaq.VISIBILIDADE: "Visibilidade",
    ColunaFaq.AUTOR: "Autor",
    ColunaFaq.EDITADO_POR: "Editado por",
    ColunaFaq.EDITADO_EM: "Editado em",
}
ROTULOS_SITUACAO: Mapping[str, str] = {
    Situacao.RASCUNHO: "Rascunho",
    Situacao.PUBLICADA: "Publicada",
    Situacao.EXCLUIDA: "Excluída",
}
ROTULOS_VISIBILIDADE: Mapping[str, str] = {
    Visibilidade.PUBLICA: "Pública",
    Visibilidade.INTERNA: "Interna",
}
SEM_AUTOR = "Sistema"
NUNCA_EDITADA = "—"
SEPARADOR_TEMA = " › "


def contexto_lista(consulta: ConsultaFaqs, excluidas: bool) -> dict[str, Any]:
    return contexto_corpo(consulta, excluidas) | {
        "colunas": colunas_da_tabela(consulta, ColunaFaq, ROTULOS_COLUNAS),
        "ordenar_por": consulta.ordenar_por.value if consulta.ordenar_por else "",
        "descendente": marca_descendente(consulta),
    }


def contexto_corpo(consulta: ConsultaFaqs, excluidas: bool) -> dict[str, Any]:
    situacoes = SITUACOES_COM_EXCLUIDAS if excluidas else SITUACOES_ATIVAS
    linhas = [_linha(registro) for registro in faqs_editaveis(situacoes)]
    return {"linhas": listar_faqs(linhas, consulta), "excluidas": excluidas}


def contexto_formulario(
    valores: ValoresFaq,
    registro: FaqModel | None = None,
    recusa: RecusaDeFormulario | None = None,
) -> dict[str, Any]:
    marcadas = set(valores.palavras_chave_ids)
    colunas = colunas_ate(None, marcadas)
    return {
        "valores": valores,
        "registro": registro,
        "eh_do_sistema": registro is not None and registro.autor_id is None,
        "recusa": recusa,
        "realce": recusa.realce if recusa is not None else {},
        "temas": opcoes_de_tema(),
        "tema_escolhido": valores.tema_id,
        "colunas": colunas,
        "vagas": range(len(colunas), PROFUNDIDADE_PALAVRA_CHAVE),
        "marcadas": marcadas_do_formulario(marcadas),
        "relacionadas_ativas": list(
            FaqModel.objects.filter(
                pk__in=valores.relacionadas_ids, situacao__in=SITUACOES_ATIVAS
            )
            .exclude(pk__in=[registro.pk] if registro is not None else [])
            .prefetch_related("perguntas"),
        ),
        "relacionadas_inertes": (
            relacionadas_do_formulario(registro)["relacionadas_inertes"]
            if registro is not None
            else []
        ),
        "opcoes_relacionadas": opcoes_de_relacionada(registro),
        "anexos_ligados": anexos_da_lista(valores.anexos_ids),
        "recusa_novos_anexos": _recusa_do_controle(recusa, CONTROLE_NOVOS_ANEXOS),
        "limite_mb": FAQ_ANEXO_TAMANHO_MAXIMO_BYTES // 1_000_000,
    }


def relacionadas_do_formulario(registro: FaqModel) -> dict[str, list[FaqModel]]:
    # As ativas viram controle (link e gesto de remover); as excluídas só aparecem marcadas.
    todas = list(registro.relacionadas.prefetch_related("perguntas"))
    return {
        "relacionadas_ativas": [f for f in todas if f.situacao != Situacao.EXCLUIDA],
        "relacionadas_inertes": [f for f in todas if f.situacao == Situacao.EXCLUIDA],
    }


def opcoes_de_tema() -> list[tuple[int, str]]:
    temas = TemaModel.objects.select_related("pai")
    return sorted(
        ((t.pk, rotulo_do_tema(t)) for t in temas),
        key=lambda opcao: opcao[1].casefold(),
    )


def opcoes_de_tema_raiz() -> list[tuple[int, str]]:
    return [
        (pk, rotulo) for pk, rotulo in opcoes_de_tema() if SEPARADOR_TEMA not in rotulo
    ]


def rotulo_do_tema(tema: TemaModel) -> str:
    return (
        f"{tema.pai.nome}{SEPARADOR_TEMA}{tema.nome}"
        if tema.pai is not None
        else tema.nome
    )


def opcoes_de_relacionada(registro: FaqModel | None) -> list[tuple[int, str]]:
    # O seletor não oferece FAQ excluída nem a própria.
    candidatas = faqs_editaveis().exclude(
        pk__in=[registro.pk] if registro is not None else []
    )
    return sorted(
        ((faq.pk, pergunta_principal(faq)) for faq in candidatas),
        key=lambda opcao: opcao[1].casefold(),
    )


def pergunta_principal(registro: FaqModel) -> str:
    return next((p.texto for p in registro.perguntas.all() if p.eh_principal), "")


def pode_excluir_registro(registro: FaqModel) -> bool:
    faq = faq_do_registro(registro)
    return faq is not None and pode_excluir(faq)


def _linha(registro: FaqModel) -> LinhaFaq:
    return LinhaFaq(
        pk=registro.pk,
        pergunta=pergunta_principal(registro),
        tema=rotulo_do_tema(registro.tema),
        situacao=ROTULOS_SITUACAO[registro.situacao],
        visibilidade=ROTULOS_VISIBILIDADE[registro.visibilidade],
        autor=registro.autor.nome_completo if registro.autor is not None else SEM_AUTOR,
        editado_por=registro.editado_por.nome_completo
        if registro.editado_por is not None
        else NUNCA_EDITADA,
        editado_em=registro.editado_em,
        eh_do_sistema=registro.autor_id is None,
        excluida=registro.situacao == Situacao.EXCLUIDA,
    )


def _recusa_do_controle(recusa: RecusaDeFormulario | None, controle: str) -> list[str]:
    # O campo de arquivo é preservado entre os swaps (hx-preserve): a mensagem mora ao lado dele.
    if recusa is None:
        return []
    return [campo.mensagem for campo in recusa.campos if campo.controle == controle]

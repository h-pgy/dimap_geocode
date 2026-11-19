import secrets
from collections.abc import Callable, Iterable
from typing import Any

from django.conf import settings
from django.http import QueryDict
from pydantic import BaseModel, ValidationError

from apps.faq.conteudo import gravar_faq
from apps.faq.models import Faq as FaqModel
from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Tema as TemaModel
from services.domain.faq import (
    Edicao,
    Editor,
    Faq,
    LinkReferencia,
    PalavraChave,
    Pergunta,
    PerguntaJaRespondida,
    Resposta,
    Situacao,
    Tema,
    Visibilidade,
    resolver_destino,
)
from services.utils.erros_formulario import (
    CampoDeFormulario,
    ErroBruto,
    Formulario,
    RecusaDeFormulario,
    RegraDeErro,
    TradutorDeRecusa,
)

from .cadastro import regravar_faq
from .consulta import SITUACOES_ATIVAS

DOMINIOS_DO_SISTEMA = settings.DOMINIOS_DO_SISTEMA

CONTROLE_PERGUNTA = "pergunta"
CONTROLE_RESPOSTA = "resposta_markdown"
CONTROLE_TEMA = "tema"
CONTROLE_SITUACAO = "situacao"
CONTROLE_VISIBILIDADE = "visibilidade"
CONTROLE_PALAVRA_CHAVE = "palavra_chave"
CONTROLE_RELACIONADA = "relacionada"
# As linhas repetíveis levam um sufixo próprio: é ele que deixa o realce cair no controle exato.
PREFIXO_VARIACAO = "variacao-"
PREFIXO_LINK_TITULO = "link_titulo-"
PREFIXO_LINK_URL = "link_url-"

ROTULO_PERGUNTA = "Pergunta principal"
ROTULO_VARIACAO = "Outras formas de perguntar"
ROTULO_LINK_TITULO = "Título do link"
ROTULO_LINK_URL = "Endereço do link"
MENSAGEM_LINK_URL = (
    "Endereço do link: use um endereço do sistema (/…) ou externo (https://…)."
)
TIPO_PERGUNTA_OCUPADA = "pergunta_ocupada"


class VariacaoNoFormulario(BaseModel):
    controle: str
    texto: str = ""


class LinkNoFormulario(BaseModel):
    sufixo: str
    titulo: str = ""
    url: str = ""

    @property
    def controle_titulo(self) -> str:
        return f"{PREFIXO_LINK_TITULO}{self.sufixo}"

    @property
    def controle_url(self) -> str:
        return f"{PREFIXO_LINK_URL}{self.sufixo}"


class ValoresFaq(BaseModel):
    """O formulário como a tela o mostra: o que veio do POST, ou o que está gravado."""

    pergunta: str = ""
    variacoes: list[VariacaoNoFormulario] = []
    resposta_markdown: str = ""
    tema_id: int | None = None
    palavras_chave_ids: list[int] = []
    links: list[LinkNoFormulario] = []
    relacionadas_ids: list[int] = []
    situacao: str = Situacao.RASCUNHO.value
    visibilidade: str = Visibilidade.PUBLICA.value


class FaqLida(BaseModel):
    faq: Faq | None = None
    recusa: RecusaDeFormulario | None = None


def novo_sufixo() -> str:
    return secrets.token_hex(4)


def valores_do_post(post: QueryDict) -> ValoresFaq:
    variacoes = [
        VariacaoNoFormulario(controle=chave, texto=post.get(chave, ""))
        for chave in post
        if chave.startswith(PREFIXO_VARIACAO)
    ]
    sufixos = [
        chave.removeprefix(PREFIXO_LINK_TITULO)
        for chave in post
        if chave.startswith(PREFIXO_LINK_TITULO)
    ]
    links = [
        LinkNoFormulario(
            sufixo=sufixo,
            titulo=post.get(f"{PREFIXO_LINK_TITULO}{sufixo}", ""),
            url=post.get(f"{PREFIXO_LINK_URL}{sufixo}", ""),
        )
        for sufixo in sufixos
    ]
    return ValoresFaq(
        pergunta=post.get(CONTROLE_PERGUNTA, ""),
        variacoes=variacoes,
        resposta_markdown=post.get(CONTROLE_RESPOSTA, ""),
        tema_id=_inteiro(post.get(CONTROLE_TEMA)),
        palavras_chave_ids=_inteiros(post.getlist(CONTROLE_PALAVRA_CHAVE)),
        links=links,
        relacionadas_ids=_inteiros(post.getlist(CONTROLE_RELACIONADA)),
        situacao=post.get(CONTROLE_SITUACAO) or Situacao.RASCUNHO.value,
        visibilidade=post.get(CONTROLE_VISIBILIDADE) or Visibilidade.PUBLICA.value,
    )


def valores_do_registro(registro: FaqModel) -> ValoresFaq:
    perguntas = sorted(registro.perguntas.all(), key=lambda p: p.pk)
    principal = next((p.texto for p in perguntas if p.eh_principal), "")
    return ValoresFaq(
        pergunta=principal,
        variacoes=[
            VariacaoNoFormulario(
                controle=f"{PREFIXO_VARIACAO}{novo_sufixo()}", texto=p.texto
            )
            for p in perguntas
            if not p.eh_principal
        ],
        resposta_markdown=registro.resposta_markdown,
        tema_id=registro.tema_id,
        palavras_chave_ids=[p.pk for p in registro.palavras_chave.all()],
        links=[
            LinkNoFormulario(sufixo=novo_sufixo(), titulo=link.titulo, url=link.url)
            for link in sorted(registro.links.all(), key=lambda link: link.ordem)
        ],
        relacionadas_ids=[
            r.pk for r in registro.relacionadas.all() if r.situacao != Situacao.EXCLUIDA
        ],
        situacao=registro.situacao,
        visibilidade=registro.visibilidade,
    )


def salvar_faq_nova(valores: ValoresFaq, editor: Editor) -> RecusaDeFormulario | int:
    lida = ler_faq(valores, faq_id=None, autor_id=editor.perfil_id)
    if lida.faq is None:
        assert lida.recusa is not None
        return lida.recusa
    return _gravando(valores, lambda: gravar_faq(lida.faq))  # type: ignore[arg-type]


def salvar_faq_existente(
    valores: ValoresFaq, registro: FaqModel, editor: Editor
) -> RecusaDeFormulario | int:
    lida = ler_faq(valores, faq_id=registro.pk, autor_id=registro.autor_id)
    if lida.faq is None:
        assert lida.recusa is not None
        return lida.recusa
    edicao = Edicao(faq=lida.faq, editor=editor)

    def _regravar() -> int:
        regravar_faq(edicao)
        return registro.pk

    return _gravando(valores, _regravar)


def ler_faq(valores: ValoresFaq, faq_id: int | None, autor_id: int | None) -> FaqLida:
    erros: list[ErroBruto] = []
    pergunta = _validar(
        erros, CONTROLE_PERGUNTA, lambda: Pergunta(texto=valores.pergunta)
    )
    variacoes = [
        _validar(erros, v.controle, lambda v=v: Pergunta(texto=v.texto))  # type: ignore[misc]
        for v in valores.variacoes
        if v.texto.strip()
    ]
    links = [
        _link(erros, link)
        for link in valores.links
        if link.titulo.strip() or link.url.strip()
    ]
    resposta = _validar(
        erros,
        CONTROLE_RESPOSTA,
        lambda: Resposta(
            markdown=valores.resposta_markdown, links=[link for link in links if link]
        ),
    )
    tema = _tema(erros, valores.tema_id)
    situacao = _validar(
        erros, CONTROLE_SITUACAO, lambda: _Situacao.model_validate({"valor": valores.situacao}).valor
    )
    visibilidade = _validar(
        erros,
        CONTROLE_VISIBILIDADE,
        lambda: _Visibilidade.model_validate({"valor": valores.visibilidade}).valor,
    )
    formulario = _catalogo(valores)
    if erros or tema is None:
        return FaqLida(recusa=TradutorDeRecusa(formulario)(erros))
    try:
        faq = Faq(
            id=faq_id,
            pergunta=pergunta,
            variacoes=[v for v in variacoes if v is not None],
            resposta=resposta,
            tema=tema,
            palavras_chave=_palavras_chave(valores.palavras_chave_ids),
            visibilidade=visibilidade,
            situacao=situacao,
            autor_id=autor_id,
            relacionadas=_relacionadas_ativas(valores.relacionadas_ids, faq_id),
        )
    except ValidationError as recusa:
        return FaqLida(recusa=TradutorDeRecusa(formulario)(_erros_gerais(recusa)))
    return FaqLida(faq=faq)


def campos_ocupados(erro: PerguntaJaRespondida, valores: ValoresFaq) -> list[ErroBruto]:
    # A mensagem vai no controle da pergunta ocupada e não diz qual FAQ a tem, embora o erro saiba.
    campos = {
        chave: (controle, rotulo)
        for controle, rotulo, chave in _perguntas_com_campo(valores)
    }
    return [
        ErroBruto(
            controle=campos[o.pergunta.chave][0],
            tipo=TIPO_PERGUNTA_OCUPADA,
            mensagem=f"{campos[o.pergunta.chave][1]}: “{o.pergunta.texto}” já é respondida por outra FAQ.",
        )
        for o in erro.ocupadas
        if o.pergunta.chave in campos
    ]


def link_do_formulario(titulo: str, url: str) -> LinkReferencia:
    # URL recusada (`//x`, `javascript:`, sem host) sobe como ValidationError, que vai ao controle do link.
    return LinkReferencia(
        titulo=titulo, destino=resolver_destino(url, DOMINIOS_DO_SISTEMA)
    )


class _Situacao(BaseModel):
    valor: Situacao


class _Visibilidade(BaseModel):
    valor: Visibilidade


def _gravando(
    valores: ValoresFaq, gravar: Callable[[], int]
) -> RecusaDeFormulario | int:
    try:
        return gravar()
    except PerguntaJaRespondida as erro:
        return TradutorDeRecusa(_catalogo(valores))(campos_ocupados(erro, valores))


def _validar[T](erros: list[ErroBruto], controle: str, construir: Callable[[], T]) -> T:
    try:
        return construir()
    except ValidationError as recusa:
        erros.extend(_erros_no_controle(recusa, controle))
        return None  # type: ignore[return-value]


def _link(erros: list[ErroBruto], link: LinkNoFormulario) -> LinkReferencia | None:
    try:
        return link_do_formulario(link.titulo, link.url)
    except ValidationError as recusa:
        for erro in recusa.errors():
            if erro["loc"] and erro["loc"][0] == "titulo":
                erros.append(
                    ErroBruto(controle=link.controle_titulo, tipo=erro["type"])
                )
            else:
                erros.append(
                    ErroBruto(
                        controle=link.controle_url,
                        tipo=erro["type"],
                        mensagem=MENSAGEM_LINK_URL,
                    )
                )
        return None


def _tema(erros: list[ErroBruto], tema_id: int | None) -> Tema | None:
    registro = (
        TemaModel.objects.select_related("pai").filter(pk=tema_id).first()
        if tema_id is not None
        else None
    )
    if registro is None:
        erros.append(
            ErroBruto(
                controle=CONTROLE_TEMA, tipo="missing", mensagem="Escolha o tema."
            )
        )
        return None
    pai = (
        Tema(nome=registro.pai.nome, ordem=registro.pai.ordem)
        if registro.pai is not None
        else None
    )
    return Tema(nome=registro.nome, pai=pai, ordem=registro.ordem)


def _palavras_chave(ids: list[int]) -> list[PalavraChave]:
    registros = PalavraChaveModel.objects.filter(pk__in=ids).select_related("pai__pai")
    return [_palavra_chave(registro) for registro in registros]


def _palavra_chave(registro: PalavraChaveModel) -> PalavraChave:
    pai = _palavra_chave(registro.pai) if registro.pai is not None else None
    return PalavraChave(id=registro.pk, nome=registro.nome, pai=pai)


def _relacionadas_ativas(ids: list[int], faq_id: int | None) -> list[int]:
    # O seletor não oferece FAQ excluída; id forjado de uma delas cai aqui.
    return list(
        FaqModel.objects.filter(pk__in=ids, situacao__in=SITUACOES_ATIVAS)
        .exclude(pk__in=[faq_id] if faq_id is not None else [])
        .values_list("pk", flat=True),
    )


def _erros_no_controle(recusa: ValidationError, controle: str) -> list[ErroBruto]:
    return [
        ErroBruto(
            controle=controle, tipo=erro["type"], mensagem=_mensagem_propria(erro)
        )
        for erro in recusa.errors()
    ]


def _erros_gerais(recusa: ValidationError) -> list[ErroBruto]:
    return [
        ErroBruto(
            controle="",
            tipo=erro["type"],
            mensagem=_mensagem_propria(erro) or "Formulário inválido.",
        )
        for erro in recusa.errors()
    ]


def _mensagem_propria(erro: Any) -> str | None:
    # O `ValueError` dos validadores do domínio já fala português; o resto o catálogo traduz.
    if erro["type"] == "value_error":
        return str(erro["ctx"]["error"])
    return None


def _perguntas_com_campo(valores: ValoresFaq) -> Iterable[tuple[str, str, str]]:
    textos = [(CONTROLE_PERGUNTA, ROTULO_PERGUNTA, valores.pergunta)]
    textos += [
        (v.controle, ROTULO_VARIACAO, v.texto)
        for v in valores.variacoes
        if v.texto.strip()
    ]
    for controle, rotulo, texto in textos:
        try:
            yield controle, rotulo, Pergunta(texto=texto).chave
        except ValidationError:
            continue


def _catalogo(valores: ValoresFaq) -> Formulario:
    return Formulario(
        campos=(
            CampoDeFormulario(controle=CONTROLE_PERGUNTA, rotulo=ROTULO_PERGUNTA),
            *(
                CampoDeFormulario(controle=v.controle, rotulo=ROTULO_VARIACAO)
                for v in valores.variacoes
            ),
            CampoDeFormulario(
                controle=CONTROLE_RESPOSTA,
                rotulo="Resposta",
                regras={
                    "string_too_short": RegraDeErro(
                        mensagem="A resposta não pode ficar em branco."
                    )
                },
            ),
            CampoDeFormulario(controle=CONTROLE_TEMA, rotulo="Tema"),
            CampoDeFormulario(controle=CONTROLE_SITUACAO, rotulo="Situação"),
            CampoDeFormulario(controle=CONTROLE_VISIBILIDADE, rotulo="Visibilidade"),
            *(
                CampoDeFormulario(
                    controle=link.controle_titulo, rotulo=ROTULO_LINK_TITULO
                )
                for link in valores.links
            ),
            *(
                CampoDeFormulario(controle=link.controle_url, rotulo=ROTULO_LINK_URL)
                for link in valores.links
            ),
        ),
    )


def _inteiro(valor: str | None) -> int | None:
    return int(valor) if valor and valor.isdigit() else None


def _inteiros(valores: list[str]) -> list[int]:
    return [int(v) for v in valores if v.isdigit()]

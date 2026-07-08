"""Orquestração (section-building) do app lote_matcher — fora das views.

Consolida a cola cross-domínio dos branches de busca de lote: a resolução do logradouro
(literal → fuzzy, motor da SPEC 013) e o lookup EXATO na base fiscal por codlog + número.
Essa composição cruza dois domínios (logradouros_match + contribuinte_match) e por isso vive
na orquestração do app, nunca em services/ (CLAUDE.md §3.3, §10.1). Nada aqui conhece `request`
nem devolve `HttpResponse`.
"""

from typing import Literal

from django.template.loader import render_to_string
from pydantic import BaseModel, computed_field

from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.contribuinte_match import (
    ContribuinteMatchInput,
    ContribuinteMatchOutput,
    EnderecoFiscalMatchInput,
    match_contribuinte,
    match_endereco_fiscal,
)
from services.domain.logradouros_match import ResolucaoLogradouroQuery, resolver_logradouro
from services.domain.roteamento_busca import (
    CodlogParse,
    ContribuinteParse,
    EnderecoLoteParse,
    LogradouroParse,
)

TITULO_CONTRIBUINTE = "Lote (por nº de contribuinte)"
TITULO_ENDERECO_LOTE = "Endereço cadastrado (lote)"

Modo = Literal["sugestao", "commit"]


def secao_contribuinte(candidato: ContribuinteParse) -> SecaoResultado | None:
    dto = ContribuinteMatchInput(
        setor=candidato.setor,
        quadra=candidato.quadra or None,
        lote=candidato.lote or None,
        dv=candidato.dv or None,
    )
    resultados = match_contribuinte(dto)
    if not resultados:
        return None  # seção OMITIDA: sem match não polui a UX
    html = render_to_string(
        "lote_matcher/partials/resultados_contribuinte.html",
        {"resultados": resultados},
    )
    return SecaoResultado(titulo=TITULO_CONTRIBUINTE, html=html)


class EnderecoLoteSugestao(BaseModel):
    """DTO de APRESENTAÇÃO (camada de app): junta o resultado fiscal EXATO ao grau de certeza
    do logradouro que o resolveu. O score é do LOGRADOURO — o número + codlog na base fiscal é
    match exato, sem incerteza."""

    resultado: ContribuinteMatchOutput
    # grau de certeza do LOGRADOURO; None = logradouro exato (literal) ou forma codlog.
    score: float | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def veio_de_fuzzy(self) -> bool:
        # semântica que "sobe" do logradouro: True só quando o logradouro foi resolvido
        # por fuzzy (score presente). Literal e forma codlog são exatos -> False.
        return self.score is not None


class OrquestradorEnderecoLote:
    """Orquestra os branches endereço-lote da busca — e existe SÓ para isso.

    Dois pontos de entrada, um por branch da view:
      - `secao`          : keyup → monta a seção "Endereço cadastrado (lote)" (ou None).
      - `melhor_sugestao`: Enter/commit → a sugestão de maior score (ou None).
    Ambos compartilham o pipeline privado `_sugestoes`, que compõe a cola cross-domínio
    (logradouros_match/codlog_match → contribuinte_match). Não implementa regra de matching —
    delega aos serviços de domínio e só decide o quê chamar e o que devolver. Sem `request`,
    sem estado.
    """

    def secao(self, candidato: EnderecoLoteParse) -> SecaoResultado | None:
        sugestoes = self._sugestoes(candidato, modo="sugestao")
        if not sugestoes:
            return None  # seção OMITIDA (como hoje)
        html = render_to_string(
            "lote_matcher/partials/resultados_endereco_lote.html", {"sugestoes": sugestoes}
        )
        return SecaoResultado(titulo=TITULO_ENDERECO_LOTE, html=html)

    def melhor_sugestao(self, candidato: EnderecoLoteParse) -> EnderecoLoteSugestao | None:
        sugestoes = self._sugestoes(candidato, modo="commit")  # já ordenadas por score desc
        return sugestoes[0] if sugestoes else None

    def _sugestoes(self, candidato: EnderecoLoteParse, modo: Modo) -> list[EnderecoLoteSugestao]:
        codlog_score = self._resolver_codlogs(candidato, modo)
        if not codlog_score:
            return []
        resultados = match_endereco_fiscal(
            EnderecoFiscalMatchInput(
                codlogs=list(codlog_score),
                numero_padronizado=candidato.numero_padronizado,
            )
        )
        sugestoes = [
            EnderecoLoteSugestao(resultado=r, score=codlog_score.get(r.codlog[:5]))
            for r in resultados
        ]
        # maior certeza no topo; literal (score None) mantém a ordem atual
        sugestoes.sort(
            key=lambda s: s.score if s.score is not None else float("inf"), reverse=True
        )
        return sugestoes

    def _resolver_codlogs(
        self, candidato: EnderecoLoteParse, modo: Modo
    ) -> dict[str, float | None]:
        # O EnderecoLoteParse chega em DUAS formas mutuamente exclusivas (validador
        # _exatamente_uma_forma do DTO). Despacho pela forma: codlog presente => logradouro JÁ
        # identificado por código exato (não roda fuzzy); ausente => veio por nome, a resolver.
        if candidato.codlog is not None:
            return self._codlogs_do_codlog_exato(candidato.codlog)
        assert candidato.logradouro is not None
        return self._codlogs_do_nome_do_logradouro(candidato.logradouro, modo)

    def _codlogs_do_codlog_exato(self, codlog: CodlogParse) -> dict[str, float | None]:
        # Logradouro JÁ identificado por código: identificador exato -> lookup direto, NENHUM
        # fuzzy roda, score sempre None.
        resultados = match_codlog(
            CodlogMatchInput(
                input_codlog=codlog.codlog,
                digito_verificador=codlog.digito_verificador or None,
            )
        )
        return {r.codlog: None for r in resultados}

    def _codlogs_do_nome_do_logradouro(
        self, logradouro: LogradouroParse, modo: Modo
    ) -> dict[str, float | None]:
        # Logradouro por nome (texto livre): resolve literal-primeiro-depois-fuzzy (motor da 013).
        # score None nos codlogs vindos do literal; preenchido nos que vieram do fuzzy.
        resolucao = resolver_logradouro(
            ResolucaoLogradouroQuery(
                nome=logradouro.nome,
                tipo=logradouro.tipo_logradouro or None,
                modo=modo,
            )
        )
        return {item.logradouro.codlog: item.score for item in resolucao.itens}


# instância única exposta pelo módulo (mesmo padrão dos serviços de domínio); a view importa isto
orquestrador_endereco_lote = OrquestradorEnderecoLote()

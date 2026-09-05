from collections.abc import Mapping
from datetime import date, timedelta
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict

from services.domain.listagem_gestao.models.consulta import ConsultaListagem

JANELA_PADRAO_DIAS = 30
# O que chega à tela de uma vez. Não há teto sobre o que a busca devolve: quem contém o volume é o
# período (SPEC painel/002, §7).
TAMANHO_PAGINA = 50

SEM_CARGO_COMISSAO = "—"
SEM_AUTOR = "—"


class ColunaExecucao(StrEnum):
    """As colunas que o cabeçalho filtra e ordena. `momento` e a autorização ficam de fora: um é
    recortado pelo período do card, o outro é badge e não tem termo a digitar (SPEC painel/002,
    §7). O valor de cada membro é o NOME do campo em `LinhaExecucao` — é por ele que o motor
    genérico lê a célula."""

    SERVIDOR = "servidor"
    UNIDADE = "unidade"
    CARGO = "cargo"
    COMISSAO = "comissao"
    ACAO = "acao"
    OPERACAO = "operacao"
    ALVO = "alvo"


class LinhaExecucao(BaseModel):
    """Uma linha já materializada da tabela do registro. Guarda o que a `ExecucaoAcao` gravou NO
    DIA do ato, não o que o cadastro do autor diz hoje."""

    pk: int
    # Formatado na materialização: a coluna só é lida, nunca filtrada nem ordenada pelo cabeçalho.
    momento: str
    servidor: str
    # Nulo quando o perfil do autor foi apagado — a FK é SET_NULL (SPEC autorizacao/004).
    servidor_pk: int | None = None
    unidade: str
    unidade_pk: int
    cor_unidade: str
    cargo: str
    comissao: str = SEM_CARGO_COMISSAO
    acao: str
    operacao: str = ""
    # "tipo: identificador", achatado num campo só — o alvo é texto livre e o par vira uma coisa
    # que se lê e se filtra de uma vez.
    alvo: str = ""
    autorizado: bool
    # Vazio quando o ato foi praticado por competência própria.
    substituindo: str = ""


ConsultaExecucoes = ConsultaListagem[ColunaExecucao]


class BuscaExecucoes(BaseModel):
    """O recorte que vai ao banco. Distinto de `ConsultaExecucoes`, que filtra em memória o que este
    recorte trouxe: aqui se decide QUAIS execuções existem para a tela; lá, quais delas sobram."""

    model_config = ConfigDict(frozen=True)

    # Primeiro campo e SEM default: as unidades que esta busca lê não são critério, são a condição
    # de existir busca. Já vêm resolvidas — o alcance do leitor cruzado com a unidade de onde ele
    # partiu (§6). Sem default, esquecê-las é erro de tipo, nunca registro inteiro vazando.
    unidades_lidas: frozenset[int]
    perfil_id: int | None = None
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None
    # Sem default de campo: "hoje" é da orquestração, como o CRS — o domínio não lê relógio.
    inicio: date
    fim: date

    @classmethod
    def de_parametros(
        cls,
        parametros: Mapping[str, str],
        hoje: date,
        unidades_lidas: frozenset[int],
    ) -> Self:
        """`hoje` e as unidades lidas entram por parâmetro porque nenhum dos dois vem do cliente —
        a unidade que o usuário escolhe já foi cruzada com o alcance dele antes de chegar aqui
        (CLAUDE.md §3.3: autorização é orquestração)."""
        return cls.model_validate(
            {
                "unidades_lidas": unidades_lidas,
                # Select sem escolha manda o campo com valor vazio. Sem esta limpeza, "" chegaria
                # ao `int | None` do Pydantic e viraria ValidationError num formulário que o
                # usuário apenas deixou em branco.
                "perfil_id": parametros.get("perfil") or None,
                "cargo_base_id": parametros.get("cargo_base") or None,
                "cargo_comissao_id": parametros.get("cargo_comissao") or None,
                # Página carregada sem período: os últimos 30 dias. É o que impede a tela de abrir
                # arrastando o registro inteiro (§7).
                "inicio": parametros.get("inicio") or hoje - timedelta(days=JANELA_PADRAO_DIAS),
                "fim": parametros.get("fim") or hoje,
            }
        )

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# `<app>.<nome>`: mesmo formato do app_label.codename do Django — origem do caminho dos ícones.
PADRAO_SLUG = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"

# Espelham as colunas da projeção no banco (SPEC autorizacao/002) — a recusa pertence ao contrato,
# primeira fronteira, não ao sincronizar_acoes.
LIMITE_SLUG = 120
LIMITE_NOME = 120
LIMITE_NOME_CURTO = 60
LIMITE_TOOLTIP = 255


class VarianteIcone(StrEnum):
    PEQUENO = "pequeno"
    GRANDE = "grande"


class TipoAlcance(BaseModel):
    """O que todo alcance é: até onde a ação pode incidir, e os parâmetros do request que carregam
    os alvos. Abstrato — cada alcance concreto é um subtipo, nunca uma instância desta classe.
    Alcance sobre lote, logradouro ou endereço não é subtipo desta classe: é regra de domínio de
    cada ação (SPEC autorizacao/004, §4)."""

    model_config = ConfigDict(frozen=True)

    # Os NOMES dos parâmetros na assinatura da view/formulário — não ids de unidade reais. Fixos no
    # código porque são parte da assinatura da ação; o id concreto (de qualquer unidade) só existe
    # em tempo de requisição, e nada aqui pode depender do dado do banco. Tupla porque um ato pode
    # incidir sobre mais de uma unidade, e todas precisam cair no alcance (SPEC criacao_usuarios/005).
    parametros_alvo: tuple[str, ...]


class UnidadesSubordinadas(TipoAlcance):
    """O alcance de quem dirige: as unidades que o perfil dirige e todas abaixo delas. O parâmetro
    carrega o id da unidade-alvo."""

    parametros_alvo: tuple[str, ...] = ("unidade",)


class LotacaoAtualEDestino(TipoAlcance):
    """O mesmo alcance de `UnidadesSubordinadas`, com dois alvos: a unidade em que o servidor está,
    lida da lotação dele, e a unidade para a qual o formulário o manda (SPEC criacao_usuarios/005) —
    mover alguém para fora do próprio ramo precisa recusar tanto quanto abrir o cadastro de quem já
    está fora dele."""

    parametros_alvo: tuple[str, ...] = ("servidor", "unidade")


class Acao(BaseModel):
    """O que a ação é. Sem rota, sem template, sem Django."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=PADRAO_SLUG, max_length=LIMITE_SLUG)
    nome: str = Field(min_length=1, max_length=LIMITE_NOME)
    tooltip: str = Field(min_length=1, max_length=LIMITE_TOOLTIP)
    nome_curto: str | None = Field(default=None, max_length=LIMITE_NOME_CURTO)
    variantes_icone: frozenset[VarianteIcone] = frozenset()
    # Competência que decorre de dirigir a unidade (titularidade/001); não passa por atribuição
    # nem concessão. Permite à projeção (SPEC 002) excluir a ação da oferta em tela.
    estrutural: bool = False
    # Ausente, a ação não incide sobre unidade e não há alvo a conferir — é o caso das que recebem
    # uma entidade territorial. Tipado pelo alcance abstrato: um alcance novo entra como subtipo de
    # `TipoAlcance`, sem mexer neste campo (SPEC autorizacao/004).
    alcance: TipoAlcance | None = None

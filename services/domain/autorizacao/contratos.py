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
    """O que todo alcance é: até onde a ação pode incidir, e o parâmetro do request que carrega o
    id da unidade-alvo. Abstrato — cada alcance concreto é um subtipo, nunca uma instância desta
    classe. Alcance sobre lote, logradouro ou endereço não é subtipo desta classe: é regra de
    domínio de cada ação (SPEC autorizacao/004, §4)."""

    model_config = ConfigDict(frozen=True)

    # O NOME do parâmetro na assinatura da view/formulário — não um id de unidade real. Fixo no
    # código porque é parte da assinatura da ação; o id concreto (de qualquer unidade) só existe em
    # tempo de requisição, e nada aqui pode depender do dado do banco.
    parametro_id_unidade_alvo: str


class UnidadesSubordinadas(TipoAlcance):
    """O alcance de quem dirige: as unidades que o perfil dirige e todas abaixo delas."""

    parametro_id_unidade_alvo: str = "unidade"


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

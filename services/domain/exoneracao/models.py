"""
Os DTOs da exoneração e da reintegração de servidor (SPEC user_admin/027): as duas faces do ato, o
que cada uma pergunta e o que a regra decide sobre ela.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class IdentidadeServidor(BaseModel):
    """O servidor projetado: o domínio não conhece o model, e do model só precisa disto."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    rf: str
    nome_completo: str


class PreviaDaExoneracao(BaseModel):
    model_config = ConfigDict(frozen=True)

    servidor: IdentidadeServidor
    # A sigla da unidade que fica sem titular. Ausente é quem não dirige nada.
    unidade_que_dirige: str | None
    impedimentos_em_aberto: int
    coberturas_em_curso: int
    delegacoes_recebidas: int
    administrador: bool
    ja_exonerado: bool = False
    # Quem assina não se retira do quadro: a recusa é da relação entre alvo e autor, não do alvo.
    eh_o_proprio_autor: bool = False


class PreviaDaReintegracao(BaseModel):
    """O reverso: o que volta, não o que sai."""

    model_config = ConfigDict(frozen=True)

    servidor: IdentidadeServidor
    exonerado_em: date | None
    # A lotação que ele guardou, e para onde volta. Extinta, não há para onde.
    unidade: str
    unidade_extinta: bool
    ja_no_quadro: bool = False


class Veredito(BaseModel):
    """Um só para as duas faces: a pergunta muda, a resposta tem a mesma forma."""

    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""

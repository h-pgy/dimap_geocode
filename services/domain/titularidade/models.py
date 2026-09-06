"""
DTOs de titularidade (SPEC user_admin/014): o estado que decide quem dirige a unidade hoje e o
requisito que decide se um cargo titulariza. Domínio puro, sem Django.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# A escala do cargo em comissão, fechada em 1..6. Mora aqui porque é sobre ela que a adequação
# compara o nível do cargo com o mínimo do tipo da unidade, e os dois lados — o cargo, em
# `user_admin`, e o tipo de unidade, em `unidades` — a declaram como validador de campo.
NIVEL_MINIMO = 1
NIVEL_MAXIMO = 6


class Direcao(StrEnum):
    TITULAR = "titular"
    SUBSTITUTO = "substituto"
    # Há titular, está fora e ninguém cobre: designar substituto resolve.
    SEM_DIRECAO = "sem_direcao"
    # Ninguém titulariza a unidade: só nomear resolve.
    SEM_TITULAR = "sem_titular"


class EstadoDaDirecao(BaseModel):
    model_config = ConfigDict(frozen=True)

    tem_titular: bool
    titular_em_exercicio: bool
    # Sem substituto designado, `False`: quem não existe não cobre ninguém.
    substituto_do_titular_em_exercicio: bool


class RequisitoTitularidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    e_chefia: bool
    alta_administracao: bool
    nivel_cargo: int | None
    # A exigência é declarada, não inferida da falta do mínimo — ver Contexto da SPEC.
    tipo_exige_alta_administracao: bool
    nivel_minimo_do_tipo: int | None

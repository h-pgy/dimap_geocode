"""
DTOs de exercício e substituição (SPEC user_admin/015): o período com fim indeterminado, os dois
papéis da designação e o afastamento fatiado em trechos. Domínio puro, sem Django.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class Periodo(BaseModel):
    model_config = ConfigDict(frozen=True)

    inicio: date
    # Nulo = indeterminado, a mesma convenção dos models.
    fim: date | None


class Substituido(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_id: int
    exonerado: bool
    tem_cargo_comissao: bool
    # Todas as que ele já recebe, deste impedimento e dos outros: duas simultâneas não dizem sob
    # qual competência o ato foi praticado, e a origem delas é indiferente para essa pergunta.
    # Ao validar uma substituição que já existe, ela própria fica de fora — senão conflita consigo.
    substituicoes_recebidas: tuple[Periodo, ...]


class Substituto(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_id: int
    exonerado: bool
    # Substituir estando fora da própria cadeira é criar o vazio na origem.
    impedimentos: tuple[Periodo, ...]
    substituicoes_exercidas: tuple[Periodo, ...]


class Designacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: Periodo
    periodo_do_impedimento: Periodo
    substituido: Substituido
    substituto: Substituto


class Trecho(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: Periodo
    # Nulo = ninguém responde neste trecho. É o que a calha deixa sem tinta.
    substituto_id: int | None

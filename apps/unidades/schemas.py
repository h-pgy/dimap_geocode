"""
DTOs das telas de unidade (SPEC user_admin/012, user_admin/020). A view constrói o DTO e deixa o
PydanticValidationMiddleware interceptar o ValidationError — nunca try/except na view (§7.2). Os
dois atos que gravam (`NovaUnidade`, `EdicaoUnidade`) fogem dessa regra de propósito: a recusa
deles volta como o próprio formulário, e é por isso que passam pelo `LeitorDeFormulario` em vez do
middleware (SPEC formularios/001).
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, BeforeValidator

# A paleta é do model (SPEC 005) e é de lá que ela vem: `TextChoices` é enum de string, o módulo
# de models não importa `schemas` e nenhum ciclo se fecha. `paleta.py` já o importa do mesmo lugar.
from apps.unidades.models import CorUnidade


def _vazio_para_nulo(valor: object) -> object:
    # O select da unidade superior manda "" na opção raiz; para o domínio, raiz é ausência de pai.
    return None if valor == "" else valor


PaiOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]
NomeDeUnidade = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
SiglaDeUnidade = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class SelecaoUnidadePai(BaseModel):
    pai: PaiOpcional = None


class NovaUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: NomeDeUnidade
    sigla: SiglaDeUnidade
    tipo_id: int
    # `PaiOpcional` só porque a raiz existe: quem não é superusuário nunca chega aqui sem pai — o
    # decorator já devolveu 400 —, e o ato recusa quem chegar.
    pai_id: PaiOpcional = None
    # Enum, e não `str`: tom fora da paleta é recusado na fronteira, e o `choices` do `full_clean`
    # deixa de ser a única guarda. O Pydantic valida pelo valor (`agua-700`) e o `CharField` grava
    # esse mesmo valor de volta.
    cor: CorUnidade


class EdicaoUnidade(BaseModel):
    """Mesmos campos de `NovaUnidade`, com o id no lugar do pai obrigatório — a cor inclusive: o
    modal edita identificação, hierarquia e identidade visual. Sem token de confirmação — ele é do
    processo, não do cadastro, e entra como argumento do ato."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    nome: NomeDeUnidade
    sigla: SiglaDeUnidade
    tipo_id: int
    cor: CorUnidade
    # Opcional só para a raiz que JÁ é raiz poder ser editada — o formulário dela não teria o que
    # mandar. Tornar raiz uma unidade que tem superior é recusado pelo ato, não pelo DTO.
    pai_id: PaiOpcional = None

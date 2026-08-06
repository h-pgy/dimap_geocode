"""
Carga do catálogo de tipos de impedimento a partir de `data/seed/tipos_impedimento.json`
(SPEC user_admin/010): grava `TipoImpedimento` a partir do arquivo versionado, com chave
natural (`nome`) e idempotência.

Mexe em persistência e orquestração, não em domínio: a única regra em jogo é a
`UniqueConstraint` condicional da sigla do model (SPEC user_admin/002), então este código
vive no app, não em `services/`.
"""

from django.db import transaction

from pydantic import BaseModel

from apps.user_admin.models import TipoImpedimento
from services.utils.io import read_json_from_folder, subpasta_de_data

NOME_SUBPASTA_SEED = "seed"
NOME_ARQUIVO_SEED = "tipos_impedimento.json"


class TipoImpedimentoSeed(BaseModel):
    nome: str
    sigla: str | None = None


class ArquivoSeedTiposImpedimento(BaseModel):
    tipos: list[TipoImpedimentoSeed]


class ContagemSeedTiposImpedimento(BaseModel):
    tipos: int


def _gravar_tipos(tipos: list[TipoImpedimentoSeed]) -> None:
    for tipo in tipos:
        # Monta em memória e só então full_clean(): get_or_create gravaria o registro novo
        # incompleto antes da validação da UniqueConstraint rodar.
        obj = TipoImpedimento.objects.filter(nome=tipo.nome).first() or TipoImpedimento(
            nome=tipo.nome
        )
        obj.sigla = tipo.sigla or ""
        obj.full_clean()
        obj.save()


def carregar_seed_tipos_impedimento(*, dry_run: bool = False) -> ContagemSeedTiposImpedimento:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    arquivo = ArquivoSeedTiposImpedimento.model_validate(dados)
    with transaction.atomic():
        _gravar_tipos(arquivo.tipos)
        if dry_run:
            transaction.set_rollback(True)
    return ContagemSeedTiposImpedimento(tipos=len(arquivo.tipos))

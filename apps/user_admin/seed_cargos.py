"""
Carga dos cargos da DIMAP a partir de `data/seed/cargos.json` (SPEC user_admin/009):
grava cargo base e cargo em comissão a partir do arquivo versionado, com chave natural
(`sigla`/`nome`) e idempotência — sem essa carga não há catálogo de cargos sem cadastro manual.

Mexe em persistência e orquestração, não em domínio: a única regra em jogo já está escrita no
`clean()` de `CargoComissao` (SPEC user_admin/001), então este código vive no app, não em
`services/`.
"""

from django.db import transaction

from pydantic import BaseModel

from apps.user_admin.models import CargoBase, CargoComissao
from services.utils.io import read_json_from_folder, subpasta_de_data

NOME_SUBPASTA_SEED = "seed"
NOME_ARQUIVO_SEED = "cargos.json"


class CargoBaseSeed(BaseModel):
    nome: str
    sigla: str


class CargoComissaoSeed(BaseModel):
    nome: str
    sigla: str
    nivel: int | None = None
    e_chefia: bool
    alta_administracao: bool = False


class ArquivoSeedCargos(BaseModel):
    cargo_base: list[CargoBaseSeed]
    cargo_comissao: list[CargoComissaoSeed]


class ContagemSeedCargos(BaseModel):
    cargo_base: int
    cargo_comissao: int


def _gravar_cargo_base(cargos: list[CargoBaseSeed]) -> None:
    for cargo in cargos:
        CargoBase.objects.update_or_create(
            sigla=cargo.sigla,
            defaults={"nome": cargo.nome},
        )


def _gravar_cargo_comissao(cargos: list[CargoComissaoSeed]) -> None:
    for cargo in cargos:
        # Monta em memória e só então full_clean(): get_or_create gravaria o registro novo
        # incompleto (sem os demais campos) antes da validação rodar.
        obj = CargoComissao.objects.filter(nome=cargo.nome).first() or CargoComissao(
            nome=cargo.nome
        )
        obj.sigla = cargo.sigla
        obj.nivel = cargo.nivel
        obj.e_chefia = cargo.e_chefia
        obj.alta_administracao = cargo.alta_administracao
        obj.full_clean()
        obj.save()


def carregar_seed_cargos(*, dry_run: bool = False) -> ContagemSeedCargos:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    arquivo = ArquivoSeedCargos.model_validate(dados)
    with transaction.atomic():
        _gravar_cargo_base(arquivo.cargo_base)
        _gravar_cargo_comissao(arquivo.cargo_comissao)
        if dry_run:
            transaction.set_rollback(True)
    return ContagemSeedCargos(
        cargo_base=len(arquivo.cargo_base),
        cargo_comissao=len(arquivo.cargo_comissao),
    )

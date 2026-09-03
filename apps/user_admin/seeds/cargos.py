"""
Carga dos cargos da DIMAP a partir de `data/seed/cargos.json` (SPEC user_admin/009):
grava cargo base e cargo em comissão a partir do arquivo versionado, com chave natural
(`sigla`/`nome`) — sem essa carga não há catálogo de cargos sem cadastro manual. Só cria o que
falta: depois do bootstrap quem mantém o catálogo é o sistema, não o arquivo.

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


def _gravar_cargo_base(cargos: list[CargoBaseSeed]) -> int:
    criados = 0
    for cargo in cargos:
        if CargoBase.objects.filter(sigla=cargo.sigla).exists():
            continue
        CargoBase.objects.create(
            nome=cargo.nome,
            sigla=cargo.sigla,
        )
        criados += 1
    return criados


def _gravar_cargo_comissao(cargos: list[CargoComissaoSeed]) -> int:
    criados = 0
    for cargo in cargos:
        if CargoComissao.objects.filter(nome=cargo.nome).exists():
            continue
        # Monta em memória e só então full_clean(): create() gravaria o registro antes de a
        # validação rodar, e a regra do model viraria IntegrityError cru.
        obj = CargoComissao(
            nome=cargo.nome,
            sigla=cargo.sigla,
            nivel=cargo.nivel,
            e_chefia=cargo.e_chefia,
            alta_administracao=cargo.alta_administracao,
        )
        obj.full_clean()
        obj.save()
        criados += 1
    return criados


def carregar_seed_cargos(*, dry_run: bool = False) -> ContagemSeedCargos:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    arquivo = ArquivoSeedCargos.model_validate(dados)
    with transaction.atomic():
        cargos_base_criados = _gravar_cargo_base(arquivo.cargo_base)
        cargos_comissao_criados = _gravar_cargo_comissao(arquivo.cargo_comissao)
        if dry_run:
            transaction.set_rollback(True)
    return ContagemSeedCargos(
        cargo_base=cargos_base_criados,
        cargo_comissao=cargos_comissao_criados,
    )

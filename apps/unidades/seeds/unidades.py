"""
Carga do organograma da DIMAP a partir de `data/seed/unidades.json` (SPEC user_admin/008):
grava tipos de unidade e unidades a partir do arquivo versionado, com chave natural
(`nome`/`sigla`) e idempotência — sem essa carga não há organograma sem cadastro manual.

Mexe em persistência e orquestração, não em domínio: a única regra em jogo já está escrita no
`clean()` de `Unidade` (SPEC user_admin/003), então este código vive no app, não em `services/`.
"""

from django.db import transaction

from pydantic import BaseModel

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from services.utils.io import read_json_from_folder, subpasta_de_data

NOME_SUBPASTA_SEED = "seed"
NOME_ARQUIVO_SEED = "unidades.json"


class TipoUnidadeSeed(BaseModel):
    nome: str
    nivel: int
    pode_ser_raiz: bool = False
    tipos_filhos_vedados: list[str] = []
    # Omitir os dois não é atalho para nada: a constraint recusa o par vazio na carga.
    exige_alta_administracao: bool = False
    nivel_minimo_titular: int | None = None


class UnidadeSeed(BaseModel):
    nome: str
    sigla: str
    tipo: str
    pai: str | None = None
    cor: CorUnidade | None = None


class ArquivoSeedUnidades(BaseModel):
    tipos: list[TipoUnidadeSeed]
    unidades: list[UnidadeSeed]


class ContagemSeed(BaseModel):
    tipos: int
    unidades: int


def _cor_padrao() -> str:
    return Unidade._meta.get_field("cor").get_default()


class AplicadorTipos:
    """Grava nível e marca de raiz primeiro; a veda de tipo-filho referencia outro tipo do arquivo."""

    def __call__(self, tipos: list[TipoUnidadeSeed]) -> int:
        return self.pipeline(tipos)

    def pipeline(self, tipos: list[TipoUnidadeSeed]) -> int:
        self._gravar_campos_base(tipos)
        self._ligar_vedas(tipos)
        return len(tipos)

    def _gravar_campos_base(self, tipos: list[TipoUnidadeSeed]) -> None:
        for tipo in tipos:
            TipoUnidade.objects.update_or_create(
                nome=tipo.nome,
                defaults={
                    "nivel": tipo.nivel,
                    "pode_ser_raiz": tipo.pode_ser_raiz,
                    "exige_alta_administracao": tipo.exige_alta_administracao,
                    "nivel_minimo_titular": tipo.nivel_minimo_titular,
                },
            )

    def _ligar_vedas(self, tipos: list[TipoUnidadeSeed]) -> None:
        # A lista do arquivo substitui a do banco: .set() troca a veda inteira, nunca acrescenta.
        for tipo in tipos:
            tipo_obj = TipoUnidade.objects.get(nome=tipo.nome)
            vedados = [
                TipoUnidade.objects.get(nome=nome_vedado)
                for nome_vedado in tipo.tipos_filhos_vedados
            ]
            tipo_obj.tipos_filhos_vedados.set(vedados)


class AplicadorUnidades:
    """Grava sem pai, depois liga a superior: a ordem do arquivo deixa de importar."""

    def __call__(self, unidades: list[UnidadeSeed]) -> int:
        return self.pipeline(unidades)

    def pipeline(self, unidades: list[UnidadeSeed]) -> int:
        self._gravar_sem_pai(unidades)
        self._ligar_superiores(unidades)
        return len(unidades)

    def _gravar_sem_pai(self, unidades: list[UnidadeSeed]) -> None:
        for unidade in unidades:
            tipo = TipoUnidade.objects.get(nome=unidade.tipo)
            Unidade.objects.update_or_create(
                sigla=unidade.sigla,
                defaults={
                    "nome": unidade.nome,
                    "tipo": tipo,
                    "cor": unidade.cor or _cor_padrao(),
                },
            )

    def _ligar_superiores(self, unidades: list[UnidadeSeed]) -> None:
        # full_clean() aqui, com o pai já ligado — antes disso a hierarquia nem existe.
        for unidade in unidades:
            obj = Unidade.objects.get(sigla=unidade.sigla)
            obj.pai = Unidade.objects.get(sigla=unidade.pai) if unidade.pai else None
            obj.full_clean()
            obj.save()


def carregar_seed_unidades(*, dry_run: bool = False) -> ContagemSeed:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    arquivo = ArquivoSeedUnidades.model_validate(dados)
    with transaction.atomic():
        total_tipos = AplicadorTipos()(arquivo.tipos)
        total_unidades = AplicadorUnidades()(arquivo.unidades)
        if dry_run:
            transaction.set_rollback(True)
    return ContagemSeed(tipos=total_tipos, unidades=total_unidades)

"""
Seed do admin inicial (SPEC user_admin/032): cria o administrador de `data/seed/admin.json` quando o
banco não tem nenhum. Só cria — nunca reescreve nem recria quem já existe.
"""

from enum import StrEnum

from django.db import transaction

from pydantic import BaseModel, ConfigDict

from apps.user_admin.models import Perfil
from apps.user_admin.schemas import NomeDePessoa, NovoSuperusuario, SobrenomeDePessoa
from apps.user_admin.superusuario import criar_superusuario
from services.utils.io import read_json_from_folder, subpasta_de_data
from services.utils.senha import gerar_senha_temporaria

NOME_SUBPASTA_SEED = "seed"
NOME_ARQUIVO_SEED = "admin.json"


class ConfiguracaoAdmin(BaseModel):
    """O que o ambiente diz do admin inicial. Texto cru: quem dá forma ao RF e ao e-mail é o
    `NovoSuperusuario`, e só quando há o que criar."""

    model_config = ConfigDict(frozen=True)

    rf: str
    # Vazio = não configurado.
    email: str
    # Desligado, a senha de uso único sai na tela em vez de ir para a caixa.
    envio_de_email_habilitado: bool


class CadastroAdmin(BaseModel):
    """A metade do `NovoSuperusuario` que o arquivo versionado carrega."""

    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    unidade_sigla: str
    cargo_base_sigla: str
    cargo_comissao_nome: str


class ArquivoSeedAdmin(BaseModel):
    admin: CadastroAdmin


class DesfechoAdmin(StrEnum):
    CRIADO = "criado"
    # Já há administrador no banco.
    DISPENSADO = "dispensado"
    # Era preciso criar e o e-mail não foi configurado.
    SEM_EMAIL = "sem_email"
    # Era preciso criar e o RF configurado já pertence a outro servidor.
    RF_OCUPADO = "rf_ocupado"


class ResultadoSeedAdmin(BaseModel):
    desfecho: DesfechoAdmin
    # True só em CRIADO: quem informar o RF na tela de primeiro acesso vê a senha de uso único.
    senha_sai_em_tela: bool = False


def carregar_seed_admin(config: ConfiguracaoAdmin, *, dry_run: bool = False) -> ResultadoSeedAdmin:
    # Antes de olhar a configuração: quem já tem administrador nunca é cobrado pelas variáveis.
    if Perfil.objects.filter(is_superuser=True).exists():
        return ResultadoSeedAdmin(desfecho=DesfechoAdmin.DISPENSADO)
    # Sem e-mail o reenvio não tem para onde mandar a senha de uso único.
    if not config.email:
        return ResultadoSeedAdmin(desfecho=DesfechoAdmin.SEM_EMAIL)
    novo = _novo_superusuario(config)
    # Exonerado perde o `is_superuser` e segue dono do RF: recriá-lo estouraria o `unique` na subida.
    if Perfil.objects.filter(rf=novo.rf).exists():
        return ResultadoSeedAdmin(desfecho=DesfechoAdmin.RF_OCUPADO)
    with transaction.atomic():
        # Ninguém conhece esta senha: ela só ocupa o campo até o reenvio do primeiro acesso.
        criar_superusuario(novo, gerar_senha_temporaria())
        if dry_run:
            transaction.set_rollback(True)
    return ResultadoSeedAdmin(
        desfecho=DesfechoAdmin.CRIADO,
        senha_sai_em_tela=not config.envio_de_email_habilitado,
    )


def _novo_superusuario(config: ConfiguracaoAdmin) -> NovoSuperusuario:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    cadastro = ArquivoSeedAdmin.model_validate(dados).admin
    return NovoSuperusuario(
        rf=config.rf,
        email=config.email,
        # Sem senha conhecida, o único caminho de entrada é o primeiro acesso.
        senha_provisoria=True,
        **cadastro.model_dump(),
    )

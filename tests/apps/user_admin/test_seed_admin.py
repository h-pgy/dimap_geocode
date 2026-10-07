"""
Testes da seed do admin inicial (SPEC user_admin/032): o administrador que nasce na subida sobre um
banco sem nenhum, a partir de `data/seed/admin.json` e das variáveis `ADMIN_*` — sem senha conhecida
por ninguém, e só quando falta.

Todos levam o marker `banco`, exceto o da ordem em `docker/run_seeds.sh`: perfil, unidade e cargos
são tabelas.
"""

from datetime import date
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist

import pytest
from pydantic import HttpUrl, ValidationError
from pytest_django.fixtures import SettingsWrapper

from apps.autenticacao.reenvio import reenviar_senha_uso_unico
from apps.autenticacao.schemas import ReenvioSenhaInput, ValidacaoOtpInput
from apps.autenticacao.services import autenticar_primeiro_login
from apps.cargos.models import CargoBase, CargoComissao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from apps.user_admin.seeds import ConfiguracaoAdmin, DesfechoAdmin, carregar_seed_admin
from services.utils.io import subpasta_de_data, write_json_to_folder

banco = pytest.mark.banco

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_SEEDS_PATH = REPO_ROOT / "docker" / "run_seeds.sh"

NOME_ARQUIVO_SEED = "admin.json"
RF_ADMIN = "0000000"
EMAIL_ADMIN = "admin@prefeitura.sp.gov.br"
SENHA_DEFINITIVA = "senha-definitiva-do-admin"
URL_ACESSO = HttpUrl("https://geocoder.dimap.local/")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _unidade() -> Unidade:
    tipo = TipoUnidade.objects.create(
        nome="Gabinete Seed Admin",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=4,
    )
    return Unidade.objects.create(
        nome="Gabinete do Secretário Municipal da Fazenda",
        sigla="SF-GAB",
        tipo=tipo,
    )


def _cargo_base() -> CargoBase:
    return CargoBase.objects.create(nome="Auditor Fiscal Tributário Municipal", sigla="AFTM")


def _cargo_comissao() -> CargoComissao:
    return CargoComissao.objects.create(
        nome="Assessor IV",
        sigla="CDA",
        nivel=4,
        e_chefia=False,
    )


def _perfil(rf: str, unidade: Unidade, cargo_base: CargoBase, **overrides: Any) -> Perfil:
    dados: dict[str, Any] = {
        "rf": rf,
        "nome": "Fulana",
        "sobrenome": "Preexistente",
        "email": f"{rf}@prefeitura.sp.gov.br",
        "unidade": unidade,
        "cargo_base": cargo_base,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)
    perfil.set_password("senha-de-quem-ja-estava")
    perfil.save()
    return perfil


def _configuracao(**overrides: Any) -> ConfiguracaoAdmin:
    dados: dict[str, Any] = {
        "rf": RF_ADMIN,
        "email": EMAIL_ADMIN,
        "envio_de_email_habilitado": True,
    }
    dados.update(overrides)
    return ConfiguracaoAdmin(**dados)


def _escrever_seed(**overrides: str) -> None:
    admin = {
        "nome": "Admin",
        "sobrenome": "do Sistema",
        "unidade_sigla": "SF-GAB",
        "cargo_base_sigla": "AFTM",
        "cargo_comissao_nome": "Assessor IV",
    }
    admin.update(overrides)
    pasta = subpasta_de_data("seed")
    write_json_to_folder(pasta, NOME_ARQUIVO_SEED, {"admin": admin})


# ---------------------------------------------------------------------------
# Banco sem administrador: o admin inicial nasce completo e em primeiro acesso
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_banco_sem_administrador_ganha_admin_inicial() -> None:
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed()

    resultado = carregar_seed_admin(_configuracao(envio_de_email_habilitado=True))

    assert resultado.desfecho is DesfechoAdmin.CRIADO
    assert resultado.senha_sai_em_tela is False
    admin = Perfil.objects.get(rf=RF_ADMIN)
    assert admin.email == EMAIL_ADMIN
    assert admin.is_superuser is True
    assert admin.unidade.sigla == "SF-GAB"
    assert admin.cargo_base.sigla == "AFTM"
    assert admin.cargo_comissao is not None
    assert admin.cargo_comissao.nome == "Assessor IV"
    assert admin.e_titular is False
    assert admin.senha_provisoria is True


@banco
@pytest.mark.django_db
def test_admin_inicial_entra_pela_senha_de_uso_unico_reenviada(
    settings: SettingsWrapper,
) -> None:
    # O mesmo flag nas duas pontas: é ele que a seed lê para o alerta e o reenvio para a entrega.
    settings.EMAIL_ENVIO_HABILITADO = False
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed()

    resultado = carregar_seed_admin(_configuracao(envio_de_email_habilitado=False))

    assert resultado.desfecho is DesfechoAdmin.CRIADO
    assert resultado.senha_sai_em_tela is True
    desfecho = reenviar_senha_uso_unico(ReenvioSenhaInput(rf=RF_ADMIN, url_acesso=URL_ACESSO))
    assert desfecho.senha_a_exibir is not None
    autenticado = autenticar_primeiro_login(
        ValidacaoOtpInput(rf=RF_ADMIN, codigo_otp=desfecho.senha_a_exibir)
    )
    assert autenticado is not None
    assert autenticado.rf == RF_ADMIN
    assert autenticado.is_superuser is True


# ---------------------------------------------------------------------------
# A seed só cria: nunca duplica, nunca reescreve, nunca cobra quem já tem administrador
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_segunda_carga_nao_duplica_nem_reescreve() -> None:
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed()
    carregar_seed_admin(_configuracao())
    admin = Perfil.objects.get(rf=RF_ADMIN)
    admin.set_password(SENHA_DEFINITIVA)
    admin.senha_provisoria = False
    admin.save()

    _escrever_seed(sobrenome="Reescrito")
    resultado = carregar_seed_admin(_configuracao(email="outro@prefeitura.sp.gov.br"))

    assert resultado.desfecho is DesfechoAdmin.DISPENSADO
    assert Perfil.objects.count() == 1
    admin.refresh_from_db()
    assert admin.sobrenome == "do Sistema"
    assert admin.email == EMAIL_ADMIN
    assert admin.check_password(SENHA_DEFINITIVA)


@banco
@pytest.mark.django_db
def test_administrador_existente_dispensa_admin_inicial_mesmo_sem_email() -> None:
    unidade = _unidade()
    cargo_base = _cargo_base()
    _cargo_comissao()
    _escrever_seed()
    _perfil("8123456", unidade, cargo_base, is_staff=True, is_superuser=True)

    resultado = carregar_seed_admin(_configuracao(email=""))

    assert resultado.desfecho is DesfechoAdmin.DISPENSADO
    assert Perfil.objects.count() == 1


# ---------------------------------------------------------------------------
# Sem como criar: nada é gravado e a carga não estoura
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_sem_email_nao_cria() -> None:
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed()

    resultado = carregar_seed_admin(_configuracao(email=""))

    assert resultado.desfecho is DesfechoAdmin.SEM_EMAIL
    assert Perfil.objects.count() == 0


@banco
@pytest.mark.django_db
def test_rf_ocupado_nao_cria_e_nao_estoura() -> None:
    unidade = _unidade()
    cargo_base = _cargo_base()
    _cargo_comissao()
    _escrever_seed()
    # Como a exoneração deixa o admin inicial: fora do quadro, sem a marca e com o RF ocupado.
    _perfil(
        RF_ADMIN,
        unidade,
        cargo_base,
        is_active=False,
        exonerado_em=date(2026, 1, 5),
    )

    resultado = carregar_seed_admin(_configuracao())

    assert resultado.desfecho is DesfechoAdmin.RF_OCUPADO
    assert Perfil.objects.count() == 1


# ---------------------------------------------------------------------------
# Configuração ou arquivo inválido: a carga aborta sem gravar nada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_rf_fora_do_formato_aborta_sem_gravar_nada() -> None:
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed()

    with pytest.raises(ValidationError):
        carregar_seed_admin(_configuracao(rf="12345"))

    assert Perfil.objects.count() == 0


@banco
@pytest.mark.django_db
def test_unidade_ausente_aborta_sem_gravar_nada() -> None:
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed(unidade_sigla="NAO-EXISTE")

    with pytest.raises(ObjectDoesNotExist):
        carregar_seed_admin(_configuracao())

    assert Perfil.objects.count() == 0


@banco
@pytest.mark.django_db
def test_dry_run_nao_persiste() -> None:
    _unidade()
    _cargo_base()
    _cargo_comissao()
    _escrever_seed()

    resultado = carregar_seed_admin(_configuracao(), dry_run=True)

    assert resultado.desfecho is DesfechoAdmin.CRIADO
    assert Perfil.objects.count() == 0


# ---------------------------------------------------------------------------
# Ordem na subida do container
# ---------------------------------------------------------------------------


def test_run_seeds_chama_seed_admin_depois_de_unidades_e_cargos() -> None:
    conteudo = RUN_SEEDS_PATH.read_text(encoding="utf-8")

    pos_unidades = conteudo.find("manage.py seed_unidades")
    pos_cargos = conteudo.find("manage.py seed_cargos")
    pos_admin = conteudo.find("manage.py seed_admin")

    assert pos_admin != -1, "Comando 'seed_admin' ausente em run_seeds.sh"
    assert pos_unidades != -1
    assert pos_cargos != -1
    assert pos_unidades < pos_admin
    assert pos_cargos < pos_admin

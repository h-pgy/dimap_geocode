"""
Django settings — DIMAP GeoCoder.

A configuração de ambiente é lida via Pydantic Settings e reextraída para
constantes UPPER_CASE locais (CLAUDE.md, "Estilo e Convenções de Código"). O resto do módulo
referencia as constantes, não o objeto de settings.
"""

import json
from datetime import time
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# Paleta do design system "Onsen de Inverno" — espelho de
# .claude/skills/componentes-frontend/references/paleta.json (fonte da verdade dos valores).
# Falha alto no boot se o JSON estiver ausente ou malformado (nunca silenciosamente).
_PALETA_DS: dict[str, Any] = json.loads((BASE_DIR / "config" / "paleta_ds.json").read_text())
_GEOMETRIAS: dict[str, str] = _PALETA_DS["geometrias"]
_ESCALAS: dict[str, dict[str, str]] = _PALETA_DS["escalas"]


class _Settings(BaseSettings):
    """Variáveis de ambiente do projeto (ver docker-compose.yml / .env.example)."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    secret_key: str = Field(
        default="dev-insecure-secret-key-change-me", alias="DJANGO_SECRET_KEY"
    )
    debug: bool = Field(default=True, alias="DJANGO_DEBUG")
    allowed_hosts: str = Field(default="*", alias="DJANGO_ALLOWED_HOSTS")
    csrf_trusted_origins: str = Field(
        default="https://*.ngrok-free.app,https://*.ngrok.app",
        alias="DJANGO_CSRF_TRUSTED_ORIGINS",
    )

    postgres_db: str = Field(default="dimap_geocode", alias="POSTGRES_DB")
    postgres_user: str = Field(default="dimap", alias="POSTGRES_USER")
    postgres_password: str = Field(default="dimap", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    wfs_domain: str = Field(default="wfs.geosampa.prefeitura.sp.gov.br", alias="WFS_DOMAIN")
    wfs_endpoint: str = Field(default="geoserver/geoportal/wfs", alias="WFS_ENDPOINT")
    wfs_namespace: str = Field(default="geoportal", alias="WFS_NAMESPACE")
    wfs_service: str = Field(default="WFS", alias="WFS_SERVICE")
    wfs_version: str = Field(default="1.0.0", alias="WFS_VERSION")
    wfs_layer_logradouros: str = Field(default="segmento_logradouro", alias="WFS_LAYER_LOGRADOUROS")
    wfs_layer_lote_cidadao: str = Field(default="lote_cidadao", alias="WFS_LAYER_LOTE_CIDADAO")
    wfs_verbose: bool = Field(default=True, alias="WFS_VERBOSE")
    wfs_request_timeout_seconds: float = Field(default=30.0, alias="WFS_REQUEST_TIMEOUT_SECONDS")
    wfs_max_retries: int = Field(default=3, alias="WFS_MAX_RETRIES")
    wfs_retry_wait_min_seconds: float = Field(default=1.0, alias="WFS_RETRY_WAIT_MIN_SECONDS")
    wfs_retry_wait_max_seconds: float = Field(default=5.0, alias="WFS_RETRY_WAIT_MAX_SECONDS")

    wms_url: str = Field(
        default="https://wms.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/ows",
        alias="WMS_URL",
    )
    wms_raster_url: str = Field(
        default="http://raster.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wms",
        alias="WMS_RASTER_URL",
    )
    wms_version: str = Field(default="1.3.0", alias="WMS_VERSION")
    wms_layer_ortofoto: str = Field(default="geoportal:ORTO_RGB_2020", alias="WMS_LAYER_ORTOFOTO")
    wms_layer_mapa_base: str = Field(
        default="geoportal:MapaBase_Politico", alias="WMS_LAYER_MAPA_BASE"
    )
    map_cor_linha: str = Field(default=_GEOMETRIAS["linha"], alias="MAP_COR_LINHA")
    map_cor_poligono: str = Field(default=_GEOMETRIAS["poligono"], alias="MAP_COR_POLIGONO")
    map_cor_ponto: str = Field(default=_GEOMETRIAS["ponto"], alias="MAP_COR_PONTO")
    map_cor_poligono_condominio: str = Field(
        default=_ESCALAS["sakura"]["700"], alias="MAP_COR_POLIGONO_CONDOMINIO"
    )
    map_tiles_publicos_url: str = Field(
        default="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        alias="MAP_TILES_PUBLICOS_URL",
    )
    map_tiles_publicos_subdominios: str = Field(
        default="abcd", alias="MAP_TILES_PUBLICOS_SUBDOMINIOS"
    )
    map_tiles_publicos_atribuicao: str = Field(
        default="&copy; OpenStreetMap &copy; CARTO",
        alias="MAP_TILES_PUBLICOS_ATRIBUICAO",
    )

    # Tipado como `time` para o Pydantic coagir o "HH:MM" do env: a aritmética da agenda
    # recebe um `time`, nunca uma string para parsear.
    dtime_atualizacao_arquivos: time = Field(
        default=time(3, 0),
        alias="DTIME_ATUALIZACAO_ARQUIVOS",
    )

    # Prefixo EMAIL_SMTP_ evita os nomes que o Django reserva para o send_mail dele
    # (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER...), que o projeto não usa.
    email_smtp_host: str = Field(default="smtp.gmail.com", alias="EMAIL_SMTP_HOST")
    email_smtp_porta: int = Field(default=587, alias="EMAIL_SMTP_PORTA")
    email_smtp_usuario: str = Field(default="", alias="EMAIL_SMTP_USUARIO")
    email_smtp_senha: str = Field(default="", alias="EMAIL_SMTP_SENHA")
    email_remetente_nome: str = Field(default="DIMAP GeoCoder", alias="EMAIL_REMETENTE_NOME")
    email_envio_habilitado: bool = Field(default=False, alias="EMAIL_ENVIO_HABILITADO")
    email_smtp_timeout_seconds: float = Field(default=30.0, alias="EMAIL_SMTP_TIMEOUT_SECONDS")
    email_smtp_max_retries: int = Field(default=2, alias="EMAIL_SMTP_MAX_RETRIES")
    email_smtp_retry_wait_min_seconds: float = Field(
        default=1.0,
        alias="EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS",
    )
    email_smtp_retry_wait_max_seconds: float = Field(
        default=5.0,
        alias="EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS",
    )

    # Fecha o cadastro de servidor (SPEC criacao_usuarios/004) aos domínios institucionais. O
    # banco não conhece esta regra — só a rota de cadastro por tela.
    enforce_prefeitura_email: bool = Field(default=True, alias="ENFORCE_PREFEITURA_EMAIL")


_env = _Settings()

SECRET_KEY = _env.secret_key
DEBUG = _env.debug
ALLOWED_HOSTS = [host.strip() for host in _env.allowed_hosts.split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in _env.csrf_trusted_origins.split(",") if origin.strip()
]

# WFS (GeoSampa → MDSF). A orquestração lê essas constantes e monta
# WfsConnectionConfig para injetar no WfsFetcher (nunca o domínio lê daqui).
WFS_DOMAIN = _env.wfs_domain
WFS_ENDPOINT = _env.wfs_endpoint
WFS_NAMESPACE = _env.wfs_namespace
WFS_SERVICE = _env.wfs_service
WFS_VERSION = _env.wfs_version
WFS_LAYER_LOGRADOUROS = _env.wfs_layer_logradouros
WFS_LAYER_LOTE_CIDADAO = _env.wfs_layer_lote_cidadao
# Liga o log da requisição WFS (URL + params) em todos os geocoders — diagnóstico
# do GeoSampa. O WfsFetcher imprime cada GET quando verbose; build_fetcher lê daqui.
WFS_VERBOSE = _env.wfs_verbose
WFS_REQUEST_TIMEOUT_SECONDS = _env.wfs_request_timeout_seconds
WFS_MAX_RETRIES = _env.wfs_max_retries
WFS_RETRY_WAIT_MIN_SECONDS = _env.wfs_retry_wait_min_seconds
WFS_RETRY_WAIT_MAX_SECONDS = _env.wfs_retry_wait_max_seconds

# WMS (GeoSampa → Leaflet tile layer). Config lida aqui e injetada no contexto do
# app mapping; o JS nunca hardcoda URL, versão ou nomes de camadas (§11).
WMS_URL = _env.wms_url
# A ortofoto NÃO é servida pelo WMS geral do GeoSampa: vem de um WMS de raster,
# em outro domínio. Cada base pode sobrescrever a URL via a chave "url"; quem
# não a define cai no WMS_URL geral (o JS resolve `b.url || wms.url`).
WMS_RASTER_URL = _env.wms_raster_url
WMS_VERSION = _env.wms_version
WMS_LAYER_ORTOFOTO = _env.wms_layer_ortofoto
WMS_LAYER_MAPA_BASE = _env.wms_layer_mapa_base
# Lista ordenada de bases; a 1ª é a visível por padrão.
WMS_BASES: list[dict[str, str]] = [
    {"nome": "Ortofoto", "layers": WMS_LAYER_ORTOFOTO, "url": WMS_RASTER_URL},
    {"nome": "Mapa base", "layers": WMS_LAYER_MAPA_BASE},
]

# Mapa — CRS de saída, centro/zoom default e cores por tipo de geometria.
MAP_OUTPUT_CRS = 4326
# CRS projetado/métrico p/ interpolar o número do endereço sobre o segmento (§7.3);
# 31983 = SIRGAS 2000 / UTM 23S, nativo do GeoSampa.
MAP_INTERPOLATION_CRS = 31983
MAP_CENTRO_DEFAULT: list[float] = [-23.55, -46.63]
# 14 preenche a viewport com a ortofoto sem mostrar os limites do município (em 12/13 sobra "vazio").
MAP_ZOOM_DEFAULT = 14
MAP_COR_LINHA = _env.map_cor_linha
MAP_COR_POLIGONO = _env.map_cor_poligono
MAP_COR_PONTO = _env.map_cor_ponto
# Cor agregada do lote condominial: mesma família do polígono, tom mais fundo (sakura-700).
MAP_COR_POLIGONO_CONDOMINIO = _env.map_cor_poligono_condominio

# Tiles públicos do fundo da área administrativa (SPEC user_admin/007): ali não há território a
# mostrar, então o fundo não gasta requisição no GeoSampa nem sugere semântica territorial.
MAP_TILES_PUBLICOS_URL = _env.map_tiles_publicos_url
MAP_TILES_PUBLICOS_SUBDOMINIOS = _env.map_tiles_publicos_subdominios
MAP_TILES_PUBLICOS_ATRIBUICAO = _env.map_tiles_publicos_atribuicao
MAP_TILES_PUBLICOS_ZOOM_MAXIMO = 20
# Mais fechado que o default do produto: a malha viária precisa de textura para a deriva ser
# percebida, e o recorte nunca alcança a borda do município.
MAP_ZOOM_FUNDO_ADMIN = 15

# Horário do dia (fuso de TIME_ZONE) em que o daemon reextrai os parquets de data/.
DTIME_ATUALIZACAO_ARQUIVOS = _env.dtime_atualizacao_arquivos

# E-mail — SMTP do Gmail (services.utils.smtp).
EMAIL_SMTP_HOST = _env.email_smtp_host
EMAIL_SMTP_PORTA = _env.email_smtp_porta
EMAIL_SMTP_USUARIO = _env.email_smtp_usuario
EMAIL_SMTP_SENHA = _env.email_smtp_senha
EMAIL_REMETENTE_NOME = _env.email_remetente_nome
EMAIL_ENVIO_HABILITADO = _env.email_envio_habilitado
EMAIL_SMTP_TIMEOUT_SECONDS = _env.email_smtp_timeout_seconds
EMAIL_SMTP_MAX_RETRIES = _env.email_smtp_max_retries
EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS = _env.email_smtp_retry_wait_min_seconds
EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS = _env.email_smtp_retry_wait_max_seconds

# Cadastro de servidor (apps.user_admin.cadastro) — desligue só em ambiente de teste.
ENFORCE_PREFEITURA_EMAIL = _env.enforce_prefeitura_email


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "apps.core",
    # Antes de user_admin: o Perfil é lotado numa unidade, e a dependência é de mão única.
    "apps.unidades",
    "apps.user_admin",
    "apps.autenticacao",
    "apps.competencias",
    "apps.search",
    "apps.logradouro_matcher",
    "apps.lote_matcher",
    "apps.address_geocoder",
    "apps.mapping",
    "apps.logradouro_geocoder",
    "apps.lote_geocoder",
    "apps.amostrador_ofertas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.PydanticValidationMiddleware",
]

# Perfil (apps.user_admin) concentra RF, cargo e unidade — o Perfil do CLAUDE.md §3.5.
AUTH_USER_MODEL = "user_admin.Perfil"

# `@login_required` sem isto cairia no default do Django (`/accounts/login/`, rota inexistente).
# Caminho literal, e não o nome da rota: é o que `settings.LOGIN_URL` compara nos testes de
# proteção de rota das demais ações (ex. apps/competencias/test_protecao.py).
LOGIN_URL = "/login/"

# Os dois backends, cada um com um papel; a ordem não decide nada, porque `has_perm` é verdadeiro
# se qualquer um deles disser sim (SPEC autorizacao/003).
AUTHENTICATION_BACKENDS = [
    # Autenticação, e as permissions do admin.
    "django.contrib.auth.backends.ModelBackend",
    # Autorização por competência: só responde permissão, e é a única fonte das ações da plataforma.
    "apps.competencias.backends.CompetenciaPermissionBackend",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # static/src entra SÓ para o {% include "tema-dimap.dev.css" %} do base.html: o tema
        # dev (fonte única do design system, SPEC design/004) é incluído server-side dentro do
        # <style type="text/tailwindcss">.
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "static" / "src"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.autenticacao.context_processors.contexto_usuario_autenticado",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database — PostGIS desde a fase inicial (CLAUDE.md, "Stack").

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": _env.postgres_db,
        "USER": _env.postgres_user,
        "PASSWORD": _env.postgres_password,
        "HOST": _env.postgres_host,
        "PORT": _env.postgres_port,
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# Static files — saída do build do Tailwind/DaisyUI (CLAUDE.md, "Estrutura do Projeto").

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static" / "dist", BASE_DIR / "static" / "src"]

# Mídia enviada por upload (hoje só a foto de perfil, SPEC user_admin/006). Servir o
# arquivo por rota é front-end e fica fora desta SPEC.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

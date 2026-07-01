"""
Django settings — DIMAP GeoCoder.

A configuração de ambiente é lida via Pydantic Settings e reextraída para
constantes UPPER_CASE locais (CLAUDE.md §10.3 / §11). O resto do módulo
referencia as constantes, não o objeto de settings.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class _Settings(BaseSettings):
    """Variáveis de ambiente do projeto (ver docker-compose.yml / .env.example)."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    secret_key: str = Field(
        default="dev-insecure-secret-key-change-me", alias="DJANGO_SECRET_KEY"
    )
    debug: bool = Field(default=True, alias="DJANGO_DEBUG")
    allowed_hosts: str = Field(default="*", alias="DJANGO_ALLOWED_HOSTS")

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
    map_cor_linha: str = Field(default="#3b82f6", alias="MAP_COR_LINHA")
    map_cor_poligono: str = Field(default="#f97316", alias="MAP_COR_POLIGONO")


_env = _Settings()

SECRET_KEY = _env.secret_key
DEBUG = _env.debug
ALLOWED_HOSTS = [host.strip() for host in _env.allowed_hosts.split(",") if host.strip()]

# WFS (GeoSampa → MDSF). A orquestração lê essas constantes e monta
# WfsConnectionConfig para injetar no WfsFetcher (nunca o domínio lê daqui).
WFS_DOMAIN = _env.wfs_domain
WFS_ENDPOINT = _env.wfs_endpoint
WFS_NAMESPACE = _env.wfs_namespace
WFS_SERVICE = _env.wfs_service
WFS_VERSION = _env.wfs_version
WFS_LAYER_LOGRADOUROS = _env.wfs_layer_logradouros
WFS_LAYER_LOTE_CIDADAO = _env.wfs_layer_lote_cidadao
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
MAP_CENTRO_DEFAULT: list[float] = [-23.55, -46.63]
MAP_ZOOM_DEFAULT = 12
MAP_COR_LINHA = _env.map_cor_linha
MAP_COR_POLIGONO = _env.map_cor_poligono


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
    "apps.search",
    "apps.logradouro_matcher",
    "apps.lote_matcher",
    "apps.address_geocoder",
    "apps.mapping",
    "apps.logradouro_geocoder",
    "apps.lote_geocoder",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database — PostGIS desde a fase inicial (CLAUDE.md §2).

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


# Static files — saída do build do Tailwind/DaisyUI (CLAUDE.md §5).

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static" / "dist", BASE_DIR / "static" / "src"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

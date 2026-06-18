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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
STATICFILES_DIRS = [BASE_DIR / "static" / "dist"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

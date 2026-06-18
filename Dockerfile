# syntax=docker/dockerfile:1

# Debian (trixie) pina as versões de GEOS, GDAL e PROJ — dependências de sistema
# do GeoDjango que NÃO podem ser instaladas via uv/pip.
FROM python:3.14-slim-trixie

# Bibliotecas de sistema exigidas pelo GeoDjango (ver CLAUDE.md §2).
#   gdal-bin / libgdal-dev -> GDAL   |   libgeos-dev -> GEOS   |   libproj-dev -> PROJ
RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# uv pinado na mesma versão que gerou o uv.lock (reprodutibilidade).
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/

# O ambiente fica FORA de /app (/opt/venv) para não ser sobrescrito pelo
# bind mount do código em desenvolvimento (ver docker-compose.yml).
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Camada de dependências: só refaz se pyproject.toml / uv.lock mudarem.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Entrypoint: roda migrações e repassa o controle ao CMD/command (fica em /
# para não ser escondido pelo bind mount do código em /app).
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Código da aplicação (em dev é sobreposto pelo bind mount do compose).
COPY . .

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
# Default de desenvolvimento; troque por gunicorn/uvicorn no deploy.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

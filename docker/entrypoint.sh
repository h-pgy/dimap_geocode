#!/bin/sh
# Entrypoint do serviço web: aplica migrações pendentes e então entrega o
# controle ao processo definido em CMD (Dockerfile) ou command (compose),
# usando `exec` para que sinais (SIGTERM/SIGINT) cheguem ao processo real.
set -e

# Antes do scaffold do projeto Django o manage.py não existe — nesse caso
# pulamos a migração para não quebrar comandos pontuais (ex.: startproject).
# Em produção, desative o migrate automático com DJANGO_AUTO_MIGRATE=0.
# Sync contra banco não migrado derrubaria a subida pelo set -e: quem desliga a migração
# automática desliga a projeção do catálogo de ações junto.
if [ -f manage.py ] && [ "${DJANGO_AUTO_MIGRATE:-1}" = "1" ]; then
    echo "==> Aplicando migrações..."
    python manage.py migrate --noinput
    echo "==> Sincronizando catálogo de ações..."
    python manage.py sincronizar_acoes

    # Executa a carga de seeds se habilitado (padrão 1).
    if [ "${DJANGO_AUTO_SEED:-1}" = "1" ]; then
        echo "==> Executando seeds..."
        sh docker/run_seeds.sh
    fi
fi

exec "$@"

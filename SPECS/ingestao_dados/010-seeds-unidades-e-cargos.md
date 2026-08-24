---
spec: ingestao_dados/010
versao: v1
atualizado_em: 2026-08-18
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC ingestao_dados/010 — Orquestração de seeds e flag no Docker Compose

## 1 · User story
**Requisito não-funcional** — automatizar a carga inicial dos catálogos versionados na inicialização do serviço web, permitindo desativação opcional por variável de ambiente e execução manual agregada via script.

## 2 · Condições de pronto
- [x] O script `docker/run_seeds.sh` executa sequencialmente `seed_unidades`, `seed_cargos` e `seed_tipos_impedimento`, abortando imediatamente em caso de erro (`set -e`).
- [x] Na inicialização padrão do container `web`, as seeds são executadas automaticamente após as migrações e a sincronização do catálogo de ações.
- [x] Definir `DJANGO_AUTO_SEED=0` impede a execução das seeds na inicialização do container `web`.
- [x] A variável `DJANGO_AUTO_SEED` está configurada com valor default `1` no `docker-compose.yml` e documentada no `.env.example`.

## 3 · Domínio
Orquestração do ciclo de inicialização do container e consumo dos management commands de seed do app `user_admin`.

Consome os comandos:
- `seed_unidades`: carga de tipos de unidade e unidades administrativas.
- `seed_cargos`: carga de cargos e atribuições.
- `seed_tipos_impedimento`: carga de tipos de impedimento.

## 4 · Fora de escopo
- Alterações na lógica interna das seeds ou nos modelos de persistência (pertence ao app `apps/user_admin`).
- Criação de novos arquivos de dados de seed em `data/seed/` (sem dono ainda).

## 5 · Peças de referência a compor
- `@apps/user_admin/management/commands/seed_unidades.py` → `Command`: carga de unidades.
- `@apps/user_admin/management/commands/seed_cargos.py` → `Command`: carga de cargos.
- `@apps/user_admin/management/commands/seed_tipos_impedimento.py` → `Command`: carga de tipos de impedimento.
- `@docker/entrypoint.sh` → entrypoint do container web.
- `@docker-compose.yml` → declaração de variáveis de ambiente do serviço web.
- Skills: `seeds`, `management-commands`.

## 6 · Snippets

**`docker/run_seeds.sh`**
```sh
#!/bin/sh
# Executa todos os management commands de seed na ordem de dependência.
set -e

echo "==> Carregando seed de unidades..."
python manage.py seed_unidades

echo "==> Carregando seed de cargos..."
python manage.py seed_cargos

echo "==> Carregando seed de tipos de impedimento..."
python manage.py seed_tipos_impedimento

echo "==> Seeds concluídas com sucesso."
```

**`docker/entrypoint.sh`**
```sh
#!/bin/sh
set -e

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
```

**`docker-compose.yml`**
```yaml
    environment:
      DJANGO_AUTO_MIGRATE: ${DJANGO_AUTO_MIGRATE:-1}
      DJANGO_AUTO_SEED: ${DJANGO_AUTO_SEED:-1}
      POSTGRES_DB: ${POSTGRES_DB:-dimap_geocode}
```

**`.env.example`**
```env
# Execução automática de seeds no startup (1 = ativo, 0 = inativo)
DJANGO_AUTO_SEED=1
```

## 7 · Caveats
A execução de seeds é condicionada ao bloco de migração automática do entrypoint. Optou-se por esse aninhamento porque seeds exigem tabelas migradas para persistir registros com integridade. O custo é que desativar migrações com `DJANGO_AUTO_MIGRATE=0` desativa também a execução automática de seeds na subida, exigindo disparo manual via `docker/run_seeds.sh`.

## 8 · Testes (TDD)
- `test_run_seeds_script_contem_todos_os_comandos_de_seed_em_ordem` — valida se o script `docker/run_seeds.sh` chama `seed_unidades`, `seed_cargos` e `seed_tipos_impedimento`.
- `test_entrypoint_chama_run_seeds_quando_auto_seed_ativo` — valida que a subida executa o script de seeds quando `DJANGO_AUTO_SEED=1`.
- `test_entrypoint_pula_run_seeds_quando_auto_seed_desativado` — valida que a subida ignora o script de seeds quando `DJANGO_AUTO_SEED=0`.

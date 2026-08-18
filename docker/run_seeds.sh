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

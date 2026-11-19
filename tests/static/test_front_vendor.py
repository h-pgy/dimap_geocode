"""
Testes das bibliotecas de front-end servidas pelo próprio sistema (SPEC infraestrutura/006).
"""

import json
from pathlib import Path
import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import Client
from django.urls import reverse
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_JSON = REPO_ROOT / "package.json"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
FRONT_VENDOR_DIR: Path = settings.FRONT_VENDOR_DIR

GRUPOS_DE_DEPENDENCIA = ("dependencies", "devDependencies")

ORIGENS_EXTERNAS_PROIBIDAS = (
    "unpkg.com",
    "cdn.jsdelivr.net",
    "esm.sh",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "picsum.photos",
)

VERSAO_EXATA = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
STATIC_VENDOR = re.compile(r"""\{%\s*static\s+['"](vendor/[^'"]+)['"]\s*%\}""")

BIBLIOTECAS_DA_HOME = (
    "vendor/htmx.min.js",
    "vendor/leaflet/leaflet.js",
    "vendor/leaflet/leaflet.css",
    "vendor/leaflet-geoman/leaflet-geoman.min.js",
    "vendor/leaflet-geoman/leaflet-geoman.css",
    "vendor/roboto/400.css",
    "vendor/roboto-mono/400.css",
)


def _templates() -> list[Path]:
    return sorted(
        [
            *(REPO_ROOT / "templates").rglob("*.html"),
            *(REPO_ROOT / "apps").glob("**/templates/**/*.html"),
        ]
    )


def _dependencias_diretas() -> dict[str, str]:
    pacote = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    return {
        nome: versao
        for grupo in GRUPOS_DE_DEPENDENCIA
        for nome, versao in pacote.get(grupo, {}).items()
    }


def test_templates_nao_referenciam_cdn() -> None:
    citacoes = [
        f"{template.relative_to(REPO_ROOT)}: {origem}"
        for template in _templates()
        for origem in ORIGENS_EXTERNAS_PROIBIDAS
        if origem in template.read_text(encoding="utf-8")
    ]

    assert not citacoes, f"template buscando biblioteca fora do servidor: {citacoes}"


def test_package_json_so_tem_versao_exata() -> None:
    com_faixa = {
        nome: versao
        for nome, versao in _dependencias_diretas().items()
        if not VERSAO_EXATA.match(versao)
    }

    assert not com_faixa, f"dependência sem versão exata no package.json: {com_faixa}"


def test_lock_bate_com_package_json() -> None:
    pacotes_travados = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))["packages"]

    divergentes = {
        nome: (versao, pacotes_travados.get(f"node_modules/{nome}", {}).get("version"))
        for nome, versao in _dependencias_diretas().items()
        if pacotes_travados.get(f"node_modules/{nome}", {}).get("version") != versao
    }

    assert not divergentes, (
        f"package.json × package-lock.json (pedida, travada): {divergentes}"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not FRONT_VENDOR_DIR.is_dir(),
    reason=(
        f"{FRONT_VENDOR_DIR} só existe na imagem do web, que não tem pytest: extraia com "
        "`docker cp $(docker create dimap-geocode-web):/opt/vendor <pasta>` e rode com "
        "FRONT_VENDOR_DIR=<pasta>"
    ),
)
def test_todo_static_vendor_dos_templates_existe() -> None:
    citados = {
        caminho
        for template in _templates()
        for caminho in STATIC_VENDOR.findall(template.read_text(encoding="utf-8"))
    }

    assert citados, "nenhum static de vendor citado: o teste perdeu o significado"
    ausentes = sorted(caminho for caminho in citados if finders.find(caminho) is None)
    assert not ausentes, (
        f"arquivo de vendor citado e não encontrado pelos finders: {ausentes}"
    )


def test_home_serve_bibliotecas_locais() -> None:
    resposta = Client().get(reverse("core:home"))

    assert resposta.status_code == 200
    html = resposta.content.decode()
    faltando = [
        caminho for caminho in BIBLIOTECAS_DA_HOME if f"/static/{caminho}" not in html
    ]
    externas = [origem for origem in ORIGENS_EXTERNAS_PROIBIDAS if origem in html]
    assert not faltando, f"biblioteca local ausente da home: {faltando}"
    assert not externas, f"home ainda cita endereço externo de biblioteca: {externas}"

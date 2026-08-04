from pathlib import Path

from apps.core.management.commands.atualizar_dados import ETAPAS
from config.settings import INSTALLED_APPS

ETAPA_ITBI = "extrair_guias_itbi"
PREFIXO_APPS = "apps."
RAIZ = Path(__file__).resolve().parents[3]


def _comandos_dos_apps_instalados() -> set[str]:
    comandos: set[str] = set()

    for app in INSTALLED_APPS:
        if not app.startswith(PREFIXO_APPS):
            continue
        pasta = RAIZ / app.replace(".", "/") / "management" / "commands"
        comandos.update(caminho.stem for caminho in pasta.glob("*.py"))

    return comandos


def test_itbi_e_a_ultima_etapa_do_pipeline() -> None:
    # Última porque o pipeline aborta na primeira falha e esta é a etapa mais frágil (portal
    # de CMS); no meio, um 503 impediria as etapas seguintes de rodar.
    assert ETAPAS[-1] == ETAPA_ITBI


def test_toda_etapa_do_pipeline_tem_comando_em_app_instalado() -> None:
    # O Django só descobre comando de app instalado: fora do INSTALLED_APPS, a etapa só
    # apareceria como CommandError no ciclo noturno.
    assert set(ETAPAS) <= _comandos_dos_apps_instalados()

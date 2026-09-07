from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from services.domain.contribuinte_match import ContribuinteCatalog
from services.domain.logradouros_match import LogradouroCatalog
from services.utils.io import config as io_config


@pytest.fixture(autouse=True)
def _isolar_diretorio_de_dados(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Testes `integration` leem os parquets reais de data/ por definição (e nunca escrevem):
    # redirecionar o diretório esvaziaria o teste. A exceção é pelo marker, nunca por lista
    # de módulos — a lista cresce, o marker não.
    if request.node.get_closest_marker("integration"):
        return
    # Um ponto único de resolução: os escritores chamam config.data_dir() pelo módulo, então
    # este patch alcança todos eles de uma vez (SPEC ingestao_dados/006).
    monkeypatch.setattr(io_config, "data_dir", lambda: tmp_path)


@pytest.fixture(autouse=True)
def _resetar_catalogos_singleton() -> Generator[None, None, None]:
    # Os catálogos são singletons (SPEC infraestrutura/003, Patch 002); sem o reset,
    # o cache TTL populado com dados sintéticos de um teste vazaria para os seguintes.
    LogradouroCatalog.resetar_instancia()
    ContribuinteCatalog.resetar_instancia()
    yield
    LogradouroCatalog.resetar_instancia()
    ContribuinteCatalog.resetar_instancia()


@pytest.fixture
def publicar_artefato(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> Callable[[str, bytes], Path]:
    """Grava o artefato onde ele sobreviva à sessão (fora do repositório) e imprime onde
    está — o produto de um teste `artefato` é o arquivo, não uma asserção."""

    def publicar(nome: str, conteudo: bytes) -> Path:
        destino = tmp_path / nome
        destino.write_bytes(conteudo)
        # `pytest-current` é o symlink que o pytest mantém para a última sessão: um caminho
        # fixo, que dá para deixar aberto no leitor de PDF/imagem e só recarregar a cada execução.
        estavel = tmp_path.parent.parent / "pytest-current" / tmp_path.name / nome
        with capsys.disabled():
            print(f"\n  {nome} → {estavel}")
        return destino

    return publicar


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--all", action="store_true", help="Roda a suíte inteira, markers inclusive.")


def pytest_configure(config: pytest.Config) -> None:
    # O `-m` herdado do addopts é o que exclui as camadas pesadas; --all simplesmente o esvazia.
    if config.getoption("--all"):
        config.option.markexpr = ""

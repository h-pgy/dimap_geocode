import pkgutil
from importlib import import_module
from inspect import Parameter, signature
from typing import Any

import services.scripts


def _subpacotes_de_scripts() -> list[str]:
    # Regra topológica (SPEC ingestao_dados/006): subpacote de services/scripts/ é script de
    # carga e tem que expor run(); módulo solto no topo é infraestrutura do pipeline
    # (contrato.py e o que a SPEC 007 trouxer) e não é varrido.
    return [
        modulo.name
        for modulo in pkgutil.iter_modules(services.scripts.__path__)
        if modulo.ispkg
    ]


def test_todo_runner_de_script_segue_o_contrato() -> None:
    pacotes = _subpacotes_de_scripts()
    assert pacotes, "nenhum subpacote encontrado em services/scripts/"

    for pacote in pacotes:
        run: Any = getattr(import_module(f"services.scripts.{pacote}"), "run", None)
        assert run is not None, f"{pacote}: subpacote de scripts sem run() exposto"

        params = signature(run).parameters
        assert list(params)[0] == "config", f"{pacote}: 1º parâmetro do run() não é 'config'"

        verbose = params.get("verbose")
        assert verbose is not None, f"{pacote}: run() não recebe 'verbose'"
        assert verbose.kind is Parameter.KEYWORD_ONLY, f"{pacote}: 'verbose' não é keyword-only"
        assert verbose.default is False, f"{pacote}: 'verbose' sem default False"

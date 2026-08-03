import traceback as traceback_mod
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from services.utils.io import read_json_from_data, write_json_to_data

from .constants import LIMITE_TRACEBACK, METADADOS_FILENAME
from .models import MetadadoArquivo


class Registro:
    """O que o runner sabe e o módulo não: a contagem gravada. Quem persiste é o contexto."""

    def __init__(self) -> None:
        self.registros: int | None = None
        self.detalhes: dict[str, Any] | None = None

    def sucesso(self, *, registros: int, detalhes: dict[str, Any] | None = None) -> None:
        self.registros = registros
        self.detalhes = detalhes


def _ler_bruto() -> dict[str, Any]:
    try:
        return read_json_from_data(METADADOS_FILENAME)
    except FileNotFoundError:
        return {}  # primeira execução / checkout limpo: nada registrado ainda


def ler_metadados() -> dict[str, MetadadoArquivo]:
    return {
        arquivo: MetadadoArquivo.model_validate(dados) for arquivo, dados in _ler_bruto().items()
    }


def _gravar(metadado: MetadadoArquivo) -> None:
    # Read-modify-write por chave: o registro de um arquivo nunca apaga o dos demais.
    registros = _ler_bruto()
    registros[metadado.arquivo] = metadado.model_dump(mode="json")
    write_json_to_data(METADADOS_FILENAME, registros)


@contextmanager
def registrar_execucao(arquivo: str, *, manual: bool) -> Iterator[Registro]:
    """Envolve o trabalho do runner: grava sucesso ao sair limpo, falha ao sair por exceção.

    Na falha devolve ao arquivo o `last_successful_run`/`registros` que já estavam lá — a memória
    do último sucesso não se perde — e relevanta a exceção: isto é observabilidade, não try/except.
    """
    anterior = ler_metadados().get(arquivo)
    registro = Registro()

    try:
        yield registro
    except Exception as exc:
        _gravar(
            MetadadoArquivo(
                arquivo=arquivo,
                status="falha",
                last_run=datetime.now(),
                manual=manual,
                erro=f"{type(exc).__name__}: {exc}",
                traceback="".join(traceback_mod.format_exception(exc))[-LIMITE_TRACEBACK:],
                last_successful_run=anterior.last_successful_run if anterior else None,
                registros=anterior.registros if anterior else None,
            )
        )
        raise

    agora = datetime.now()
    _gravar(
        MetadadoArquivo(
            arquivo=arquivo,
            status="sucesso",
            last_run=agora,
            manual=manual,
            last_successful_run=agora,
            registros=registro.registros,
            detalhes=registro.detalhes,
        )
    )

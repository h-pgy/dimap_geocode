from pathlib import Path

import pytest

from services.utils.io import escrever_atomico


def test_escrita_interrompida_preserva_arquivo_anterior(tmp_path: Path) -> None:
    alvo = tmp_path / "artefato.parquet"
    escrever_atomico(alvo, lambda destino: destino.write_bytes(b"carga anterior inteira"))

    def escritor_que_morre_no_meio(destino: Path) -> None:
        destino.write_bytes(b"carga nova pela met")
        raise RuntimeError("disco cheio")

    with pytest.raises(RuntimeError):
        escrever_atomico(alvo, escritor_que_morre_no_meio)

    # Quem lê vê o velho inteiro ou o novo inteiro, nunca um truncado.
    assert alvo.read_bytes() == b"carga anterior inteira"
    assert list(tmp_path.glob("*.tmp")) == [], "temporário ficou para trás em data/"

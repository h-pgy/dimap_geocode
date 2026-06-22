from services.scripts.logradouros.augment_tipos_logradouro import (
    QWERTY_ABNT2_NEIGHBORS,
    _gerar_variacoes,
    run,
)
from services.utils.io import read_parquet_from_data
from services.utils.normalization import normalize_text


def test_variacoes_avenida_contem_trocas_esperadas() -> None:
    variacoes = _gerar_variacoes("AVENIDA", QWERTY_ABNT2_NEIGHBORS)

    # A (pos 0) → vizinhos QWSZ
    assert "QVENIDA" in variacoes
    assert "WVENIDA" in variacoes
    assert "SVENIDA" in variacoes
    assert "ZVENIDA" in variacoes

    # I (pos 4) → vizinhos 89UOJKL
    assert "AVENUDA" in variacoes
    assert "AVENODA" in variacoes

    # o próprio nome não é variação
    assert "AVENIDA" not in variacoes


def test_run_normaliza_chaves() -> None:
    run()
    result = read_parquet_from_data("tipos_logradouro_cache.parquet")
    nomes: list[object] = result["nome_tipo"]

    # chave original "Avenida" deve ter sido normalizada para "AVENIDA"
    assert "AVENIDA" in nomes
    assert "Avenida" not in nomes

    # todas as entradas estão em caixa alta (sem lowercase)
    for nome in nomes:
        assert str(nome) == normalize_text(str(nome)), f"nome_tipo não normalizado: {nome!r}"


def test_run_idempotente() -> None:
    stats_1 = run()
    stats_2 = run()

    assert stats_1.n_original == stats_2.n_original
    assert stats_1.n_variacoes == stats_2.n_variacoes
    assert stats_1.n_total == stats_2.n_total
    assert stats_1.tipos_nao_mapeados == stats_2.tipos_nao_mapeados

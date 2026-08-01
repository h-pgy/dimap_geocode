import pytest

from services.scripts.augment_tipos_logradouro import AugmentRequest, gerar_variacoes_nome, run
from services.utils.io import read_parquet_from_data, write_json_to_data, write_parquet_to_data
from services.utils.normalization import normalize_text

JSON_TIPOS = "tipos_sinteticos.json"
PARQUET_NOMES = "nomes_sinteticos.parquet"
PARQUET_SAIDA = "cache_sintetico.parquet"


@pytest.fixture
def insumos_sinteticos() -> AugmentRequest:
    # Insumos próprios no diretório temporário (fixture _isolar_diretorio_de_dados do
    # conftest): o teste não lê nem reescreve os artefatos versionados de data/.
    write_json_to_data(JSON_TIPOS, {"Avenida": "AV", "Rua": "R"})
    write_parquet_to_data(
        {"codlog": ["168610", "100000"], "cd_tipo_logradouro": ["AV", "R"]},
        PARQUET_NOMES,
    )
    return AugmentRequest(
        input_json_name=JSON_TIPOS,
        input_parquet_name=PARQUET_NOMES,
        output_parquet_name=PARQUET_SAIDA,
    )


def test_variacoes_avenida_contem_trocas_esperadas() -> None:
    variacoes = gerar_variacoes_nome("AVENIDA")

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


def test_run_normaliza_chaves(insumos_sinteticos: AugmentRequest) -> None:
    run(insumos_sinteticos)
    result = read_parquet_from_data(PARQUET_SAIDA)
    nomes: list[object] = result["nome_tipo"]

    # chave original "Avenida" deve ter sido normalizada para "AVENIDA"
    assert "AVENIDA" in nomes
    assert "Avenida" not in nomes

    # todas as entradas estão em caixa alta (sem lowercase)
    for nome in nomes:
        assert str(nome) == normalize_text(str(nome)), f"nome_tipo não normalizado: {nome!r}"


def test_run_idempotente(insumos_sinteticos: AugmentRequest) -> None:
    stats_1 = run(insumos_sinteticos)
    stats_2 = run(insumos_sinteticos)

    assert stats_1 == stats_2


def test_augment_verbose_apura_variacoes_por_tipo(insumos_sinteticos: AugmentRequest) -> None:
    stats_verboso = run(insumos_sinteticos, verbose=True)
    stats_silencioso = run(insumos_sinteticos)

    # verbose no augment não é "imprimir mais": é apurar e devolver mais.
    assert stats_silencioso.variacoes_por_tipo is None
    assert stats_verboso.variacoes_por_tipo is not None
    assert set(stats_verboso.variacoes_por_tipo) == {"AVENIDA", "RUA"}
    assert sum(stats_verboso.variacoes_por_tipo.values()) == stats_verboso.n_variacoes

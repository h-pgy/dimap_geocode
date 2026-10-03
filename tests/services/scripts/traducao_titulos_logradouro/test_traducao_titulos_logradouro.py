from services.scripts.traducao_titulos_logradouro import TraducaoTitulosConfig, run
from services.utils.io import read_parquet_from_data, write_json_to_data, write_parquet_to_data

JSON_TITULOS = "titulos_sinteticos.json"
PARQUET_NOMES = "nomes_sinteticos.parquet"
PARQUET_SAIDA = "titulos_cache_sintetico.parquet"


def _config() -> TraducaoTitulosConfig:
    # Insumos próprios no diretório temporário (fixture _isolar_diretorio_de_dados do conftest):
    # o teste não lê nem reescreve o dicionário versionado de data/.
    write_json_to_data(JSON_TITULOS, {"CON": "Cônego", "BRIG": "Brigadeiro"})
    write_parquet_to_data(
        {
            "codlog": ["011711", "121657", "053287", "999990"],
            "cd_titulo_logradouro": ["CON", "BRIG", None, "XPTO"],
        },
        PARQUET_NOMES,
    )
    return TraducaoTitulosConfig(
        input_json_name=JSON_TITULOS,
        input_parquet_name=PARQUET_NOMES,
        output_parquet_name=PARQUET_SAIDA,
    )


def test_traducao_de_titulos_normaliza_e_avisa_sigla_sem_extenso() -> None:
    stats = run(_config())

    cache = read_parquet_from_data(PARQUET_SAIDA)
    extenso_por_sigla = dict(zip(cache["cd_titulo_logradouro"], cache["nome_titulo"]))
    assert extenso_por_sigla == {"CON": "CONEGO", "BRIG": "BRIGADEIRO"}
    assert stats.siglas_sem_extenso == ["XPTO"]

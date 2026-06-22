from dataclasses import dataclass, field

from services.utils.io import read_json_from_data, read_parquet_from_data, write_parquet_to_data
from services.utils.normalization import normalize_text
from .gerar_variacoes_typos_qwerty import gerar_todas_as_variacoes
from .constants import TIPOS_LOGRADOURO_AUMENTADO_MANUAL, PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL
from .models import AugmentStats

OUTPUT_PARQUET_NAME = "tipos_logradouro_cache.parquet"
COL_CODIGO = "cd_tipo_logradouro"
COL_NOME = "nome_tipo"


def check_dados_input_consistentes(dados_json_aumentado_manual: dict[str, str],
                                   input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL) -> list[str]:

    parquet_data = read_parquet_from_data(input_parquet_name)
    codigos_parquet: set[str] = set(str(v) for v in parquet_data[COL_CODIGO])
    

    codigos_json: set[str] = set(dados_json_aumentado_manual.values())
    tipos_nao_mapeados = sorted(codigos_parquet - codigos_json)

    return tipos_nao_mapeados


def colunas_nomes_e_codigos(dados_aumentados_normalizados: dict[str, str], variacoes_acumuladas: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    
    #aqui tira as duplicadas caso a variação já esteja no dicionario original e ja gera as colunas
    seen: set[str] = set()
    nomes: list[str] = []
    codigos: list[str] = []

    for nome, codigo in list(dados_aumentados_normalizados.items()) + variacoes_acumuladas:
        if nome not in seen:
            seen.add(nome)
            nomes.append(nome)
            codigos.append(codigo)

    return nomes, codigos

def pipeline(
    input_json_name: str = TIPOS_LOGRADOURO_AUMENTADO_MANUAL,
    input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL,
    output_parquet_name: str = OUTPUT_PARQUET_NAME,
) -> AugmentStats:
    
    dados_json_aumentados_manual = read_json_from_data(input_json_name)
    tipos_nao_mapeados = check_dados_input_consistentes(dados_json_aumentados_manual, input_parquet_name)
    
    dados_aumentados_normalizados: dict[str, str] = {
        normalize_text(chave): codigo for chave, codigo in dados_json_aumentados_manual.items()
    }

    variacoes_acumuladas = gerar_todas_as_variacoes(dados_aumentados_normalizados)
    nomes, codigos = colunas_nomes_e_codigos(dados_aumentados_normalizados, variacoes_acumuladas)
    write_parquet_to_data({COL_NOME: nomes, COL_CODIGO: codigos}, output_parquet_name)

    return AugmentStats(
        n_original=len(dados_aumentados_normalizados),
        n_variacoes=len(variacoes_acumuladas),
        n_total=len(nomes),
        tipos_nao_mapeados=tipos_nao_mapeados,
    )

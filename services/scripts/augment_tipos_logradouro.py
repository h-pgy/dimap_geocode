from dataclasses import dataclass, field

from services.utils.io import read_json_from_data, read_parquet_from_data, write_parquet_to_data
from services.utils.normalization import normalize_text

INPUT_JSON_NAME = "tipos_logradouro_aumentado.json"
INPUT_PARQUET_NAME = "nomes_logradouros.parquet"
OUTPUT_PARQUET_NAME = "tipos_logradouro_cache.parquet"
COL_CODIGO = "cd_tipo_logradouro"
COL_NOME = "nome_tipo"

# Layout físico QWERTY ABNT2 (Ç representada como C, coerente com normalize_text):
#   1 2 3 4 5 6 7 8 9 0
#    Q W E R T Y U I O P
#     A S D F G H J K L Ç
#      Z X C V B N M
QWERTY_ABNT2_NEIGHBORS: dict[str, str] = {
    "Q": "12WAS",   "W": "23QEASD",  "E": "34WRSDF",  "R": "45ETDFG",
    "T": "56RYFGH", "Y": "67TUGHJ",  "U": "78YIHJK",  "I": "89UOJKL",
    "O": "90IPKLC", "P": "0OLC",
    "A": "QWSZ",    "S": "QWEADZXC", "D": "WERSFXCV", "F": "ERTDGCVB",
    "G": "RTYFHVBN","H": "TYUGJBNM", "J": "YUIHKNM",  "K": "UIOJLM",
    "L": "IOPKC",
    "Z": "ASX",     "X": "ASDZC",    "C": "SDFXV",    "V": "CDFGB",
    "B": "VNFGH",   "N": "BGHJM",    "M": "NJHK",
}


@dataclass
class AugmentStats:
    n_original: int
    n_variacoes: int
    n_total: int
    tipos_nao_mapeados: list[str] = field(default_factory=list)


def _gerar_variacoes(nome: str, vizinhos: dict[str, str]) -> set[str]:
    variacoes: set[str] = set()
    for i, ch in enumerate(nome):
        for vizinho in vizinhos.get(ch, ""):
            variacoes.add(nome[:i] + vizinho + nome[i + 1:])
    variacoes.discard(nome)
    return variacoes


def run(
    input_json_name: str = INPUT_JSON_NAME,
    input_parquet_name: str = INPUT_PARQUET_NAME,
    output_parquet_name: str = OUTPUT_PARQUET_NAME,
) -> AugmentStats:
    raw: dict[str, str] = read_json_from_data(input_json_name)
    normalized: dict[str, str] = {
        normalize_text(chave): codigo for chave, codigo in raw.items()
    }

    parquet_data = read_parquet_from_data(input_parquet_name)
    codigos_parquet: set[str] = set(str(v) for v in parquet_data[COL_CODIGO])
    codigos_json: set[str] = set(normalized.values())
    tipos_nao_mapeados = sorted(codigos_parquet - codigos_json)

    chaves_originais: set[str] = set(normalized.keys())
    variacoes_acumuladas: list[tuple[str, str]] = []

    for nome, codigo in normalized.items():
        for variacao in _gerar_variacoes(nome, QWERTY_ABNT2_NEIGHBORS):
            if variacao not in chaves_originais:
                variacoes_acumuladas.append((variacao, codigo))

    # Monta lista final sem duplicatas por nome_tipo (originais têm precedência)
    seen: set[str] = set()
    nomes: list[str] = []
    codigos: list[str] = []

    for nome, codigo in list(normalized.items()) + variacoes_acumuladas:
        if nome not in seen:
            seen.add(nome)
            nomes.append(nome)
            codigos.append(codigo)

    write_parquet_to_data({COL_NOME: nomes, COL_CODIGO: codigos}, output_parquet_name)

    return AugmentStats(
        n_original=len(normalized),
        n_variacoes=len(variacoes_acumuladas),
        n_total=len(nomes),
        tipos_nao_mapeados=tipos_nao_mapeados,
    )

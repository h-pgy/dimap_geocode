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

TIPOS_LOGRADOURO_AUMENTADO_MANUAL = "tipos_logradouro_aumentado.json"
PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL = "nomes_logradouros.parquet"
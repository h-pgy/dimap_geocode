class ItbiCargaVaziaError(Exception):
    """Levantada quando não há nenhum ano parseado em disco: parquet vazio nunca sobrescreve
    o bom."""

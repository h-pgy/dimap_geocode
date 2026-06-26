from pydantic import BaseModel

class AugmentStats(BaseModel):
    n_original: int
    n_variacoes: int
    n_total: int
    tipos_nao_mapeados: list[str] = []
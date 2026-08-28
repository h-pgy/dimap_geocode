from pathlib import Path

from pydantic import BaseModel

from config.pontos_fundo import PontoFundo
from services.integrations.wms import WmsConnectionConfig


class OrtofotoConfig(BaseModel):
    pontos: dict[str, PontoFundo]  # o catálogo do §3, envelopado
    conexao: WmsConnectionConfig  # a config da integration, envelopada
    destino: Path
    camada: str
    metros_por_pixel: float
    largura_px: int
    altura_px: int
    crs_entrada: int
    crs_saida: int
    forcar: bool = False


class OrtofotoResultado(BaseModel):
    geradas: list[str]
    puladas: list[str]

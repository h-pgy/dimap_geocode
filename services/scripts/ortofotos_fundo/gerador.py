from io import BytesIO
from pathlib import Path

from PIL import Image

from config.pontos_fundo import PontoFundo
from services.integrations.wms import WmsFetcher, WmsMapRequest

from .contrato import OrtofotoConfig, OrtofotoResultado
from .enquadramento import enquadrar


class GeradorOrtofotosFundo:
    def __call__(
        self, config: OrtofotoConfig, *, verbose: bool = False, manual: bool = True
    ) -> OrtofotoResultado:
        return self.pipeline(config)

    def pipeline(self, config: OrtofotoConfig) -> OrtofotoResultado:
        geradas: list[str] = []
        puladas: list[str] = []
        for chave, ponto in config.pontos.items():
            destino = config.destino / f"{chave}.png"
            # A chave é o nome do arquivo: ponto novo no catálogo é o único que vai à rede.
            if destino.exists() and not config.forcar:
                puladas.append(chave)
                continue
            self._gravar(self._buscar(ponto, config), destino)
            geradas.append(chave)
        return OrtofotoResultado(geradas=geradas, puladas=puladas)

    def _buscar(self, ponto: PontoFundo, config: OrtofotoConfig) -> bytes:
        # raster=True escolhe o WMS de raster: a ortofoto não é servida pelo WMS geral do GeoSampa.
        requisicao = WmsMapRequest(
            layer=config.camada,
            bbox=enquadrar(ponto, config),
            crs=f"EPSG:{config.crs_saida}",
            width=config.largura_px,
            height=config.altura_px,
            raster=True,
            transparent=False,
            image_format="image/png",
        )
        return WmsFetcher(config.conexao)(requisicao).content

    def _gravar(self, bruto: bytes, destino: Path) -> None:
        # Cinza no disco, não no CSS: a lente descartaria os outros dois canais de qualquer jeito,
        # e o PNG colorido custa três vezes o mesmo pixel renderizado.
        imagem = Image.open(BytesIO(bruto)).convert("L")
        destino.parent.mkdir(parents=True, exist_ok=True)
        imagem.save(destino, format="PNG", optimize=True)

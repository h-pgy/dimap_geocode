from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image

from config.pontos_fundo import PontoFundo
from services.integrations.wms import (
    WmsConnectionError,
    WmsFetcher,
    WmsMapRequest,
    WmsTimeoutError,
)

from .contrato import OrtofotoConfig, OrtofotoResultado
from .enquadramento import enquadrar

SONDA_LADO_PX = 16
ERROS_DE_INDISPONIBILIDADE = (WmsConnectionError, WmsTimeoutError)


def _calado(mensagem: str) -> None:
    return None


class GeradorOrtofotosFundo:
    def __init__(self, avisar: Callable[[str], None] = _calado) -> None:
        self.avisar = avisar

    def __call__(
        self, config: OrtofotoConfig, *, verbose: bool = False, manual: bool = True
    ) -> OrtofotoResultado:
        return self.pipeline(config)

    def pipeline(self, config: OrtofotoConfig) -> OrtofotoResultado:
        faltantes = self._faltantes(config)
        geradas: list[str] = []
        indisponibilidade: str | None = None
        if faltantes:
            self.avisar(f"Baixando {len(faltantes)} ortofoto(s) de fundo do GeoSampa...")
            try:
                self._sondar(next(iter(faltantes.values())), config)
                for ordem, (chave, ponto) in enumerate(faltantes.items(), start=1):
                    self.avisar(f"[{ordem}/{len(faltantes)}] {chave}")
                    self._gravar(self._buscar(ponto, config), config.destino / f"{chave}.png")
                    geradas.append(chave)
            except ERROS_DE_INDISPONIBILIDADE as exc:
                indisponibilidade = str(exc)
        return OrtofotoResultado(
            geradas=geradas,
            puladas=[chave for chave in config.pontos if chave not in faltantes],
            pendentes=[chave for chave in faltantes if chave not in geradas],
            indisponibilidade=indisponibilidade,
        )

    def _faltantes(self, config: OrtofotoConfig) -> dict[str, PontoFundo]:
        # A chave é o nome do arquivo: ponto novo no catálogo é o único que vai à rede.
        return {
            chave: ponto
            for chave, ponto in config.pontos.items()
            if config.forcar or not (config.destino / f"{chave}.png").exists()
        }

    def _sondar(self, ponto: PontoFundo, config: OrtofotoConfig) -> None:
        # Mesma requisição da ortofoto, encolhida: responde se o GeoSampa está no ar sem custar
        # o recorte inteiro.
        sonda = config.model_copy(update={"largura_px": SONDA_LADO_PX, "altura_px": SONDA_LADO_PX})
        self._buscar(ponto, sonda)

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

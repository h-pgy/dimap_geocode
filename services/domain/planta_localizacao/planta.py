import operator
from collections.abc import Callable
from functools import reduce
from io import BytesIO

from PIL import Image as PILImage, ImageDraw

from services.domain.geometry import para_geos
from services.integrations.wms.models import BoundingBox, WmsImage, WmsMapRequest
from .models import (
    CamadaPlanta,
    EstiloGeometria,
    PlantaConfig,
    PlantaLocalizacao,
    PlantaLocalizacaoInput,
)

OrtofotoDoEnquadramento = Callable[[WmsMapRequest], WmsImage]
DPI = 200
LADO_PX_DE_REFERENCIA = 1600.0
ESPESSURA_MINIMA_PX = 2


def _com_folga(
    extent: tuple[float, float, float, float], folga: float
) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = extent
    return minx - folga, miny - folga, maxx + folga, maxy + folga


def _quadrado_centrado(
    minx: float, miny: float, maxx: float, maxy: float, crs: str
) -> BoundingBox:
    lado = max(maxx - minx, maxy - miny)
    centro_x = (minx + maxx) / 2
    centro_y = (miny + maxy) / 2
    metade = lado / 2
    return BoundingBox(
        minx=centro_x - metade,
        miny=centro_y - metade,
        maxx=centro_x + metade,
        maxy=centro_y + metade,
        crs=crs,
    )


def _hex_para_rgba(hex_cor: str, alfa: float) -> tuple[int, int, int, int]:
    canais = hex_cor.lstrip("#")
    vermelho = int(canais[0:2], 16)
    verde = int(canais[2:4], 16)
    azul = int(canais[4:6], 16)
    return vermelho, verde, azul, int(alfa * 255)


class GerarPlantaLocalizacao:
    def __init__(self, ortofoto: OrtofotoDoEnquadramento) -> None:
        self._ortofoto = ortofoto

    def __call__(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
        return self.pipeline(entrada)

    def pipeline(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
        enquadramento = self._enquadrar(entrada)
        # Erro do WMS sobe: certidão com planta falsa é pior que certidão não emitida.
        fundo = self._ortofoto(self._request(enquadramento, entrada.config))
        png = self._desenhar(fundo, enquadramento, entrada)
        return PlantaLocalizacao(png=png, enquadramento=enquadramento)

    def _enquadrar(self, entrada: PlantaLocalizacaoInput) -> BoundingBox:
        uniao = reduce(
            operator.or_,
            (
                para_geos(geometria, entrada.config.crs)
                for camada in entrada.camadas
                for geometria in camada.geometrias
            ),
        )
        minx, miny, maxx, maxy = _com_folga(uniao.extent, entrada.config.folga_m)
        return _quadrado_centrado(minx, miny, maxx, maxy, f"EPSG:{entrada.config.crs}")

    def _request(self, enquadramento: BoundingBox, config: PlantaConfig) -> WmsMapRequest:
        return WmsMapRequest(
            layer=config.camada_ortofoto,
            bbox=enquadramento,
            crs=enquadramento.crs,
            width=config.lado_px,
            height=config.lado_px,
            raster=True,
            transparent=False,
            image_format="image/png",
        )

    def _desenhar(
        self,
        fundo: WmsImage,
        enquadramento: BoundingBox,
        entrada: PlantaLocalizacaoInput,
    ) -> bytes:
        base = self._base(fundo, entrada.config.lado_px)
        sobreposicao = self._sobrepor(enquadramento, entrada)
        composta = PILImage.alpha_composite(base, sobreposicao).convert("RGB")
        saida = BytesIO()
        composta.save(saida, format="PNG")
        return saida.getvalue()

    def _base(self, fundo: WmsImage, lado: int) -> PILImage.Image:
        imagem = PILImage.open(BytesIO(fundo.content)).convert("RGBA")
        if imagem.size != (lado, lado):
            imagem = imagem.resize((lado, lado), PILImage.Resampling.LANCZOS)
        return imagem

    def _sobrepor(
        self, enquadramento: BoundingBox, entrada: PlantaLocalizacaoInput
    ) -> PILImage.Image:
        lado = entrada.config.lado_px
        sobreposicao = PILImage.new("RGBA", (lado, lado), (0, 0, 0, 0))
        pincel = ImageDraw.Draw(sobreposicao)
        # O contexto primeiro e o destaque por último, não a ordem declarada: é o que põe o objeto
        # do documento por cima dos vizinhos.
        ordenadas = sorted(
            entrada.camadas, key=lambda camada: camada.estilo == EstiloGeometria.DESTAQUE
        )
        for camada in ordenadas:
            self._plotar(pincel, camada, enquadramento, entrada.config)
        return sobreposicao

    def _plotar(
        self,
        pincel: ImageDraw.ImageDraw,
        camada: CamadaPlanta,
        enquadramento: BoundingBox,
        config: PlantaConfig,
    ) -> None:
        destaque = camada.estilo == EstiloGeometria.DESTAQUE
        paleta = config.paleta
        cor = paleta.cor_destaque if destaque else paleta.cor_contexto
        espessura_pt = (
            paleta.espessura_destaque_pt if destaque else paleta.espessura_contexto_pt
        )
        largura = self._largura_px(espessura_pt, config.lado_px)
        aneis = [
            [self._para_px(ponto, enquadramento, config.lado_px) for ponto in anel]
            for geometria in camada.geometrias
            for anel in geometria.coordinates
        ]
        if destaque and paleta.alfa_preenchimento_destaque > 0:
            preenchimento = _hex_para_rgba(cor, paleta.alfa_preenchimento_destaque)
            for anel in aneis:
                if len(anel) >= 3:
                    pincel.polygon(anel, fill=preenchimento)
        for anel in aneis:
            if len(anel) >= 2:
                pincel.line(anel, fill=cor, width=largura)

    def _largura_px(self, espessura_pt: float, lado_px: int) -> int:
        escala = (lado_px / LADO_PX_DE_REFERENCIA) * (DPI / 72.0)
        return max(ESPESSURA_MINIMA_PX, int(espessura_pt * escala))

    def _para_px(
        self, ponto: list[float], enquadramento: BoundingBox, lado: int
    ) -> tuple[float, float]:
        largura = enquadramento.maxx - enquadramento.minx
        altura = enquadramento.maxy - enquadramento.miny
        x = (ponto[0] - enquadramento.minx) / largura * lado
        y = (enquadramento.maxy - ponto[1]) / altura * lado
        return x, y

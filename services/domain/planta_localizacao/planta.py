from collections.abc import Callable
from io import BytesIO
from PIL import Image as PILImage, ImageDraw

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


def _com_folga(
    extent: tuple[float, float, float, float], folga: float
) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = extent
    return minx - folga, miny - folga, maxx + folga, maxy + folga


def _quadrado_centrado(
    minx: float, miny: float, maxx: float, maxy: float, crs: str
) -> BoundingBox:
    dx = maxx - minx
    dy = maxy - miny
    lado = max(dx, dy)
    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    metade = lado / 2
    return BoundingBox(
        minx=cx - metade,
        miny=cy - metade,
        maxx=cx + metade,
        maxy=cy + metade,
        crs=crs,
    )


def _hex_to_rgba(hex_cor: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    h = hex_cor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r, g, b, int(alpha * 255)


class GerarPlantaLocalizacao:
    def __init__(self, ortofoto: OrtofotoDoEnquadramento | None = None) -> None:
        self._ortofoto = ortofoto

    def __call__(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
        return self.pipeline(entrada)

    def pipeline(self, entrada: PlantaLocalizacaoInput) -> PlantaLocalizacao:
        enquadramento = self._enquadrar(entrada)
        fundo: WmsImage | None = None
        if self._ortofoto is not None:
            try:
                fundo = self._ortofoto(self._request(enquadramento, entrada.config))
            except Exception:
                fundo = None
        png = self._desenhar(fundo, enquadramento, entrada)
        return PlantaLocalizacao(png=png, enquadramento=enquadramento)

    def _enquadrar(self, entrada: PlantaLocalizacaoInput) -> BoundingBox:
        xs: list[float] = []
        ys: list[float] = []
        for camada in entrada.camadas:
            for geom in camada.geometrias:
                for anel in geom.coordinates:
                    for pt in anel:
                        xs.append(pt[0])
                        ys.append(pt[1])
        if not xs or not ys:
            minx, miny, maxx, maxy = 0.0, 0.0, 1.0, 1.0
        else:
            minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
        minx, miny, maxx, maxy = _com_folga((minx, miny, maxx, maxy), entrada.config.folga_m)
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
        fundo: WmsImage | None,
        enquadramento: BoundingBox,
        entrada: PlantaLocalizacaoInput,
    ) -> bytes:
        lado = entrada.config.lado_px
        conteudo_fundo: bytes | None = None
        if isinstance(fundo, bytes):
            conteudo_fundo = fundo
        elif hasattr(fundo, "content") and isinstance(fundo.content, bytes):
            conteudo_fundo = fundo.content
        elif hasattr(fundo, "bytes") and isinstance(fundo.bytes, bytes):
            conteudo_fundo = fundo.bytes

        if conteudo_fundo:
            try:
                img = PILImage.open(BytesIO(conteudo_fundo)).convert("RGBA")
                if img.size != (lado, lado):
                    img = img.resize((lado, lado), PILImage.Resampling.LANCZOS)
            except Exception:
                img = PILImage.new("RGBA", (lado, lado), (240, 243, 246, 255))
        else:
            img = PILImage.new("RGBA", (lado, lado), (240, 243, 246, 255))

        overlay = PILImage.new("RGBA", (lado, lado), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        dx = enquadramento.maxx - enquadramento.minx
        dy = enquadramento.maxy - enquadramento.miny
        if dx <= 0:
            dx = 1.0
        if dy <= 0:
            dy = 1.0

        def to_px(x: float, y: float) -> tuple[float, float]:
            px = (x - enquadramento.minx) / dx * lado
            py = (enquadramento.maxy - y) / dy * lado
            return px, py

        camadas_ordenadas = sorted(
            entrada.camadas, key=lambda c: c.estilo == EstiloGeometria.DESTAQUE
        )
        for camada in camadas_ordenadas:
            is_destaque = camada.estilo == EstiloGeometria.DESTAQUE
            cor_linha = (
                entrada.config.paleta.cor_destaque
                if is_destaque
                else entrada.config.paleta.cor_contexto
            )
            espessura_pt = (
                entrada.config.paleta.espessura_destaque_pt
                if is_destaque
                else entrada.config.paleta.espessura_contexto_pt
            )
            # Escala a espessura para a resolução da imagem em pixels
            fator_escala = (lado / 1600.0) * (DPI / 72.0)
            largura = max(2, int(espessura_pt * fator_escala))

            # Preenchimento semitransparente para destacar o polígono sobre a foto aérea
            if is_destaque and entrada.config.paleta.alfa_preenchimento_destaque > 0:
                cor_fill = _hex_to_rgba(
                    cor_linha, entrada.config.paleta.alfa_preenchimento_destaque
                )
                for geom in camada.geometrias:
                    for anel in geom.coordinates:
                        pts = [to_px(p[0], p[1]) for p in anel]
                        if len(pts) >= 3:
                            draw.polygon(pts, fill=cor_fill)

            for geom in camada.geometrias:
                for anel in geom.coordinates:
                    pts = [to_px(p[0], p[1]) for p in anel]
                    if len(pts) >= 2:
                        draw.line(pts, fill=cor_linha, width=largura)

        final_img = PILImage.alpha_composite(img, overlay).convert("RGB")
        saida = BytesIO()
        final_img.save(saida, format="PNG")
        return saida.getvalue()

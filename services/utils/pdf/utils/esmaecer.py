import re
from functools import partial
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# `fill:rgb(0%,65.1%,31.37%)` — a forma que os SVGs do projeto trazem.
COR_SVG = re.compile(r"(fill|stroke):rgb\(([\d.]+)%,([\d.]+)%,([\d.]+)%\)")
COR_NAO_SUPORTADA = re.compile(r"(?:fill|stroke):\s*(#[0-9a-fA-F]+|rgb\((?![\d.]+%))")


class EsmaecerSvgInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    caminho: Path
    forca: float


class EsmaecerSvgOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    caminho: Path
    cores_clareadas: int


class EsmaecerSvg:
    """Callable: clareia cada cor do SVG CONTRA O BRANCO do papel, no próprio arquivo.

    Clarear a cor, e não baixar a opacidade: alpha compõe a cada camada e mancha onde os traços se
    sobrepõem — ver Caveats da SPEC documentos_oficiais/001.
    """

    def __call__(self, pedido: EsmaecerSvgInput) -> EsmaecerSvgOutput:
        return self.pipeline(pedido)

    def pipeline(self, pedido: EsmaecerSvgInput) -> EsmaecerSvgOutput:
        original = pedido.caminho.read_text()
        self._recusar_cor_desconhecida(original)
        claro, trocas = COR_SVG.subn(partial(self._clarear, forca=pedido.forca), original)
        pedido.caminho.write_text(claro)
        return EsmaecerSvgOutput(caminho=pedido.caminho, cores_clareadas=trocas)

    def _clarear(self, achado: re.Match[str], forca: float) -> str:
        canais = [self._canal(float(achado.group(i)), forca) for i in (2, 3, 4)]
        return f"{achado.group(1)}:rgb({canais[0]}%,{canais[1]}%,{canais[2]}%)"

    def _canal(self, valor: float, forca: float) -> float:
        return round(valor + (100 - valor) * forca, 4)

    def _recusar_cor_desconhecida(self, svg: str) -> None:
        # Cor num formato que a regex não pega passaria intacta e sairia escura sob o texto — o
        # inverso do que este utilitário existe para garantir.
        if achados := set(COR_NAO_SUPORTADA.findall(svg)):
            raise ValueError(f"SVG com cor em formato não suportado: {sorted(achados)}")


esmaecer_svg = EsmaecerSvg()

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CorrecaoQr(StrEnum):
    """Quanto do símbolo pode ser perdido e ele ainda ser lido. O valor é a letra do padrão, que é
    o que a biblioteca recebe."""

    BAIXA = "L"
    MEDIA = "M"
    QUARTIL = "Q"
    MAXIMA = "H"


class QrCodeInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    conteudo: str = Field(min_length=1)
    # Documento oficial é dobrado, carimbado e digitalizado: o padrão é o nível que tolera 25% de
    # perda, e não o mínimo.
    correcao: CorrecaoQr = CorrecaoQr.QUARTIL
    # A zona de silêncio se mede em MÓDULOS, não em milímetros: ela é do símbolo, não da página.
    silencio_modulos: int = Field(default=4, ge=1)


class QrCodeSvg(BaseModel):
    """O símbolo pronto. `modulos` é o lado da matriz COM o silêncio — é ele que divide a largura
    impressa e diz quanto milímetro cada módulo recebe."""

    model_config = ConfigDict(frozen=True)

    svg: bytes
    modulos: int

from pydantic import BaseModel, ConfigDict

# Módulo à parte de `marcacao.py`: `MarcacaoConfig` depende de `conteudo.py` para os defaults
# institucionais, e `conteudo.py` depende do bloco `SeloDeFecho` para tipar `Bloco` — colocar estas
# duas classes em `marcacao.py` fecharia esse triângulo num import circular.


class QuadroSeloConfig(BaseModel):
    """Quanto um quadro do selo ocupa. Medida de papel, como a do timbre e a da marca d'água — cor e
    espessura do traço não entram aqui: são tema."""

    model_config = ConfigDict(frozen=True)

    largura_mm: float
    # O símbolo dentro do quadro, descontados a moldura e o respiro interno.
    largura_qr_mm: float
    respiro_interno_mm: float


class SeloConfig(BaseModel):
    """Os dois quadros são a mesma peça em duas medidas. O QR do compacto não desce de 20 mm: abaixo
    disso o módulo fica menor que o mínimo de impressão (`MODULO_MINIMO_MM`)."""

    model_config = ConfigDict(frozen=True)

    compacto: QuadroSeloConfig = QuadroSeloConfig(
        largura_mm=68.0,
        largura_qr_mm=20.0,
        respiro_interno_mm=2.0,
    )
    fecho: QuadroSeloConfig = QuadroSeloConfig(
        largura_mm=90.0,
        largura_qr_mm=35.0,
        respiro_interno_mm=6.0,
    )

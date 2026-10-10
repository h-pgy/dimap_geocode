from hashlib import sha256
from io import BytesIO

from pydantic import BaseModel, ConfigDict, model_validator

from services.utils.qr_code import QrCodeSvg

from .forma import VetorNomeado
from .vetor import carregar_vetor

# Abaixo disto o módulo some na impressão a laser e no scanner do protocolo.
MODULO_MINIMO_MM = 0.5


class QrCodePdfInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # O símbolo inteiro, não o conteúdo dele: gerar o QR é do utilitário, e recopiar conteúdo e
    # correção aqui seria a mesma declaração em dois lugares.
    simbolo: QrCodeSvg
    largura_mm: float

    @model_validator(mode="after")
    def _modulo_cabe_no_papel(self) -> "QrCodePdfInput":
        # Recusar aqui, e não na impressão: símbolo pequeno demais sai bonito no PDF e só falha no
        # celular de quem recebeu o documento.
        modulo_mm = self.largura_mm / self.simbolo.modulos
        if modulo_mm < MODULO_MINIMO_MM:
            raise ValueError(
                f"{self.largura_mm} mm deixam cada módulo com {modulo_mm:.2f} mm, abaixo do mínimo "
                f"de {MODULO_MINIMO_MM} mm: este símbolo precisa de ao menos "
                f"{self.simbolo.modulos * MODULO_MINIMO_MM:.1f} mm."
            )
        return self


class QrCodePdf:
    """Callable: símbolo → o vetor nomeado do QR. Especialização do caminho de imagem do motor — o
    SVG do QR entra pelo mesmo `carregar_vetor` do timbre e da marca d'água, e nada aqui redesenha
    nada."""

    def __call__(self, pedido: QrCodePdfInput) -> VetorNomeado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: QrCodePdfInput) -> VetorNomeado:
        return VetorNomeado(
            desenho=carregar_vetor(BytesIO(pedido.simbolo.svg), pedido.largura_mm),
            nome=self._nome(pedido),
        )

    def _nome(self, pedido: QrCodePdfInput) -> str:
        # O nome sai do que se desenha — os bytes do símbolo e a largura que os escala. Dois QRs de
        # conteúdos diferentes na mesma página ganham forms distintos, e o mesmo QR repetido em
        # toda página ganha o MESMO, sem ninguém batizar nada à mão.
        digest = sha256(pedido.simbolo.svg).hexdigest()[:12]
        return f"qr_{digest}_{int(pedido.largura_mm * 100)}"


qr_code_pdf = QrCodePdf()

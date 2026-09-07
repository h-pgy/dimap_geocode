import pytest
from pydantic import ValidationError

from services.utils.pdf import VetorNomeado, qr_code_pdf
from services.utils.pdf.qr_code import MODULO_MINIMO_MM, QrCodePdfInput
from services.utils.qr_code import QrCodeInput, gerar_qr_code

# ---------------------------------------------------------------------------
# Largura que deixa o módulo ilegível é recusada na construção
# ---------------------------------------------------------------------------


def test_largura_que_deixa_o_modulo_ilegivel_eh_recusada() -> None:
    simbolo = gerar_qr_code(QrCodeInput(conteudo="https://exemplo.sp.gov.br/verificar"))
    largura_minima = simbolo.modulos * MODULO_MINIMO_MM

    with pytest.raises(ValidationError):
        QrCodePdfInput(simbolo=simbolo, largura_mm=largura_minima - 0.01)

    no_limite = QrCodePdfInput(simbolo=simbolo, largura_mm=largura_minima)
    assert no_limite.largura_mm == largura_minima


# ---------------------------------------------------------------------------
# Identidade do form: conteúdo ou largura diferentes viram formas distintas
# ---------------------------------------------------------------------------


def _vetor(conteudo: str, largura_mm: float = 30.0) -> VetorNomeado:
    simbolo = gerar_qr_code(QrCodeInput(conteudo=conteudo))
    return qr_code_pdf(QrCodePdfInput(simbolo=simbolo, largura_mm=largura_mm))


def test_qrs_de_conteudos_diferentes_ganham_formas_distintas() -> None:
    a = _vetor("https://exemplo.sp.gov.br/a")
    b = _vetor("https://exemplo.sp.gov.br/b")
    a_de_novo = _vetor("https://exemplo.sp.gov.br/a")
    a_mais_largo = _vetor("https://exemplo.sp.gov.br/a", largura_mm=45.0)

    assert a.nome != b.nome
    assert a.nome == a_de_novo.nome
    assert a.nome != a_mais_largo.nome

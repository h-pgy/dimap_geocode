from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet

from services.utils.pdf.models import Grade
from services.utils.pdf.tabela import EstiloTabela
from services.utils.pdf.tabela.regras import FundoDoCabecalho, GradeDeLinhas, RegraTabela, Respiro

ESTILO_PARAGRAFO = getSampleStyleSheet()["Normal"]


def _estilo(*regras: RegraTabela) -> EstiloTabela:
    return EstiloTabela(celula=ESTILO_PARAGRAFO, cabecalho=ESTILO_PARAGRAFO, regras=regras)


# ---------------------------------------------------------------------------
# Composição: cada regra soma os comandos dela, sem afetar as demais
# ---------------------------------------------------------------------------


def test_estilo_soma_os_comandos_das_regras() -> None:
    fundo = FundoDoCabecalho(HexColor("#cccccc"))
    grade_de_linhas = GradeDeLinhas(HexColor("#000000"), espessura_pt=0.5)
    respiro = Respiro(horizontal_mm=2.0, vertical_mm=1.0)
    grade_com_cabecalho = Grade(colunas=2, linhas_cabecalho=1, linhas_corpo=3)
    grade_sem_cabecalho = Grade(colunas=2, linhas_cabecalho=0, linhas_corpo=3)

    so_fundo = _estilo(fundo)
    fundo_e_grade = _estilo(fundo, grade_de_linhas)
    com_respiro = _estilo(fundo, grade_de_linhas, respiro)

    comandos_fundo = so_fundo(grade_com_cabecalho).getCommands()
    comandos_fundo_e_grade = fundo_e_grade(grade_com_cabecalho).getCommands()
    comandos_com_respiro = com_respiro(grade_com_cabecalho).getCommands()

    assert comandos_fundo == list(fundo(grade_com_cabecalho))
    # Acrescentar uma regra preserva os comandos das que já estavam lá, e só soma os dela.
    assert comandos_fundo_e_grade == [*comandos_fundo, *grade_de_linhas(grade_com_cabecalho)]
    assert comandos_com_respiro == [*comandos_fundo_e_grade, *respiro(grade_com_cabecalho)]
    # Tabela sem cabeçalho não recebe comando de FundoDoCabecalho algum.
    assert so_fundo(grade_sem_cabecalho).getCommands() == []

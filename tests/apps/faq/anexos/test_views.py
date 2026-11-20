from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from docx import Document

from apps.cargos.models import CargoBase
from apps.faq.conteudo import gravar_faq
from apps.faq.models import Anexo as AnexoModel
from apps.faq.models import Faq as FaqModel
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.faq import Faq, Pergunta, Resposta, Situacao, Tema, Visibilidade
from services.utils.extracao_texto.deteccao import MENSAGEM_DOC

banco = pytest.mark.banco

CONTEUDO_ANEXO = b"%PDF-1.4 conteudo do anexo"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _perfil(rf: str, superusuario: bool = True) -> Perfil:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo FAQ", sigla="CFAQ")
    tipo = TipoUnidade.objects.create(
        nome=f"Divisão {rf}", nivel=10, pode_ser_raiz=True, nivel_minimo_titular=1
    )
    unidade = Unidade.objects.create(nome=f"Unidade {rf}", sigla=f"U-{rf}", tipo=tipo)
    return Perfil.objects.create(
        rf=rf,
        nome="Ana",
        sobrenome="Ramos",
        cargo_base=cargo,
        unidade=unidade,
        senha_provisoria=False,
        is_superuser=superusuario,
        is_staff=superusuario,
    )


def _anexo(perfil: Perfil) -> AnexoModel:
    return AnexoModel.objects.create(
        titulo="Manual",
        nome_arquivo="manual.pdf",
        tipo="pdf",
        arquivo=CONTEUDO_ANEXO,
        hash_conteudo="a" * 64,
        tamanho_bytes=len(CONTEUDO_ANEXO),
        texto="texto extraído do manual",
        origem_texto="camada_de_texto",
        enviado_por=perfil,
    )


def _faq_com_anexo(
    pergunta: str, anexo: AnexoModel, situacao: Situacao, visibilidade: Visibilidade
) -> int:
    return gravar_faq(
        Faq(
            pergunta=Pergunta(texto=pergunta),
            resposta=Resposta(markdown="Resposta.", anexos=[anexo.pk]),
            tema=Tema(nome="Certidões"),
            situacao=situacao,
            visibilidade=visibilidade,
        )
    )


def _docx() -> bytes:
    documento = Document()
    documento.add_paragraph(
        "Este manual orienta a emissão da certidão de lançamento do IPTU."
    )
    saida = BytesIO()
    documento.save(saida)
    return saida.getvalue()


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


LIGACOES = {
    "so_interna": [(Situacao.PUBLICADA, Visibilidade.INTERNA)],
    "interna_e_publica": [
        (Situacao.PUBLICADA, Visibilidade.INTERNA),
        (Situacao.PUBLICADA, Visibilidade.PUBLICA),
    ],
    "so_rascunho": [(Situacao.RASCUNHO, Visibilidade.PUBLICA)],
}


@banco
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("ligacao", "anonimo", "logado"),
    [
        ("so_interna", 404, 200),
        ("interna_e_publica", 200, 200),
        ("so_rascunho", 404, 404),
    ],
)
def test_download_segue_a_faq_mais_aberta(
    ligacao: str, anonimo: int, logado: int
) -> None:
    perfil = _perfil("720001", superusuario=False)
    anexo = _anexo(perfil)
    for indice, (situacao, visibilidade) in enumerate(LIGACOES[ligacao]):
        _faq_com_anexo(f"Pergunta número {indice}?", anexo, situacao, visibilidade)
    url = reverse("faq:anexo_baixar", args=[anexo.pk])
    cliente_logado = Client()
    cliente_logado.force_login(perfil)

    resposta_anonimo = Client().get(url)
    resposta_logado = cliente_logado.get(url)

    assert resposta_anonimo.status_code == anonimo
    assert resposta_logado.status_code == logado
    if logado == 200:
        assert resposta_logado.content == CONTEUDO_ANEXO
        assert resposta_logado["Content-Disposition"].startswith("attachment")


# ---------------------------------------------------------------------------
# Conferência ao escolher o arquivo
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_rota_de_conferencia_nao_grava() -> None:
    cliente = Client()
    cliente.force_login(_perfil("720002"))
    bom = SimpleUploadedFile("manual.docx", _docx())
    recusado = SimpleUploadedFile(
        "antigo.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + bytes(64)
    )

    resposta = cliente.post(
        reverse("faq:admin_anexo_conferir"), {"novos_anexos": [bom, recusado]}
    )

    assert resposta.status_code == 200
    conferencias = resposta.context["conferencias"]
    assert [c.nome_arquivo for c in conferencias] == ["manual.docx", "antigo.doc"]
    assert conferencias[0].eh_aceito
    assert conferencias[1].recusa == MENSAGEM_DOC
    html = resposta.content.decode()
    assert "manual.docx" in html
    assert MENSAGEM_DOC in html
    assert not AnexoModel.objects.exists()
    assert not FaqModel.objects.exists()


# ---------------------------------------------------------------------------
# Texto extraído
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_texto_extraido_so_para_superusuario() -> None:
    superusuario = _perfil("720003")
    comum = _perfil("720004", superusuario=False)
    anexo = _anexo(superusuario)
    url = reverse("faq:admin_anexo_texto", args=[anexo.pk])
    cliente_super = Client()
    cliente_super.force_login(superusuario)
    cliente_comum = Client()
    cliente_comum.force_login(comum)

    resposta_super = cliente_super.get(url)
    resposta_comum = cliente_comum.get(url)
    resposta_inexistente = cliente_super.get(
        reverse("faq:admin_anexo_texto", args=[anexo.pk + 1])
    )

    assert resposta_super.status_code == 200
    html = resposta_super.content.decode()
    assert "texto extraído do manual" in html
    assert "Camada de texto" in html
    assert resposta_comum.status_code == 403
    assert resposta_inexistente.status_code == 404

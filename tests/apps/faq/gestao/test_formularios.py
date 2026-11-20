from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from docx import Document

from apps.cargos.models import CargoBase
from apps.faq.anexos import recebimento
from apps.faq.conteudo import gravar_faq
from apps.faq.models import Anexo as AnexoModel
from apps.faq.models import Faq as FaqModel
from apps.faq.models import Tema as TemaModel
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.faq import Faq, Pergunta, Resposta, Tema
from services.utils.extracao_texto import ExtratorTexto, TextoExtraido, TipoDocumento
from services.utils.extracao_texto.deteccao import MENSAGEM_DOC

banco = pytest.mark.banco

TEXTO_DOCX = (
    "Este manual orienta a emissão da certidão de lançamento do IPTU pela DIMAP."
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _perfil(rf: str) -> Perfil:
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
        is_superuser=True,
        is_staff=True,
    )


def _cliente(perfil: Perfil) -> Client:
    cliente = Client()
    cliente.force_login(perfil)
    return cliente


def _tema() -> TemaModel:
    return TemaModel.objects.create(nome="Certidões", ordem=0)


def _docx(texto: str = TEXTO_DOCX) -> bytes:
    documento = Document()
    documento.add_paragraph(texto)
    saida = BytesIO()
    documento.save(saida)
    return saida.getvalue()


def _arquivo(nome: str, conteudo: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo)


def _post_faq(tema: TemaModel, pergunta: str, **extras: object) -> dict[str, object]:
    return {
        "pergunta": pergunta,
        "resposta_markdown": "Veja o manual anexo.",
        "tema": tema.pk,
        "situacao": "rascunho",
        "visibilidade": "publica",
        **extras,
    }


def _faq_gravada(pergunta: str) -> int:
    return gravar_faq(
        Faq(
            pergunta=Pergunta(texto=pergunta),
            resposta=Resposta(markdown="Resposta."),
            tema=Tema(nome="Certidões"),
        )
    )


class ExtratorContado(ExtratorTexto):
    chamadas = 0

    def pipeline(self, conteudo: bytes) -> tuple[TipoDocumento, TextoExtraido]:
        ExtratorContado.chamadas += 1
        return super().pipeline(conteudo)


# ---------------------------------------------------------------------------
# Anexos no salvar da FAQ
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_reenvio_do_mesmo_arquivo_reaproveita_o_anexo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ExtratorContado.chamadas = 0
    monkeypatch.setattr(recebimento, "ExtratorTexto", ExtratorContado)
    cliente = _cliente(_perfil("710001"))
    tema = _tema()
    conteudo = _docx()

    for pergunta in ("Como emito a certidão?", "Onde encontro o manual?"):
        resposta = cliente.post(
            reverse("faq:admin_nova"),
            _post_faq(tema, pergunta, novos_anexos=_arquivo("manual.docx", conteudo)),
        )
        assert resposta.status_code == 204

    anexo = AnexoModel.objects.get()
    assert anexo.faqs.count() == 2
    assert anexo.titulo == "manual"
    assert ExtratorContado.chamadas == 1


@banco
@pytest.mark.django_db
@pytest.mark.parametrize("caso", ["arquivo_recusado", "pergunta_ocupada"])
def test_salvar_recusado_nao_grava_nada(caso: str) -> None:
    cliente = _cliente(_perfil("710002"))
    tema = _tema()
    ocupada = "Como emito a certidão?"
    _faq_gravada(ocupada)
    faqs_antes = FaqModel.objects.count()
    if caso == "arquivo_recusado":
        dados = _post_faq(
            tema,
            "Uma pergunta ainda livre?",
            novos_anexos=_arquivo(
                "antigo.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + bytes(64)
            ),
        )
    else:
        dados = _post_faq(tema, ocupada, novos_anexos=_arquivo("manual.docx", _docx()))

    resposta = cliente.post(reverse("faq:admin_nova"), dados)

    assert resposta.status_code == 422
    assert not AnexoModel.objects.exists()
    assert FaqModel.objects.count() == faqs_antes
    if caso == "arquivo_recusado":
        recusa = resposta.context["recusa"]
        assert "novos_anexos" in recusa.realce
        assert f"antigo.doc: {MENSAGEM_DOC}" in recusa.mensagens


@banco
@pytest.mark.django_db
def test_anexos_ligam_e_desligam_ao_salvar_a_faq() -> None:
    cliente = _cliente(_perfil("710003"))
    tema = _tema()
    pergunta = "Como emito a certidão?"

    criada = cliente.post(
        reverse("faq:admin_nova"),
        _post_faq(tema, pergunta, novos_anexos=_arquivo("manual.docx", _docx())),
    )
    assert criada.status_code == 204
    registro = FaqModel.objects.get()
    anexo = AnexoModel.objects.get()
    assert list(registro.anexos.all()) == [anexo]

    reaberta = cliente.get(reverse("faq:admin_editar", args=[registro.pk]))
    marcados = reaberta.context["valores"].anexos_ids
    sem_mexer = cliente.post(
        reverse("faq:admin_editar", args=[registro.pk]),
        _post_faq(tema, pergunta, anexo=marcados),
    )
    assert sem_mexer.status_code == 204
    assert list(registro.anexos.all()) == [anexo]

    desmarcado = cliente.post(
        reverse("faq:admin_editar", args=[registro.pk]), _post_faq(tema, pergunta)
    )
    assert desmarcado.status_code == 204
    assert not registro.anexos.exists()
    assert AnexoModel.objects.filter(pk=anexo.pk).exists()

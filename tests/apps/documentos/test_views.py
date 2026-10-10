"""Testes de apps/documentos/views.py (SPEC documentos_oficiais/008): as quatro rotas da
conferência — a página do código, o upload de arquivo e a segunda via."""

from io import BytesIO
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from reportlab.pdfgen.canvas import Canvas

import pytest

from apps.cargos.models import CargoBase
from apps.documentos.acervo import guardar_documento
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.documento_selado import (
    AlvoDoAto,
    AutorDoAto,
    EnvelopeAto,
    gerar_codigo,
    montar_envelope,
)
from services.domain.documento_selado.constants import TAMANHO_MAXIMO_BYTES, TAMANHO_MAXIMO_MB
from services.domain.documento_selado.datas import por_extenso
from services.utils.assinatura import DocumentoSelado, SelarInput, selar_documento

banco = pytest.mark.banco

SEGREDO = settings.ASSINATURA_SEGREDO


def _pdf() -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 720, "Documento de teste")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _virar_byte(pdf: bytes, posicao: int) -> bytes:
    return pdf[:posicao] + bytes([pdf[posicao] ^ 0x01]) + pdf[posicao + 1 :]


def _autor(**overrides: Any) -> AutorDoAto:
    defaults: dict[str, Any] = {
        "nome": "Marina Salgado de Almeida",
        "unidade": "DIMAP-1",
        "cargo_base": "Analista de Ordenamento Territorial",
        "cargo_comissao": None,
    }
    return AutorDoAto(**(defaults | overrides))


def _ato(**overrides: Any) -> EnvelopeAto:
    defaults: dict[str, Any] = {
        "codigo": gerar_codigo(),
        "acao": "certidoes.lancamento",
        "operacao": "emissao",
        "autor": _autor(),
        "alvo": AlvoDoAto(tipo="lote", identificador="123.456.7890-1"),
        "emitido_em": timezone.localtime(),
        "campos_publicos": ("contribuinte",),
        "extras": {"contribuinte": "013.045.0021-8", "sigilo_interno": "não mostrar"},
    }
    return EnvelopeAto(**(defaults | overrides))


def _selar(ato: EnvelopeAto, **overrides: Any) -> DocumentoSelado:
    defaults: dict[str, Any] = {
        "pdf": _pdf(),
        "dados": montar_envelope(ato),
        "campos_publicos": ato.campos_publicos,
        "segredo": SEGREDO,
        "id_chave": "k1",
    }
    return selar_documento(SelarInput(**(defaults | overrides)))


def _emitir(**overrides: object) -> tuple[EnvelopeAto, DocumentoSelado]:
    ato = _ato(**overrides)
    selado = _selar(ato)
    guardar_documento(selado, ato, execucao=None)
    return ato, selado


def _tipo_unidade() -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome="Divisão Documentos", nivel=10, pode_ser_raiz=True, nivel_minimo_titular=1
    )


def _perfil(rf: str = "900001") -> Perfil:
    unidade = Unidade.objects.create(nome=f"Divisão {rf}", sigla=f"DIV{rf}", tipo=_tipo_unidade())
    cargo, _ = CargoBase.objects.get_or_create(
        nome="Analista de Ordenamento Territorial", defaults={"sigla": "AOT"}
    )
    return Perfil.objects.create_user(
        rf=rf, nome="Fulano", sobrenome="de Tal", password="segredo123",
        cargo_base=cargo, unidade=unidade,
    )


# ---------------------------------------------------------------------------
# A página do código mostra a ficha do ato — e nada fora dos campos públicos
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_conferencia_por_codigo_mostra_a_ficha_do_ato(client: Client) -> None:
    ato, _selado = _emitir()

    resposta = client.get(reverse("documentos:conferir", kwargs={"codigo": ato.codigo}))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert ato.autor.nome in html
    assert ato.autor.cargo_base in html
    assert ato.autor.unidade in html
    assert por_extenso(ato.emitido_em) in html
    assert "013.045.0021-8" in html
    assert "não mostrar" not in html
    assert "sigilo_interno" not in html


# ---------------------------------------------------------------------------
# Código inexistente: 404, sem distinguir "nunca existiu" de "não está mais lá"
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_codigo_inexistente_responde_nao_localizado(client: Client) -> None:
    resposta = client.get(reverse("documentos:conferir", kwargs={"codigo": "NAOEXISTEAB"}))

    assert resposta.status_code == 404
    assert "não localizado" in resposta.content.decode().lower()


# ---------------------------------------------------------------------------
# Arquivo íntegro e conhecido confere
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_arquivo_integro_e_conhecido_confere(client: Client) -> None:
    ato, selado = _emitir()

    resposta = client.post(
        reverse("documentos:conferir_arquivo"),
        {"arquivo": SimpleUploadedFile("doc.pdf", selado.pdf, content_type="application/pdf")},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert ato.codigo in html
    assert ato.autor.nome in html


# ---------------------------------------------------------------------------
# Arquivo alterado com código conhecido não confere, e oferece o original
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_arquivo_alterado_com_codigo_conhecido_nao_confere_e_oferece_original(
    client: Client,
) -> None:
    ato, selado = _emitir()
    # Bem depois do /Info, dentro do stream comprimido da página.
    posicao = selado.pdf.find(b"stream") + 30
    adulterado = _virar_byte(selado.pdf, posicao)

    resposta = client.post(
        reverse("documentos:conferir_arquivo"),
        {"arquivo": SimpleUploadedFile("doc.pdf", adulterado, content_type="application/pdf")},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert ato.autor.nome not in html
    assert reverse("documentos:segunda_via", kwargs={"codigo": ato.codigo}) in html


# ---------------------------------------------------------------------------
# A tela do código esconde o link do original de quem não está logado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tela_do_codigo_esconde_o_original_do_anonimo(client: Client) -> None:
    ato, _selado = _emitir()
    url_original = reverse("documentos:segunda_via", kwargs={"codigo": ato.codigo})

    anonimo = client.get(reverse("documentos:conferir", kwargs={"codigo": ato.codigo}))
    assert url_original not in anonimo.content.decode()

    client.force_login(_perfil())
    logado = client.get(reverse("documentos:conferir", kwargs={"codigo": ato.codigo}))
    assert url_original in logado.content.decode()


# ---------------------------------------------------------------------------
# A segunda via exige login e devolve os mesmos bytes guardados na emissão
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_segunda_via_devolve_os_mesmos_bytes_e_exige_login(client: Client) -> None:
    ato, selado = _emitir()
    url = reverse("documentos:segunda_via", kwargs={"codigo": ato.codigo})

    anonimo = client.get(url)
    assert anonimo.status_code == 302
    assert anonimo["Location"].startswith(str(settings.LOGIN_URL))

    client.force_login(_perfil())
    logado = client.get(url)
    assert logado.status_code == 200
    assert logado.content == selado.pdf


# ---------------------------------------------------------------------------
# Upload vazio ou acima do teto é recusado, com mensagem em português
# ---------------------------------------------------------------------------


def test_upload_vazio_ou_acima_do_limite_eh_recusado(client: Client) -> None:
    vazio = client.post(reverse("documentos:conferir_arquivo"), {})
    assert vazio.status_code == 422
    assert "Escolha o arquivo PDF a conferir." in vazio.content.decode()

    grande = SimpleUploadedFile(
        "grande.pdf", b"0" * (TAMANHO_MAXIMO_BYTES + 1), content_type="application/pdf"
    )
    resposta = client.post(reverse("documentos:conferir_arquivo"), {"arquivo": grande})
    assert resposta.status_code == 422
    assert f"{TAMANHO_MAXIMO_MB} MB" in resposta.content.decode()


# ---------------------------------------------------------------------------
# Filtro por_extenso converte UTC para o fuso local do ambiente
# ---------------------------------------------------------------------------


def test_filtro_por_extenso_converte_utc_para_fuso_local() -> None:
    from datetime import datetime
    from datetime import timezone as py_timezone

    from apps.documentos.templatetags.documentos import por_extenso as filtro_por_extenso

    # 14:37 UTC equivale a 11:37 no fuso America/Sao_Paulo (-03:00)
    momento_utc = datetime(2026, 9, 9, 14, 37, 0, tzinfo=py_timezone.utc)
    formatado = filtro_por_extenso(momento_utc)

    assert "11h37min" in formatado
    assert "9 de setembro de 2026" in formatado


# ---------------------------------------------------------------------------
# SPEC documentos_oficiais/010 — UX da validação de documento
# ---------------------------------------------------------------------------


def test_pagina_escolha_conferencia_mostra_dois_caminhos(client: Client) -> None:
    resposta = client.get(reverse("documentos:pagina"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Validar documento" in html
    assert "Tenho o documento em mãos" in html
    assert "Tenho o código em mãos" in html
    assert f'{reverse("documentos:pagina")}?via=documento' in html
    assert f'{reverse("documentos:pagina")}?via=codigo' in html


def test_pagina_conferencia_por_codigo_mostra_12_caixas_otp_sem_aviso_de_letras(
    client: Client,
) -> None:
    resposta = client.get(reverse("documentos:pagina"), {"via": "codigo"})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Digitar código" in html
    assert html.count('class="otp-caixa') == 12
    assert "Voltar" in html
    assert f'href="{reverse("documentos:pagina")}"' in html
    assert "não usa as letras" not in html
    assert "I, L, O e U" not in html


@banco
@pytest.mark.django_db
def test_conferencia_codigo_inexistente_devolve_mesmo_formulario_com_status_422_e_realce_erro(
    client: Client,
) -> None:
    resposta = client.post(
        reverse("documentos:pagina"),
        {"via": "codigo", "codigo": "ERRADO123456"},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "Código errado" in html
    assert "campo-realce-erro" in html
    assert "Digitar código" in html


@banco
@pytest.mark.django_db
def test_conferencia_codigo_com_letras_omitidas_submete_e_devolve_erro(
    client: Client,
) -> None:
    resposta = client.post(
        reverse("documentos:pagina"),
        {"via": "codigo", "codigo": "7K4M9I2XQUOB"},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "Código errado" in html
    assert "campo-realce-erro" in html


@banco
@pytest.mark.django_db
def test_conferencia_codigo_existente_redireciona_para_tela_do_documento(
    client: Client,
) -> None:
    ato, _selado = _emitir()

    resposta = client.post(
        reverse("documentos:pagina"),
        {"via": "codigo", "codigo": ato.codigo},
    )

    assert resposta.status_code == 302
    assert resposta["Location"] == reverse("documentos:conferir", kwargs={"codigo": ato.codigo})


def test_pagina_upload_mostra_formulario_com_botao_oculto_e_link_voltar(
    client: Client,
) -> None:
    resposta = client.get(reverse("documentos:pagina"), {"via": "documento"})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Conferir documento" in html
    assert "data-btn-conferir" in html
    assert "hidden" in html
    assert "Voltar" in html
    assert f'href="{reverse("documentos:pagina")}"' in html


def test_carregar_novo_documento_devolve_formulario_limpo(client: Client) -> None:
    resposta = client.get(reverse("documentos:conferir_arquivo"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "data-arquivo-input" in html
    assert "data-btn-conferir" in html
    assert "hidden" in html

    resposta_via = client.get(reverse("documentos:pagina"), {"via": "form_upload"})
    assert resposta_via.status_code == 200
    assert "data-arquivo-input" in resposta_via.content.decode()


@banco
@pytest.mark.django_db
def test_resultado_conferencia_arquivo_inclui_botao_carregar_novo_documento(
    client: Client,
) -> None:
    ato, selado = _emitir()

    resposta = client.post(
        reverse("documentos:conferir_arquivo"),
        {"arquivo": SimpleUploadedFile("doc.pdf", selado.pdf, content_type="application/pdf")},
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Carregar novo documento" in html
    assert 'hx-target="#area-upload"' in html



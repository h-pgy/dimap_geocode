"""Área de edição da FAQ (SPEC faq/002): portão de superusuário, última edição, FAQ do sistema,
formulário, publicação, exclusão lógica e relacionadas inertes."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from apps.cargos.models import CargoBase
from apps.faq.conteudo import gravar_faq
from apps.faq.models import Faq as FaqModel
from apps.faq.models import Pergunta as PerguntaModel
from apps.faq.models import Tema as TemaModel
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.faq import (
    Faq,
    Pergunta,
    Resposta,
    Situacao,
    Tema,
)

banco = pytest.mark.banco

SENHA = "SenhaForte123!"
MARKDOWN = (
    "Texto com **negrito** e ~~riscado~~.\n\n"
    "### Como emitir\n\n"
    "1. Localize o imóvel.\n"
    "2. Abra **Ações**.\n\n"
    "- [ ] tarefa\n\n"
    "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
    "Veja [a busca](/).\n"
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _unidade(rf: str) -> Unidade:
    tipo = TipoUnidade.objects.create(
        nome=f"Divisão FAQ {rf}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    return Unidade.objects.create(
        nome=f"Unidade FAQ {rf}", sigla=f"FAQ-{rf}", tipo=tipo
    )


def _perfil(rf: str, superusuario: bool = True, nome: str = "Ana") -> Perfil:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo FAQ", sigla="CFAQ")
    perfil = Perfil(
        rf=rf,
        nome=nome,
        sobrenome="Ramos",
        cargo_base=cargo,
        unidade=_unidade(rf),
        senha_provisoria=False,
        is_superuser=superusuario,
        is_staff=superusuario,
    )
    perfil.set_password(SENHA)
    perfil.save()
    return perfil


def _faq(
    pergunta: str,
    autor: Perfil | None = None,
    situacao: Situacao = Situacao.RASCUNHO,
    variacoes: list[str] | None = None,
    relacionadas: list[int] | None = None,
) -> int:
    return gravar_faq(
        Faq(
            pergunta=Pergunta(texto=pergunta),
            variacoes=[Pergunta(texto=v) for v in variacoes or []],
            resposta=Resposta(markdown=f"Resposta de {pergunta}"),
            tema=Tema(nome="Certidões"),
            situacao=situacao,
            autor_id=autor.pk if autor is not None else None,
            relacionadas=relacionadas or [],
        ),
    )


def _formulario(registro: FaqModel, **overrides: object) -> dict[str, object]:
    """O POST que o formulário de edição mandaria, sem tocar em nada."""
    perguntas = sorted(registro.perguntas.all(), key=lambda p: p.pk)
    dados: dict[str, object] = {
        "pergunta": next(p.texto for p in perguntas if p.eh_principal),
        "resposta_markdown": registro.resposta_markdown,
        "tema": registro.tema_id,
        "situacao": registro.situacao,
        "visibilidade": registro.visibilidade,
    }
    for indice, variacao in enumerate(p for p in perguntas if not p.eh_principal):
        dados[f"variacao-{indice}"] = variacao.texto
    dados.update(overrides)
    return dados


def _controle(html: str, nome: str) -> str:
    """A tag do controle chamado `nome`: é nela que o realce do erro precisa estar."""
    achado = re.search(
        rf'<(?:input|select|textarea)\b[^>]*name="{re.escape(nome)}"[^>]*>', html
    )
    assert achado is not None, f"controle {nome!r} não está no HTML"
    return achado.group(0)


def _radio_marcado(html: str, nome: str) -> str:
    marcados = [
        tag
        for tag in re.findall(rf'<input\b[^>]*name="{nome}"[^>]*>', html)
        if re.search(r"\schecked\b", tag)
    ]
    assert len(marcados) == 1, marcados
    valor = re.search(r'value="([^"]*)"', marcados[0])
    assert valor is not None
    return valor.group(1)


def _cliente(perfil: Perfil) -> Client:
    cliente = Client()
    cliente.force_login(perfil)
    return cliente


# ---------------------------------------------------------------------------
# Portão
# ---------------------------------------------------------------------------


ROTAS_GET = [
    ("faq:admin_lista", False),
    ("faq:admin_corpo", False),
    ("faq:admin_nova", False),
    ("faq:admin_editar", True),
    ("faq:admin_excluir", True),
    ("faq:admin_palavras_chave_coluna", False),
    ("faq:admin_palavra_chave_nova", False),
    ("faq:admin_tema_novo", False),
]
ROTAS_POST = [
    ("faq:admin_situacao", True),
    ("faq:admin_restaurar", True),
]


@banco
@pytest.mark.django_db
@pytest.mark.parametrize(("rota", "com_faq"), ROTAS_GET + ROTAS_POST)
def test_rotas_de_edicao_exigem_superusuario(
    client: Client, rota: str, com_faq: bool
) -> None:
    faq_id = _faq("Como emito a certidão?")
    url = reverse(rota, args=[faq_id] if com_faq else [])
    pedir = client.post if (rota, com_faq) in ROTAS_POST else client.get

    anonimo = pedir(url)
    assert anonimo.status_code == 302
    assert anonimo["Location"].startswith(reverse("autenticacao:login"))

    client.force_login(_perfil("700001", superusuario=False))
    assert pedir(url).status_code == 403


@banco
@pytest.mark.django_db
def test_painel_mostra_grupo_faq_so_ao_superusuario() -> None:
    admin = _cliente(_perfil("700002")).get(reverse("painel:painel")).content.decode()
    comum = (
        _cliente(_perfil("700003", superusuario=False))
        .get(reverse("painel:painel"))
        .content.decode()
    )

    assert "Lista de FAQs" in admin
    assert "Nova FAQ" in admin
    assert "Lista de FAQs" not in comum
    assert "Nova FAQ" not in comum
    assert "Administração do Sistema" in comum


# ---------------------------------------------------------------------------
# Última edição
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_admin_edita_faq_de_outro_e_fica_como_ultimo_editor() -> None:
    a = _perfil("700010", nome="Ana")
    b = _perfil("700011", nome="Bruno")
    faq_id = _faq("Como emito a certidão?", autor=a)
    criada = FaqModel.objects.get(pk=faq_id)
    assert criada.editado_por_id == a.pk
    assert criada.editado_em is not None

    cliente_b = _cliente(b)
    assert (
        "Como emito a certidão?"
        in cliente_b.get(reverse("faq:admin_corpo")).content.decode()
    )

    antes = criada.editado_em
    resposta = cliente_b.post(
        reverse("faq:admin_editar", args=[faq_id]),
        _formulario(criada, resposta_markdown="Resposta nova."),
    )
    assert resposta.status_code in (200, 204)
    editada = FaqModel.objects.get(pk=faq_id)
    assert editada.autor_id == a.pk
    assert editada.editado_por_id == b.pk
    assert editada.editado_em is not None
    assert editada.editado_em > antes
    assert editada.resposta_markdown == "Resposta nova."

    for gesto, url, dados in [
        (
            "publicar",
            reverse("faq:admin_situacao", args=[faq_id]),
            {"situacao": "publicada"},
        ),
        ("excluir", reverse("faq:admin_excluir", args=[faq_id]), {}),
        ("restaurar", reverse("faq:admin_restaurar", args=[faq_id]), {}),
    ]:
        FaqModel.objects.filter(pk=faq_id).update(editado_por=a)
        assert _cliente(b).post(url, dados).status_code in (200, 204), gesto
        assert FaqModel.objects.get(pk=faq_id).editado_por_id == b.pk, gesto

    linha = cliente_b.get(reverse("faq:admin_corpo")).content.decode()
    assert "Bruno" in linha
    assert FaqModel.objects.get(pk=faq_id).editado_em.strftime("%d/%m/%Y") in linha  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# FAQ do sistema
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_faq_do_sistema_eh_editavel_e_despublicavel_mas_nao_excluivel() -> None:
    faq_id = _faq("Como uso o sistema?", autor=None, situacao=Situacao.PUBLICADA)
    a = _cliente(_perfil("700020"))
    b = _cliente(_perfil("700021"))

    registro = FaqModel.objects.get(pk=faq_id)
    assert a.post(
        reverse("faq:admin_editar", args=[faq_id]),
        _formulario(registro, resposta_markdown="Editada por A."),
    ).status_code in (200, 204)
    assert b.post(
        reverse("faq:admin_situacao", args=[faq_id]), {"situacao": "rascunho"}
    ).status_code in (200, 204)

    registro = FaqModel.objects.get(pk=faq_id)
    assert registro.autor_id is None
    assert registro.situacao == Situacao.RASCUNHO
    assert registro.resposta_markdown == "Editada por A."

    corpo = a.get(reverse("faq:admin_corpo")).content.decode()
    assert reverse("faq:admin_excluir", args=[faq_id]) not in corpo

    editado_em = registro.editado_em
    assert b.post(reverse("faq:admin_excluir", args=[faq_id])).status_code == 403
    intacta = FaqModel.objects.get(pk=faq_id)
    assert intacta.situacao == Situacao.RASCUNHO
    assert intacta.editado_em == editado_em
    assert all(p.chave for p in intacta.perguntas.all())


# ---------------------------------------------------------------------------
# Formulário
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
@pytest.mark.parametrize(
    "caso", ["variacao_ocupada", "subtema_sob_subtema", "palavra_no_quarto_nivel"]
)
def test_formulario_devolve_erro_no_campo(caso: str) -> None:
    cliente = _cliente(_perfil("700030"))

    if caso == "variacao_ocupada":
        _faq("Como emitir a certidão?")
        faq_id = _faq("Como trocar a senha?")
        registro = FaqModel.objects.get(pk=faq_id)
        markdown_antes = registro.resposta_markdown
        resposta = cliente.post(
            reverse("faq:admin_editar", args=[faq_id]),
            _formulario(
                registro,
                **{
                    "variacao-7": "Como emitir a certidão?",
                    "resposta_markdown": "Mudou.",
                },
            ),
        )
        controle = "variacao-7"
        assert FaqModel.objects.get(pk=faq_id).resposta_markdown == markdown_antes
        assert PerguntaModel.objects.filter(faq_id=faq_id).count() == 1
    elif caso == "subtema_sob_subtema":
        raiz = TemaModel.objects.create(nome="Certidões")
        sub = TemaModel.objects.create(nome="Lançamento", pai=raiz)
        resposta = cliente.post(
            reverse("faq:admin_tema_novo"), {"nome": "Segunda via", "pai": sub.pk}
        )
        controle = "pai"
        assert not TemaModel.objects.filter(nome="Segunda via").exists()
    else:
        from apps.faq.models import PalavraChave as PalavraChaveModel

        iptu = PalavraChaveModel.objects.create(nome="IPTU")
        certidao = PalavraChaveModel.objects.create(nome="Certidão", pai=iptu)
        lancamento = PalavraChaveModel.objects.create(nome="Lançamento", pai=certidao)
        resposta = cliente.post(
            reverse("faq:admin_palavra_chave_nova"),
            {"nome": "Segunda via", "pai": lancamento.pk},
        )
        controle = "pai"
        assert not PalavraChaveModel.objects.filter(nome="Segunda via").exists()

    html = resposta.content.decode()
    assert resposta.status_code == 422
    assert "campo-realce-erro" in _controle(html, controle)
    assert any(
        frase in html
        for frase in (
            "já é respondida por outra FAQ",
            "Subtema não pode ter subtema",
            "no máximo três níveis",
        )
    )


@banco
@pytest.mark.django_db
def test_promover_variacao_a_pergunta_principal() -> None:
    cliente = _cliente(_perfil("700040"))
    faq_id = _faq("Como emito a certidão?", variacoes=["Como tiro a certidão?"])
    registro = FaqModel.objects.get(pk=faq_id)

    resposta = cliente.post(
        reverse("faq:admin_editar", args=[faq_id]),
        _formulario(
            registro,
            pergunta="Como tiro a certidão?",
            **{"variacao-0": "Como emito a certidão?"},
        ),
    )

    assert resposta.status_code in (200, 204)
    perguntas = {
        p.texto: p.eh_principal for p in PerguntaModel.objects.filter(faq_id=faq_id)
    }
    assert perguntas == {"Como tiro a certidão?": True, "Como emito a certidão?": False}


# ---------------------------------------------------------------------------
# Publicação
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_faq_nova_nasce_rascunho_e_publica_e_publicacao_muda_a_pagina() -> None:
    admin = _perfil("700050")
    cliente = _cliente(admin)
    tema = TemaModel.objects.create(nome="Acesso")

    formulario = cliente.get(reverse("faq:admin_nova")).content.decode()
    assert _radio_marcado(formulario, "situacao") == "rascunho"
    assert _radio_marcado(formulario, "visibilidade") == "publica"

    resposta = cliente.post(
        reverse("faq:admin_nova"),
        {
            "pergunta": "Como peço acesso ao sistema?",
            "resposta_markdown": "Peça ao chefe.",
            "tema": tema.pk,
        },
    )
    assert resposta.status_code in (200, 204)
    registro = FaqModel.objects.get()
    assert registro.situacao == Situacao.RASCUNHO
    assert registro.visibilidade == "publica"
    assert registro.autor_id == admin.pk

    anonimo = Client()
    assert (
        "Como peço acesso ao sistema?"
        not in anonimo.get(reverse("faq:pagina")).content.decode()
    )

    cliente.post(
        reverse("faq:admin_situacao", args=[registro.pk]), {"situacao": "publicada"}
    )
    assert (
        "Como peço acesso ao sistema?"
        in anonimo.get(reverse("faq:pagina")).content.decode()
    )

    cliente.post(
        reverse("faq:admin_situacao", args=[registro.pk]), {"situacao": "rascunho"}
    )
    assert (
        "Como peço acesso ao sistema?"
        not in anonimo.get(reverse("faq:pagina")).content.decode()
    )


@banco
@pytest.mark.django_db
def test_markdown_editado_volta_identico() -> None:
    cliente = _cliente(_perfil("700060"))
    faq_id = _faq("Como emito a certidão?")
    registro = FaqModel.objects.get(pk=faq_id)

    cliente.post(
        reverse("faq:admin_editar", args=[faq_id]),
        _formulario(registro, resposta_markdown=MARKDOWN),
    )

    assert FaqModel.objects.get(pk=faq_id).resposta_markdown == MARKDOWN
    html = cliente.get(reverse("faq:admin_editar", args=[faq_id])).content.decode()
    achado = re.search(
        r'<textarea\b[^>]*name="resposta_markdown"[^>]*>(.*?)</textarea>', html, re.S
    )
    assert achado is not None
    from html import unescape

    # O Django põe uma quebra depois da tag de abertura do textarea; o navegador a descarta.
    assert unescape(achado.group(1)).removeprefix("\n") == MARKDOWN


# ---------------------------------------------------------------------------
# Exclusão lógica
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_excluir_eh_logico_e_restaurar_volta_rascunho() -> None:
    admin = _perfil("700070")
    cliente = _cliente(admin)
    livre = _faq("Como troco a senha?", autor=admin, situacao=Situacao.PUBLICADA)
    ocupada = _faq("Como emito a certidão?", autor=admin, situacao=Situacao.PUBLICADA)

    for faq_id in (livre, ocupada):
        assert cliente.post(
            reverse("faq:admin_excluir", args=[faq_id])
        ).status_code in (200, 204)

    pagina = Client().get(reverse("faq:pagina")).content.decode()
    assert "Como troco a senha?" not in pagina
    assert (
        "Como troco a senha?"
        not in cliente.get(reverse("faq:admin_corpo")).content.decode()
    )
    assert FaqModel.objects.get(pk=livre).situacao == Situacao.EXCLUIDA

    reaproveitou = _faq("Como emito a certidão?")

    assert cliente.post(reverse("faq:admin_restaurar", args=[livre])).status_code in (
        200,
        204,
    )
    restaurada = FaqModel.objects.get(pk=livre)
    assert restaurada.situacao == Situacao.RASCUNHO
    assert all(p.chave for p in restaurada.perguntas.all())

    recusa = cliente.post(reverse("faq:admin_restaurar", args=[ocupada]))
    assert recusa.status_code == 409
    assert "Como emito a certidão?" in recusa.content.decode()
    assert FaqModel.objects.get(pk=ocupada).situacao == Situacao.EXCLUIDA
    assert (
        PerguntaModel.objects.get(
            chave__isnull=False, texto="Como emito a certidão?"
        ).faq_id
        == reaproveitou
    )


@banco
@pytest.mark.django_db
def test_relacionada_excluida_fica_inerte_e_volta_na_restauracao() -> None:
    admin = _perfil("700080")
    cliente = _cliente(admin)
    b = _faq("Pergunta da FAQ B?", autor=admin, situacao=Situacao.PUBLICADA)
    a = _faq(
        "Pergunta da FAQ A?", autor=admin, situacao=Situacao.PUBLICADA, relacionadas=[b]
    )

    cliente.post(reverse("faq:admin_excluir", args=[b]))

    pagina = Client().get(reverse("faq:pagina")).content.decode()
    assert "Pergunta da FAQ A?" in pagina
    assert "Pergunta da FAQ B?" not in pagina

    formulario = cliente.get(reverse("faq:admin_editar", args=[a])).content.decode()
    assert "chip-inerte" in formulario
    assert f'name="relacionada" value="{b}"' not in formulario
    assert reverse("faq:admin_editar", args=[b]) not in formulario

    registro = FaqModel.objects.get(pk=a)
    cliente.post(reverse("faq:admin_editar", args=[a]), _formulario(registro))
    assert set(
        FaqModel.objects.get(pk=a).relacionadas.values_list("pk", flat=True)
    ) == {b}

    cliente.post(reverse("faq:admin_restaurar", args=[b]))
    cliente.post(reverse("faq:admin_situacao", args=[b]), {"situacao": "publicada"})
    pagina = Client().get(reverse("faq:pagina")).content.decode()
    item_a = pagina[pagina.index(f'id="faq-{a}"') : pagina.index(f'id="faq-{b}"')]
    assert f'href="#faq-{b}"' in item_a

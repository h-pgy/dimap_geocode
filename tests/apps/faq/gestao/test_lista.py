"""Lista de FAQs da área de edição (SPEC faq/002): a tabela de vidro filtra, ordena e revela as
excluídas."""

import re
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cargos.models import CargoBase
from apps.faq.conteudo import gravar_faq
from apps.faq.models import Faq as FaqModel
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.faq import Faq, Pergunta, Resposta, Tema

banco = pytest.mark.banco


def _perfil(rf: str) -> Perfil:
    tipo = TipoUnidade.objects.create(
        nome=f"Divisão Lista {rf}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade = Unidade.objects.create(
        nome=f"Unidade Lista {rf}", sigla=f"LST-{rf}", tipo=tipo
    )
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Lista", sigla="CLST")
    perfil = Perfil(
        rf=rf,
        nome="Ana",
        sobrenome="Ramos",
        cargo_base=cargo,
        unidade=unidade,
        senha_provisoria=False,
        is_superuser=True,
        is_staff=True,
    )
    perfil.set_password("SenhaForte123!")
    perfil.save()
    return perfil


def _faq(pergunta: str, tema: Tema, autor: Perfil | None = None) -> int:
    return gravar_faq(
        Faq(
            pergunta=Pergunta(texto=pergunta),
            resposta=Resposta(markdown="Resposta."),
            tema=tema,
            autor_id=autor.pk if autor is not None else None,
        ),
    )


def _perguntas(html: str) -> list[str]:
    return re.findall(r'data-pergunta="([^"]+)"', html)


@banco
@pytest.mark.django_db
def test_lista_de_faqs_filtra_ordena_e_revela_excluidas() -> None:
    admin = _perfil("710001")
    cliente = Client()
    cliente.force_login(admin)
    busca = Tema(nome="Busca")
    certidoes = Tema(nome="Certidões")

    agora = timezone.now()
    banana = _faq("Banana pergunta?", busca, autor=admin)
    abacate = _faq("Abacate pergunta?", certidoes, autor=admin)
    da_seed = _faq("Cereja pergunta?", busca, autor=None)
    excluida = _faq("Damasco pergunta?", busca, autor=admin)
    FaqModel.objects.filter(pk=banana).update(editado_em=agora - timedelta(days=1))
    FaqModel.objects.filter(pk=abacate).update(editado_em=agora)
    FaqModel.objects.filter(pk=da_seed).update(editado_por=None, editado_em=None)
    cliente.post(reverse("faq:admin_excluir", args=[excluida]))

    url = reverse("faq:admin_corpo")

    filtrada = cliente.get(url, {"tema": "certid"}).content.decode()
    assert _perguntas(filtrada) == ["Abacate pergunta?"]

    por_pergunta = cliente.get(url, {"ordenar_por": "pergunta"}).content.decode()
    assert _perguntas(por_pergunta) == [
        "Abacate pergunta?",
        "Banana pergunta?",
        "Cereja pergunta?",
    ]

    por_data = cliente.get(url, {"ordenar_por": "editado_em"}).content.decode()
    assert _perguntas(por_data) == [
        "Banana pergunta?",
        "Abacate pergunta?",
        "Cereja pergunta?",
    ]
    por_data_desc = cliente.get(
        url, {"ordenar_por": "editado_em", "descendente": "1"}
    ).content.decode()
    assert _perguntas(por_data_desc) == [
        "Abacate pergunta?",
        "Banana pergunta?",
        "Cereja pergunta?",
    ]

    assert "Damasco pergunta?" not in _perguntas(cliente.get(url).content.decode())
    com_excluidas = cliente.get(url, {"excluidas": "1"}).content.decode()
    assert "Damasco pergunta?" in _perguntas(com_excluidas)
    linha_excluida = re.search(
        r'<tr[^>]*data-pergunta="Damasco pergunta\?"[^>]*>.*?</tr>', com_excluidas, re.S
    )
    assert linha_excluida is not None
    assert "linha-extinta" in linha_excluida.group(0)
    assert reverse("faq:admin_restaurar", args=[excluida]) in linha_excluida.group(0)

    assert reverse("faq:admin_excluir", args=[da_seed]) not in com_excluidas
    assert reverse("faq:admin_excluir", args=[banana]) in com_excluidas

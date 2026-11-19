"""Árvore horizontal de palavras-chave (SPEC faq/002): a coluna das filhas e a marcação que
sobrevive à troca de ramo."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from apps.cargos.models import CargoBase
from apps.faq.models import Faq as FaqModel
from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Tema as TemaModel
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco


def _perfil() -> Perfil:
    tipo = TipoUnidade.objects.create(
        nome="Divisão Árvore",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade = Unidade.objects.create(nome="Unidade Árvore", sigla="ARV", tipo=tipo)
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Árvore", sigla="CARV")
    perfil = Perfil(
        rf="720001",
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


def _palavra(nome: str, pai: PalavraChaveModel | None = None) -> PalavraChaveModel:
    return PalavraChaveModel.objects.create(nome=nome, pai=pai)


def _coluna(html: str, pai_id: int | None) -> str:
    """Só a coluna pedida: a resposta também traz, fora de banda, a coluna do pai com o ramo aberto."""
    marca = f'data-pai="{pai_id if pai_id is not None else ""}"'
    inicio = html.index(marca)
    fim = html.find("data-pai=", inicio + len(marca))
    return html[inicio : fim if fim != -1 else len(html)]


def _nomes(coluna: str) -> list[str]:
    return re.findall(r'data-palavra-nome="([^"]+)"', coluna)


@banco
@pytest.mark.django_db
def test_arvore_de_palavras_chave_abre_filhas_e_preserva_marcadas() -> None:
    cliente = Client()
    cliente.force_login(_perfil())
    iptu = _palavra("IPTU")
    itbi = _palavra("ITBI")
    isencao = _palavra("Isenção", iptu)
    certidao = _palavra("Certidão", iptu)
    desconto = _palavra("Desconto", iptu)
    base = _palavra("Base de cálculo", itbi)
    url = reverse("faq:admin_palavras_chave_coluna")

    raizes = cliente.get(url).content.decode()
    assert _nomes(_coluna(raizes, None)) == ["IPTU", "ITBI"]

    filhas = _coluna(
        cliente.get(
            url, {"pai": str(iptu.pk), "palavra_chave": [str(desconto.pk)]}
        ).content.decode(),
        iptu.pk,
    )
    assert _nomes(filhas) == ["Certidão", "Desconto", "Isenção"]
    marcadas = re.findall(r'<input\b[^>]*value="(\d+)"[^>]*\schecked\b[^>]*>', filhas)
    assert marcadas == [str(desconto.pk)]

    # Marcar num ramo, abrir outro e marcar outra: a lista de marcadas, e não a coluna, leva os ids.
    lista = cliente.get(
        reverse("faq:admin_palavras_chave_marcadas"),
        {"alternar": certidao.pk},
    ).content.decode()
    ids = re.findall(r'name="palavra_chave" value="(\d+)"', lista)
    cliente.get(url, {"pai": str(itbi.pk), "palavra_chave": ids})
    lista = cliente.get(
        reverse("faq:admin_palavras_chave_marcadas"),
        {"alternar": str(base.pk), "palavra_chave": ids},
    ).content.decode()
    ids = re.findall(r'name="palavra_chave" value="(\d+)"', lista)
    assert sorted(ids) == sorted([str(certidao.pk), str(base.pk)])

    tema = TemaModel.objects.create(nome="Impostos")
    cliente.post(
        reverse("faq:admin_nova"),
        {
            "pergunta": "Como emito a certidão do imposto?",
            "resposta_markdown": "Pelo sistema.",
            "tema": tema.pk,
            "palavra_chave": ids,
        },
    )
    faq = FaqModel.objects.get()
    assert set(faq.palavras_chave.values_list("pk", flat=True)) == {
        certidao.pk,
        base.pk,
    }
    assert isencao.pk not in set(faq.palavras_chave.values_list("pk", flat=True))

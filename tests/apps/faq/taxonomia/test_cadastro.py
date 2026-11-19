"""Cadastro da taxonomia da FAQ (SPEC faq/001): níveis máximos e palavra-chave relacionada."""

import pytest
from django.core.exceptions import ValidationError

from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Tema as TemaModel
from apps.faq.taxonomia import gravar_palavra_chave
from services.domain.faq import PalavraChave

banco = pytest.mark.banco


@banco
@pytest.mark.django_db
def test_tema_recusa_subtema_de_subtema() -> None:
    raiz = TemaModel.objects.create(nome="Busca")
    sub = TemaModel.objects.create(nome="Lotes", pai=raiz)

    with pytest.raises(ValidationError) as erro:
        TemaModel(nome="Contribuintes", pai=sub).full_clean()

    assert "pai" in erro.value.message_dict


@banco
@pytest.mark.django_db
def test_palavra_chave_recusa_quarto_nivel() -> None:
    primeira = PalavraChaveModel.objects.create(nome="IPTU")
    segunda = PalavraChaveModel.objects.create(nome="Certidão", pai=primeira)
    terceira = PalavraChaveModel.objects.create(nome="Lançamento", pai=segunda)

    with pytest.raises(ValidationError) as erro:
        PalavraChaveModel(nome="Segunda via", pai=terceira).full_clean()

    assert "pai" in erro.value.message_dict


@banco
@pytest.mark.django_db
def test_palavra_chave_nasce_relacionada_nos_dois_sentidos() -> None:
    iptu = PalavraChaveModel.objects.create(nome="IPTU")

    nova = gravar_palavra_chave(
        PalavraChave(nome="Imposto predial", relacionadas=[iptu.pk])
    )

    assert list(PalavraChaveModel.objects.get(pk=nova).relacionadas.all()) == [iptu]
    assert list(iptu.relacionadas.values_list("pk", flat=True)) == [nova]

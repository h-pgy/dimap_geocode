from django.db import transaction

from apps.faq.models import PalavraChave as PalavraChaveModel
from apps.faq.models import Tema as TemaModel
from services.domain.faq import PalavraChave


@transaction.atomic
def gravar_palavra_chave(palavra: PalavraChave) -> int:
    # Porta única de criação: a resolução por caminho de gravar_faq e a edição de faq/002 passam aqui.
    registro = PalavraChaveModel(
        nome=palavra.nome,
        pai_id=palavra.pai.id if palavra.pai is not None else None,
    )
    registro.full_clean()
    registro.save()
    # Na criação, não no passo seguinte: a palavra já nasce ligada, numa transação só.
    registro.relacionadas.set(palavra.relacionadas)
    return registro.pk


@transaction.atomic
def renomear_palavra_chave(palavra_id: int, nome: str) -> None:
    registro = PalavraChaveModel.objects.get(pk=palavra_id)
    registro.nome = nome
    registro.full_clean()
    registro.save(update_fields=["nome"])


@transaction.atomic
def gravar_tema(nome: str, pai_id: int | None) -> int:
    registro = TemaModel(nome=nome, pai_id=pai_id)
    registro.full_clean()
    registro.save()
    return registro.pk


@transaction.atomic
def renomear_tema(tema_id: int, nome: str) -> None:
    registro = TemaModel.objects.get(pk=tema_id)
    registro.nome = nome
    registro.full_clean()
    registro.save(update_fields=["nome"])

from django.db import transaction

from apps.faq.models import PalavraChave as PalavraChaveModel
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

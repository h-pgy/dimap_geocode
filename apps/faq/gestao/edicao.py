from django.utils import timezone

from apps.faq.models import Faq as FaqModel
from services.domain.faq import Editor


def marcar_edicao(registro: FaqModel, editor: Editor) -> None:
    # Toda escrita da área de edição passa por aqui; `autor` nunca é tocado.
    registro.editado_por_id = editor.perfil_id
    registro.editado_em = timezone.now()
    registro.save(update_fields=["editado_por", "editado_em"])

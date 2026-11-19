from django.http import HttpRequest

from services.domain.faq import Leitor


def leitor_de(request: HttpRequest) -> Leitor:
    # Todo Perfil tem RF (é o USERNAME_FIELD): logado ⇔ RF preenchido.
    return Leitor(rf=request.user.rf if request.user.is_authenticated else None)

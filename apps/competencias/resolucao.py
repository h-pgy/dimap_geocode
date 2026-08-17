"""A borda entre o request e o router (SPEC autorizacao/005): resolve o conjunto de slugs
liberados a um usuário, para alimentar `MontagemMenu` sem que o router precise conhecer o ciclo
de request nem o backend de autorização."""

from django.contrib.auth.models import AnonymousUser

from apps.user_admin.models import Perfil

from .registro import REGISTRO


def slugs_liberados(usuario: Perfil | AnonymousUser) -> frozenset[str]:
    """Superusuário recebe o registro inteiro: o atalho do PermissionsMixin cobre `has_perm`, não a
    enumeração — sem esta linha ele veria menu vazio e executaria tudo pela URL."""
    if getattr(usuario, "is_superuser", False):
        # Do registro em código, não da tabela projetada: o registro é, por construção, só o que
        # existe hoje, e ler dali dispensa filtrar por `ativa`.
        return frozenset(item.acao.slug for item in REGISTRO.todas())
    return frozenset(usuario.get_all_permissions())

"""A borda entre o request e o router (SPEC autorizacao/005): resolve o conjunto de slugs
liberados a um usuário, para alimentar `MontagemMenu` sem que o router precise conhecer o ciclo
de request nem o backend de autorização."""

from django.contrib.auth.models import AnonymousUser

from apps.user_admin.models import Perfil

from .registro import REGISTRO


def slugs_liberados(usuario: Perfil | AnonymousUser) -> frozenset[str]:
    """Superusuário recebe o registro inteiro: o atalho do PermissionsMixin cobre `has_perm`, não a
    enumeração — sem esta linha ele veria menu vazio e executaria tudo pela URL."""
    # SPEC user_admin/027: a cascata do painel some com todo card de AÇÃO do exonerado pelo mesmo
    # motivo — o atalho do superusuário abaixo devolveria o registro inteiro a quem a rota vai
    # recusar card por card. O item livre não passa por aqui e continua de pé — ele não é ato.
    if getattr(usuario, "exonerado", False):
        return frozenset()
    if getattr(usuario, "is_superuser", False):
        # Do registro em código, não da tabela projetada: o registro é, por construção, só o que
        # existe hoje, e ler dali dispensa filtrar por `ativa`.
        return frozenset(item.acao.slug for item in REGISTRO.todas())
    return frozenset(usuario.get_all_permissions())

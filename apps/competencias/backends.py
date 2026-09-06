"""
Backend de autorização da DIMAP (SPEC autorizacao/003): serve `has_perm` a partir da competência
(concessão da unidade + direção), sem autenticar ninguém. Entra ao lado do `ModelBackend` em
`AUTHENTICATION_BACKENDS` — quem autentica continua sendo ele.
"""

from django.http import HttpRequest

from apps.competencias.consulta import montar_avaliacao
from apps.user_admin.models import Perfil
from services.domain.autorizacao import avaliar_competencia

ATRIBUTO_CACHE = "_competencia_cache"


class CompetenciaPermissionBackend:
    """Serve `has_perm` a partir da competência (concessão da unidade + direção), sem autenticar
    ninguém.

    Não há classe-base a herdar — o Django resolve backend por duck typing, e é a assinatura destes
    três métodos que faz esta classe ser aceita em `AUTHENTICATION_BACKENDS`."""

    def authenticate(self, request: HttpRequest | None, **credenciais: object) -> None:
        # Quem autentica segue sendo o ModelBackend: devolver None aqui é como o protocolo diz
        # "não é comigo", e o Django passa ao backend seguinte.
        return None

    def get_all_permissions(self, user_obj: object, obj: object | None = None) -> set[str]:
        """Os slugs liberados, montados uma vez e guardados no próprio objeto de usuário — mesma
        técnica do ModelBackend, com atributo próprio para não colidir com o cache dele.

        É aqui que o custo fixo se cumpre: a primeira pergunta paga a consulta, e o menu que
        pergunta por dez ações seguidas não paga mais nada."""
        # Anônimo não tem caneta nenhuma. Superusuário nem chega aqui: `PermissionsMixin.has_perm`
        # responde True antes de consultar backend algum.
        if not isinstance(user_obj, Perfil):
            return set()
        # Permissão por objeto não tem dono (SPEC autorizacao/003, §4), e negar é o default
        # seguro: devolver o conjunto global responderia "pode" a uma pergunta sobre um objeto
        # específico.
        if obj is not None:
            return set()
        cacheado = getattr(user_obj, ATRIBUTO_CACHE, None)
        if cacheado is None:
            # Exoneração e afastamento não são conferidos aqui: entram no DTO como `em_exercicio`,
            # e o avaliador zera tudo antes de olhar concessão.
            entrada = montar_avaliacao(user_obj)
            avaliacao = avaliar_competencia(entrada)
            cacheado = set(avaliacao.slugs_liberados)
            setattr(user_obj, ATRIBUTO_CACHE, cacheado)
        return cacheado

    def has_perm(self, user_obj: object, perm: str, obj: object | None = None) -> bool:
        # O protocolo do Django é plano: a pergunta é pertinência no conjunto, e o `obj` só é
        # repassado para que a negativa por objeto aconteça num lugar só.
        return perm in self.get_all_permissions(user_obj, obj)

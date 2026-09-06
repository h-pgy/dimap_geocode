"""
O ato que escreve `is_superuser` de um servidor (SPEC user_admin/022): dá e retira plenos
poderes. Ser administrador já é atributo do `Perfil` — o que este módulo modela é o ato que
escreve esse atributo, não um novo dado.
"""

from dataclasses import dataclass

from django.shortcuts import get_object_or_404

from apps.user_admin.formularios import traduzir_recusa
from apps.user_admin.models import Perfil
from apps.user_admin.schemas import MudancaDeAdministrador
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario

ERRO_AUTO_REVOGACAO = (
    "Você não pode retirar de si mesmo a condição de administrador do sistema: "
    "peça a outro administrador."
)


@dataclass(frozen=True)
class DesfechoAdministrador:
    """Recado do ato para a view — mesma natureza do `DesfechoCadastro` de `cadastro.py`."""

    perfil: Perfil | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def recusa_de_auto_revogacao(
    servidor_id: int,
    autor_id: int,
    tornar: bool,
) -> RecusaDeFormulario | None:
    """A regra que garante que sempre reste um administrador: quem assina não se desfaz da própria
    caneta. Como só administrador escreve a marca, recusar a auto-revogação já implica que o
    conjunto nunca esvazia.

    Mora aqui, e não em cada ato: a mesma marca é escrita pela rota direta e pelo formulário de
    edição (SPEC user_admin/022 v3), e a regra escrita duas vezes divergiria na primeira mudança."""
    if tornar or servidor_id != autor_id:
        return None
    return traduzir_recusa(
        (
            ErroBruto(
                controle="administrador",
                tipo="auto_revogacao",
                mensagem=ERRO_AUTO_REVOGACAO,
            ),
        )
    )


def mudar_administrador(mudanca: MudancaDeAdministrador) -> DesfechoAdministrador:
    """O ato da rota direta: escreve a caneta e nada mais do cadastro."""
    recusa = recusa_de_auto_revogacao(mudanca.servidor_id, mudanca.autor_id, mudanca.tornar)
    if recusa is not None:
        return DesfechoAdministrador(perfil=None, recusa=recusa)
    perfil = get_object_or_404(Perfil, pk=mudanca.servidor_id)
    perfil.is_superuser = mudanca.tornar
    # Campo só, e não `save()` inteiro: o ato escreve a caneta e nada mais do cadastro — `is_staff`
    # fica de fora de propósito, o /admin do Django não abre por aqui (SPEC, §4).
    perfil.save(update_fields=["is_superuser"])
    return DesfechoAdministrador(perfil=perfil)

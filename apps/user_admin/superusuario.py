"""
Criação de superusuário com lotação (SPEC criacao_usuarios/006). `createsuperuser` preenche só
`rf`, `nome` e `sobrenome`; `unidade` e `cargo_base` são obrigatórios e não estão em
`REQUIRED_FIELDS`, então o `save()` dele estoura no banco — este é o caminho que produz um `Perfil`
gravável.
"""

from django.db import transaction
from pydantic import SecretStr

from apps.user_admin.models import CargoBase, CargoComissao, Perfil, Unidade
from apps.user_admin.schemas import NovoSuperusuario
from apps.user_admin.titularidade import definir_titular


def criar_superusuario(novo: NovoSuperusuario, senha: SecretStr) -> Perfil:
    """Um ato só: sem unidade, cargo ou compatibilidade de titularidade, nada é gravado."""
    with transaction.atomic():
        perfil = Perfil(
            rf=novo.rf,
            nome=novo.nome,
            sobrenome=novo.sobrenome,
            email=novo.email,
            unidade=_unidade(novo.unidade_sigla),
            cargo_base=_cargo_base(novo.cargo_base_sigla),
            cargo_comissao=_cargo_comissao(novo.cargo_comissao_nome),
            is_staff=True,
            is_superuser=True,
        )
        # A senha nasce hasheada: nem o banco, nem o log, nem um traceback guardam o texto claro.
        perfil.set_password(senha.get_secret_value())
        perfil.full_clean(exclude=["password"])
        perfil.save()
        if novo.e_titular:
            # Depois do save: `definir_titular` cruza cargo → unidade → tipo e precisa da linha.
            definir_titular(perfil)
    return perfil


def _unidade(sigla: str) -> Unidade:
    return Unidade.objects.get(sigla=sigla)


def _cargo_base(sigla: str) -> CargoBase:
    return CargoBase.objects.get(sigla=sigla)


def _cargo_comissao(nome: str) -> CargoComissao:
    # Pelo nome, e não pela sigla: a sigla do cargo em comissão é o padrão de vencimento, e vários
    # cargos a compartilham.
    return CargoComissao.objects.get(nome=nome)

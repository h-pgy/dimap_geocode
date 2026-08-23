"""
Como um servidor aparece na tela: o avatar já resolvido e o selo do exercício. Mora fora do
`context.py` porque três páginas o pedem — a do servidor, a da unidade (titular e substituto) e a
listagem —, e a da unidade vive no app `unidades`, que não pode importar o contexto daqui sem
fechar ciclo com ele.
"""

from services.domain.avatar import ImagemPerfilOutput, resolver_imagem_perfil

from apps.unidades.paleta import TINTA_AVATAR, hex_da_cor
from apps.user_admin.models import Perfil

# Selo do exercício: o vermelho é da unidade sem direção (SPEC 016), nunca da pessoa.
SELO_EM_EXERCICIO = ("Em exercício", "badge-success")
SELO_AFASTADO = ("Afastado", "badge-warning")
SELO_EXONERADO = ("Exonerado", "badge-warning")


def imagem_do_perfil(perfil: Perfil) -> ImagemPerfilOutput:
    return resolver_imagem_perfil(
        nome=perfil.nome,
        sobrenome=perfil.sobrenome,
        cor_fundo=hex_da_cor(perfil.cor_unidade),
        cor_tinta=TINTA_AVATAR,
        foto_url=_foto_url(perfil),
    )


def selo_do_exercicio(perfil: Perfil) -> dict[str, str]:
    # O selo descreve a PESSOA e nunca fica vermelho: afastado e exonerado dividem o âmbar, e o
    # que os separa é a palavra. Vermelho é da unidade sem direção (SPEC 016).
    if perfil.exonerado:
        rotulo, classe = SELO_EXONERADO
    elif perfil.em_exercicio:
        rotulo, classe = SELO_EM_EXERCICIO
    else:
        rotulo, classe = SELO_AFASTADO
    return {
        "rotulo": rotulo,
        "classe": classe,
    }


def _foto_url(perfil: Perfil) -> str | None:
    # Registro órfão (arquivo apagado do storage) viraria <img> quebrado: sem arquivo em disco, o
    # avatar de iniciais assume. A checagem é daqui, não do resolver — ele é domínio puro e não
    # conhece Django nem I/O (SPEC user_admin/006).
    nome_arquivo = perfil.foto.name
    if not nome_arquivo:
        return None
    if not perfil.foto.storage.exists(nome_arquivo):
        return None
    return perfil.foto.url

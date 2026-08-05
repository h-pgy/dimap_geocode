from .generator import AvatarIniciaisSvg
from .models import AvatarIniciaisInput, ImagemPerfilOutput


def resolver_imagem_perfil(
    nome: str,
    sobrenome: str,
    cor_fundo: str,
    cor_tinta: str,
    foto_url: str | None = None,
) -> ImagemPerfilOutput:
    if foto_url:
        return ImagemPerfilOutput(tipo="foto", valor=foto_url)
    avatar = AvatarIniciaisSvg()(
        AvatarIniciaisInput(
            nome=nome,
            sobrenome=sobrenome,
            cor_fundo=cor_fundo,
            cor_tinta=cor_tinta,
        )
    )
    return ImagemPerfilOutput(tipo="avatar", valor=avatar.svg)

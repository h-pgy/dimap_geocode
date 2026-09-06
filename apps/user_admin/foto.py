"""
Conferência da foto enviada no cadastro de servidor (SPEC criacao_usuarios/006). O `ImageField` do
model não confere conteúdo: quem confere no Django é o field de FORMULÁRIO, que este projeto não
usa — sem isto, um arquivo de texto chamado `retrato.png` é gravado.
"""

from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

from services.utils.erros_formulario import ErroBruto

LIMITE_BYTES = 2 * 1024 * 1024
ERRO_TAMANHO = "Foto acima de 2 MB: envie uma imagem menor."
ERRO_FORMATO = "O arquivo enviado não é uma imagem."


def conferir_foto(foto: UploadedFile | None) -> ErroBruto | None:
    """Sem foto nova não há nada a conferir — é o caso mais comum da edição."""
    if foto is None:
        return None
    # Upload de tamanho desconhecido não é recusado por tamanho: quem o recusa é a conferência de
    # imagem, logo abaixo.
    tamanho = foto.size or 0
    if tamanho > LIMITE_BYTES:
        return ErroBruto(controle="foto", tipo="tamanho", mensagem=ERRO_TAMANHO)
    if not _eh_imagem(foto):
        return ErroBruto(controle="foto", tipo="formato", mensagem=ERRO_FORMATO)
    return None


def _eh_imagem(foto: UploadedFile) -> bool:
    # `verify()` lê o cabeçalho e deixa o arquivo consumido: o seek devolve o ponteiro para quem
    # vai gravar depois.
    try:
        Image.open(foto).verify()
    except (UnidentifiedImageError, OSError):
        return False
    finally:
        foto.seek(0)
    return True

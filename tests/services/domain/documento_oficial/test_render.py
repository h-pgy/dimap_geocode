import pytest

from services.domain.documento_oficial import (
    ConteudoDocumento,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    TemaConfig,
    Titulo,
    montar_escritores,
    montar_tema,
)
from services.utils.pdf import Marcacao, MarcacaoDocumento


def _marcacao_vazia() -> MarcacaoDocumento:
    return MarcacaoDocumento(
        principal=Marcacao(
            marcas=(),
            margem_lateral_mm=20.0,
            margem_vertical_mm=10.0,
            respiro_mm=5.0,
        )
    )


# ---------------------------------------------------------------------------
# Bloco sem escritor não some do documento: levanta na montagem
# ---------------------------------------------------------------------------


def test_bloco_sem_escritor_falha_na_montagem() -> None:
    tema = montar_tema(TemaConfig())
    incompleto = {
        tipo: escritor for tipo, escritor in montar_escritores(tema).items() if tipo != "titulo"
    }
    renderizador = RenderizarDocumentoOficial(tema, escritores=incompleto)
    conteudo = ConteudoDocumento(
        titulo="Teste",
        nome_arquivo="teste.pdf",
        blocos=(Titulo(texto="Bloco sem escritor"),),
    )

    with pytest.raises(KeyError):
        renderizador(RenderizarDocumentoInput(conteudo=conteudo, marcacao=_marcacao_vazia()))

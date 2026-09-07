from datetime import datetime

from pydantic import BaseModel, ConfigDict

from services.utils.pdf import MarcacaoDocumento

from .conteudo import ConteudoDocumento


class DocumentoAmostraInput(BaseModel):
    """O pedido da amostra. Sem caminho de saída: gravar é do comando, gerar é do domínio."""

    model_config = ConfigDict(frozen=True)

    # De onde a amostra partiu, para quem confere saber qual ambiente foi provado.
    ambiente: str
    momento: datetime


class RenderizarDocumentoInput(BaseModel):
    """O que o documento diz, e sobre que papel."""

    # `MarcacaoDocumento` é classe do motor, sem schema Pydantic — ver Caveats.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    conteudo: ConteudoDocumento
    marcacao: MarcacaoDocumento


class DocumentoRenderizado(BaseModel):
    """O PDF pronto, com o nome que o conteúdo pediu: é o que a rota devolve e o que o comando
    grava. Bytes, nunca caminho — persistir é de quem chama."""

    model_config = ConfigDict(frozen=True)

    pdf: bytes
    nome_arquivo: str

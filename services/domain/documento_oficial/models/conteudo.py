from pydantic import BaseModel, ConfigDict, Field

from .blocos import Bloco


class ConteudoDocumento(BaseModel):
    """O que o documento diz e como ele se identifica. Sem cabeçalho nem rodapé: aquilo é da
    marcação, não do conteúdo."""

    model_config = ConfigDict(frozen=True)

    # Vai para os metadados do PDF, e é o que o leitor mostra na barra de título.
    titulo: str
    # O nome com que o documento se salva ou se baixa. Quem monta o documento sabe qual é; a
    # orquestração só o repassa ao `Content-Disposition` ou ao arquivo.
    nome_arquivo: str
    blocos: tuple[Bloco, ...] = Field(min_length=1)


# Os valores institucionais são conhecimento de domínio, e o default mora AQUI — uma vez só. O
# ambiente sobrepõe pelo builder do §6; calado o ambiente, é isto que sai no papel.
UNIDADE_PADRAO = (
    "Secretaria da Fazenda",
    "Subsecretaria da Receita Municipal",
    "Departamento de Cadastro",
    "Divisão do Mapa de Valores",
)
ENDERECO_PADRAO = ("Rua Líbero Badaró, 190 - Centro, São Paulo - SP (CEP 01008-000)",)

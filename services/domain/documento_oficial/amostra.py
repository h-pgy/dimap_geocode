from services.utils.pdf import Alinhamento, ColunaFixa, ColunaFluida

from .models import (
    Bloco,
    ConteudoDocumento,
    DocumentoAmostraInput,
    Lista,
    Paragrafo,
    Subtitulo,
    Tabela,
    Titulo,
)

# Repetido até o corpo estourar a primeira página — é o que prova a marcação se repetindo na
# segunda, sem que o comando precise forçar quebra de página manualmente.
PARAGRAFO_LONGO = (
    "Este parágrafo existe só para ocupar espaço e forçar a quebra de página: o papel timbrado "
    "da Secretaria da Fazenda precisa se repetir de forma idêntica na primeira e na segunda "
    "página, com o timbre, o cabeçalho da unidade, a marca d'água, o rodapé de endereço e a "
    "numeração de páginas presentes nas duas. "
) * 6


class MontarDocumentoAmostra:
    """Callable: o pedido vira o que o documento vai dizer. Todos os tipos de bloco textual, de
    lista e de tabela aparecem, os três níveis de subtítulo também, e o texto é longo o bastante
    para virar a página — é o que prova a marcação repetida."""

    def __call__(self, pedido: DocumentoAmostraInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: DocumentoAmostraInput) -> ConteudoDocumento:
        return ConteudoDocumento(
            titulo="Documento de amostra",
            nome_arquivo="documento_amostra.pdf",
            blocos=self._blocos(pedido),
        )

    def _blocos(self, pedido: DocumentoAmostraInput) -> tuple[Bloco, ...]:
        return (
            Titulo(texto="Documento de amostra"),
            Paragrafo(
                texto=(
                    f"Amostra gerada no ambiente {pedido.ambiente}, em "
                    f"{pedido.momento:%d/%m/%Y %H:%M:%S}, para conferir o timbre, a marca "
                    "d'água e a numeração antes de qualquer ato administrativo emitir "
                    "documento de verdade."
                )
            ),
            Subtitulo(texto="Subtítulo de nível I", nivel=1),
            Paragrafo(texto=PARAGRAFO_LONGO),
            Subtitulo(texto="Subtítulo de nível II", nivel=2),
            Paragrafo(
                texto=(
                    "Este é um parágrafo recuado, como uma transcrição ou citação dentro do "
                    "ato administrativo."
                ),
                recuado=True,
            ),
            Subtitulo(texto="Subtítulo de nível III", nivel=3),
            Lista(
                ordenada=True,
                itens=("Primeiro item numerado", "Segundo item numerado", "Terceiro item numerado"),
            ),
            Lista(ordenada=False, itens=("Primeiro item com marcador", "Segundo item com marcador")),
            Tabela(
                colunas=(
                    ColunaFixa(largura_mm=40.0),
                    ColunaFluida(alinhamento=Alinhamento.DIREITA),
                ),
                cabecalho=("Campo", "Valor"),
                linhas=(
                    ("Ambiente", pedido.ambiente),
                    ("Momento", f"{pedido.momento:%d/%m/%Y %H:%M:%S}"),
                ),
            ),
            Paragrafo(texto=PARAGRAFO_LONGO),
        )


montar_documento_amostra = MontarDocumentoAmostra()

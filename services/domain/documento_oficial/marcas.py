from pathlib import Path

from reportlab.lib.units import mm

from services.utils.pdf import (
    EstiloTexto,
    Faixa,
    Folha,
    Marca,
    Posicao,
    QrCodePdfInput,
    VetorNomeado,
    carregar_vetor,
    qr_code_pdf,
)
from services.utils.qr_code import QrCodeInput, gerar_qr_code


class TimbreHorizontal(Marca):
    """O logotipo da Secretaria, no alto de toda página."""

    posicao = Posicao.SUPERIOR

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # ALTERADO nesta SPEC: o desenho carrega o nome junto. Ele segue carregado UMA vez e reusado
        # em toda página: o SVG tem centenas de traços, e reabri-lo por página seria o custo desta
        # marca multiplicado pelo tamanho do documento.
        self._vetor = VetorNomeado(desenho=carregar_vetor(caminho_svg, largura_mm), nome="timbre")
        # Medidas do que a marca pinta, não constantes escritas à mão: mudar a largura do timbre
        # não pode deixar a moldura do corpo desatualizada (Caveats da SPEC 001).
        self.altura_mm = self._vetor.desenho.height / mm
        self.largura_mm = self._vetor.desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, self._vetor)


class LinhasDeTexto(Marca):
    """Base das marcas que são linhas empilhadas — o cabeçalho da unidade e o rodapé de endereço.
    Recebe as linhas prontas: nenhum texto institucional é literal numa marca."""

    def __init__(self, linhas: tuple[str, ...], estilo: EstiloTexto, entrelinha_mm: float) -> None:
        self._linhas = linhas
        self._estilo = estilo
        self._entrelinha_mm = entrelinha_mm
        # As linhas vêm da config e podem ser mais que o padrão: com altura constante de classe,
        # uma unidade de seis níveis invadiria a faixa vizinha sem que nada recusasse.
        self.altura_mm = len(linhas) * entrelinha_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        for numero, linha in enumerate(self._linhas, start=1):
            folha.texto(
                faixa.esquerda_mm,
                faixa.topo_mm + numero * self._entrelinha_mm,
                linha,
                self._estilo,
            )


class CabecalhoUnidade(LinhasDeTexto):
    """A unidade da DIMAP, um nível por linha. O logotipo já traz 'PREFEITURA DE SÃO PAULO /
    SECRETARIA DA FAZENDA', então esta marca nomeia só a unidade — nada é dito duas vezes."""

    posicao = Posicao.SUPERIOR


class RodapeEndereco(LinhasDeTexto):
    posicao = Posicao.INFERIOR


class CabecalhoTimbrado(Marca):
    """Timbre à esquerda, unidade à direita, na MESMA faixa. Empilhadas, as duas marcas somariam a
    altura de cada uma e o cabeçalho comeria a página; lado a lado, a faixa é a do mais alto."""

    posicao = Posicao.SUPERIOR

    def __init__(
        self,
        timbre: TimbreHorizontal,
        unidade: CabecalhoUnidade,
        respiro_mm: float,
    ) -> None:
        self._timbre = timbre
        self._unidade = unidade
        self._recuo_unidade_mm = timbre.largura_mm + respiro_mm
        self.altura_mm = max(timbre.altura_mm, unidade.altura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self._timbre(faixa, folha)
        self._unidade(self._faixa_da_unidade(faixa), folha)

    def _faixa_da_unidade(self, faixa: Faixa) -> Faixa:
        return faixa.model_copy(
            update={
                "esquerda_mm": faixa.esquerda_mm + self._recuo_unidade_mm,
                "largura_mm": faixa.largura_mm - self._recuo_unidade_mm,
            }
        )


class MarcaDagua(Marca):
    """O logotipo vertical no meio do papel. Reserva ZERO: o corpo passa por cima.

    O SVG que chega aqui já é o claro — clarear é preparação de ativo, feita uma vez à mão pelo
    comando do §6 e comitada, e não trabalho repetido a cada emissão.
    """

    posicao = Posicao.FUNDO
    altura_mm = 0.0

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # ALTERADO nesta SPEC: idem `TimbreHorizontal`.
        self._vetor = VetorNomeado(
            desenho=carregar_vetor(caminho_svg, largura_mm), nome="marca_dagua"
        )

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        # Centralizada na FOLHA, e não na faixa: a marca de fundo ignora a moldura das outras.
        folha.vetor(
            (folha.tamanho.largura_mm - self._vetor.desenho.width / mm) / 2,
            (folha.tamanho.altura_mm - self._vetor.desenho.height / mm) / 2,
            self._vetor,
        )


class NumeracaoPaginas(Marca):
    """'Página X de Y'. O total vem da folha, que já o conhece."""

    posicao = Posicao.INFERIOR

    def __init__(self, estilo: EstiloTexto, entrelinha_mm: float) -> None:
        self._estilo = estilo
        self.altura_mm = entrelinha_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.texto(
            faixa.esquerda_mm,
            faixa.topo_mm,
            f"Página {folha.pagina} de {folha.total}",
            self._estilo,
        )


class QrCodeRodape(Marca):
    """O símbolo de verificação no pé, encostado na DIREITA da faixa. Recebe o que o QR diz, nunca
    o desenho: quem gera o símbolo é o utilitário, como no bloco do corpo."""

    posicao = Posicao.INFERIOR

    def __init__(self, conteudo: str, largura_mm: float) -> None:
        self._vetor = qr_code_pdf(
            QrCodePdfInput(
                simbolo=gerar_qr_code(QrCodeInput(conteudo=conteudo)),
                largura_mm=largura_mm,
            )
        )
        # Medida do que a marca pinta, como no timbre: o símbolo escolhe a versão do QR conforme o
        # conteúdo, e uma altura escrita à mão desalinharia com a matriz que saiu.
        self.altura_mm = self._vetor.desenho.height / mm
        self.largura_mm = self._vetor.desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        # O canto direito da faixa, e não a esquerda: o endereço ocupa a esquerda do mesmo pé.
        folha.vetor(
            faixa.esquerda_mm + faixa.largura_mm - self.largura_mm,
            faixa.topo_mm,
            self._vetor,
        )


class RodapeComQr(Marca):
    """O texto do pé à esquerda, o QR à direita, na MESMA faixa — o espelho do `CabecalhoTimbrado`.
    Soltas, endereço, paginação e símbolo somariam as três alturas e o pé comeria a página."""

    posicao = Posicao.INFERIOR

    def __init__(
        self,
        texto: Marca,
        qr_code: QrCodeRodape,
        respiro_mm: float,
    ) -> None:
        self._texto = texto
        self._qr_code = qr_code
        # O que sobra para o texto depois do símbolo e do respiro entre os dois.
        self._largura_do_qr_mm = qr_code.largura_mm + respiro_mm
        self.altura_mm = max(texto.altura_mm, qr_code.altura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        self._texto(self._faixa_do_texto(faixa), folha)
        # A faixa INTEIRA para o QR: é ele quem se encosta na direita dela.
        self._qr_code(faixa, folha)

    def _faixa_do_texto(self, faixa: Faixa) -> Faixa:
        return faixa.model_copy(
            update={"largura_mm": faixa.largura_mm - self._largura_do_qr_mm}
        )

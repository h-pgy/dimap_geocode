from pathlib import Path

from reportlab.lib.units import mm

from services.utils.pdf import EstiloTexto, Faixa, Folha, Marca, Posicao, carregar_vetor


class TimbreHorizontal(Marca):
    """O logotipo da Secretaria, no alto de toda página."""

    posicao = Posicao.SUPERIOR

    def __init__(self, caminho_svg: Path, largura_mm: float) -> None:
        # O Drawing é carregado UMA vez e reusado em toda página: o SVG tem centenas de traços, e
        # reabri-lo por página seria o custo desta marca multiplicado pelo tamanho do documento.
        self._desenho = carregar_vetor(caminho_svg, largura_mm)
        # Medidas do que a marca pinta, não constantes escritas à mão: mudar a largura do timbre
        # não pode deixar a moldura do corpo desatualizada (Caveats da SPEC 001).
        self.altura_mm = self._desenho.height / mm
        self.largura_mm = self._desenho.width / mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, self._desenho, nome="timbre")


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
        self._desenho = carregar_vetor(caminho_svg, largura_mm)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        # Centralizada na FOLHA, e não na faixa: a marca de fundo ignora a moldura das outras.
        folha.vetor(
            (folha.tamanho.largura_mm - self._desenho.width / mm) / 2,
            (folha.tamanho.altura_mm - self._desenho.height / mm) / 2,
            self._desenho,
            nome="marca_dagua",
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

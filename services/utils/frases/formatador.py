import re

_ESPACOS = re.compile(r"\s+")
_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")
_PONTUACAO_FINAL = ".!?…;:,"
_ABERTURAS = "\"'“‘«([{¿¡"


class FormatadorDeFrases:
    """Quebra o texto em frases e põe a primeira letra de cada uma em caixa alta.

    `inicio_de_frase` e `fim_de_frase` valem para cada frase; `primeiro` e `ultimo`, para a
    sequência toda, aplicados depois. Um caractere final substitui a pontuação final que houver,
    e nenhum caractere se duplica se o texto já o traz.
    """

    def __init__(
        self,
        primeiro: str | None = None,
        ultimo: str | None = None,
        inicio_de_frase: str | None = None,
        fim_de_frase: str | None = None,
    ) -> None:
        self._primeiro = primeiro
        self._ultimo = ultimo
        self._inicio_de_frase = inicio_de_frase
        self._fim_de_frase = fim_de_frase

    def __call__(self, texto: str) -> str:
        return self.pipeline(texto)

    def pipeline(self, texto: str) -> str:
        limpo = _ESPACOS.sub(" ", texto).strip()
        if not limpo:
            return limpo
        frases = [self._frase(frase) for frase in _FIM_DE_FRASE.split(limpo)]
        sequencia = " ".join(frases)
        return _com_inicio(_com_fim(sequencia, self._ultimo), self._primeiro)

    def _frase(self, frase: str) -> str:
        capitalizada = self._capitalizar(frase)
        return _com_inicio(
            _com_fim(capitalizada, self._fim_de_frase), self._inicio_de_frase
        )

    def _capitalizar(self, frase: str) -> str:
        for posicao, caractere in enumerate(frase):
            if caractere in _ABERTURAS:
                continue
            # Frase que abre com número ("2ª via") não ganha maiúscula no meio.
            if not caractere.isalpha():
                return frase
            return frase[:posicao] + caractere.upper() + frase[posicao + 1 :]
        return frase


def _com_fim(texto: str, fim: str | None) -> str:
    if fim is None or texto.endswith(fim):
        return texto
    return texto.rstrip(_PONTUACAO_FINAL).rstrip() + fim


def _com_inicio(texto: str, inicio: str | None) -> str:
    if inicio is None or texto.startswith(inicio):
        return texto
    return inicio + texto

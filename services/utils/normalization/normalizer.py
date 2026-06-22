import inspect
import re
import unicodedata
from collections.abc import Callable

_CLEAN_PREFIX = "_clean"
_CLEAN_PATTERN = re.compile(r"^_clean_(\d+)_[a-z][a-z0-9_]*$")
_PUNCT_AND_SYMBOLS = re.compile(r"[^\w\s]", flags=re.UNICODE)
_UNDERSCORE = re.compile(r"_")
_WHITESPACE = re.compile(r"\s+")

_Etapa = Callable[[str], str]


def _expected_signature() -> inspect.Signature:
    return inspect.Signature(
        parameters=[
            inspect.Parameter("text", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
        ],
        return_annotation=str,
    )


class TextNormalizer:
    def __init__(self) -> None:
        self._pipeline: list[_Etapa] = self._build_pipeline()

    # ---------- construção do pipeline ----------

    def _build_pipeline(self) -> list[_Etapa]:
        candidatos = self._descobrir_candidatos()
        numerados = self._checar_metodos_pipeline(candidatos)
        return self._ordenar_e_checar(numerados)

    def _descobrir_candidatos(self) -> list[tuple[str, _Etapa]]:
        return [
            (name, method)
            for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if name.startswith(_CLEAN_PREFIX)
        ]

    # ---------- checagens: uma por regra + agregador ----------

    def _checar_metodos_pipeline(
        self, candidatos: list[tuple[str, _Etapa]]
    ) -> dict[int, tuple[str, _Etapa]]:
        numerados: dict[int, tuple[str, _Etapa]] = {}
        for name, method in candidatos:
            numero = self._checar_nome(name)
            self._checar_assinatura(name, method)
            self._checar_duplicado(name, numero, numerados)
            numerados[numero] = (name, method)
        if not numerados:
            raise ValueError("Nenhuma etapa '_clean_<n>_<nome>' encontrada no normalizador.")
        return numerados

    def _checar_nome(self, name: str) -> int:
        m = _CLEAN_PATTERN.match(name)
        if m is None:
            raise ValueError(
                f"Etapa de limpeza '{name}' não segue o padrão obrigatório "
                f"'_clean_<n>_<nome_semantico>' (n inteiro >= 1). Renomeie o método."
            )
        return int(m.group(1))

    def _checar_assinatura(self, name: str, method: _Etapa) -> None:
        if inspect.signature(method) != _expected_signature():
            raise TypeError(
                f"'{name}' deve ter assinatura (text: str) -> str; "
                f"recebido {inspect.signature(method)}."
            )

    def _checar_duplicado(
        self, name: str, numero: int, numerados: dict[int, tuple[str, _Etapa]]
    ) -> None:
        if numero in numerados:
            outro = numerados[numero][0]
            raise ValueError(
                f"Número de etapa duplicado: '{name}' e '{outro}' usam o índice {numero}. "
                f"Cada etapa deve ter um número único."
            )

    # ---------- ordenação + checagem de sequência ----------

    def _ordenar_e_checar(self, numerados: dict[int, tuple[str, _Etapa]]) -> list[_Etapa]:
        ordenados = sorted(numerados)
        esperado = list(range(1, len(ordenados) + 1))
        if ordenados != esperado:
            faltando = sorted(set(esperado) - set(ordenados))
            raise ValueError(
                f"Sequência de etapas inválida: encontrados {ordenados}, esperado {esperado} "
                f"(contígua a partir de 1, sem pular números). Faltando: {faltando}."
            )
        return [numerados[n][1] for n in ordenados]

    # ---------- ponto de entrada ----------

    def __call__(self, text: str) -> str:
        for etapa in self._pipeline:
            text = etapa(text)
        return text

    # ---------- etapas ----------

    def _clean_1_remover_pontuacao(self, text: str) -> str:
        text = _PUNCT_AND_SYMBOLS.sub(" ", text)
        return _UNDERSCORE.sub(" ", text)

    def _clean_2_cedilha_para_c(self, text: str) -> str:
        return text.replace("ç", "c").replace("Ç", "C")

    def _clean_3_remover_acentos(self, text: str) -> str:
        decomposto = unicodedata.normalize("NFD", text)
        sem_marcas = "".join(c for c in decomposto if not unicodedata.combining(c))
        return unicodedata.normalize("NFC", sem_marcas)

    def _clean_4_caixa_alta(self, text: str) -> str:
        return text.upper()

    def _clean_5_colapsar_espacos(self, text: str) -> str:
        return _WHITESPACE.sub(" ", text).strip()

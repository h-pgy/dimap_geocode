import inspect

import pytest

from services.utils.normalization import normalize_text
from services.utils.normalization.normalizer import TextNormalizer


# ---------------------------------------------------------------------------
# Comportamento: casos de input/output da spec
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        # espaços nas pontas e duplos colapsados
        ("  Av.  Paulista ", "AV PAULISTA"),
        # tab e newline viram espaço único
        ("Rua\tda\nEsquina", "RUA DA ESQUINA"),
        # pontuação removida, dígitos preservados
        ("R. Direita, 123!", "R DIREITA 123"),
        # ç → c e acentos removidos
        ("Praça da Sé", "PRACA DA SE"),
        # acentos variados: acento agudo, grave, circunflexo
        ("água, égua e avô", "AGUA EGUA E AVO"),
        # AÇAÍ em maiúsculo já, mas com cedilha e acento
        ("AÇAÍ", "ACAI"),
        # underscore tratado como pontuação
        ("a_b", "A B"),
        # entrada já normalizada (idempotência trivial via casos conhecidos)
        ("AV PAULISTA", "AV PAULISTA"),
        # São Paulo completo
        ("São Paulo", "SAO PAULO"),
        # múltiplos tipos de espaço juntos
        ("  \t  rua  \n  da  ", "RUA DA"),
        # ponto e vírgula, parênteses
        ("Rua (das) Flores; n. 10", "RUA DAS FLORES N 10"),
        # º (U+00BA) é letra Unicode (Lo) — preservado pela normalização
        ("n.º 10", "N º 10"),
        # só dígitos passam intactos (exceto caixa que não se aplica)
        ("123", "123"),
        # string vazia
        ("", ""),
        # string só de pontuação vira vazia
        ("...,,,!!!", ""),
        # acento til: ã, õ
        ("Coração de leão", "CORACAO DE LEAO"),
        # diaeresis: ü, ï (não comum no PT, mas cobre o caso genérico)
        ("müller", "MULLER"),
        # letra maiúscula com acento
        ("Átila", "ATILA"),
    ],
)
def test_normalize_text_casos_conhecidos(text: str, expected: str) -> None:
    assert normalize_text(text) == expected


# ---------------------------------------------------------------------------
# Idempotência
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "  Av.  Paulista ",
        "Praça da Sé",
        "água, égua e avô",
        "AÇAÍ",
        "a_b",
        "R. Direita, 123!",
        "São Paulo",
        "",
    ],
)
def test_normalize_text_idempotencia(text: str) -> None:
    r1 = normalize_text(text)
    r2 = normalize_text(r1)
    assert r1 == r2, f"Idempotência falhou: normalize(normalize({text!r})) != normalize({text!r})"


# ---------------------------------------------------------------------------
# Callable e retorno de tipo str
# ---------------------------------------------------------------------------


def test_normalize_text_e_callable() -> None:
    assert callable(normalize_text)


def test_normalize_text_retorna_str() -> None:
    result = normalize_text("qualquer coisa")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Exposição como função (não exige instanciar a classe)
# ---------------------------------------------------------------------------


def test_normalize_text_e_instancia_de_text_normalizer() -> None:
    assert isinstance(normalize_text, TextNormalizer)


# ---------------------------------------------------------------------------
# Pipeline: ordem, responsabilidade única das checagens
# ---------------------------------------------------------------------------


def test_pipeline_e_montado_por_introspeccao() -> None:
    normalizer = TextNormalizer()
    metodos_clean =  [
        m for m in inspect.getmembers(normalizer, predicate=inspect.ismethod)
        if m[0].startswith("_clean")
    ]
    assert len(normalizer._pipeline) == len(metodos_clean), "Pipeline não corresponde ao número de métodos _clean_*"

def test_pipeline_nao_e_vazio()->None:

    normalizer = TextNormalizer()
    assert len(normalizer._pipeline) > 0, "Pipeline está vazio"

def test_pipeline_segue_ordem_numerica_nao_alfabetica() -> None:
    normalizer = TextNormalizer()
    metodos_em_ordem = [
        m for m in inspect.getmembers(normalizer, predicate=inspect.ismethod)
        if m[0].startswith("_clean")
    ]
    numeros = [int(name.split("_")[2]) for name, _ in metodos_em_ordem]
    assert numeros == sorted(numeros), "Números dos métodos _clean_* não estão em ordem crescente"
    assert numeros[0] == 1, "O primeiro método _clean_* deve ser _clean_1_*"


# ---------------------------------------------------------------------------
# Validações na construção — erros semânticos na instanciação
# ---------------------------------------------------------------------------


def test_validacao_nome_sem_numero_levanta_na_instanciacao() -> None:
    class Quebrado(TextNormalizer):
        def _clean_punctuation(self, text: str) -> str:  # sem número
            return text

    with pytest.raises(ValueError, match="_clean_punctuation"):
        Quebrado()


def test_validacao_nome_sem_sufixo_semantico_levanta_na_instanciacao() -> None:
    class Quebrado(TextNormalizer):
        def _clean_6(self, text: str) -> str:  # sem nome semântico
            return text

    with pytest.raises(ValueError, match="_clean_6"):
        Quebrado()


def test_validacao_numero_pulado_levanta_na_instanciacao() -> None:
    class Quebrado(TextNormalizer):
        # sobrescreve _clean_5 com _clean_7, pulando o 6
        def _clean_7_extra(self, text: str) -> str:
            return text

    with pytest.raises(ValueError, match="Faltando"):
        Quebrado()


def test_validacao_numero_duplicado_levanta_na_instanciacao() -> None:
    class Quebrado(TextNormalizer):
        def _clean_1_duplicado(self, text: str) -> str:
            return text

    with pytest.raises(ValueError, match="duplicado"):
        Quebrado()


def test_validacao_assinatura_extra_argumento_levanta_na_instanciacao() -> None:
    class Quebrado(TextNormalizer):
        def _clean_6_errada(self, text: str, extra: str) -> str:
            return text

    with pytest.raises(TypeError, match="_clean_6_errada"):
        Quebrado()


def test_validacao_assinatura_retorno_errado_levanta_na_instanciacao() -> None:
    class Quebrado(TextNormalizer):
        def _clean_6_errada(self, text: str) -> int:  # type: ignore[override]
            return 0

    with pytest.raises(TypeError, match="_clean_6_errada"):
        Quebrado()


# ---------------------------------------------------------------------------
# Instanciável sem parâmetros
# ---------------------------------------------------------------------------


def test_instanciavel_sem_parametros() -> None:
    n = TextNormalizer()
    assert callable(n)

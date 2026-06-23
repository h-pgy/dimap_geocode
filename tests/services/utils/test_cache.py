import time
from unittest.mock import patch

import pytest

from services.utils.cache import TTLCachedProperty, ttl_cached_property


# ---------------------------------------------------------------------------
# Carregamento preguiçoso — a função só é chamada na primeira leitura
# ---------------------------------------------------------------------------


def test_nao_chama_na_definicao_da_classe() -> None:
    chamadas: list[int] = []

    class Sujeito:
        @ttl_cached_property(ttl_seconds=60)
        def valor(self) -> int:
            chamadas.append(1)
            return 42

    assert chamadas == []


def test_chama_uma_vez_no_primeiro_acesso() -> None:
    chamadas: list[int] = []

    class Sujeito:
        @ttl_cached_property(ttl_seconds=60)
        def valor(self) -> int:
            chamadas.append(1)
            return 42

    s = Sujeito()
    _ = s.valor
    assert len(chamadas) == 1


# ---------------------------------------------------------------------------
# Cache dentro do TTL — segunda leitura não recalcula
# ---------------------------------------------------------------------------


def test_cache_nao_recalcula_dentro_do_ttl() -> None:
    chamadas: list[int] = []

    class Sujeito:
        @ttl_cached_property(ttl_seconds=60)
        def valor(self) -> int:
            chamadas.append(1)
            return 99

    s = Sujeito()
    _ = s.valor
    _ = s.valor
    assert len(chamadas) == 1


def test_retorna_o_mesmo_valor_em_chamadas_repetidas() -> None:
    class Sujeito:
        @ttl_cached_property(ttl_seconds=60)
        def valor(self) -> list[int]:
            return [1, 2, 3]

    s = Sujeito()
    assert s.valor is s.valor


# ---------------------------------------------------------------------------
# Expiração do TTL — após o prazo a função é rechamada
# ---------------------------------------------------------------------------


def test_recalcula_apos_expirar_o_ttl() -> None:
    chamadas: list[int] = []
    agora = 1000.0

    class Sujeito:
        @ttl_cached_property(ttl_seconds=5)
        def valor(self) -> int:
            chamadas.append(1)
            return 7

    s = Sujeito()

    with patch("services.utils.cache.time.monotonic", return_value=agora):
        _ = s.valor  # popula o cache

    with patch("services.utils.cache.time.monotonic", return_value=agora + 6):
        _ = s.valor  # TTL expirado: deve recalcular

    assert len(chamadas) == 2


def test_nao_recalcula_antes_de_expirar_o_ttl() -> None:
    chamadas: list[int] = []
    agora = 1000.0

    class Sujeito:
        @ttl_cached_property(ttl_seconds=5)
        def valor(self) -> int:
            chamadas.append(1)
            return 7

    s = Sujeito()

    with patch("services.utils.cache.time.monotonic", return_value=agora):
        _ = s.valor

    with patch("services.utils.cache.time.monotonic", return_value=agora + 4):
        _ = s.valor  # ainda dentro do TTL

    assert len(chamadas) == 1


# ---------------------------------------------------------------------------
# Isolamento entre instâncias — caches independentes
# ---------------------------------------------------------------------------


def test_instancias_tem_caches_independentes() -> None:
    chamadas: list[str] = []

    class Sujeito:
        def __init__(self, nome: str) -> None:
            self.nome = nome

        @ttl_cached_property(ttl_seconds=60)
        def valor(self) -> str:
            chamadas.append(self.nome)
            return self.nome

    a = Sujeito("a")
    b = Sujeito("b")

    assert a.valor == "a"
    assert b.valor == "b"
    assert chamadas == ["a", "b"]
    # segunda leitura de cada um: não recalcula
    _ = a.valor
    _ = b.valor
    assert chamadas == ["a", "b"]


# ---------------------------------------------------------------------------
# Acesso via classe — retorna o descritor, não o valor
# ---------------------------------------------------------------------------


def test_acesso_via_classe_retorna_o_descriptor() -> None:
    class Sujeito:
        @ttl_cached_property(ttl_seconds=60)
        def valor(self) -> int:
            return 1

    assert isinstance(Sujeito.valor, TTLCachedProperty)


# ---------------------------------------------------------------------------
# __set_name__ — o atributo de cache usa o nome da propriedade
# ---------------------------------------------------------------------------


def test_set_name_usa_nome_da_propriedade() -> None:
    class Sujeito:
        @ttl_cached_property(ttl_seconds=60)
        def minha_prop(self) -> int:
            return 0

    s = Sujeito()
    _ = s.minha_prop
    assert "_ttlcache_minha_prop" in s.__dict__


# ---------------------------------------------------------------------------
# TTL zero — cada acesso recalcula
# ---------------------------------------------------------------------------


def test_ttl_zero_recalcula_a_cada_acesso() -> None:
    chamadas: list[int] = []

    class Sujeito:
        @ttl_cached_property(ttl_seconds=0)
        def valor(self) -> int:
            chamadas.append(1)
            return 5

    s = Sujeito()
    _ = s.valor
    _ = s.valor
    assert len(chamadas) == 2

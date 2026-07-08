import time
from typing import ClassVar

import pandas as pd

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data
from services.utils.normalization import chave_numero_porta  # a MESMA do numero_padronizado

NOME_ARQUIVO_PADRAO = "enderecos_fiscais.parquet"
DATA_TTL_SECONDS = 3600


class ContribuinteCatalog:
    _instancia: ClassVar["ContribuinteCatalog | None"] = None

    def __new__(cls, *args: object, **kwargs: object) -> "ContribuinteCatalog":
        # singleton só na classe exata: subclasses (fakes de teste) constroem normalmente
        if cls is not ContribuinteCatalog:
            return super().__new__(cls)
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def resetar_instancia(cls) -> None:
        # isolamento de testes: a próxima construção nasce fria
        cls._instancia = None

    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        # __init__ roda a cada "construção" do singleton — só a primeira grava o arquivo
        if not hasattr(self, "_nome_arquivo"):
            self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def enderecos_fiscais(self) -> pd.DataFrame:
        df = pd.DataFrame(read_parquet_from_data(self._nome_arquivo))
        # '00' significa "não é condomínio" — enderecos_fiscais_com_chave herda via .copy()
        df["is_condominio"] = df["cd_condominio"] != "00"
        return df

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def enderecos_fiscais_com_chave(self) -> pd.DataFrame:
        df = self.enderecos_fiscais.copy()
        # cd_numero_porta tem NULOS no parquet (~23 mil) — fillna("") antes da chave, senão
        # normalize_text recebe None e quebra. Linha sem porta ganha chave "" (não casa
        # startswith de nenhuma consulta, já que numero_padronizado tem min_length=1).
        # chave_numero_porta já embute normalize_text + canonicalização de "sem número",
        # então a coluna cacheada sai canonizada — nada é reprocessado por request.
        df["chave_numero_porta"] = df["cd_numero_porta"].fillna("").map(chave_numero_porta)
        # cd_logradouro tem 6 dígitos (codlog+DV); os matchers de logradouro devolvem 5:
        df["codlog5"] = df["cd_logradouro"].str[:5]
        return df

    def aquecer(self) -> None:
        print("[ContribuinteCatalog] aquecendo cache...")
        inicio = time.perf_counter()
        _ = self.enderecos_fiscais
        _ = self.enderecos_fiscais_com_chave
        duracao = time.perf_counter() - inicio
        print(f"[ContribuinteCatalog] cache aquecido em {duracao:.2f}s")

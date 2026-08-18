from pathlib import Path
from typing import ClassVar

from django.contrib.staticfiles import finders

from services.domain.autorizacao import VarianteIcone

from .checks import GABARITO_CAMINHO_ICONE

ICONE_GENERICO = (
    '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/>'
    '<path d="M12 8v4"/><path d="M12 16h.01"/></svg>'
)


class ResolvedorIcones:
    """Cacheado por processo: inline custa ler o arquivo no render, e é isso que paga o custo."""

    _cache: ClassVar[dict[tuple[str, VarianteIcone], str]] = {}

    def __call__(self, slug: str, variante: VarianteIcone) -> str:
        chave = (slug, variante)
        if chave not in self._cache:
            self._cache[chave] = self._ler_do_disco(slug, variante)
        return self._cache[chave]

    def _ler_do_disco(self, slug: str, variante: VarianteIcone) -> str:
        prefixo, nome = slug.split(".")
        caminho = GABARITO_CAMINHO_ICONE.format(app=prefixo, nome=nome, variante=variante.value)
        caminho_absoluto = finders.find(caminho)
        # Arquivo ausente já é erro de system check no boot (SPEC 001). Em runtime, um glifo
        # genérico degrada melhor que um buraco no meio do menu.
        if caminho_absoluto is None:
            return ICONE_GENERICO
        return Path(caminho_absoluto).read_text()

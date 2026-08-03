import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from services.utils.http import HttpFetchError

from .constants import SELETOR_SECAO, SUFIXO_PLANILHA
from .exceptions import ItbiEstruturaInesperadaError, ItbiPaginaError
from .models import ItbiPortalConfig, PlanilhaItbi

PADRAO_ANO = re.compile(r"\d{4}")


class ItbiPortalScraper:
    """Callable: página do portal → uma planilha por ano publicado, com URL absoluta."""

    def __init__(self, fetcher: Callable[..., Any]) -> None:
        self._fetcher = fetcher

    def __call__(self, config: ItbiPortalConfig) -> list[PlanilhaItbi]:
        return self.pipeline(config)

    def pipeline(self, config: ItbiPortalConfig) -> list[PlanilhaItbi]:
        html = self._baixar_pagina(config.url_pagina)
        secao = self._secao(html)
        planilhas = self._planilhas(secao, config.url_pagina)
        if not planilhas:
            raise ItbiEstruturaInesperadaError(
                f"{config.url_pagina}: nenhuma planilha {SUFIXO_PLANILHA} em {SELETOR_SECAO}"
            )
        return planilhas

    def _baixar_pagina(self, url_pagina: str) -> str:
        # O erro do utilitário morre aqui: para fora deste pacote só sai exceção da ITBI.
        try:
            return str(self._fetcher(url_pagina).text)
        except HttpFetchError as exc:
            raise ItbiPaginaError(f"página do portal: {exc}") from exc

    def _secao(self, html: str) -> Tag:
        secao = BeautifulSoup(html, "html.parser").select_one(SELETOR_SECAO)
        if secao is None:
            raise ItbiEstruturaInesperadaError(
                f"seção {SELETOR_SECAO} ausente: o portal mudou de layout"
            )
        return secao

    def _planilhas(self, secao: Tag, url_pagina: str) -> list[PlanilhaItbi]:
        planilhas: list[PlanilhaItbi] = []
        for item in secao.select("li"):
            planilha = self._item_para_planilha(item, url_pagina)
            if planilha is not None:
                planilhas.append(planilha)
        return planilhas

    def _item_para_planilha(self, item: Tag, url_pagina: str) -> PlanilhaItbi | None:
        ano = self._ano(item)
        url = self._url_planilha(item, url_pagina)
        if ano is None or url is None:
            return None
        return PlanilhaItbi(ano=ano, url=url)

    def _ano(self, item: Tag) -> int | None:
        """O ano é o do <strong>, não o do nome do arquivo — que traz a data de publicação."""
        rotulo = item.select_one("strong")
        if rotulo is None:
            return None
        encontrado = PADRAO_ANO.search(rotulo.get_text())
        if encontrado is None:
            return None
        return int(encontrado.group())

    def _url_planilha(self, item: Tag, url_pagina: str) -> str | None:
        for link in item.select("a[href]"):
            # urljoin em TODO link: absoluto passa intacto, relativo resolve contra a página —
            # e o portal já inverteu qual dos dois usa.
            url = urljoin(url_pagina, str(link["href"]))
            if url.lower().endswith(SUFIXO_PLANILHA):
                return url
        return None

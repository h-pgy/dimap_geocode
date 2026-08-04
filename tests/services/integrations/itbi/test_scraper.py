from unittest.mock import Mock

import pytest

from services.integrations.itbi import (
    ItbiEstruturaInesperadaError,
    ItbiPortalConfig,
    ItbiPortalScraper,
)

URL_PAGINA = "https://portal.test/acesso-a-informacao/itbi"

# O <li> de 2025 traz href relativo e nome de arquivo com a data de PUBLICAÇÃO (28012026) — é
# por isso que o ano vem do <strong>. O de 2024 traz href absoluto. Cada um tem seu .ods.
PAGINA_HTML = f"""
<html>
  <body>
    <section class="psp-agencies-other">
      <ul><li><strong>2099</strong>
        <a href="/documents/fora_da_secao.xlsx">Excel</a>
      </li></ul>
    </section>
    <section class="psp-agencies-content">
      <ul>
        <li>
          <strong>2025</strong>
          <a href="/documents/itbi%20(28012026).xlsx">Excel</a>
          <a href="/documents/itbi%20(28012026).ods">ODS</a>
        </li>
        <li>
          <strong>2024</strong>
          <a href="{URL_PAGINA}/../arquivos/itbi_2024.ods">ODS</a>
          <a href="https://arquivos.portal.test/itbi_2024.xlsx">Excel</a>
        </li>
      </ul>
    </section>
  </body>
</html>
"""


def _fetcher(html: str) -> Mock:
    resposta = Mock()
    resposta.text = html
    return Mock(return_value=resposta)


def test_scraper_extrai_ano_do_strong_e_resolve_url_relativa() -> None:
    planilhas = ItbiPortalScraper(_fetcher(PAGINA_HTML))(ItbiPortalConfig(url_pagina=URL_PAGINA))

    assert {planilha.ano: planilha.url for planilha in planilhas} == {
        2025: "https://portal.test/documents/itbi%20(28012026).xlsx",
        2024: "https://arquivos.portal.test/itbi_2024.xlsx",
    }
    # Dois itens: os .ods ficaram de fora, e a seção vizinha não foi varrida.
    assert len(planilhas) == 2


def test_scraper_sem_secao_esperada_levanta_erro_proprio() -> None:
    config = ItbiPortalConfig(url_pagina=URL_PAGINA)

    sem_secao = "<html><body><div><a href='/x.xlsx'>Excel</a></div></body></html>"
    with pytest.raises(ItbiEstruturaInesperadaError):
        ItbiPortalScraper(_fetcher(sem_secao))(config)

    # Seção presente e vazia é a mesma notícia: o CMS mudou o layout.
    secao_sem_xlsx = '<html><body><section class="psp-agencies-content"></section></body></html>'
    with pytest.raises(ItbiEstruturaInesperadaError):
        ItbiPortalScraper(_fetcher(secao_sem_xlsx))(config)


# O ano corrente é publicado como documento do CMS, sem extensão no href — os dois links do <li>
# terminam em "-xlsx"/"-ods" sem ponto, e só o rótulo os distingue.
PAGINA_SEM_EXTENSAO = """
<html><body>
  <section class="psp-agencies-content">
    <ul><li>
      <strong>2026 (Excel/xlsx) (ODS)</strong>
      <a href="/documents/d/fazenda/guias-de-itbi-pagas-4-xlsx">Excel/xlsx</a>
      <a href="/documents/d/fazenda/guias-de-itbi-pagas-2026-ods-2-ods">ODS</a>
    </li></ul>
  </section>
</body></html>
"""


def test_scraper_reconhece_planilha_sem_extensao_no_href() -> None:
    planilhas = ItbiPortalScraper(_fetcher(PAGINA_SEM_EXTENSAO))(
        ItbiPortalConfig(url_pagina=URL_PAGINA)
    )

    assert [(p.ano, p.url) for p in planilhas] == [
        (2026, "https://portal.test/documents/d/fazenda/guias-de-itbi-pagas-4-xlsx")
    ]

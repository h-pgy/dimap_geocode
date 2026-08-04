from collections.abc import Callable
from pathlib import Path

from services.integrations.itbi import ItbiIntegrationError, ItbiPortalConfig, PlanilhaItbi

from .constants import NOME_XLSX
from .models import ColetaItbi, ColetaStats, ItbiConfig


class ItbiColetor:
    """ETAPA 1: portal → arquivos na pasta. Não abre planilha, não apaga nada e não decide o
    que entra no parquet: só atualiza o que conseguir."""

    def __init__(
        self,
        scraper: Callable[[ItbiPortalConfig], list[PlanilhaItbi]],
        downloader: Callable[[PlanilhaItbi, Path], Path],
    ) -> None:
        self._scraper = scraper
        self._downloader = downloader
        self._baixados: list[int] = []
        self._falhas: dict[int, str] = {}

    def __call__(self, config: ItbiConfig, originais: Path) -> ColetaItbi:
        return self.pipeline(config, originais)

    def pipeline(self, config: ItbiConfig, originais: Path) -> ColetaItbi:
        planilhas = self._scraper(config.portal)
        for planilha in planilhas:
            self._baixar(planilha, originais)
        return ColetaItbi(
            stats=ColetaStats(
                anos_publicados=sorted(planilha.ano for planilha in planilhas),
                anos_baixados=sorted(self._baixados),
                falhas_por_ano=self._falhas,
            )
        )

    def _baixar(self, planilha: PlanilhaItbi, pasta: Path) -> None:
        try:
            self._downloader(planilha, pasta / NOME_XLSX.format(ano=planilha.ano))
        except ItbiIntegrationError as exc:
            # Sem fallback: o xlsx da carga anterior continua em disco e o parse vai
            # encontrá-lo sozinho. Aqui só se registra que este ano não atualizou.
            self._falhas[planilha.ano] = f"{type(exc).__name__}: {exc}"
            return
        self._baixados.append(planilha.ano)

from services.integrations.itbi import ItbiPlanilhaDownloader, ItbiPortalScraper, build_fetcher
from services.scripts.contrato import ScriptRunner
from services.utils.io import subpasta_de_data, write_dataframe_to_data
from services.utils.metadados import registrar_execucao

from .coletor import ItbiColetor
from .consolidador import ItbiConsolidador
from .constants import OUTPUT_FILENAME, PASTA_ORIGINAIS, PASTA_PARSEADOS
from .models import ItbiConfig, ItbiResult
from .parser import ItbiParser


def run(config: ItbiConfig, *, verbose: bool = False, manual: bool = True) -> ItbiResult:
    originais = subpasta_de_data(PASTA_ORIGINAIS)
    parseados = subpasta_de_data(PASTA_PARSEADOS)

    # UM fetcher para as duas chamadas: é o que faz a Session valer alguma coisa —
    # mesmos headers e mesma conexão para a página e para os downloads.
    fetcher = build_fetcher(config.portal, verbose=verbose)
    coletor = ItbiColetor(
        ItbiPortalScraper(fetcher),
        ItbiPlanilhaDownloader(fetcher),
    )

    with registrar_execucao(OUTPUT_FILENAME, manual=manual) as registro:
        coleta = coletor(config, originais)
        parse = ItbiParser()(originais, parseados, config.escopo)
        # A consolidação NUNCA filtra: é a projeção da pasta inteira, e é o que faz uma carga
        # `recente` continuar entregando o parquet com todos os anos.
        consolidacao = ItbiConsolidador()(parseados)
        output_path = write_dataframe_to_data(consolidacao.dados, OUTPUT_FILENAME)

        resultado = ItbiResult(
            escopo=config.escopo,
            coleta=coleta.stats,
            parse=parse.stats,
            consolidacao=consolidacao.stats,
            output_path=output_path,
            linhas_por_ano=consolidacao.linhas_por_ano if verbose else None,
        )
        # Sucesso parcial é sucesso — mas o que ficou velho, e o que caiu, tem que sobreviver
        # ao terminal: é daqui que sai o log do daemon dias depois.
        registro.sucesso(
            registros=resultado.consolidacao.total_records,
            detalhes=resultado.para_metadados(),
        )

    return resultado


_contrato: ScriptRunner[ItbiConfig, ItbiResult] = run

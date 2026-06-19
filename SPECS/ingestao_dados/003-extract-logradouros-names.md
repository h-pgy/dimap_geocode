---

## spec: ingestao-dados/003
versao: v2
atualizado_em: 2026-06-18
changelog:
v1: versão inicial
v2: remoção de valores nulos no modelo e adequação do uso de partials nas funções de IO.

# SPEC ingestao-dados/003 — Extração de nomes/codlogs únicos de logradouros (WFS para Parquet)

## User story

Como desenvolvedor do domínio, solicito a elaboração de um script de carga que utilize o WfsFetcher para extrair do WFS exclusivamente os atributos codlog, cd_tipo_logradouro e nm_logradouro da camada de segmentos de logradouro. O script deve deduplicar estes triplos e registrá-los em formato Parquet no diretório data/ da raiz do projeto. Esta base simplificada será consumida pelos scripts subsequentes, como a geração de variações de escrita e a construção do cache de lookup, eliminando a necessidade de novas requisições ao WFS ou de processamento de dados geométricos.

## Critérios de aceite

O script de domínio deve estar localizado em services/scripts/, correspondendo à subcamada estabelecida no §7.4, e deve compor o WfsFetcher sem importar recursos do framework Django, abstendo-se de reimplementar paginação ou protocolos HTTP.

A requisição enviada ao WFS deve especificar unicamente codlog, cd_tipo_logradouro e nm_logradouro através do parâmetro property_names da classe WfsFeatureRequest. Dados de geometria e outros atributos adicionais devem ser excluídos da requisição.

O processo de deduplicação deve ocorrer no lado do cliente. As páginas recebidas devem ser iteradas, acumulando unicamente as tuplas contendo codlog, cd_tipo_logradouro e nm_logradouro em uma estrutura de conjunto. As feições completas não devem ser retidas na memória.

As operações de entrada e saída referentes ao formato Parquet devem ser alocadas em services/utils/io/, configurando um utilitário neutro sem vínculo com o domínio, conforme §7.1. O módulo deve expor as funções originais write_parquet e read_parquet que exigirão obrigatoriamente os parâmetros filename e folder. O script de domínio deve compor estes utilitários utilizando functools.partial para gerar funções derivadas, como write_parquet_to_data, que fixam o parâmetro folder para apontar ao diretório de dados do projeto.

O resultado deve ser gravado no arquivo data/nomes_logradouros.parquet na raiz do projeto. O esquema do arquivo deve conter estritamente três colunas do tipo string: codlog, cd_tipo_logradouro e nm_logradouro. Não são admitidos valores nulos nestas colunas.

As informações de conexão, o nome da camada e o caminho do diretório de saída devem ser injetados no escopo do domínio por meio de WfsConnectionConfig e de um DTO de requisição. O domínio é impedido de ler configurações globais ou de resolver caminhos do sistema operacional de forma autônoma. O nome do arquivo resultante deve ser mantido como uma constante no módulo do script.

É necessário inserir a chave WFS_LAYER_LOGRADOUROS com o valor v_logradouro_segmento no diretório config/. Esta chave destina-se exclusivamente à leitura pelo comando de orquestração.

Um comando de gerenciamento deve ser criado em apps/logradouro_matcher/management/commands/. O comando lerá as configurações estabelecidas, resolverá o caminho físico do diretório data/, construirá os DTOs, acionará o script de domínio e emitirá relatório no canal padrão de saída, sem conter qualquer regra de negócio, em conformidade com o §8.

Exige-se tipagem de dados completa compatível com a ferramenta mypy. A importação de recursos do módulo **future** é vedada, conforme estipulado no §10.5.

A estrutura de diretórios em tests/ deve espelhar os pacotes de domínio e utilitários. Os testes automatizados via pytest devem ser formulados sem acesso à rede, empregando dublês de requisição para garantir a cobertura das operações de deduplicação, tratamento de dados e conversão para o formato Parquet.

## Contexto e decisões de arquitetura

A arquitetura abrange quatro segmentos operacionais independentes. O segmento utilitário neutro concentra as operações genéricas de entrada e saída em formato Parquet, sem relação direta com lógicas de domínio. O segmento de domínio implementa as regras relativas à extração, deduplicação e entrega de logradouros, compondo as abstrações necessárias. O segmento de orquestração faz a interface entre as configurações estáticas e os scripts orientados a domínio. O segmento de configurações armazena as chaves de integração.

A limitação da requisição aos três atributos estritos ocorre porque o payload nativo do WFS contém elementos geométricos extensos e metadados excedentes. O uso do property_names permite instruir o GeoServer a omitir o envio destes elementos não essenciais, reduzindo o volume de tráfego de rede e os ciclos de processamento de desserialização.

A deduplicação processada no cliente é necessária dada a ausência de suporte nativo à cláusula DISTINCT em consultas diretas ao protocolo WFS padrão. Segmentos colineares do mesmo logradouro figuram como registros separados no retorno. A consolidação é feita pela conversão dos dados paginados em tuplas simplificadas de texto, registradas em estruturas de conjuntos da linguagem.

A extração das funções de manipulação de Parquet para utilities visa o reaproveitamento por outros fluxos de carga projetados para o sistema. O desenho exige que as funções originais recebam a pasta base como parâmetro formal. As lógicas de domínio aplicam ferramentas de programação funcional para pré-configurar estes caminhos fixos via partials, mitigando acoplamentos estruturais profundos e definindo a biblioteca pyarrow como dependência estrita para estas rotinas.

A execução não contempla normalização semântica nesta etapa. Os dados consumidos preservam o formato oficial do banco de origem. O tratamento padronizado e a identificação de variações serão delegados a uma etapa sucessiva, operada por script dedicado, garantindo a especialização do módulo desenvolvido.

A injeção de dependências ocorre diretamente nos construtores das classes extratoras, garantindo testabilidade em isolamento. As entradas e saídas utilizam modelos validados via Pydantic.

## Peças de referência a compor

WfsFetcher, WfsFeatureRequest, WfsConnectionConfig e WfsFeatureCollection devem ser compostos a partir de services/integrations/wfs para execução da busca paginada e validação de tipos.

As chaves WFS_DOMAIN, WFS_ENDPOINT, WFS_SERVICE, WFS_VERSION, WFS_NAMESPACE e WFS_LAYER_LOGRADOUROS devem ser lidas a partir de config/ somente pelo comando de orquestração.

O subpacote utils/io deve ser implementado para as funções fundamentais de leitura e gravação no formato Parquet, parametrizando sempre o arquivo e a pasta de destino de forma explícita.

## Snippets sugeridos

```python
# services/utils/io/parquet.py
from collections.abc import Mapping, Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

Columns = Mapping[str, Sequence[object]]

def write_parquet(columns: Columns, filename: str, folder: Path | str) -> Path:
    path = Path(folder) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(dict(columns)), path)
    return path

def read_parquet(filename: str, folder: Path | str) -> dict[str, list[object]]:
    path = Path(folder) / filename
    return pq.read_table(path).to_pydict()

```

```python
# services/utils/io/__init__.py
from .parquet import read_parquet, write_parquet

__all__ = [
    "write_parquet",
    "read_parquet",
]

```

```python
# services/scripts/logradouros/models.py
from pathlib import Path
from pydantic import BaseModel

class NomesLogradourosRequest(BaseModel):
    layer_name: str
    data_folder: Path

class LogradouroNome(BaseModel):
    codlog: str
    cd_tipo_logradouro: str
    nm_logradouro: str

class NomesLogradourosResult(BaseModel):
    total_unique: int
    output_path: Path

```

```python
# services/scripts/logradouros/extractor.py
from collections.abc import Callable, Iterable
from services.integrations.wfs import WfsFeatureRequest, WfsFeatureCollection
from .models import LogradouroNome, NomesLogradourosRequest

PROPERTY_NAMES: list[str] = ["codlog", "cd_tipo_logradouro", "nm_logradouro"]
PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

def _as_str(value: object) -> str:
    return "" if value is None else str(value)

class NomesLogradourosExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: NomesLogradourosRequest) -> list[LogradouroNome]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=PROPERTY_NAMES,
            count=PAGE_SIZE,
        )
        seen: set[tuple[str, str, str]] = set()
        
        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties
                codlog = props.get("codlog")
                if codlog is None:
                    continue
                seen.add((
                    str(codlog),
                    _as_str(props.get("cd_tipo_logradouro")),
                    _as_str(props.get("nm_logradouro"))
                ))
                
        return [LogradouroNome(codlog=c, cd_tipo_logradouro=t, nm_logradouro=n)
                for c, t, n in sorted(seen, key=lambda k: (k[0], k[2]))]

```

```python
# services/scripts/logradouros/__init__.py
from functools import partial
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher
from services.utils.io import write_parquet

from .extractor import NomesLogradourosExtractor
from .models import LogradouroNome, NomesLogradourosRequest, NomesLogradourosResult

OUTPUT_FILENAME: str = "nomes_logradouros.parquet"

__all__ = [
    "run",
    "OUTPUT_FILENAME",
    "NomesLogradourosExtractor",
    "NomesLogradourosRequest",
    "NomesLogradourosResult",
    "LogradouroNome",
]

def _to_columns(rows: list[LogradouroNome]) -> dict[str, list[str]]:
    return {
        "codlog": [r.codlog for r in rows],
        "cd_tipo_logradouro": [r.cd_tipo_logradouro for r in rows],
        "nm_logradouro": [r.nm_logradouro for r in rows],
    }

def run(
    config: WfsConnectionConfig,
    request: NomesLogradourosRequest,
    verbose: bool = False,
) -> NomesLogradourosResult:
    fetcher = WfsFetcher(config, verbose=verbose)
    rows = NomesLogradourosExtractor(fetcher)(request)
    
    write_parquet_to_data = partial(write_parquet, folder=request.data_folder)
    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
    
    return NomesLogradourosResult(
        total_unique=len(rows),
        output_path=output_path,
    )

```

```python
# apps/logradouro_matcher/management/commands/extrair_nomes_logradouros.py
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import WfsConnectionConfig
from services.scripts.logradouros import NomesLogradourosRequest, run

class Command(BaseCommand):
    help = "Extrai codlog/tipo/nome únicos de logradouros do WFS e salva em data/nomes_logradouros.parquet."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = WfsConnectionConfig(
            domain=settings.WFS_DOMAIN,
            endpoint=settings.WFS_ENDPOINT,
            namespace=settings.WFS_NAMESPACE,
            service=settings.WFS_SERVICE,
            version=settings.WFS_VERSION,
        )
        request = NomesLogradourosRequest(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
            data_folder=Path(settings.BASE_DIR) / "data",
        )
        result = run(config, request, verbose=bool(options["verbose"]))
        self.stdout.write(self.style.SUCCESS(
            f"{result.total_unique} logradouros únicos salvos em {result.output_path}"
        ))

```

```python
# tests/services/utils/io/test_parquet.py
from pathlib import Path
from services.utils.io import read_parquet, write_parquet

def test_write_and_read_roundtrip_with_folder(tmp_path):
    cols = {"codlog": ["168610", "100000"], "nm_logradouro": ["RAMOS DE AZEVEDO", "DIREITA"]}
    path = write_parquet(cols, "nomes.parquet", folder=tmp_path)
    assert path == Path(tmp_path) / "nomes.parquet"
    assert read_parquet("nomes.parquet", folder=tmp_path) == cols

def test_write_creates_missing_folder(tmp_path):
    sub = tmp_path / "data"
    write_parquet({"codlog": ["1"]}, "x.parquet", folder=sub)
    assert (sub / "x.parquet").exists()

```

```python
# tests/services/scripts/logradouros/test_extractor.py
from services.integrations.wfs import WfsFeatureCollection
from services.scripts.logradouros.extractor import NomesLogradourosExtractor
from services.scripts.logradouros.models import NomesLogradourosRequest

def _page(props_list):
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(props_list),
        "features": [{"type": "Feature", "properties": p} for p in props_list],
    })

def _req():
    return NomesLogradourosRequest(layer_name="v_logradouro_segmento", data_folder=".")

def test_dedups_triples_across_pages():
    pages = [
        _page([
            {"codlog": "168610", "cd_tipo_logradouro": "PC", "nm_logradouro": "RAMOS DE AZEVEDO"},
            {"codlog": "168610", "cd_tipo_logradouro": "PC", "nm_logradouro": "RAMOS DE AZEVEDO"},
        ]),
        _page([{"codlog": "100000", "cd_tipo_logradouro": "R", "nm_logradouro": "DIREITA"}]),
    ]
    rows = NomesLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 2
    assert rows[0].codlog == "100000"

def test_skips_rows_without_codlog_and_converts_nulls_to_empty_strings():
    pages = [_page([
        {"codlog": None, "cd_tipo_logradouro": "R", "nm_logradouro": "SEM CODLOG"},
        {"codlog": "200000", "cd_tipo_logradouro": None, "nm_logradouro": None},
    ])]
    rows = NomesLogradourosExtractor(lambda req: iter(pages))(_req())
    assert [r.codlog for r in rows] == ["200000"]
    assert rows[0].cd_tipo_logradouro == "" and rows[0].nm_logradouro == ""

def test_ignores_geometry_when_present():
    pages = [_page([{
        "codlog": "168610", "cd_tipo_logradouro": "PC", "nm_logradouro": "RAMOS DE AZEVEDO",
        "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
    }])]
    rows = NomesLogradourosExtractor(lambda req: iter(pages))(_req())
    assert rows[0].nm_logradouro == "RAMOS DE AZEVEDO"

```

## Fora de escopo

A geração de variações de escrita e a etapa de normalização ocorrerão em escopos subsequentes.
A construção do cache de persistência para leitura em bancos PostGIS está reservada para épicos próprios.
A extração de endereços fiscais e a carga de lotes configuram domínios isolados, com documentações particulares.
Qualquer tratamento com finalidade analítica ou de reprojeção sobre as geometrias vetoriais não será realizado no script em questão.
O acionamento das configurações dentro dos arquivos do domínio permanece proscrito, cabendo à orquestração suprir os parâmetros via construtor.
O uso de visualizações formatadas no lado do GeoServer para gerar agrupamentos nativos encontra-se fora do escopo institucional atual.
Outros formatos de gravação, a exemplo de delimitações por vírgula ou serialização GeoJSON, não são tratados na presente especificação.

## Notas de teste

Testar a classe NomesLogradourosExtractor injetando dublês que retornam iteráveis de WfsFeatureCollection. Testar a interface run aplicando simulação para as bibliotecas de rede a fim de validar a integração ponta a ponta gravando os resultados em um diretório temporário.
Para a extração, assegurar cobertura da consolidação das chaves repedidas, garantindo a eliminação de registros desprovidos do logradouro e a conversão mandatória de campos ausentes em cadeias de texto vazias.
Para os utilitários de saída, aferir a capacidade de criação automática de diretórios não pré-existentes, confirmando o esquema restrito das três colunas textuais na operação de ida e volta.
Certificar que estruturas de retorno dotadas de propriedades geométricas indesejadas pelo GeoServer não interrompam a desserialização das feições principais. Identificar possíveis falhas de paginação que produzam páginas de tamanho ignorado sem comprometer a terminação do laço principal do iterador WFS.
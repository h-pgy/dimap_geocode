---

spec: ingestao-dados/005
versao: v8
atualizado_em: 2026-06-19
changelog:

* v1: versão inicial
* v2: inclusão do parâmetro property_names no DTO de requisição e adequação do fluxo
* v3: centralização dos atributos em arquivo de constantes no escopo do domínio e remoção da injeção via orquestrador
* v4: refatoração da construção de dicionários e transposição de colunas utilizando iteração dinâmica sobre a constante de atributos
* v5: simplificação do laço de extração e delegação da conversão de tipos
* v6: remoção de função auxiliar de conversão e adoção de condicional inline na construção do dicionário
* v7: correção do cql_filter — substituição de string literal por utils.cql_eq via services/integrations/wfs/utils
* v8: nr_contribuinte removido — campo não é retornado pelo WFS; cd_identificador passa a ser o único campo obrigatório e chave de ordenação

---

# SPEC ingestao-dados/005 — Extração de endereços fiscais do cadastro de lotes (WFS para Parquet)

## User story

Como desenvolvedor do domínio, quero um script de carga que extraia da camada de lotes do WFS os atributos de endereço de porta vinculados a cada número de contribuinte, filtrando apenas os registros ativos e salvando-os em arquivo Parquet no diretório data/, para criar um mapeamento tabular de endereços fiscais sem o descarregamento de dados geométricos.

## Critérios de aceite

* [ ] O script de extração reside em services/scripts/enderecos_fiscais/, não importa recursos do Django e compõe o WfsFetcher.
* [ ] Os atributos alvo são definidos em uma constante centralizada no arquivo constants.py dentro do módulo do domínio.
* [ ] A requisição WFS solicita os atributos mapeados na constante interna via property_names do WfsFeatureRequest, omitindo geometrias.
* [ ] A chamada ao WFS inclui o parâmetro cql_filter definido como cd_situacao=1 para restringir a busca aos lotes ativos.
* [ ] A paginação itera sobre as respostas e acumula os registros em memória construindo os dicionários de forma dinâmica baseada na constante de atributos, com conversão de tipos inline e preservação de nulos.
* [ ] O módulo de domínio utiliza a função partial pré-existente write_parquet_to_data de services/utils/io/ para persistência direta na pasta de dados, com a transposição de linhas para colunas realizada iterativamente via getattr.
* [ ] O arquivo de saída é gravado como data/enderecos_fiscais.parquet contendo as colunas mapeadas.
* [ ] O modelo Pydantic define cd_identificador como único campo obrigatório, mantendo os demais atributos de localização como opcionais com valor nulo nativo.
* [ ] O nome da camada geoportal:lote_cidadao é configurado no management command e injetado no domínio por meio do DTO de requisição, sem repasse de atributos.
* [ ] Existe um management command em apps/address_geocoder/management/commands/ que orquestra o processo.
* [ ] O código possui tipagem estrita compatível com mypy e não utiliza importações do módulo future.
* [ ] Testes automatizados validam o fluxo sem acesso à rede, utilizando fetchers dublês.

## Contexto e decisões de arquitetura

A rotina consolida o repositório de endereços oficiais associados a contribuintes do município. A supressão das geometrias de polígonos durante a integração com o GeoServer viabiliza o processamento da volumetria estipulada em 3,6 milhões de registros. A organização em formato Parquet garante que o domínio acesse a totalidade da base para roteamento e correspondência de buscas sem onerar a latência da aplicação web.

O fluxo mantém conformidade estrutural com os scripts anteriores de ingestão. O isolamento no pacote enderecos_fiscais cumpre a diretiva de separação por domínio de dados. A centralização dos atributos na camada de domínio e o uso de iteração dinâmica para construção de dicionários e colunas eliminam a redundância de código, facilitando a adição futura de novos campos sem refatoração em múltiplos arquivos. A conversão de tipos estruturada em condicional inline previne a coerção inadequada e assegura a validação estrita pelo Pydantic. A gravação delega ao utilitário neutro a resolução de caminhos no sistema operacional.

## Peças de referência a compor

A comunicação paginada consome os componentes WfsFetcher, WfsConnectionConfig, WfsFeatureRequest e WfsFeatureCollection presentes no pacote services/integrations/wfs. A consolidação de dados aciona o método write_parquet_to_data estruturado no pacote services/utils/io/. A execução depende da leitura de configurações de integração do Django promovida pelo management command do aplicativo address_geocoder, que deve registrar a nova chave WFS_LAYER_LOTE_CIDADAO correspondente ao valor geoportal:lote_cidadao.

## Snippets sugeridos

```python
# services/scripts/enderecos_fiscais/constants.py
ATRIBUTOS_ALVO: list[str] = [
    "cd_identificador",
    "cd_setor_fiscal",
    "cd_tipo_quadra",
    "cd_quadra_fiscal",
    "cd_condominio",
    "cd_tipo_lote",
    "cd_lote",
    "cd_digito_sql",
    "cd_logradouro",
    "nm_logradouro_completo",
    "cd_numero_porta",
    "tx_complemento_endereco",
    "nr_contribuinte",
]

```

```python
# services/scripts/enderecos_fiscais/models.py
from pathlib import Path
from pydantic import BaseModel

class EnderecosFiscaisRequest(BaseModel):
    layer_name: str

class EnderecoFiscal(BaseModel):
    nr_contribuinte: str
    cd_identificador: str
    cd_setor_fiscal: str | None = None
    cd_tipo_quadra: str | None = None
    cd_quadra_fiscal: str | None = None
    cd_condominio: str | None = None
    cd_tipo_lote: str | None = None
    cd_lote: str | None = None
    cd_digito_sql: str | None = None
    cd_logradouro: str | None = None
    nm_logradouro_completo: str | None = None
    cd_numero_porta: str | None = None
    tx_complemento_endereco: str | None = None

class EnderecosFiscaisResult(BaseModel):
    total_records: int
    output_path: Path

```

```python
# services/scripts/enderecos_fiscais/extractor.py
from collections.abc import Callable, Iterable
from services.integrations import wfs
from services.integrations.wfs import WfsFeatureRequest, WfsFeatureCollection
from .constants import ATRIBUTOS_ALVO
from .models import EnderecoFiscal, EnderecosFiscaisRequest

PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

class EnderecosFiscaisExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: EnderecosFiscaisRequest) -> list[EnderecoFiscal]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=ATRIBUTOS_ALVO,
            count=PAGE_SIZE,
            cql_filter=wfs.utils.cql_eq("cd_situacao", 1),
        )
        records: list[EnderecoFiscal] = []
        
        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties
                
                if props.get("nr_contribuinte") is None or props.get("cd_identificador") is None:
                    continue
                    
                kwargs = {k: str(props.get(k)) if props.get(k) is not None else None for k in ATRIBUTOS_ALVO}
                records.append(EnderecoFiscal(**kwargs))
                
        return sorted(records, key=lambda x: x.nr_contribuinte)

```

```python
# services/scripts/enderecos_fiscais/__init__.py
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher
from services.utils.io import write_parquet_to_data
from .constants import ATRIBUTOS_ALVO
from .extractor import EnderecosFiscaisExtractor
from .models import EnderecoFiscal, EnderecosFiscaisRequest, EnderecosFiscaisResult

OUTPUT_FILENAME: str = "enderecos_fiscais.parquet"

__all__ = [
    "run",
    "OUTPUT_FILENAME",
    "EnderecosFiscaisExtractor",
    "EnderecosFiscaisRequest",
    "EnderecosFiscaisResult",
    "EnderecoFiscal",
]

def _to_columns(rows: list[EnderecoFiscal]) -> dict[str, list[str | None]]:
    cols: dict[str, list[str | None]] = {attr: [] for attr in ATRIBUTOS_ALVO}
    for row in rows:
        for attr in ATRIBUTOS_ALVO:
            cols[attr].append(getattr(row, attr))
    return cols

def run(
    config: WfsConnectionConfig,
    request: EnderecosFiscaisRequest,
    verbose: bool = False,
) -> EnderecosFiscaisResult:
    fetcher = WfsFetcher(config, verbose=verbose)
    rows = EnderecosFiscaisExtractor(fetcher)(request)
    
    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
    
    return EnderecosFiscaisResult(
        total_records=len(rows),
        output_path=output_path,
    )

```

```python
# apps/address_geocoder/management/commands/extrair_enderecos_fiscais.py
from django.conf import settings
from django.core.management.base import BaseCommand
from services.integrations.wfs import WfsConnectionConfig
from services.scripts.enderecos_fiscais import EnderecosFiscaisRequest, run

class Command(BaseCommand):
    help = "Extrai enderecos de porta do cadastro de lotes do WFS para arquivo Parquet."

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
        
        request = EnderecosFiscaisRequest(
            layer_name=settings.WFS_LAYER_LOTE_CIDADAO,
        )
        
        result = run(config, request, verbose=bool(options["verbose"]))
        self.stdout.write(self.style.SUCCESS(
            f"Concluido. {result.total_records} registros salvos em {result.output_path}"
        ))

```

```python
# tests/services/scripts/enderecos_fiscais/test_extractor.py
from services.integrations.wfs import WfsFeatureCollection
from services.scripts.enderecos_fiscais.extractor import EnderecosFiscaisExtractor
from services.scripts.enderecos_fiscais.models import EnderecosFiscaisRequest

def _page(props_list):
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(props_list),
        "features": [{"type": "Feature", "properties": p} for p in props_list],
    })

def _req():
    return EnderecosFiscaisRequest(layer_name="geoportal:lote_cidadao")

def test_extracts_addresses_and_keeps_nulls():
    pages = [
        _page([
            {
                "nr_contribuinte": "001002003",
                "cd_identificador": "57088",
                "nm_logradouro_completo": "RAMOS DE AZEVEDO",
                "cd_numero_porta": "81",
                "tx_complemento_endereco": None
            }
        ])
    ]
    rows = EnderecosFiscaisExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 1
    assert rows[0].nr_contribuinte == "001002003"
    assert rows[0].cd_identificador == "57088"
    assert rows[0].tx_complemento_endereco is None

def test_ignores_records_with_missing_mandatory_keys():
    pages = [_page([
        {"nr_contribuinte": None, "cd_identificador": "57088"},
        {"nr_contribuinte": "001002003", "cd_identificador": None},
    ])]
    rows = EnderecosFiscaisExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 0

```

## Fora de escopo

Esta especificação não engloba o processamento de geometrias poligonais ou coordenadas espaciais. A normalização textual avançada ou correção ortográfica de logradouros pertencem a etapas posteriores. A filtragem de lotes inativos por lógicas internas do domínio fica excluída, sendo delegada diretamente à origem via parâmetro de consulta cql_filter.

## Notas de teste

Os testes unitários devem validar o comportamento do extrator com dublês de paginação sem efetuar conexões externas. Os cenários precisam cobrir o descarte de feições sem identificador principal ou número de contribuinte e a correta manutenção de valores nulos nos campos opcionais. A validação do arquivo final deve inspecionar a presença exata das colunas declaradas através do modelo e iteradas dinamicamente.

## Patches

- 2026-06-19 (v7): cql_filter do extractor estava tipado como string literal; corrigido para usar `wfs.utils.cql_eq("cd_situacao", 1)`. A função `cql_eq` foi criada em `services/integrations/wfs/utils.py` junto com as demais funções utilitárias de construção de filtros CQL (`cql_not_eq`, `cql_gt`, `cql_lt`, `cql_gte`, `cql_lte`, `cql_like`, `cql_ilike`), expostas via `from services.integrations import wfs`.
- 2026-06-19 (v8): nr_contribuinte não é retornado pelo WFS da camada lote_cidadao; campo removido de ATRIBUTOS_ALVO, do modelo EnderecoFiscal e da guard do extractor. cd_identificador passa a ser o único campo obrigatório e chave de ordenação do resultado.
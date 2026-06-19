---

spec: ingestao-dados/004
versao: v6
atualizado_em: 2026-06-18
changelog:

* v1: versão inicial
* v2: alteração do diretório para segmentos_logradouros e consolidação dos atributos
* v3: inclusão dos atributos numéricos de numeração par e ímpar
* v4: adequação do formato dos critérios de aceite, redução de verbosidade e tipagem opcional para atributos numéricos
* v5: correção do fluxo de IO, adotando a função write_parquet_in pré-existente
* v6: remoção do parâmetro data_folder do DTO e adoção da partial pré-existente write_parquet_to_data

---

# SPEC ingestao-dados/004 — Extração de mapeamento entre segmentos e logradouros (WFS para Parquet)

## User story

Como desenvolvedor do domínio, quero um script de carga que extraia da camada de segmentos do WFS os identificadores e intervalos de numeração viária, salvando-os em arquivo Parquet no diretório data/, para indexar a relação entre logradouros e segmentos viários sem trafegar dados geométricos.

## Critérios de aceite

* [ ] O script de extração reside em services/scripts/segmentos_logradouros/, não importa recursos do Django e compõe o WfsFetcher.
* [ ] A requisição WFS solicita exclusivamente codlog, cd_identificador, cd_numero_inicial_par, cd_numero_final_par, cd_numero_inicial_impar e cd_numero_final_impar via property_names do WfsFeatureRequest, omitindo geometrias.
* [ ] A paginação itera sobre as respostas e acumula os registros em memória estruturados por colunas, sem aplicar rotinas de deduplicação.
* [ ] O módulo de domínio utiliza a função partial pré-existente write_parquet_to_data de services/utils/io/, que já fixa a gravação no diretório data/, eliminando a necessidade de passagem de caminhos de pasta via DTO.
* [ ] O arquivo de saída é gravado como data/segmentos_logradouros.parquet contendo as seis colunas mapeadas.
* [ ] O modelo Pydantic define os quatro atributos de numeração como opcionais, tolerando valores nulos oriundos da base cartográfica, e o DTO de requisição recebe apenas o nome da camada.
* [ ] O nome da camada é resolvido pela orquestração e injetado no construtor via DTO, mantendo o domínio independente da leitura direta de configurações do sistema.
* [ ] Existe um management command em apps/logradouro_matcher/management/commands/ que orquestra o processo, lendo as chaves de integração e injetando as dependências na camada de domínio.
* [ ] O código possui tipagem estrita compatível com mypy e não utiliza importações do módulo future.
* [ ] Testes automatizados validam o fluxo sem acesso à rede, utilizando fetchers dublês para verificar a extração de dados e o tratamento de valores nulos.

## Contexto e decisões de arquitetura

A rotina mapeia a estrutura da malha viária, documentando a relação de um para muitos entre códigos de logradouros e identificadores de segmento. O armazenamento tabular sem geometria otimiza buscas e permite a futura interpolação de endereços fiscais utilizando os limites de numeração par e ímpar extraídos.

A arquitetura isola a extração de segmentos do domínio de tratamento de nomes, seguindo o princípio de responsabilidade única. A persistência adota a partial padronizada já presente no projeto, que encapsula o caminho de destino e abstrai a complexidade do sistema de arquivos para o script de domínio. O management command atua como orquestrador exclusivo, resolvendo as configurações antes de acionar a lógica de domínio.

Valores ausentes nos limites de numeração são preservados como nulos no modelo de dados, refletindo a realidade cartográfica de trechos viários sem emplacamento definido.

## Peças de referência a compor

O módulo compõe WfsFetcher, WfsConnectionConfig, WfsFeatureRequest e WfsFeatureCollection disponíveis em services/integrations/wfs para gerenciar a comunicação paginada com o GeoServer.

A escrita do arquivo utiliza a função write_parquet_to_data exposta por services/utils/io/.

A orquestração via management command lê as chaves de ambiente do Django que definem credenciais e o nome da camada geográfica, repassando os parâmetros ao script isolado.

## Snippets sugeridos

```python
# services/scripts/segmentos_logradouros/models.py
from pathlib import Path
from pydantic import BaseModel

class SegmentosLogradourosRequest(BaseModel):
    layer_name: str

class SegmentoLogradouro(BaseModel):
    codlog: str
    cd_identificador: str
    cd_numero_inicial_par: str | None = None
    cd_numero_final_par: str | None = None
    cd_numero_inicial_impar: str | None = None
    cd_numero_final_impar: str | None = None

class SegmentosLogradourosResult(BaseModel):
    total_segments: int
    output_path: Path

```

```python
# services/scripts/segmentos_logradouros/extractor.py
from collections.abc import Callable, Iterable
from services.integrations.wfs import WfsFeatureRequest, WfsFeatureCollection
from .models import SegmentoLogradouro, SegmentosLogradourosRequest

PROPERTY_NAMES: list[str] = [
    "codlog",
    "cd_identificador",
    "cd_numero_inicial_par",
    "cd_numero_final_par",
    "cd_numero_inicial_impar",
    "cd_numero_final_impar",
]
PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

def _as_str(value: object) -> str | None:
    return None if value is None else str(value)

class SegmentosLogradourosExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: SegmentosLogradourosRequest) -> list[SegmentoLogradouro]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=PROPERTY_NAMES,
            count=PAGE_SIZE,
        )
        records: list[SegmentoLogradouro] = []
        
        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties
                codlog = props.get("codlog")
                cd_identificador = props.get("cd_identificador")
                if codlog is None or cd_identificador is None:
                    continue
                records.append(SegmentoLogradouro(
                    codlog=str(codlog),
                    cd_identificador=str(cd_identificador),
                    cd_numero_inicial_par=_as_str(props.get("cd_numero_inicial_par")),
                    cd_numero_final_par=_as_str(props.get("cd_numero_final_par")),
                    cd_numero_inicial_impar=_as_str(props.get("cd_numero_inicial_impar")),
                    cd_numero_final_impar=_as_str(props.get("cd_numero_final_impar"))
                ))
                
        return sorted(records, key=lambda x: (x.codlog, x.cd_identificador))

```

```python
# services/scripts/segmentos_logradouros/__init__.py
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher
from services.utils.io import write_parquet_to_data
from .extractor import SegmentosLogradourosExtractor
from .models import SegmentoLogradouro, SegmentosLogradourosRequest, SegmentosLogradourosResult

OUTPUT_FILENAME: str = "segmentos_logradouros.parquet"

__all__ = [
    "run",
    "OUTPUT_FILENAME",
    "SegmentosLogradourosExtractor",
    "SegmentosLogradourosRequest",
    "SegmentosLogradourosResult",
    "SegmentoLogradouro",
]

def _to_columns(rows: list[SegmentoLogradouro]) -> dict[str, list[str | None]]:
    return {
        "codlog": [r.codlog for r in rows],
        "cd_identificador": [r.cd_identificador for r in rows],
        "cd_numero_inicial_par": [r.cd_numero_inicial_par for r in rows],
        "cd_numero_final_par": [r.cd_numero_final_par for r in rows],
        "cd_numero_inicial_impar": [r.cd_numero_inicial_impar for r in rows],
        "cd_numero_final_impar": [r.cd_numero_final_impar for r in rows],
    }

def run(
    config: WfsConnectionConfig,
    request: SegmentosLogradourosRequest,
    verbose: bool = False,
) -> SegmentosLogradourosResult:
    fetcher = WfsFetcher(config, verbose=verbose)
    rows = SegmentosLogradourosExtractor(fetcher)(request)
    
    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
    
    return SegmentosLogradourosResult(
        total_segments=len(rows),
        output_path=output_path,
    )

```

```python
# apps/logradouro_matcher/management/commands/extrair_segmentos_logradouros.py
from django.conf import settings
from django.core.management.base import BaseCommand
from services.integrations.wfs import WfsConnectionConfig
from services.scripts.segmentos_logradouros import SegmentosLogradourosRequest, run

class Command(BaseCommand):
    help = "Extrai metadados e limites de numeracao da camada de segmentos do WFS para arquivo Parquet."

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
        request = SegmentosLogradourosRequest(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
        )
        result = run(config, request, verbose=bool(options["verbose"]))
        self.stdout.write(self.style.SUCCESS(
            f"Concluido. {result.total_segments} segmentos salvos em {result.output_path}"
        ))

```

```python
# tests/services/scripts/segmentos_logradouros/test_extractor.py
from services.integrations.wfs import WfsFeatureCollection
from services.scripts.segmentos_logradouros.extractor import SegmentosLogradourosExtractor
from services.scripts.segmentos_logradouros.models import SegmentosLogradourosRequest

def _page(props_list):
    return WfsFeatureCollection.model_validate({
        "type": "FeatureCollection",
        "numberMatched": len(props_list),
        "features": [{"type": "Feature", "properties": p} for p in props_list],
    })

def _req():
    return SegmentosLogradourosRequest(layer_name="v_logradouro_segmento")

def test_extracts_segments_and_keeps_nulls():
    pages = [
        _page([
            {
                "codlog": "168610",
                "cd_identificador": 57088,
                "cd_numero_inicial_par": None,
                "cd_numero_final_par": None,
                "cd_numero_inicial_impar": 81,
                "cd_numero_final_impar": 181
            }
        ])
    ]
    rows = SegmentosLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 1
    assert rows[0].codlog == "168610"
    assert rows[0].cd_identificador == "57088"
    assert rows[0].cd_numero_inicial_par is None
    assert rows[0].cd_numero_final_par is None
    assert rows[0].cd_numero_inicial_impar == "81"
    assert rows[0].cd_numero_final_impar == "181"

def test_ignores_records_with_missing_mandatory_keys():
    pages = [_page([
        {"codlog": None, "cd_identificador": 1234},
        {"codlog": "300000", "cd_identificador": None},
    ])]
    rows = SegmentosLogradourosExtractor(lambda req: iter(pages))(_req())
    assert len(rows) == 0

```

## Fora de escopo

O processamento de coordenadas geográficas e a manipulação de objetos espaciais não integram este escopo.

A deduplicação de identificadores não é aplicada, respeitando a atomicidade dos segmentos viários.

Mecanismos de recuperação de códigos ausentes ou inferência espacial para preenchimento de dados nulos estão excluídos desta operação de extração pura.

## Notas de teste

Testes unitários devem garantir o comportamento do extrator mediante a injeção de dublês que simulam o retorno do GeoServer.

Casos de teste devem avaliar o correto mapeamento de valores nulos nos atributos opcionais e o descarte sumário de feições que não apresentem codlog ou cd_identificador na propriedade lida.

A integridade do esquema do arquivo Parquet deve ser aferida para confirmar a presença das seis colunas declaradas no modelo.

## Patches
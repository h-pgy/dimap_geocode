from services.scripts.pipeline import AtualizacaoConfig, PipelineAtualizacao

ETAPAS: tuple[str, ...] = (
    "extrair_segmentos_logradouros",
    "extrair_nomes_logradouros",
    "extrair_enderecos_fiscais",
    "augment_logradouro_types",
)


class ExecutorFake:
    """Substitui o `call_command`: registra a ordem e levanta na etapa combinada."""

    def __init__(self, falha_em: str | None = None) -> None:
        self.chamadas: list[str] = []
        self._falha_em = falha_em

    def __call__(self, etapa: str) -> None:
        self.chamadas.append(etapa)
        if etapa == self._falha_em:
            raise RuntimeError("GeoSampa fora do ar")


def test_pipeline_executa_etapas_na_ordem() -> None:
    executor = ExecutorFake()

    resultado = PipelineAtualizacao(executor)(AtualizacaoConfig(etapas=ETAPAS))

    assert executor.chamadas == list(ETAPAS)
    assert resultado.executadas == list(ETAPAS)
    assert resultado.falhou_em is None
    assert resultado.erro is None


def test_pipeline_aborta_na_primeira_falha() -> None:
    executor = ExecutorFake(falha_em="extrair_nomes_logradouros")

    resultado = PipelineAtualizacao(executor)(AtualizacaoConfig(etapas=ETAPAS))

    # A 3ª e a 4ª consomem o artefato das anteriores: não podem rodar sobre carga velha.
    assert executor.chamadas == [
        "extrair_segmentos_logradouros",
        "extrair_nomes_logradouros",
    ]
    assert resultado.executadas == ["extrair_segmentos_logradouros"]
    assert resultado.falhou_em == "extrair_nomes_logradouros"
    assert resultado.erro is not None
    assert "GeoSampa fora do ar" in resultado.erro

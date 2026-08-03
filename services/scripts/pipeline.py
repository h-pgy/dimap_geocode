from collections.abc import Callable

from pydantic import BaseModel


class AtualizacaoConfig(BaseModel):
    etapas: tuple[str, ...]


class AtualizacaoResult(BaseModel):
    executadas: list[str]
    falhou_em: str | None = None
    erro: str | None = None


class PipelineAtualizacao:
    """Executa as etapas na ordem recebida e para na primeira falha.

    Não sabe o que é management command: recebe nomes de etapa e um executor por composição.
    """

    def __init__(self, executar: Callable[[str], None]) -> None:
        self._executar = executar

    def __call__(self, config: AtualizacaoConfig) -> AtualizacaoResult:
        executadas: list[str] = []

        for etapa in config.etapas:
            try:
                self._executar(etapa)
            except Exception as exc:
                # A etapa seguinte consome o artefato desta: seguir produziria cache de dado velho.
                return AtualizacaoResult(
                    executadas=executadas,
                    falhou_em=etapa,
                    erro=f"{type(exc).__name__}: {exc}",
                )
            executadas.append(etapa)

        return AtualizacaoResult(executadas=executadas)

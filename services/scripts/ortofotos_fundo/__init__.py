from services.scripts.contrato import ScriptRunner

from .contrato import OrtofotoConfig, OrtofotoResultado
from .enquadramento import enquadrar
from .gerador import GeradorOrtofotosFundo

# Satisfaz o contrato estrutural de services/scripts/ (skill management-commands): todo
# subpacote expõe run() com a assinatura de ScriptRunner. GeradorOrtofotosFundo não guarda
# estado, então a instância é reutilizável como o run() do pacote.
run: ScriptRunner[OrtofotoConfig, OrtofotoResultado] = GeradorOrtofotosFundo()

__all__ = [
    "run",
    "GeradorOrtofotosFundo",
    "OrtofotoConfig",
    "OrtofotoResultado",
    "enquadrar",
]

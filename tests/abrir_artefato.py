import platform
import shlex
import shutil
import subprocess
import warnings
from pathlib import Path

# Um comando por SO, como o próprio SO abre um arquivo pelo handler padrão do usuário.
COMANDO_ABRIR_ARTEFATO_POR_SO: dict[str, str] = {
    "Linux": "xdg-open {caminho}",
    "Darwin": "open {caminho}",
    "Windows": 'cmd /c start "" {caminho}',
}
# Alguns visualizadores só devolvem o controle do processo quando fecham; o timeout é o que
# impede a suíte de travar esperando alguém fechar o artefato na tela.
TIMEOUT_ABRIR_ARTEFATO_S = 2.0


def abrir_artefato(caminho: Path) -> None:
    """Tenta abrir o artefato no visualizador padrão do SO. Conveniência best-effort: SO sem
    comando mapeado, executável ausente ou timeout viram warning, nunca falham o teste."""
    comando = COMANDO_ABRIR_ARTEFATO_POR_SO.get(platform.system())
    if comando is None:
        warnings.warn(f"sem comando de abertura para o SO {platform.system()!r}", stacklevel=2)
        return
    executavel = shlex.split(comando)[0]
    if shutil.which(executavel) is None:
        warnings.warn(f"{executavel!r} não encontrado; artefato só gravado", stacklevel=2)
        return
    try:
        subprocess.run(
            shlex.split(comando.format(caminho=shlex.quote(str(caminho)))),
            timeout=TIMEOUT_ABRIR_ARTEFATO_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pass

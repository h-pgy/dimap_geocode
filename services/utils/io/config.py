from pathlib import Path

# Raiz do projeto: services/utils/io/ está três níveis abaixo de <project_root>/
_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"


def data_dir() -> Path:
    return _DATA_DIR


def subpasta_de_data(nome: str) -> Path:
    """Subpasta de insumo em `data/`, criada se faltar — para as etapas não montarem Path."""
    pasta = data_dir() / nome
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta

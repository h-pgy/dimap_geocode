from pathlib import Path

# Raiz do projeto: services/utils/io/ está três níveis abaixo de <project_root>/
_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"

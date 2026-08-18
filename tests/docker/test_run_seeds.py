import os
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_SEEDS_PATH = REPO_ROOT / "docker" / "run_seeds.sh"


# ---------------------------------------------------------------------------
# Execução e ordem dos management commands de seed
# ---------------------------------------------------------------------------


def test_run_seeds_script_contem_todos_os_comandos_de_seed_em_ordem(
    tmp_path: Path,
) -> None:
    assert RUN_SEEDS_PATH.is_file(), f"Arquivo {RUN_SEEDS_PATH} não encontrado."

    conteudo = RUN_SEEDS_PATH.read_text(encoding="utf-8")
    assert "set -e" in conteudo

    pos_unidades = conteudo.find("seed_unidades")
    pos_cargos = conteudo.find("seed_cargos")
    pos_impedimento = conteudo.find("seed_tipos_impedimento")

    assert pos_unidades != -1, "Comando 'seed_unidades' ausente em run_seeds.sh"
    assert pos_cargos != -1, "Comando 'seed_cargos' ausente em run_seeds.sh"
    assert (
        pos_impedimento != -1
    ), "Comando 'seed_tipos_impedimento' ausente em run_seeds.sh"
    assert (
        pos_unidades < pos_cargos < pos_impedimento
    ), "Os comandos de seed devem ser chamados na ordem: unidades -> cargos -> tipos_impedimento"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "invocations.txt"

    python_fake = bin_dir / "python"
    python_fake.write_text(
        f'#!/bin/sh\nif [ "$1" = "manage.py" ]; then echo "$2" >> "{log_file}"; fi\n',
        encoding="utf-8",
    )
    python_fake.chmod(0o755)

    manage_fake = tmp_path / "manage.py"
    manage_fake.write_text("#!/bin/sh\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    resultado = subprocess.run(
        ["sh", str(RUN_SEEDS_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    chamadas = [
        linha.strip()
        for linha in log_file.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    assert chamadas == ["seed_unidades", "seed_cargos", "seed_tipos_impedimento"]
    assert "Seeds concluídas com sucesso" in resultado.stdout

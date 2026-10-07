import os
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT_PATH = REPO_ROOT / "docker" / "entrypoint.sh"


def _configurar_ambiente_de_teste(
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    python_fake = bin_dir / "python"
    python_fake.write_text(
        "#!/bin/sh\nexit 0\n",
        encoding="utf-8",
    )
    python_fake.chmod(0o755)

    manage_fake = tmp_path / "manage.py"
    manage_fake.write_text("#!/bin/sh\n", encoding="utf-8")

    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()

    seeds_log = tmp_path / "seeds_executadas.log"
    run_seeds_fake = docker_dir / "run_seeds.sh"
    run_seeds_fake.write_text(
        f'#!/bin/sh\necho "SEEDS_RODADAS" >> "{seeds_log}"\n',
        encoding="utf-8",
    )
    run_seeds_fake.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    return seeds_log, run_seeds_fake, env


# ---------------------------------------------------------------------------
# Execução condicional de seeds no entrypoint
# ---------------------------------------------------------------------------


def test_entrypoint_chama_run_seeds_quando_auto_seed_ativo(tmp_path: Path) -> None:
    seeds_log, _, env = _configurar_ambiente_de_teste(tmp_path)
    env["DJANGO_AUTO_MIGRATE"] = "1"
    env["DJANGO_AUTO_SEED"] = "1"

    resultado = subprocess.run(
        ["sh", str(ENTRYPOINT_PATH), "true"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert seeds_log.is_file(), (
        "run_seeds.sh deveria ter sido executado quando DJANGO_AUTO_SEED=1"
    )
    assert seeds_log.read_text(encoding="utf-8").strip() == "SEEDS_RODADAS"
    assert "==> Executando seeds..." in resultado.stdout


def test_entrypoint_pula_run_seeds_quando_auto_seed_desativado(
    tmp_path: Path,
) -> None:
    seeds_log, _, env = _configurar_ambiente_de_teste(tmp_path)
    env["DJANGO_AUTO_MIGRATE"] = "1"
    env["DJANGO_AUTO_SEED"] = "0"

    resultado = subprocess.run(
        ["sh", str(ENTRYPOINT_PATH), "true"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert not seeds_log.exists(), (
        "run_seeds.sh NÃO deveria ter sido executado quando DJANGO_AUTO_SEED=0"
    )
    assert "==> Executando seeds..." not in resultado.stdout


# ---------------------------------------------------------------------------
# Geração das ortofotos de fundo na subida
# ---------------------------------------------------------------------------


def test_entrypoint_gera_ortofotos_antes_do_processo_final(tmp_path: Path) -> None:
    _, _, env = _configurar_ambiente_de_teste(tmp_path)
    env["DJANGO_AUTO_MIGRATE"] = "0"
    comandos_log = tmp_path / "comandos.log"
    processo_final = tmp_path / "processo_final.log"
    python_fake = tmp_path / "bin" / "python"
    python_fake.write_text(
        f'#!/bin/sh\necho "$2" >> "{comandos_log}"\n'
        'if [ "$2" = "gerar_ortofotos_fundo" ]; then exit 1; fi\n',
        encoding="utf-8",
    )

    resultado = subprocess.run(
        ["sh", str(ENTRYPOINT_PATH), "touch", str(processo_final)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert comandos_log.read_text(encoding="utf-8").split() == ["gerar_ortofotos_fundo"]
    assert resultado.returncode != 0
    assert not processo_final.exists()

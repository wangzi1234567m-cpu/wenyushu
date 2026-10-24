"""Cross-platform Compose launcher. Never prints generated credentials."""
import argparse
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["up", "down", "logs", "status"])
    action = parser.parse_args().action
    if not shutil.which("docker"):
        raise SystemExit("Docker is missing. Install/start Docker Desktop with Linux containers.")
    subprocess.run(["docker", "compose", "version"], check=True)
    folder = ROOT / ".local"
    folder.mkdir(exist_ok=True)
    env = folder / "compose.env"
    if not env.exists():
        if action != "up":
            raise SystemExit("No local configuration; run up first.")
        with env.open("x", encoding="utf-8") as stream:
            stream.write(f"POSTGRES_PASSWORD={secrets.token_hex(32)}\n"
                         f"CSRF_SECRET={secrets.token_hex(32)}\n")
        env.chmod(0o600)
    args = {"up": ["up", "--build", "-d", "--wait", "--wait-timeout", "180"],
            "down": ["down"], "logs": ["logs", "--tail", "100"], "status": ["ps"]}[action]
    subprocess.run(["docker", "compose", "--env-file", str(env),
                    "-f", str(ROOT / "infra/compose.yaml"), *args], check=True, cwd=ROOT)
    if action == "up":
        print("Open http://localhost:3000 ; down preserves the database volume.")


if __name__ == "__main__":
    main()

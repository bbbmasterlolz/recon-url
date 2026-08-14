import subprocess
import sys
import tempfile
from pathlib import Path

import requests


TREE = Path(__file__).resolve().parent / "tree.py"


def analyze_js(link: str):
    response = requests.get(link, timeout=30)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        encoding="utf-8",
        delete=False,
    ) as file:
        file.write(response.text)
        js_file = Path(file.name)

    try:
        result = subprocess.run(
            [sys.executable, str(TREE), str(js_file)],
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        if result.returncode != 0:
            print(f"[!] tree.py error:")
            print(result.stderr)
            return []

        return result.stdout.splitlines()

    finally:
        js_file.unlink(missing_ok=True)
import subprocess
from pathlib import Path
import requests

JSLUICE = Path(__file__).resolve().parents[2] / "tools_p" / "jsluice.exe"


def analyze_js(link: str):
    # Download the JavaScript
    response = requests.get(link, timeout=30)
    response.raise_for_status()

    js_content = response.text

    # Send the downloaded JavaScript directly to jsluice
    result = subprocess.run(
        [str(JSLUICE), "urls", "-"],
        input=js_content,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    if result.returncode != 0:
        print("jsluice error:")
        print(result.stderr)
        return []

    return result.stdout.splitlines()
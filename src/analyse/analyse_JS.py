import tempfile
from pathlib import Path

import requests

# Import tree module directly — avoids subprocess startup overhead
from analyse import tree
from analyse import Tester


def analyze_js(link: str, aggressive:bool):
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
        results, _const, _strings = tree.parse_and_extract(str(js_file))

        # Test URLs and return results with status/allowed info
        tested = Tester.test_urls(sorted(results), aggressive)
        return tested

    except Exception as e:
        print(f"[!] tree analysis error: {e}")
        return []

    finally:
        js_file.unlink(missing_ok=True)
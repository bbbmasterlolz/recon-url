import tempfile
from pathlib import Path

import requests


def download_js(url: str) -> Path:
    """Download a JS file from *url* to a temporary file.

    Returns the Path to the temp file.  Caller is responsible for
    cleaning it up (e.g. with ``path.unlink(missing_ok=True)``).
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        encoding="utf-8",
        delete=False,
    )

    with tmp:
        tmp.write(response.text)

    return Path(tmp.name)

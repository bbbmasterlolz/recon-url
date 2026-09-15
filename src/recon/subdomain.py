import subprocess
from pathlib import Path

_tools_dir = Path(__file__).resolve().parents[2] / "tools"
_subfinder = _tools_dir / "subfinder.exe"


def find_subdomains(domain: str) -> list[str]:
    """Run subfinder to enumerate subdomains for a given domain.

    Returns a sorted list of discovered subdomains.
    """
    if not _subfinder.exists():
        raise FileNotFoundError(
            f"subfinder not found at {_subfinder}. Run 'reconAPI setup' first."
        )

    result = subprocess.run(
        [str(_subfinder), "-d", domain, "-silent"],
        capture_output=True,
        text=True,
        timeout=300,
    )

    subdomains = set()
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line:
            subdomains.add(line)

    return sorted(subdomains)

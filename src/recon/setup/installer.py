import shutil
import importlib
import sys
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[3]
tools_dir = root / "tools"
tools = [
    "subfinder",
]

def check_tool(name):
    if tools_dir:
        return (tools_dir / f"{name}.exe").exists()
    else:
        return False

def setup_tools():

    print("Recon Tool Setup")
    print("================")

    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )

    for tool in tools:
        if check_tool(tool):
            print(f"[OK]         {tool}")
        else:
            print(f"[INSTALLING] {tool}")
            module = importlib.import_module(f'recon.tool_installer.{tool}')
            module.install(tools_dir / f'{tool}.exe')
            print("done")

    print("\nFinished")

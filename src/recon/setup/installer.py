import shutil
import importlib
from pathlib import Path

root = Path(__file__).resolve().parents[3]
tools_dir = root / "tools"
tools = [
    "subfinder",
    "katana",
]

def check_tool(name):
    if tools_dir:
        return (tools_dir / f"{name}.exe").exists()
    else:
        return False

def setup_tools():
    missing = []

    print("Recon Tool Setup")
    print("================")

    for tool in tools:
        if check_tool(tool):
            print(f"[OK]         {tool}")
        else:
            print(f"[MISSING]    {tool}")
            missing.append(tool)

    if not missing:
        print("All Tools are already installed")
        return

    print("================")
    for tool in missing:
        print(f"[INSTALLING] {tool}")
        module = importlib.import_module(f'recon.tool_installer.{tool}')
        module.install(tools_dir / f'{tool}.exe')
        print("done")

    print("Finished")



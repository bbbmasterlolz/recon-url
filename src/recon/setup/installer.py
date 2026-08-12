import shutil
import importlib


def check_tool(name):
    return shutil.which(name) is not None


def setup_tools():
    tools = [
        "subfinder",
        "jsluice",
    ]

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
        module = importlib.import_module(f'recon.tools.{tool}')
        module.install()


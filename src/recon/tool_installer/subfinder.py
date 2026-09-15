import platform
import requests
import zipfile
from pathlib import Path

system = platform.system()
arch = platform.machine()


def install(dest):
    if machine != "windows":
        print("Install for windows only, failing to install subfinder will only prevent the usage of -d flag")
        return

    machine = f"{system}_{arch}".lower()
    url = (f"https://github.com/projectdiscovery/subfinder/releases/download/v2.15.0/subfinder_2.15.0_{machine}.zip")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    temp_zip = dest.parent / "temp.zip"

    try:
        # Download ZIP
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(temp_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # open ZIP
        with zipfile.ZipFile(temp_zip) as z:
            exe = next(
                name
                for name in z.namelist()
                if name.lower().endswith(".exe")
            )

            # Extract EXE
            with z.open(exe) as source, open(dest, "wb") as target:
                while chunk := source.read(8192):
                    target.write(chunk)

    except Exception as e:
        print(f"Installation failed: {e}")

    finally:
        temp_zip.unlink(missing_ok=True)

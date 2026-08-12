import argparse

from recon.setup.installer import setup_tools

def main():
    parser = argparse.ArgumentParser(
        prog="recon",
        description="Reconnaissance toolkit",
    )

    parser.add_argument(
        "command",
        choices=["setup"],
        help="Command to execute",
    )

    args = parser.parse_args()

    if args.command == "setup":
        setup_tools()

if __name__ == "__main__":
    main()
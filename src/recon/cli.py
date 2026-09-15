import argparse
import asyncio

from recon.setup.installer import setup_tools
from recon.main import run


def main():
    parser = argparse.ArgumentParser(
        prog="reconAPI",
        description="Reconnaissance toolkit — discover and test API endpoints from JavaScript",
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── setup command ──
    subparsers.add_parser(
        "setup",
        help="Install required tools (Playwright, subfinder, etc.)",
    )

    # ── scan command (default behavior when just a URL is given) ──
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a URL for JS files and test discovered API endpoints",
    )

    scan_parser.add_argument(
        "url",
        help="Target URL to scan",
    )

    scan_parser.add_argument(
        "-a", "--aggressive",
        action="store_true",
        help="Enable aggressive API testing mode",
    )

    scan_parser.add_argument(
        "-o", "--output",
        action="store_true",
        help="Save output to PDF",
    )

    # ── Handle bare URL usage:  reconAPI https://example.com ──
    # If the first arg looks like a URL, treat it as "scan <url>"
    args, remaining = parser.parse_known_args()

    if args.command is None and remaining:
        first = remaining[0]
        if first.startswith(("http://", "https://")):
            # Re-parse as: scan <url> [remaining flags]
            args = parser.parse_args(["scan"] + remaining)

    if args.command == "setup":
        setup_tools()

    elif args.command == "scan":
        asyncio.run(run(args.url, args.aggressive, args.output))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

import argparse
import asyncio
from playwright.async_api import async_playwright
from analyse.analyse_JS import analyze_js
from pdf.pdf_maker import make_pdf

async def find_js(url: str, max_seconds: int = 60):
    js_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        def handle_response(response):
            if response.request.resource_type == "script":
                js_urls.add(response.url)

        page.on("response", handle_response)

        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
        except Exception as e:
            print(f"[!] Failed to load page: {e}")

        try:
            await asyncio.wait_for(
                page.wait_for_load_state(
                    "networkidle",
                    timeout=max_seconds * 1000,
                ),
                timeout=max_seconds,
            )
        except asyncio.TimeoutError:
            print(f"[!] Network idle timeout after {max_seconds}s")
        except Exception as e:
            print(f"[!] Error waiting for network idle: {e}")

        await browser.close()

    return sorted(js_urls)


async def main(url: str, aggressive:bool, output:bool):
    print("scanning, this can take up to 60s")

    urls = await find_js(url, max_seconds=60)
    results = []

    for js_url in urls:
        print(f"\n[*] Analyzing: {js_url}")

        try:
            results.append(analyze_js(js_url, aggressive))
        except Exception as e:
            print(f"[!] Error: {type(e).__name__}: {e}")

    if not output:
        for result in results:
            for response in result:
                if hasattr(response, 'status_code'):
                    print(f"{response.url}")
                    print(f"status  : {response.status_code}")
                    print(f"allowed : {response.headers.get('Allow')}")
                else:
                    print(response)
                print("")

    else:
        make_pdf(results, urls)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find and analyze JavaScript URLs"
    )

    parser.add_argument(
        "url",
        help="Target URL",
    )

    parser.add_argument(
        "-a",
        "--aggressive",
        action="store_true",
        help="Enable aggressive api testing mode ",
    )

    parser.add_argument(
        "-o",
        "--output",
        action="store_true",
        help="save output to PDF ",
    )

    args = parser.parse_args()

    asyncio.run(main(args.url, args.aggressive, args.output))
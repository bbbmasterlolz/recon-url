import asyncio
from playwright.async_api import async_playwright
from analyse.analyse_JS import analyze_js

async def find_js(url: str, max_seconds: int = 60):
    js_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        def handle_response(response):
            if response.request.resource_type in ("script", "xhr", "fetch"):
                js_urls.add(response.url)

        page.on("response", handle_response)

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30_000,
        )

        try:
            # Wait until network becomes idle or 60s
            await asyncio.wait_for(
                page.wait_for_load_state(
                    "networkidle",
                    timeout=max_seconds * 1000,
                ),
                timeout=max_seconds,
            )

        except (asyncio.TimeoutError, Exception):
            pass

        await browser.close()

    return sorted(js_urls)


async def main():
    print("scanning, this can take up to 60s")

    urls = await find_js(
        "https://ketelo-tegalrejo.web.app/",
        max_seconds=60,
    )

    for js_url in urls:
        print(f"\n[*] Analyzing: {js_url}")

        results = analyze_js(js_url)

        for result in results:
            print(result)

asyncio.run(main())
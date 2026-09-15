import asyncio
from playwright.async_api import async_playwright


async def find_js_urls(url: str, max_seconds: int = 60) -> list[str]:
    """Use Playwright to discover all JS URLs loaded by a page.

    Returns a sorted list of JS script URLs.
    """
    js_urls: set[str] = set()

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

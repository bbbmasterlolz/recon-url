import asyncio

from recon import scanner, downloader, parser, tester, reporter


async def run(url: str, aggressive: bool = False, output: bool = False):
    """Main orchestrator — every module returns here, main decides what's next."""

    print(f"[*] Scanning {url}, this can take up to 60s")

    # Step 1: Discover JS URLs loaded by the page
    js_urls = await scanner.find_js_urls(url, max_seconds=60)

    if not js_urls:
        print("[!] No JavaScript files found.")
        return

    print(f"[+] Found {len(js_urls)} JS file(s)\n")

    all_results: list[list] = []

    for js_url in js_urls:
        print(f"[*] Analyzing: {js_url}")

        try:
            # Step 2: Download JS to temp file
            js_path = downloader.download_js(js_url)

            try:
                # Step 3: Extract endpoints from the JS file
                endpoints = parser.extract_endpoints(js_path)

                # Step 4: Test discovered endpoints
                tested = tester.test_urls(sorted(endpoints), aggressive)
                all_results.append(tested)

            finally:
                # Always clean up the temp file
                js_path.unlink(missing_ok=True)

        except Exception as e:
            print(f"[!] Error: {type(e).__name__}: {e}")

    # Step 5: Report results
    if output:
        reporter.make_pdf(all_results, js_urls)
        print(f"\n[+] PDF saved to output.pdf")
    else:
        reporter.print_results(all_results)

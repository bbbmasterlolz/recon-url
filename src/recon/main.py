import asyncio

from recon import scanner, downloader, parser, tester, reporter, subdomain


async def run(url: str, aggressive: bool = False, output: bool = False):
    """Scan a single URL — discover JS, extract endpoints, test, report."""

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
        reporter.make_pdf(all_results, js_urls, url)
    else:
        reporter.print_results(all_results)


async def run_domain(domain: str, aggressive: bool = False, output: bool = False):
    """Enumerate subdomains, then scan each one immediately with output per domain."""

    print(f"[*] Finding subdomains for {domain}...")
    subdomains = subdomain.find_subdomains(domain)

    if not subdomains:
        print("[!] No subdomains found.")
        return

    print(f"[+] Found {len(subdomains)} subdomain(s)\n")

    for i, sub in enumerate(subdomains, 1):
        url = f"https://{sub}"

        print(f"\n{'='*60}")
        print(f"[{i}/{len(subdomains)}] {url}")
        print(f"{'='*60}")

        await run(url, aggressive, output)

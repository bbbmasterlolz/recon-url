import heapq
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

REQUEST_TIMEOUT = 5
MAX_WORKERS = 20


class URLTester:
    """Test discovered endpoints via OPTIONS requests.

    Instance-based so state is isolated per run (no module globals).
    """

    def __init__(self, aggressive: bool = False):
        self.aggressive = aggressive
        self._tested: list = []
        self._valid_base: set[str] = set()
        self._heap: list = []
        self._session = requests.Session()

    # ── public API ──

    def test_urls(self, urls, aggressive: bool | None = None) -> list:
        """Test a list of endpoint URLs. Returns list of Response | str."""
        if aggressive is not None:
            self.aggressive = aggressive

        last_update = time.monotonic()
        count = 0
        total = len(urls)

        for url in urls:
            if "://" in url:
                weight = url.count("/")
                heapq.heappush(self._heap, (weight, url))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._test_one, url): url for url in urls}

            for future in as_completed(futures):
                count += 1

                if time.monotonic() - last_update >= 10:
                    print(f"[Status] Tested {count}/{total} URLs")
                    last_update = time.monotonic()

                result = future.result()
                if result:
                    if isinstance(result, list):
                        self._tested.extend(result)
                    else:
                        self._tested.append(result)

        return self._tested

    # ── internal ──

    def _test_one(self, url):
        """Test a single URL and return the result."""
        if "://" in url:
            try:
                response = self._session.options(url, timeout=REQUEST_TIMEOUT)
                return response
            except requests.RequestException:
                return f"{url}"

        elif "{base_url}" in url:
            result = self._resolve_base(url)
            return result if result else url

        return None

    def _resolve_base(self, url):
        """Try to resolve a {base_url} placeholder against known bases."""
        this_tested = []

        # Try known-good bases first using a snapshot
        if not self.aggressive:
            for base_url in list(self._valid_base):
                target = url.replace("{base_url}", base_url)
                try:
                    response = self._session.options(target, timeout=REQUEST_TIMEOUT)
                    if response.status_code != 404:
                        return response
                except requests.RequestException:
                    continue

        # Fall back to candidate bases from the heap
        sorted_bases = sorted(self._heap)
        for weight, base_url in sorted_bases:
            target = url.replace("{base_url}", base_url)
            try:
                response = self._session.options(target, timeout=REQUEST_TIMEOUT)
                if response.status_code != 404:
                    self._valid_base.add(base_url)
                    if self.aggressive:
                        this_tested.append(response)
                    else:
                        return response
            except requests.RequestException:
                continue

        if self.aggressive:
            return this_tested

        return url


# ── Module-level convenience function ──

def test_urls(urls, aggressive: bool = False) -> list:
    """Convenience wrapper — creates a fresh URLTester per call."""
    tester = URLTester(aggressive=aggressive)
    return tester.test_urls(urls)

import requests
import heapq
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

tested = set()
valid_base = set()
heap = []

# Reuse TCP connections across requests
_session = requests.Session()

REQUEST_TIMEOUT = 5
MAX_WORKERS = 20


def _test_one(url):
    """Test a single URL and return the result string, or None."""
    if "://" in url:
        try:
            response = _session.options(url, timeout=REQUEST_TIMEOUT)
            return (
                f"{url}\n"
                f"status  : {response.status_code}\n"
                f"allowed : {response.headers.get('Allow')}\n"
            )
        except requests.RequestException:
            return f"{url}\nError\n"

    elif "{base_url}" in url:
        result = resolve_base(url)
        return result if result else url

    return None


def test_urls(urls):
    last_update = time.monotonic()
    count = 0
    total = len(urls)

    for url in urls:
        if "://" in url:
            weight = url.count("/")
            heapq.heappush(heap, (weight, url))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_test_one, url): url for url in urls}

        for future in as_completed(futures):
            count += 1

            if time.monotonic() - last_update >= 10:
                print(f"[Status] Tested {count}/{total} URLs")
                last_update = time.monotonic()

            result = future.result()
            if result:
                tested.add(result)

    return tested


def resolve_base(url):
    # Try known-good bases first (no copy needed, iterate directly)
    for base_url in list(valid_base):
        target = url.replace("{base_url}", base_url)
        try:
            response = _session.options(target, timeout=REQUEST_TIMEOUT)
            if response.status_code != 404:
                return (
                    f"{target}\n"
                    f"status  : {response.status_code}\n"
                    f"allowed : {response.headers.get('Allow')}\n"
                )
        except requests.RequestException:
            continue

    # Fall back to candidate bases from the heap (sorted copy, iterate once)
    sorted_bases = sorted(heap)
    for weight, base_url in sorted_bases:
        target = url.replace("{base_url}", base_url)
        try:
            response = _session.options(target, timeout=REQUEST_TIMEOUT)
            if response.status_code != 404:
                valid_base.add(base_url)
                return (
                    f"{target}\n"
                    f"status  : {response.status_code}\n"
                    f"allowed : {response.headers.get('Allow')}\n"
                )
        except requests.RequestException:
            continue
import requests

url = "https://httpbin.org"

try:
    r = requests.options(
        url,
        timeout=10,
        proxies={
            "http": None,
            "https": None,
        }
    )

    print(r.status_code)
    print(r.url)

except Exception as e:
    print(type(e).__name__)
    print(e)
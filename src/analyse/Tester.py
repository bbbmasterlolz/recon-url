import requests

def test_urls(urls):
    tested = set()
    n_max = len(urls)
    n = 0
    for url in urls:
        n += 1
        if n % 50 == 0:
            print(f"testing ({n}/{n_max})")
        if "://" in url:
            try:
                response = requests.options(url)
                tested.add(f"{url}\n"
                           f"status  : {response.status_code}\n"
                           f"allowed :{response.headers.get("Allow")}\n")
            except requests.RequestException as e:
                tested.add(f"{url}\nError\n")
        else:
            tested.add(f"{url}\n")

    return tested
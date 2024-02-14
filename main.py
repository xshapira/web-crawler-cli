import requests
from bs4 import BeautifulSoup


def fetch_images_from_url(url, current_depth, max_depth):
    # stop crawling if the current depth exceeds the maximum depth
    # to prevent recursive calls
    if current_depth > max_depth:
        return

    print(f"Fetching images from {url} at depth {current_depth}")
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as exc:
        print(f"Failed to fetch images from {url}: {exc}")
        return

    images = [
        {
            "url": img["src"],
            "page": url,
            "depth": current_depth,
        }
        for img in soup.find_all("img")
        if "src" in img.attrs
    ]
    if current_depth < max_depth:
        links = [a["href"] for a in soup.find_all("a") if "href" in a.attrs]
        for link in links:
            images.extend(
                # `current_depth` incremented by 1 indicating it's now one level deeper.
                fetch_images_from_url(link, current_depth + 1, max_depth),
            )

    return images


def main() -> None:
    pass


if __name__ == "__main__":
    main()

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def fetch_images_from_url(url, current_depth, max_depth):
    """
    Recursively fetch images from a given URL up to a specified depth.

    It requests the content from the given URL, parses it to find all image sources, and then recursively follows all links found on the page to continue gathering images from those pages, up to the defined maximum depth.

    Args:
        url (str): The starting URL from which to fetch images.
        current_depth (int): The current position in the link hierarchy
        max_depth (int): The maximum number of links to follow from the initial page.

    Returns:
        A list of dictionaries, each containing the 'url' of an image, the 'page' on which the image was found, and the 'depth' at which the image was found. Returns an empty list if no images are found or in case of a request failure.
    """

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


def save_images(images):
    """
    Saves images from a list of image URLs to a local directory and creates a JSON file listing the collected images.

    Args:
        images (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the image to be downloaded and saved.
    """
    if not images:
        print("No images to save.")
        return

    images_dir = Path("images")
    if not images_dir.exists():
        images_dir.mkdir()

    image_json = {"images": images}
    with open("images/images.json", "w") as fp:
        json.dump(image_json, fp, indent=4)

    for image in images:
        try:
            img_data = requests.get(image["url"]).content
            img_name = Path(image["url"]).name
            with open(f"images/{img_name}", "wb") as fp:
                fp.write(img_data)
            print(f"Downloaded image {img_name}")
        except requests.exceptions.RequestException as exc:
            print(f"Failed to download image {image['url']}: {exc}")


def main() -> None:
    pass


if __name__ == "__main__":
    main()

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from logger import setup_logger

logger = setup_logger(__name__)

# maximum number of images to download
MAX_IMAGES = 10


def fetch_images_from_url(url: str, current_depth: int, max_depth: int) -> list[dict]:
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
        return []

    logger.info(f"Fetching images from {url} at depth {current_depth}")
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Failed to fetch images from {url}: {exc}")
        return []

    collected_images = [
        {
            "url": img["src"],
            "page": url,
            "depth": current_depth,
        }
        for img in soup.find_all("img")
        if "src" in img.attrs
    ]
    # slicing the list makes sure we don't process more images than the limit
    # set by `MAX_IMAGES`.
    # note that it first collects all the matching images without considering the limit.
    images = collected_images[:MAX_IMAGES]
    if current_depth < max_depth:
        links = [a["href"] for a in soup.find_all("a") if "href" in a.attrs]
        for link in links:
            images.extend(
                # `current_depth` incremented by 1 indicating it's now one level deeper.
                fetch_images_from_url(link, current_depth + 1, max_depth),
            )

    return images


def save_images(images: list[dict]) -> None:
    """
    Saves images from a list of image URLs to a local directory and creates a JSON file listing the collected images.

    Args:
        images (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the image to be downloaded and saved.
    """
    if not images:
        logger.info("No images to save.")
        return

    images_dir = Path("images")
    if not images_dir.exists():
        images_dir.mkdir()

    image_json = {"images": images}
    with open("images/images.json", "w") as fp:
        json.dump(image_json, fp, indent=4)

    downloaded_images = set()
    for image in images:
        if image["url"] in downloaded_images:
            # skip duplicate images
            continue
        try:
            img_data = requests.get(image["url"]).content
            img_name = Path(image["url"]).name
            if img_name not in downloaded_images:
                with open(f"images/{img_name}", "wb") as fp:
                    fp.write(img_data)
                logger.info(f"Downloaded image {img_name}")
                downloaded_images.add(image["url"])
        except requests.exceptions.RequestException as exc:
            logger.error(f"Failed to download image {image['url']}: {exc}")


def main() -> None:
    # ensure exactly two command-line arguments are provided (excluding the script name)
    if len(sys.argv) != 3:
        logger.error("Usage: <script_name> <start_url> <depth>")
        sys.exit(1)

    start_url = sys.argv[1]
    depth = int(sys.argv[2])
    images = fetch_images_from_url(start_url, 1, depth)
    save_images(images)


if __name__ == "__main__":
    main()

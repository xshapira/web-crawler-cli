import json
import mimetypes
import shutil
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from logger import setup_logger

log = setup_logger(__name__)

# maximum number of images to download
MAX_IMAGES = 10


def fetch_html_content(url: str) -> BeautifulSoup | None:
    """
    Fetches HTML content for a given URL.

    Args:
        url (str): The starting URL from which to fetch images.

    Returns:
        BeautifulSoup object containing the parsed HTML content.
    """
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as exc:
        log.error(f"Failed to fetch images from {url}: {exc}")
        return None
    return soup


def extract_image_urls(
    html_content: BeautifulSoup, url: str, current_depth: int
) -> list[dict]:
    """
    Parses HTML content to extract image URLs.

    Args:
        html_content (str): BeautifulSoup object containing the parsed HTML content.
        url (str): The starting URL from which to fetch images.
        current_depth (int): The current position in the link hierarchy

    Returns:
        A list of image metadata. Metadata includes the image URL, the page URL, and the depth.
    """
    collected_images = [
        {
            "url": urljoin(url, img["src"]),
            "page": url,
            "depth": current_depth,
        }
        for img in html_content.find_all("img")
        if "src" in img.attrs
    ]
    # Slicing the list makes sure we don't process more images than the limit
    # set by `MAX_IMAGES`.
    # Note that it first collects all the matching images without considering the limit.
    return collected_images[:MAX_IMAGES]


def extract_links(html_content: BeautifulSoup, url: str) -> list[str]:
    """
    Parses HTML content to extract links.

    Args:
        html_content (str): BeautifulSoup object containing the parsed HTML content.
        url (str): The starting URL from which to fetch images.

    Returns:
        A list of URL strings from the href attributes of anchor tags.
    """
    return [a["href"] for a in html_content.find_all("a") if "href" in a.attrs]


def fetch_images_from_url(url: str, current_depth: int, max_depth: int) -> list[dict]:
    """
    Orchestrates the recursive fetching of images - recursively follows all links found on the page to continue aggregates images from those pages, up to the defined maximum depth.

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

    log.info(f"Fetching images from {url} at depth {current_depth}")
    html_content = fetch_html_content(url)
    images = extract_image_urls(html_content, url, current_depth)
    if current_depth < max_depth:
        links = extract_links(html_content, url)
        for link in links:
            # `current_depth` incremented by 1 indicating it's now one level deeper.
            page_url = urljoin(url, link)
            images += fetch_images_from_url(page_url, current_depth + 1, max_depth)

    return images


def save_images_metadata(images: list[dict]) -> None:
    """
    Saves image metadata to a JSON file.

    Args:
        images (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the image to be downloaded and saved.
    """
    images_dir = Path("images")
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(exist_ok=True)

    if not images:
        log.info("No images to save.")
        return

    # don't raise an error if directory already exists
    # if images_dir.exists():

    image_json = {"images": images}
    with open(images_dir / "images.json", "w") as fp:
        json.dump(image_json, fp, indent=4)


def save_images_locally(images: list[dict]) -> None:
    """
    Downloads and saves images from URLs to disk.

    Args:
        images (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the image to be downloaded and saved. The 'url' is used to determine the source of the image and the filename under which the image is saved locally.
    """
    # tracks downloaded images to avoid duplicates
    downloaded_images = set()
    for image in images:
        if image["url"] in downloaded_images:
            # skip duplicate images
            continue
        try:
            img_data = requests.get(image["url"])
            content_type = img_data.headers.get("Content-Type")
            extension = mimetypes.guess_extension(content_type)
            img_name = Path(image["url"]).name
            img_without_ext = img_name.rsplit(".", 1)[0]
            image_name = f"{img_without_ext}{extension}"
            with open(f"images/{image_name}", "wb") as fp:
                fp.write(img_data.content)
            log.info(f"Downloaded image {img_name}")
            downloaded_images.add(image["url"])
        except requests.exceptions.RequestException as exc:
            log.error(f"Failed to download image {image['url']}: {exc}")


def main() -> None:
    # check if only two command-line arguments are provided (excluding the script name)
    if len(sys.argv) != 3:
        log.error("Usage: <script_name> <start_url> <depth>")
        sys.exit(1)

    start_url = sys.argv[1]
    depth = int(sys.argv[2])
    images = fetch_images_from_url(start_url, 1, depth)
    save_images_metadata(images)
    save_images_locally(images)


if __name__ == "__main__":
    main()

import contextlib
import hashlib
import json
import shutil
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

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


def hash_url(url: str) -> int:
    """
    Compute the SHA-256 hash of a URL and return it as an integer.

    Hashing the URL allows for efficient storage and comparison in the `visited_urls` set by reducing memory usage compared to storing full URL strings.

    Args:
        url (str): The URL string to be hashed.

    Returns:
        int: The integer representation of the SHA-256 hash of the URL.
    """
    return int(hashlib.sha256(url.encode()).hexdigest(), 16)


def fetch_images_from_url(url: str, current_depth: int, max_depth: int) -> list[dict]:
    """
    Fetch images from a URL and its linked pages up to a specified depth using the BFS algorithm. While traversing the pages, extract images from the current page regardless of depth, but only follows links within the specified depth.

    Args:
        url (str): The starting URL from which to fetch images.
        current_depth (int): The current depth of the URL being processed.
        max_depth (int): The maximum depth to crawl from the starting URL.

    Returns:
        A list of dictionaries, each containing the following keys:
        - 'url': The URL of the image.
        - 'page': The URL of the page where the image was found.
        - 'depth': The depth at which the image was found relative to the starting URL.

        Returns an empty list if no images are found or in case of a request failure.
    """

    images = []
    visited_urls_hashes = set()
    queue = deque([(url, current_depth)])

    while queue:
        current_url, current_depth = queue.popleft()
        current_url_hash = hash_url(current_url)
        # Skip processing if the URL has already been visited
        if current_url_hash in visited_urls_hashes:
            continue
        visited_urls_hashes.add(current_url_hash)

        log.info(f"Fetching images from {current_url} at depth {current_depth}")
        html_content = fetch_html_content(current_url)
        images.extend(extract_image_urls(html_content, current_url, current_depth))

        # Stop crawling if current depth reaches maximum depth
        if current_depth == max_depth:
            continue
        links = extract_links(html_content, current_url)
        for link in links:
            page_url = urljoin(current_url, link)
            # `current_depth` incremented by 1
            # indicating it's now one level deeper.
            queue.append((page_url, current_depth + 1))

    return images


def extract_filename_from_url(url: str) -> str:
    """
    Extracts the filename from a URL, ignoring query parameters.

    Args:
        url (str): The URL from which to extract the filename.

    Returns:
        str: The filename with its extension, without query parameters.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path
    # use Path to get the last component of the path as filename
    return Path(path).name


def is_based64_encoded(text: str) -> bool:
    """
    Checks if the given string is a based64 encoded data URI.

    Args:
        text (str): The string to be checked.

    Returns:
        bool: True if the string is a Base64-encoded data URI for an image; False otherwise.

    """
    with contextlib.suppress(AttributeError):
        if text.startswith("data:image") and ";base64" in text:
            return True
    return False


# def save_image_from_base64(data_uri, filepath):
#     """
#     Save an image from a base64 data URI to a file.
#     """
#     _, encoded = data_uri.split(",", 1)
#     data = base64.b64code(encoded)
#     with open(filepath, "wb") as fp:
#         fp.write(data)


def save_images_metadata(images: list[dict]) -> None:
    """
    Saves image metadata to a JSON file.

    Args:
        images (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the image to be downloaded and saved.
    """
    images_dir = Path("images")
    if images_dir.exists():
        shutil.rmtree(images_dir)
    # don't raise an error if directory already exists
    images_dir.mkdir(exist_ok=True)

    if not images:
        log.info("No images to save.")
        return

    metadata = {"images": images}
    with open(images_dir / "images.json", "w") as fp:
        json.dump(metadata, fp, indent=4)


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
            if is_based64_encoded(image["url"]):
                log.error("Found Base64-encoded data.")
                continue
            with requests.get(image["url"], stream=True) as image_data:
                image_name = extract_filename_from_url(image["url"])
                with open(f"images/{image_name}", "wb") as fp:
                    fp.write(image_data.content)
                log.info(f"Downloaded image {image_name}")
                downloaded_images.add(image["url"])
        except requests.exceptions.RequestException as exc:
            log.error(f"Failed to download image {image['url']}: {exc}")


def main() -> None:
    # check if only two command-line arguments are provided (excluding the script name)
    if len(sys.argv) != 3:
        log.error("Usage: <script_name> <start_url> <depth>")
        sys.exit(1)

    _, start_url, depth = sys.argv
    images = fetch_images_from_url(start_url, 1, int(depth))
    save_images_metadata(images)
    save_images_locally(images)


if __name__ == "__main__":
    main()

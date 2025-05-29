import argparse
import functools
import hashlib
import json
import shutil
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from logger import setup_logger

log = setup_logger(__name__)

# maximum number of PDFs to download (when not downloading all)
MAX_PDFS = 50
# set to True to download all PDFs without limit
DOWNLOAD_ALL_PDFS = False


def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Args:
        url (str): The URL to extract domain from

    Returns:
        str: The domain (netloc) from the URL
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_same_domain(url: str, base_domain: str) -> bool:
    """
    Check if a URL belongs to the same domain as the base domain.

    Args:
        url (str): The URL to check
        base_domain (str): The base domain to compare against

    Returns:
        bool: True if the URL belongs to the same domain
    """
    url_domain = get_domain(url)
    return url_domain == base_domain


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid for crawling (not JavaScript, mailto, etc.)

    Args:
        url (str): The URL to validate

    Returns:
        bool: True if the URL is valid for crawling
    """
    if not url:
        return False

    # Skip JavaScript URLs, mailto links, tel links, etc.
    invalid_schemes = ["javascript:", "mailto:", "tel:", "ftp:", "file:"]
    if any(url.lower().startswith(scheme) for scheme in invalid_schemes):
        return False

    # skip anchor-only links that don't change the page
    return not url.startswith("#")


def is_pdf_url(url: str) -> bool:
    """
    Check if a URL points to a PDF file

    Args:
        url (str): The URL to check

    Returns:
        bool: True if the URL appears to point to a PDF
    """
    return (
        url.lower().endswith(".pdf")
        or "pdf" in url.lower().split("/")[-1]
        or "/pdf/" in url.lower()
    )


@functools.lru_cache(maxsize=500)
def fetch_html_content(url: str) -> BeautifulSoup | None:
    """
    Fetches HTML content for a given URL.

    Args:
        url (str): The starting URL from which to fetch content.

    Returns:
        BeautifulSoup object containing the parsed HTML content.
    """
    if not is_valid_url(url):
        log.debug(f"Skipping invalid URL: {url}")
        return None

    # Don't try to parse PDF files as HTML
    if is_pdf_url(url):
        log.debug(f"Skipping PDF URL for HTML parsing: {url}")
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Check content type before parsing
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            log.debug(
                f"Skipping non-HTML content: {url} (content-type: {content_type})"
            )
            return None

        # Use lxml parser if available, fallback to html.parser
        try:
            soup = BeautifulSoup(response.content, "lxml")
        except Exception:
            soup = BeautifulSoup(response.content, "html.parser")

    except requests.RequestException as exc:
        log.debug(f"Failed to fetch content from {url}: {exc}")
        return None
    except Exception as exc:
        log.debug(f"Error parsing content from {url}: {exc}")
        return None
    return soup


def extract_pdf_urls(
    html_content: BeautifulSoup,
    url: str,
    current_depth: int,
    download_all: bool = False,
) -> list[dict]:
    """
    Parses HTML content to extract PDF URLs.

    Args:
        html_content: BeautifulSoup object containing the parsed HTML content.
        url (str): The starting URL from which to fetch PDFs.
        current_depth (int): The current position in the link hierarchy
        download_all (bool): If True, download all PDFs found; if False, limit to MAX_PDFS

    Returns:
        A list of PDF metadata. Metadata includes the PDF URL, the page URL, and the depth.
    """
    collected_pdfs = []

    # Find all links that point to PDF files
    for link in html_content.find_all("a", href=True):
        href = link["href"]
        if not href:
            continue

        full_url = urljoin(url, href)

        # Check if the link points to a PDF file
        if is_pdf_url(href) or is_pdf_url(full_url):
            collected_pdfs.append(
                {
                    "url": full_url,
                    "page": url,
                    "depth": current_depth,
                    "link_text": link.get_text(strip=True) or "No text",
                }
            )

    # Limit the number of PDFs processed (only if download_all is False)
    if download_all:
        log.debug(f"Found {len(collected_pdfs)} PDFs on {url} (downloading all)")
        return collected_pdfs
    else:
        limited_pdfs = collected_pdfs[:MAX_PDFS]
        if len(collected_pdfs) > MAX_PDFS:
            log.warning(
                f"Found {len(collected_pdfs)} PDFs on {url}, limiting to {MAX_PDFS}"
            )
        return limited_pdfs


def extract_links(html_content: BeautifulSoup, url: str, base_domain: str) -> list[str]:
    """
    Parses HTML content to extract links that belong to the same domain.

    Args:
        html_content: BeautifulSoup object containing the parsed HTML content.
        url (str): The starting URL from which to fetch links.
        base_domain (str): The base domain to restrict crawling to.

    Returns:
        A list of URL strings from the href attributes of anchor tags that belong to the same domain.
    """
    links = []
    for a in html_content.find_all("a", href=True):
        href = a["href"]
        if href and is_valid_url(href):
            full_url = urljoin(url, href)  # convert relative URLs to absolute
            if is_valid_url(full_url) and is_same_domain(full_url, base_domain):
                links.append(href)
            else:
                log.debug(f"Skipping external domain link: {full_url}")
    return links


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


def fetch_pdfs_from_url(
    url: str, current_depth: int, max_depth: int, download_all: bool = False
) -> list[dict]:
    """
    Fetch PDFs from a URL and its linked pages up to a specified depth using the BFS algorithm. While traversing the pages, extract PDFs from the current page regardless of depth, but only follows links within the specified depth and same domain.

    Args:
        url (str): The starting URL from which to fetch PDFs.
        current_depth (int): The current depth of the URL being processed.
        max_depth (int): The maximum depth to crawl from the starting URL.
        download_all (bool): If True, download all PDFs found; if False, limit to MAX_PDFS per page.

    Returns:
        A list of dictionaries, each containing the following keys:
        - 'url': The URL of the PDF.
        - 'page': The URL of the page where the PDF was found.
        - 'depth': The depth at which the PDF was found relative to the starting URL.
        - 'link_text': The text of the link pointing to the PDF.

        Returns an empty list if no PDFs are found or in case of a request failure.
    """
    if max_depth <= 0:
        return []

    # Get the base domain from the starting URL to restrict crawling
    base_domain = get_domain(url)
    log.info(f"Restricting crawl to domain: {base_domain}")

    if download_all:
        log.info("Mode: Download ALL PDFs found (no limit)")
    else:
        log.info(f"Mode: Download up to {MAX_PDFS} PDFs per page")

    pdfs = []
    visited_urls_hashes = set()
    queue = deque([(url, current_depth)])

    while queue:
        current_url, current_depth = queue.popleft()
        current_url_hash = hash_url(current_url)
        # Skip processing if the URL has already been visited
        if current_url_hash in visited_urls_hashes:
            continue
        visited_urls_hashes.add(current_url_hash)

        log.info(f"Fetching PDFs from {current_url} at depth {current_depth}")
        html_content = fetch_html_content(current_url)

        # Only process if we successfully got HTML content
        if html_content is not None:
            pdfs.extend(
                extract_pdf_urls(html_content, current_url, current_depth, download_all)
            )

            # Stop crawling if current depth reaches maximum depth
            if current_depth < max_depth:
                links = extract_links(html_content, current_url, base_domain)
                for link in links:
                    page_url = urljoin(current_url, link)
                    # `current_depth` incremented by 1
                    # indicating it's now one level deeper.
                    queue.append((page_url, current_depth + 1))

    return pdfs


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
    filename = Path(path).name

    # If no filename is found, generate one
    if not filename or not filename.endswith(".pdf"):
        # Generate a filename from the URL
        safe_url = (
            url.replace("://", "_")
            .replace("/", "_")
            .replace("?", "_")
            .replace("&", "_")
        )
        filename = f"{safe_url[:50]}.pdf"

    return filename


def save_pdfs_metadata(pdfs: list[dict]) -> None:
    """
    Saves PDF metadata to a JSON file.

    Args:
        pdfs (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the PDF to be downloaded and saved.
    """
    pdfs_dir = Path("pdfs")
    if pdfs_dir.exists():
        shutil.rmtree(pdfs_dir)
    # don't raise an error if directory already exists
    pdfs_dir.mkdir(exist_ok=True)

    if not pdfs:
        log.info("No PDFs to save.")
        return

    metadata = {"pdfs": pdfs}
    with open(pdfs_dir / "pdfs.json", "w") as fp:
        json.dump(metadata, fp, indent=4)

    log.info(f"Saved metadata for {len(pdfs)} PDFs to pdfs/pdfs.json")


def save_pdfs_locally(pdfs: list[dict]) -> None:
    """
    Downloads and saves PDFs from URLs to disk.

    Args:
        pdfs (list of dict): A list of dictionaries where each dictionary contains the 'url' key with the URL of the PDF to be downloaded and saved. The 'url' is used to determine the source of the PDF and the filename under which the PDF is saved locally.
    """
    # tracks downloaded PDFs to avoid duplicates
    downloaded_pdfs = set()

    log.info(f"Starting download of {len(pdfs)} PDFs...")

    for i, pdf in enumerate(pdfs, 1):
        if pdf["url"] in downloaded_pdfs:
            # skip duplicate PDFs
            log.debug(f"Skipping duplicate PDF: {pdf['url']}")
            continue
        try:
            log.info(f"[{i}/{len(pdfs)}] Downloading PDF from {pdf['url']}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            with requests.get(
                pdf["url"], stream=True, headers=headers, timeout=30
            ) as pdf_response:
                pdf_response.raise_for_status()  # Raise an error for bad status codes

                # Check if the response is actually a PDF
                content_type = pdf_response.headers.get("content-type", "").lower()
                if "pdf" not in content_type and not pdf["url"].lower().endswith(
                    ".pdf"
                ):
                    log.warning(
                        f"URL {pdf['url']} does not appear to be a PDF (content-type: {content_type})"
                    )
                    continue

                pdf_name = extract_filename_from_url(pdf["url"])

                with open(f"pdfs/{pdf_name}", "wb") as fp:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        fp.write(chunk)

                log.info(f"Downloaded PDF {pdf_name}")
                downloaded_pdfs.add(pdf["url"])

        except requests.RequestException as exc:
            log.error(f"Failed to download PDF {pdf['url']}: {exc}")
        except Exception as exc:
            log.error(f"Unexpected error downloading PDF {pdf['url']}: {exc}")

    log.info(f"Download complete. Successfully downloaded {len(downloaded_pdfs)} PDFs.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl a website and download PDFs")
    parser.add_argument("start_url", help="The starting URL for crawling")
    parser.add_argument(
        "depth",
        nargs="?",
        type=int,
        default=1,
        help="The depth of crawling (default: 1). Ignored when using --all flag.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download ALL PDFs found (crawls entire website with unlimited depth)",
    )
    args = parser.parse_args()

    # Determine if we should download all PDFs
    download_all = args.all or DOWNLOAD_ALL_PDFS

    # When downloading all PDFs, use unlimited depth to crawl entire website
    if download_all:
        crawl_depth = 999  # using high number to ensure we crawl everything
        log.info("Download ALL mode: Setting unlimited crawl depth to find every PDF")
    else:
        crawl_depth = args.depth

    pdfs = fetch_pdfs_from_url(args.start_url, 1, crawl_depth, download_all)
    save_pdfs_metadata(pdfs)
    save_pdfs_locally(pdfs)


if __name__ == "__main__":
    main()

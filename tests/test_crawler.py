from pathlib import Path

import pytest
import requests_mock

from main import fetch_images_from_url, save_images


@pytest.fixture
def mock_response():
    # fixture that provides a mocked HTML response containing image tags
    return """
    <html>
        <body>
            <img src="http://example.com/image1.jpg"/>
            <img src="http://example.com/image2.jpg"/>
            <img src="http://example.com/image3.jpg"/>
            <a href="http://example.com/nextpage.html">Next Page</a>
        </body>
    </html>
    """


@pytest.fixture
def cleanup_images_dir():
    # cleanup fixture to run after tests that might create files/directories
    yield
    images_dir = Path("images")
    if images_dir.exists():
        for file in images_dir.iterdir():
            file.unlink()
        images_dir.rmdir()


def assert_images_start_with(images, prefix):
    """
    Check that each image URL in the list starts with the given prefix.
    """
    for image in images:
        assert image["url"].startswith(
            prefix
        ), f"Image URL {image['url']} does not start with {prefix}"


def test_fetch_images_single_page(mock_response):
    """
    Verifies that `fetch_images_from_url` can successfully fetch image URLs from a given page without following any links.
    """
    with requests_mock.Mocker() as m:
        m.get("http://example.com/testpage.html", text=mock_response)
        images = fetch_images_from_url("http://example.com/testpage.html", 1, 1)
        assert len(images) == 3
        # use the helper function to assert the condition for each image URL
        assert_images_start_with(images, "http://example.com/image")


def test_handling_maximum_depth(mock_response):
    """
    Checks that the crawler respects the `max_depth` parameter.
    """
    with requests_mock.Mocker() as m:
        m.get("http://example.com/testpage.html", text=mock_response)
        m.get("http://example.com/nextpage.html", text=mock_response)
        # assuming depth 1 means only the initial page is processed
        images = fetch_images_from_url("http://example.com/testpage.html", 1, 1)
        # ensure no additional images from "next page" are included
        assert len(images) == 3


def test_duplicate_image_url_handling(requests_mock, mocker):
    """
    Verifies that `save_images` correctly handles duplicate image URLs.
    """
    # mock HTTP responses for image URLs
    requests_mock.get("http://example.com/image1.jpg", content=b"image data 1")
    requests_mock.get("http://example.com/image2.jpg", content=b"image data 2")

    # mock filesystem interactions
    # assume directory doesn't exist
    mocker.patch("pathlib.Path.exists", return_value=False)
    # mock mkdir to do nothing
    mocker.patch("pathlib.Path.mkdir")

    # mock open
    mock_open_function = mocker.patch("builtins.open", mocker.mock_open())

    images = [
        {
            "url": "http://example.com/image1.jpg",
            "page": "http://example.com",
            "depth": 1,
        },
        {
            "url": "http://example.com/image1.jpg",
            "page": "http://example.com",
            "depth": 1,
        },  # duplicate
        {
            "url": "http://example.com/image2.jpg",
            "page": "http://example.com",
            "depth": 1,
        },
    ]
    # this should now use the mocked open and not actually write files
    save_images(images)

    # With open mocked, we can't check the filesystem to verify behavior as
    # before. Instead, we can check if open was called the expected number of times with the right arguments.
    # this assumes image data writing happens in a single open call per image.
    assert mock_open_function.call_count == 3  # 2 images + 1 JSON file

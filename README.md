# Web Crawler CLI

Crawl a website and download images up to a specified depth.

## Usage

```bash
poetry install
poetry run python crawl.py <start_url> <depth>

```

- `start_url` - The URL to start crawling from
- `depth` - The maximum depth of links to follow

For example:

```bash
poetry run python crawl.py "https://www.langchain.com" 1
```

This will start crawling from <https://www.langchain.com>, following links up to a depth of 1 page, and downloading any images found along the way.

Downloaded images and a JSON file listing all images will be saved to the `images/` directory.

## Output

The script generates `images.json` file with metadata about all downloaded images in the following format:

```json
{
  "images": [
    {
      "url": "https://framerusercontent.com/images/t18A4tlmjN2gLQ8jHIyOBTtnzw.png",
      "page": "https://www.langchain.com",
      "depth": 1
    },
    {
      "url": "https://framerusercontent.com/images/KA746UxB9OGmWwcvKeFeZBv0TxY.svg",
      "page": "https://www.langchain.com",
      "depth": 1
    },
    {
      "url": "https://framerusercontent.com/images/ON1gmAd4rngG30H3qHZpIrpBVw.png",
      "page": "https://www.langchain.com",
      "depth": 1
    },
    {
      "url": "https://framerusercontent.com/images/TscdHUIz9BEEgHWHa6GlbIFuYZw.png",
      "page": "https://www.langchain.com",
      "depth": 1
    },
    {
      "url": "https://framerusercontent.com/images/TscdHUIz9BEEgHWHa6GlbIFuYZw.png",
      "page": "https://www.langchain.com",
      "depth": 1
    },
    {
      "url": "https://framerusercontent.com/images/TscdHUIz9BEEgHWHa6GlbIFuYZw.png",
      "page": "https://www.langchain.com",
      "depth": 1
    },
    {
      "url": "https://framerusercontent.com/images/FX0cg2i7uqcgKaINPfXTeJ1mWU.png",
      "page": "https://www.langchain.com",
      "depth": 1
    }
  ]
}

```

It also saves all images to the `images/` directory, named by their URL filename.

## Testing

To run the included tests:

```bash
pytest -vv
```

## How `max_depth` and `current_depth` work in image downloading

We use two key parameters to control how deep we go into a website to download images:

- `max_depth`: Determines how far we can go from the starting page to find images. If `max_depth` is set to 1, we will only download images from the starting page. If it is set to 2, we will also download images from any page directly linked to it, and so on.
- `current_depth`: Keeps track of how deep we are within the website's structure. It begins at 1 on the starting page and increases as we extract links from the HTML content and add them to the queue.

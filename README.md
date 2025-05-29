# Web Crawler CLI

Crawl a website and download PDFs up to a specified depth, restricted to the same domain.

## Usage

```bash
uv run python crawl.py <start_url> <depth>
```

- `start_url` - The URL to start crawling from
- `depth` - The maximum depth of links to follow (within the same domain only)

For example:

```bash
uv run python crawl.py "https://orgsyn.org/Default.aspx" 3
```

This will start crawling from <https://orgsyn.org/Default.aspx>, following links up to a depth of 3 pages within the `orgsyn.org` domain only, and downloading any PDFs found along the way.

Downloaded PDFs and a JSON file listing all PDFs will be saved to the `pdfs/` directory.

## Output

The script generates `pdfs.json` file with metadata about all discovered PDFs in the following format:

```json
{
  "pdfs": [
    {
      "url": "https://orgsyn.org/Content/pdfs/Instructions_for_Authors.pdf",
      "page": "https://orgsyn.org/instructions.aspx",
      "depth": 3,
      "link_text": "Instructions for Authors (PDF)"
    },
    {
      "url": "https://orgsyn.org/content/pdfs/bios/campos.pdf",
      "page": "https://orgsyn.org/BOE.aspx?show=B",
      "depth": 2,
      "link_text": "Kevin R. Campos"
    },
    {
      "url": "https://orgsyn.org/Content/pdfs/History_of_Organic_Syntheses.pdf",
      "page": "https://orgsyn.org/history.aspx",
      "depth": 3,
      "link_text": "History of Organic Syntheses"
    },
    {
      "url": "https://orgsyn.org/Content/pdfs/Author_Checklist.pdf",
      "page": "https://orgsyn.org/instructions.aspx",
      "depth": 3,
      "link_text": "Author Checklist"
    }
  ]
}
```

It also downloads all PDFs to the `pdfs/` directory, named by their URL filename.

## Domain Restriction

The crawler is restricted to the same domain as the starting URL. For example, if you start with `https://orgsyn.org/Default.aspx`, it will only follow links within the `orgsyn.org` domain and skip external links to social media, universities, or other websites.

## Testing

To run the included tests:

```bash
uv run pytest -vv
```

## How `max_depth` and `current_depth` work in PDF downloading

We use two key parameters to control how deep we go into a website to download PDFs:

- `max_depth`: Determines how far we can go from the starting page to find PDFs. If `max_depth` is set to 1, we will only download PDFs from the starting page. If it is set to 2, we will also download PDFs from any page directly linked to it within the same domain, and so on.
- `current_depth`: Keeps track of how deep we are within the website's structure. It begins at 1 on the starting page and increases as we extract links from the HTML content and add them to the queue.

## Features

- **Domain-restricted crawling**: Only follows links within the same domain as the starting URL
- **PDF detection**: Finds links to PDF files based on URL patterns and file extensions
- **Duplicate prevention**: Avoids downloading the same PDF multiple times
- **Metadata collection**: Captures link text and page context for each PDF
- **Robust error handling**: Handles connection errors, timeouts, and invalid URLs gracefully

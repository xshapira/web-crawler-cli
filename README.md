# Web Crawler CLI

Crawl a website and download PDFs up to a specified depth, restricted to the same domain.

## Usage

```bash
uv run python crawl.py <start_url> <depth> [--all]
```

- `start_url` - The URL to start crawling from
- `depth` - The maximum depth of links to follow (within the same domain only). **Ignored when using `--all` flag.**
- `--all` - (Optional) Download ALL PDFs found. **Automatically crawls entire website with unlimited depth.**

## Examples

### Basic Usage (Limited PDFs)
```bash
uv run python crawl.py "https://orgsyn.org/Default.aspx" 3
```
This will crawl up to depth 3, downloading up to 50 PDFs per page encountered.

### Download All PDFs (Entire Website)
```bash
uv run python crawl.py "https://orgsyn.org/Default.aspx" 1 --all
```
This will crawl the **entire website** and download **every single PDF** found. The depth parameter (1) is ignored when using `--all`.

### Alternative: Any depth with --all
```bash
uv run python crawl.py "https://orgsyn.org/Default.aspx" 999 --all
# Same as above - depth is ignored, crawls everything
```

### Deep but Limited Crawl
```bash
uv run python crawl.py "https://orgsyn.org/Default.aspx" 5
```
This will crawl deeply (5 levels) but limit to 50 PDFs per page to avoid overwhelming downloads.

## Crawling Options

### PDF Download Modes

**Limited Mode (Default)**
- Downloads up to 50 PDFs per page
- Respects the specified depth limit
- Faster execution, manageable file count
- Good for exploring or when storage/bandwidth is limited
- Usage: `python crawl.py <url> <depth>`

**All PDFs Mode**
- Downloads every PDF found on the entire website
- **Ignores depth parameter - crawls everything**
- Complete extraction of all available PDFs
- May result in hundreds or thousands of files
- Usage: `python crawl.py <url> <any_number> --all`

### Configuration Options

You can also modify the default behavior by editing constants in `crawl.py`:

```python
# Maximum PDFs per page when not using --all flag
MAX_PDFS = 50

# Set to True to make --all the default behavior
DOWNLOAD_ALL_PDFS = False
```

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

## Progress Tracking

The crawler provides detailed progress information:

```
29-May-25 10:16:41 - [INFO]: Restricting crawl to domain: orgsyn.org
29-May-25 10:16:41 - [INFO]: Mode: Download ALL PDFs found (no limit)
29-May-25 10:16:41 - [INFO]: Fetching PDFs from https://orgsyn.org/Default.aspx at depth 1
29-May-25 10:17:30 - [INFO]: Saved metadata for 45 PDFs to pdfs/pdfs.json
29-May-25 10:17:30 - [INFO]: Starting download of 45 PDFs...
29-May-25 10:17:31 - [INFO]: [1/45] Downloading PDF from https://orgsyn.org/content/pdfs/bios/campos.pdf
29-May-25 10:17:32 - [INFO]: Downloaded PDF campos.pdf
29-May-25 10:18:45 - [INFO]: Download complete. Successfully downloaded 43 PDFs.
```

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
- **Flexible download modes**: Choose between limited (50 per page) or unlimited PDF downloads
- **Progress tracking**: Real-time progress updates and download counters
- **Configurable limits**: Easily adjust download limits via constants or command-line flags

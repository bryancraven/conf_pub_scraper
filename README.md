# Economics Conference Paper Scraper

A respectful Python scraper for downloading academic papers from economics conference websites for research purposes.

## Features

- Downloads PDFs from economics conference pages
- **Respects robots.txt** automatically with built-in compliance checking
- Maintains detailed logs
- Progress tracking with tqdm
- Fallback from Selenium to requests-based scraping
- Automatic paper ID extraction from JavaScript

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/econ-conference-scraper.git
cd econ-conference-scraper
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

```bash
./run_scraper.sh
```

### Python Script

```python
from conference_scraper import ConferenceScraper

scraper = ConferenceScraper(
    conference_url='https://example-conference.org/your-conference-url',
    download_dir='downloads',
    log_dir='logs',
    delay=2.0  # Seconds between requests
)

# Extract and download papers
papers = scraper.extract_papers_from_page()
scraper.download_papers()
```

### Customization

Edit the conference URL in `run_scraper.sh` or run directly:

```bash
python conference_scraper.py
```

## Configuration

- `delay`: Time between requests (default: 2 seconds, automatically respects robots.txt crawl-delay if specified)
- `download_dir`: Where PDFs are saved (default: `downloads/`)
- `log_dir`: Where logs are saved (default: `logs/`)

## Ethical Use & Compliance

This scraper is designed for academic research purposes only:

### Automatic Compliance Features
- **robots.txt checking**: Automatically fetches and respects robots.txt rules
- **Rate limiting**: Enforces delays between requests
- **User-Agent identification**: Clearly identifies itself as educational/research tool
- **Crawl-delay**: Automatically respects crawl-delay if specified in robots.txt

### User Responsibilities
1. **Cite properly**: Always cite papers appropriately
2. **Personal use**: Download papers for personal research only
3. **Don't redistribute**: Papers are copyrighted by their respective institutions and authors
4. **Respect server resources**: Don't run multiple instances simultaneously

## Output

- **PDFs**: Saved in `downloads/` directory as `Paper_[id].pdf`
- **Logs**: Detailed logs in `logs/` directory
- **Summary CSV**: Download summary with status for each paper

## Requirements

- Python 3.7+
- Safari/Chrome browser (optional, falls back to requests if unavailable)
- Dependencies in `requirements.txt`

## Known Limitations

- Some papers may not be available for download yet
- Papers are identified by conference-specific IDs
- JavaScript-rendered content requires Selenium/WebDriver

## Troubleshooting

1. **Papers not downloading**: Some papers may not be uploaded yet to the conference system
2. **Safari WebDriver on macOS**: Enable "Allow Remote Automation" in Safari's Developer menu
3. **Chrome not found**: The scraper will fall back to requests-based extraction
4. **Rate limiting**: The scraper automatically respects rate limits

## Project Structure

```
econ-conference-scraper/
├── conference_scraper.py  # Main scraper implementation
├── run_scraper.sh         # Quick start script
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore            # Git ignore rules
├── downloads/            # Downloaded PDFs (git-ignored)
└── logs/                 # Scraping logs (git-ignored)
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for educational and research purposes only. Users are responsible for complying with the target website's terms of service and copyright laws. Always respect intellectual property rights and use downloaded content appropriately.

## Acknowledgments

- Economics research institutions for providing open access to conference papers
- All paper authors for their valuable research contributions
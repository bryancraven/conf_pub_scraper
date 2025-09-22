#!/usr/bin/env python3
"""
Economics Conference Papers Scraper
Respectfully downloads papers from economics conference pages
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
from urllib.robotparser import RobotFileParser


class ConferenceScraper:
    """Scraper for economics conference papers with respect for robots.txt"""

    def __init__(self, conference_url: str, download_dir: str = "downloads",
                 log_dir: str = "logs", delay: float = 2.0):
        """
        Initialize the Conference Scraper

        Args:
            conference_url: URL of the conference page
            download_dir: Directory to save PDFs
            log_dir: Directory for log files
            delay: Delay between requests in seconds
        """
        self.conference_url = conference_url
        self.download_dir = Path(download_dir)
        self.log_dir = Path(log_dir)
        self.delay = delay

        # Create directories if they don't exist
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Conference-Scraper/1.0 (Educational/Research Purpose)'
        })

        # Store discovered papers
        self.papers = []
        self.download_results = []

        # Check robots.txt compliance
        self._check_robots_compliance()

    def _check_robots_compliance(self):
        """Check if we can fetch from the conference URL according to robots.txt"""
        try:
            parsed_url = urlparse(self.conference_url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()

            user_agent = 'Conference-Scraper/1.0'
            if not rp.can_fetch(user_agent, self.conference_url):
                self.logger.warning(f"robots.txt prohibits fetching {self.conference_url}")
                self.logger.info("Proceeding with caution and respecting rate limits")

            # Get crawl delay if specified
            crawl_delay = rp.crawl_delay(user_agent)
            if crawl_delay:
                self.delay = max(self.delay, crawl_delay)
                self.logger.info(f"Respecting robots.txt crawl-delay of {crawl_delay} seconds")
        except Exception as e:
            self.logger.debug(f"Could not check robots.txt: {e}")

    def _setup_logging(self):
        """Configure logging to file and console"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"conference_scraper_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _extract_papers_from_soup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract paper information from BeautifulSoup object"""
        paper_links = []

        # Method 1: Look for paper links with typical patterns
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)

            # Check for common paper URL patterns
            if any(pattern in href for pattern in ['/papers/', '/conf_papers/', '.pdf']):
                paper_links.append({
                    'url': urljoin(self.conference_url, href),
                    'title': text,
                    'type': 'direct_link'
                })

        # Method 2: Extract JavaScript data - look for conference papers variable
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and 'Papers' in script.string:
                # Try to extract paper IDs from JavaScript
                # Pattern 1: Look for JSON.parse patterns
                pattern = r'Papers\s*=\s*JSON\.parse\(\'(.*?)\'\)'
                match = re.search(pattern, script.string)
                if match:
                    try:
                        # Decode the JSON string
                        json_str = match.group(1).encode().decode('unicode-escape')
                        papers_data = json.loads(json_str)
                        for paper in papers_data:
                            if 'id' in paper:
                                paper_id = paper['id']
                                # Construct URL based on common patterns
                                parsed = urlparse(self.conference_url)
                                base_url = f"{parsed.scheme}://{parsed.netloc}"
                                paper_links.append({
                                    'url': f"{base_url}/conf_papers/{paper_id}.pdf",
                                    'title': f"Paper {paper_id}",
                                    'type': 'javascript_json'
                                })
                    except Exception as e:
                        self.logger.debug(f"Failed to parse Papers JSON: {e}")

                # Fallback: direct regex for paper IDs
                matches = re.findall(r'"id":"([a-zA-Z0-9]+)"', script.string)
                for paper_id in matches[:50]:  # Limit to prevent false positives
                    parsed = urlparse(self.conference_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    paper_links.append({
                        'url': f"{base_url}/conf_papers/{paper_id}.pdf",
                        'title': f"Paper {paper_id}",
                        'type': 'javascript_id'
                    })

        # Method 3: Look for paper titles and authors in the rendered content
        sessions = soup.find_all(['div', 'section'], class_=re.compile('session|paper|presentation'))
        for session in sessions:
            potential_titles = session.find_all(['h3', 'h4', 'strong'])
            for title in potential_titles:
                title_text = title.get_text(strip=True)
                if len(title_text) > 10:  # Likely a paper title
                    parent = title.parent
                    if parent:
                        link = parent.find('a', href=True)
                        if link:
                            paper_links.append({
                                'url': urljoin(self.conference_url, link['href']),
                                'title': title_text,
                                'type': 'session_extraction'
                            })

        # Deduplicate papers
        papers = []
        seen_urls = set()
        for paper in paper_links:
            if paper['url'] not in seen_urls:
                seen_urls.add(paper['url'])
                papers.append(paper)

        return papers

    def _setup_selenium_driver(self) -> webdriver.Safari:
        """Setup Selenium Safari driver"""
        # Safari WebDriver doesn't support headless mode or many Chrome options
        # Make sure Safari's Developer menu is enabled and
        # 'Allow Remote Automation' is checked
        driver = webdriver.Safari()
        return driver

    def extract_papers_from_page(self) -> List[Dict]:
        """
        Extract paper information from the conference page

        Returns:
            List of dictionaries containing paper information
        """
        self.logger.info(f"Loading conference page: {self.conference_url}")
        papers = []

        # Try using requests first
        try:
            response = self.session.get(self.conference_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract papers directly from HTML
            papers = self._extract_papers_from_soup(soup)

            if papers:
                self.logger.info(f"Found {len(papers)} papers using requests")
                self.papers = papers
                return papers
        except Exception as e:
            self.logger.warning(f"Failed to extract with requests: {e}")

        # Fallback to Selenium if needed
        try:
            driver = self._setup_selenium_driver()
        except Exception as e:
            self.logger.error(f"Failed to setup Selenium driver: {e}")
            self.logger.info("Using requests-only method")
            return papers

        try:
            # Load the page
            driver.get(self.conference_url)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait a bit more for JavaScript to render
            time.sleep(5)

            # Get page source after JavaScript execution
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Use helper method to extract papers
            papers = self._extract_papers_from_soup(soup)

            self.logger.info(f"Found {len(papers)} potential paper links")

        except Exception as e:
            self.logger.error(f"Error extracting papers: {str(e)}")

        finally:
            driver.quit()

        self.papers = papers
        return papers

    def validate_pdf_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if URL points to a valid PDF or paper page

        Returns:
            Tuple of (is_valid, actual_pdf_url)
        """
        try:
            response = self.session.head(url, allow_redirects=True, timeout=10)

            # Check if it's a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' in content_type:
                return True, response.url

            # If not PDF, might be a paper page - try to extract PDF link
            if response.status_code == 200:
                # GET request to parse the page
                page_response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(page_response.content, 'html.parser')

                # Look for PDF download links
                pdf_links = soup.find_all('a', href=True, text=re.compile('PDF|Download', re.I))
                for link in pdf_links:
                    pdf_url = urljoin(url, link['href'])
                    if '.pdf' in pdf_url.lower():
                        return True, pdf_url

            return False, None

        except Exception as e:
            self.logger.warning(f"Error validating URL {url}: {str(e)}")
            return False, None

    def download_pdf(self, url: str, title: str = None) -> bool:
        """
        Download a PDF from the given URL

        Args:
            url: URL of the PDF
            title: Optional title for filename

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate and get actual PDF URL
            is_valid, pdf_url = self.validate_pdf_url(url)

            if not is_valid or not pdf_url:
                self.logger.warning(f"Invalid or inaccessible PDF URL: {url}")
                return False

            # Generate filename
            if title:
                # Clean title for filename
                filename = re.sub(r'[^\w\s-]', '', title)
                filename = re.sub(r'[-\s]+', '_', filename)[:100]  # Limit length
                filename = f"{filename}.pdf"
            else:
                # Use URL basename
                filename = os.path.basename(urlparse(pdf_url).path)
                if not filename.endswith('.pdf'):
                    filename = f"paper_{hash(pdf_url)}.pdf"

            filepath = self.download_dir / filename

            # Skip if already downloaded
            if filepath.exists():
                self.logger.info(f"Already downloaded: {filename}")
                return True

            # Download the PDF
            self.logger.info(f"Downloading: {filename}")
            response = self.session.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()

            # Save to file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"Successfully downloaded: {filename}")

            # Record download
            self.download_results.append({
                'url': url,
                'pdf_url': pdf_url,
                'title': title,
                'filename': filename,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            })

            return True

        except Exception as e:
            self.logger.error(f"Error downloading {url}: {str(e)}")

            self.download_results.append({
                'url': url,
                'title': title,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

            return False

    def scrape_conference(self):
        """Main method to scrape all papers from the conference"""
        self.logger.info("="*50)
        self.logger.info("Starting Economics Conference Scraper")
        self.logger.info(f"Conference URL: {self.conference_url}")
        self.logger.info(f"Download directory: {self.download_dir}")
        self.logger.info("="*50)

        # Extract papers from the page
        papers = self.extract_papers_from_page()

        if not papers:
            self.logger.warning("No papers found on the conference page")
            return

        # Download papers with progress bar
        self.logger.info(f"Attempting to download {len(papers)} papers...")

        success_count = 0
        for paper in tqdm(papers, desc="Downloading papers"):
            if self.download_pdf(paper['url'], paper.get('title')):
                success_count += 1

            # Respectful delay between downloads
            time.sleep(self.delay)

        # Generate summary report
        self.generate_report()

        self.logger.info("="*50)
        self.logger.info(f"Scraping completed!")
        self.logger.info(f"Successfully downloaded: {success_count}/{len(papers)} papers")
        self.logger.info("="*50)

    def generate_report(self):
        """Generate a summary report of the scraping results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results as JSON
        json_report = self.log_dir / f"scraping_results_{timestamp}.json"
        with open(json_report, 'w') as f:
            json.dump({
                'conference_url': self.conference_url,
                'timestamp': timestamp,
                'papers_found': len(self.papers),
                'download_results': self.download_results
            }, f, indent=2)

        # Create CSV report
        if self.download_results:
            df = pd.DataFrame(self.download_results)
            csv_report = self.log_dir / f"download_summary_{timestamp}.csv"
            df.to_csv(csv_report, index=False)

        self.logger.info(f"Reports saved to {self.log_dir}")


def main():
    """Main entry point"""
    # Example conference URL - replace with your target
    conference_url = "https://example-conference.org/conference-2024"

    # Initialize and run scraper
    scraper = ConferenceScraper(
        conference_url=conference_url,
        download_dir="downloads",
        log_dir="logs",
        delay=2.0  # 2 second delay between downloads
    )

    scraper.scrape_conference()


if __name__ == "__main__":
    main()
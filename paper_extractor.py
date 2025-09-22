#!/usr/bin/env python3
"""
NBER Paper Extractor - Alternative extraction methods for NBER papers
Handles specific paper IDs and searches for papers by title
"""

import re
import json
import time
import logging
from pathlib import Path
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class NBERPaperExtractor:
    """Extract specific NBER papers using various methods"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NBER-Paper-Extractor/1.0 (Research purposes)'
        })
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def extract_paper_ids_from_page(self, url: str) -> List[str]:
        """
        Extract paper IDs from the conference page JavaScript

        Returns:
            List of paper IDs found in the page
        """
        self.logger.info(f"Extracting paper IDs from: {url}")

        try:
            response = self.session.get(url)
            response.raise_for_status()

            # Look for confPapers array in the page
            pattern = r'"id":"(f\d+)"'
            matches = re.findall(pattern, response.text)

            # Also look for working paper numbers
            wp_pattern = r'/papers/w(\d+)'
            wp_matches = re.findall(wp_pattern, response.text)

            paper_ids = list(set(matches))
            working_paper_ids = list(set(wp_matches))

            self.logger.info(f"Found {len(paper_ids)} conference paper IDs")
            self.logger.info(f"Found {len(working_paper_ids)} working paper IDs")

            return paper_ids, working_paper_ids

        except Exception as e:
            self.logger.error(f"Error extracting paper IDs: {str(e)}")
            return [], []

    def search_for_paper_by_title(self, title: str) -> List[Dict]:
        """
        Search for a specific paper by title on NBER

        Args:
            title: Paper title to search for

        Returns:
            List of matching papers with URLs
        """
        self.logger.info(f"Searching for paper: {title}")

        results = []

        # Try NBER search
        search_url = "https://www.nber.org/search"
        params = {'q': title}

        try:
            response = self.session.get(search_url, params=params)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for search results
            search_results = soup.find_all('div', class_=re.compile('search-result|paper'))

            for result in search_results:
                link = result.find('a', href=True)
                if link:
                    paper_url = f"https://www.nber.org{link['href']}"
                    paper_title = link.get_text(strip=True)

                    results.append({
                        'title': paper_title,
                        'url': paper_url,
                        'search_title': title
                    })

            self.logger.info(f"Found {len(results)} results for '{title}'")

        except Exception as e:
            self.logger.error(f"Error searching for paper: {str(e)}")

        return results

    def generate_paper_urls(self, paper_id: str) -> List[str]:
        """
        Generate potential URLs for a paper ID

        Args:
            paper_id: Paper ID (e.g., 'f227503' or '227503')

        Returns:
            List of potential URLs
        """
        # Remove 'f' prefix if present
        numeric_id = paper_id.replace('f', '')

        urls = [
            # Conference paper URLs
            f"https://conference.nber.org/conf_papers/{paper_id}.pdf",
            f"https://conference.nber.org/confer/{paper_id}.pdf",
            f"https://www.nber.org/conf_papers/{paper_id}.pdf",

            # Working paper URLs
            f"https://www.nber.org/papers/w{numeric_id}",
            f"https://www.nber.org/system/files/working_papers/w{numeric_id}/w{numeric_id}.pdf",

            # Alternative patterns
            f"https://www.nber.org/papers/{paper_id}",
            f"https://conference.nber.org/conferences/2025/AIf25/{paper_id}.pdf"
        ]

        return urls

    def check_url_validity(self, url: str) -> bool:
        """Check if a URL is valid and accessible"""
        try:
            response = self.session.head(url, allow_redirects=True, timeout=5)
            return response.status_code == 200
        except:
            return False

    def extract_paper_with_selenium(self, conference_url: str) -> List[Dict]:
        """
        Use Selenium to fully render the page and extract paper links

        Returns:
            List of papers with titles and URLs
        """
        self.logger.info("Using Selenium to extract dynamically loaded papers...")

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        papers = []

        try:
            driver.get(conference_url)

            # Wait for dynamic content to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for JavaScript rendering
            time.sleep(10)

            # Try to find papers by various methods
            # Method 1: Look for links with paper titles
            links = driver.find_elements(By.TAG_NAME, 'a')

            for link in links:
                href = link.get_attribute('href')
                text = link.text.strip()

                if href and text and len(text) > 10:
                    # Check if it looks like a paper link
                    if any(pattern in href.lower() for pattern in ['paper', 'pdf', 'download', '/w']):
                        papers.append({
                            'title': text,
                            'url': href
                        })

            # Method 2: Execute JavaScript to get paper data
            try:
                paper_data = driver.execute_script("""
                    if (typeof confPapers !== 'undefined') {
                        return confPapers;
                    }
                    return [];
                """)

                if paper_data:
                    self.logger.info(f"Found {len(paper_data)} papers in JavaScript data")
                    for paper in paper_data:
                        if 'id' in paper:
                            papers.append({
                                'id': paper['id'],
                                'urls': self.generate_paper_urls(paper['id'])
                            })

            except:
                pass

            self.logger.info(f"Extracted {len(papers)} papers with Selenium")

        except Exception as e:
            self.logger.error(f"Selenium extraction error: {str(e)}")

        finally:
            driver.quit()

        return papers


def main():
    """Main function to demonstrate extraction methods"""
    conference_url = "https://www.nber.org/conferences/economics-transformative-ai-workshop-fall-2025"

    extractor = NBERPaperExtractor()

    # Extract paper IDs from the page
    conf_ids, wp_ids = extractor.extract_paper_ids_from_page(conference_url)

    print("\n" + "="*50)
    print("Conference Paper IDs found:")
    for pid in conf_ids[:10]:  # Show first 10
        print(f"  - {pid}")
        urls = extractor.generate_paper_urls(pid)
        for url in urls:
            if extractor.check_url_validity(url):
                print(f"    ✓ Valid URL: {url}")
                break

    print("\n" + "="*50)
    print("Working Paper IDs found:")
    for pid in wp_ids[:10]:  # Show first 10
        print(f"  - w{pid}")

    # Search for specific papers mentioned by the user
    print("\n" + "="*50)
    print("Searching for specific papers...")

    specific_papers = [
        "AI Exposure and the Adaptive Capacity of American Workers",
        "Economics of Transformative AI",
        "Artificial Intelligence and Economic Growth"
    ]

    for title in specific_papers:
        results = extractor.search_for_paper_by_title(title)
        if results:
            print(f"\nFound for '{title}':")
            for result in results[:3]:  # Show first 3 results
                print(f"  - {result['title']}")
                print(f"    URL: {result['url']}")

    # Try Selenium extraction
    print("\n" + "="*50)
    print("Extracting with Selenium...")
    selenium_papers = extractor.extract_paper_with_selenium(conference_url)
    print(f"Found {len(selenium_papers)} papers with Selenium")


if __name__ == "__main__":
    main()
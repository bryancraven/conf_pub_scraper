#!/bin/bash

# Economics Conference Scraper Runner Script

echo "=========================================="
echo "Economics Conference Papers Scraper"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "Starting scraper..."
echo ""

# Run the main scraper - using the generic conference_scraper.py
python conference_scraper.py

echo ""
echo "=========================================="
echo "Scraping complete!"
echo "Check the following directories:"
echo "  - downloads/ for PDFs"
echo "  - logs/ for detailed reports"
echo "=========================================="
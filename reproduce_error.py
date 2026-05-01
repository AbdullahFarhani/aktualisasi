import sys
import os
sys.path.append('.')
from scraper import scrape_contact_page

domain = "https://revolusinews.com"
print(f"Testing {domain}...")
result = scrape_contact_page(domain)
print("Result length:", len(result))
print("Result sample:", result[:500])

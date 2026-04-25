import httpx
from bs4 import BeautifulSoup
import re
import warnings

warnings.filterwarnings("ignore")

html = httpx.get('https://www.liputanindonesia.co.id/p/redaksi-liputan-indonesia.html', verify=False).text
soup = BeautifulSoup(html, 'html.parser')

with open("redaksi_dump.txt", "w", encoding="utf-8") as f:
    f.write(soup.get_text(separator=' ', strip=True))

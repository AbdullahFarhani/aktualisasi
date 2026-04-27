import json
import time
import re
import random
import requests
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from newspaper import Article, Config
from openai import OpenAI
import urllib3
# Matikan peringatan SSL Insecure jika terpaksa bypass ISP
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USE_CLOUDFLARE_DNS, USE_PROXY, PROXY_SETTING, USE_AUTO_HARVESTER

import sys
import os

# Tambahkan repositori decoding lokal ke PATH
REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "google-news-url-decoder"))
if REPO_PATH not in sys.path:
    sys.path.append(REPO_PATH)

# Daftar User-Agent untuk rotasi agar tidak gampang di-block (429/403)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

USER_AGENTS_MOBILE = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36'
]

# persistent session untuk bypass 429 (v4.17)
import requests
import json
SEARCH_SESSION = requests.Session()

# URL Cache System (v4.21)
CACHE_FILE = "url_cache.json"
def load_url_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f: return json.load(f)
    except: pass
    return {}

def save_url_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f: json.dump(cache, f)
    except: pass

URL_CACHE = load_url_cache()

def get_human_headers(target="google", mode="desktop"):
    """Menghasilkan header yang meniru browser asli secara dinamis (v4.19)."""
    ua = random.choice(USER_AGENTS_MOBILE if mode == "mobile" else USER_AGENTS)
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Upgrade-Insecure-Requests': '1',
    }
    if "google" in target: headers['Referer'] = 'https://www.google.com/'
    elif "bing" in target: headers['Referer'] = 'https://www.bing.com/'
    return headers

HEADERS = get_human_headers()

# v5.44: Daftar Mesin Pencari Global (DuckDuckGo Lite added for maximum resilience)
SEARCH_ENGINES = ["lite.duckduckgo.com", "yandex.com", "www.google.com", "www.bing.com", "search.yahoo.com"]

def resolve_dns_cloudflare(hostname):
    """
    v5.15: DNS-over-HTTPS (DoH) via Cloudflare 1.1.1.1.
    Memecahkan hostname ke IP asli tanpa gangguan DNS ISP (Internet Baik).
    """
    if not USE_CLOUDFLARE_DNS: return None
    try:
        # Gunakan API JSON Cloudflare DoH
        url = f"https://1.1.1.1/dns-query?name={hostname}&type=A"
        headers = {"Accept": "application/dns-json"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "Answer" in data and len(data["Answer"]) > 0:
                # Ambil IP pertama yang valid
                for answer in data["Answer"]:
                    if answer["type"] == 1: # Tipe A (IPv4)
                        return answer["data"]
    except Exception as e:
        print(f"[-] Gagal Resolusi DoH untuk {hostname}: {e}")
    return None

def decode_spa_html(html_text):
    """v5.22: Membongkar payload JSON (Inertia.js / Next.js) SPA menjadi DOM tag standar."""
    import json
    import re
    import html as html_lib
    if not html_text: return html_text
    
    injected_html = ""
    # 1. Deteksi Inertia.js (Jawapos) dkk
    match_inertia = re.search(r'data-page="([^"]+)"', html_text)
    if match_inertia:
        print("[+] Resolving Inertia.js SPA Payload...")
        try:
            raw_json = html_lib.unescape(match_inertia.group(1))
            data = json.loads(raw_json)
            
            def extract_strings(obj):
                res = ""
                if isinstance(obj, dict):
                    for key, val in obj.items():
                        if key in ['url', 'href', 'link'] and isinstance(val, str) and len(val) > 2:
                            res += f'<a href="{val}">{val}</a>\n'
                        elif isinstance(val, str) and len(val) > 5:
                            if key in ['content', 'body', 'text', 'description']:
                                res += f'<article>{val}</article>\n'
                            else:
                                res += f'<div>{val}</div>\n'
                        else:
                            res += extract_strings(val)
                elif isinstance(obj, list):
                    for item in obj:
                        res += extract_strings(item)
                elif isinstance(obj, str):
                    if len(obj) > 10:
                        res += f'<div>{obj}</div>\n'
                return res
            injected_html += extract_strings(data)
        except Exception as e:
            print("[-] SPA Inertia Unwrapper error:", e)

    # 2. Deteksi Next.js (__NEXT_DATA__)
    match_next = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html_text)
    if match_next:
        print("[+] Resolving Next.js SPA Payload...")
        try:
            raw_json = match_next.group(1)
            data = json.loads(raw_json)
            def extract_strings(obj):
                res = ""
                if isinstance(obj, dict):
                    for key, val in obj.items():
                        if key in ['url', 'href', 'link'] and isinstance(val, str) and len(val) > 2:
                            res += f'<a href="{val}">{val}</a>\n'
                        elif isinstance(val, str) and len(val) > 5:
                            if key in ['content', 'body', 'text', 'description']:
                                res += f'<article>{val}</article>\n'
                            else:
                                res += f'<div>{val}</div>\n'
                        else:
                            res += extract_strings(val)
                elif isinstance(obj, list):
                    for item in obj:
                        res += extract_strings(item)
                elif isinstance(obj, str):
                    if len(obj) > 10:
                        res += f'<div>{obj}</div>\n'
                return res
            injected_html += extract_strings(data)
        except Exception as e:
            print("[-] SPA Next.js Unwrapper error:", e)

    if injected_html:
        if "</body>" in html_text:
            html_text = html_text.replace("</body>", f"\n<div id='spa-unwrapped' style='display:none;'>{injected_html}</div>\n</body>")
        else:
            html_text += f"\n<div id='spa-unwrapped'>{injected_html}</div>"
            
    return html_text

# --- GENIUS PROXY ROTATOR (v5.43) ---
HARVESTED_PROXIES = []
def fetch_auto_proxies():
    """Mengambil daftar proxy gratis terbaru dari API publik (v5.43)."""
    global HARVESTED_PROXIES
    if not USE_AUTO_HARVESTER: return []
    
    print("[*] Menjalankan Genius Proxy Harvester... Mencari jalur aman...")
    apis = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=8000&country=all&ssl=yes&anonymity=anonymous",
        "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps"
    ]
    
    new_proxies = []
    for api in apis:
        try:
            resp = requests.get(api, timeout=10)
            if resp.status_code == 200:
                if "geonode" in api:
                    data = resp.json()
                    for p in data.get('data', []):
                        new_proxies.append(f"http://{p['ip']}:{p['port']}")
                else:
                    lines = resp.text.strip().split("\n")
                    for line in lines:
                        if ":" in line: new_proxies.append(f"http://{line.strip()}")
        except: pass
    
    random.shuffle(new_proxies)
    HARVESTED_PROXIES = new_proxies[:30] # Ambil 30 teratas
    print(f"[+] Berhasil memanen {len(HARVESTED_PROXIES)} proxy segar!")
    return HARVESTED_PROXIES

def get_current_proxy():
    """Mendapatkan proxy aktif (Manual > Auto)."""
    if USE_PROXY: return PROXY_SETTING
    if USE_AUTO_HARVESTER:
        if not HARVESTED_PROXIES: fetch_auto_proxies()
        if HARVESTED_PROXIES:
            p = random.choice(HARVESTED_PROXIES)
            return {"http": p, "https": p}
    return None

def resilient_download(url, timeout=12, max_retries=2, target="generic", silent=False):
    """
    Fungsi unduh tangguh (v5.46 - Stealth Edition) dengan sistem jitter dinamis.
    Membantu melewati blokir 403 Forbidden dan 429 Rate Limit dengan jeda manusiawi.
    """
    from config import STEALTH_JITTER
    last_error = None
    
    # v5.46: Jeda awal untuk memecah ritme bot
    time.sleep(random.uniform(2, 5))
    
    for attempt in range(max_retries + 1):
        try:
            # Rotasi header di setiap percobaan
            headers = get_human_headers(target=target)
            
            # v5.46: STEALTH JITTER (Jeda lebih panjang di percobaan ulang)
            if attempt > 0:
                wait_time = random.uniform(STEALTH_JITTER[0], STEALTH_JITTER[1])
                if not silent: print(f"[*] Stealth Mode Re-attempt ({attempt}/{max_retries}). Pendinginan {wait_time:.1f}s...")
                time.sleep(wait_time)
            
            # v5.43: Dynamic Proxy Selection
            proxies = get_current_proxy() if (attempt > 0 or "google" in url or "yandex" in url) else None
            response = requests.get(url, headers=headers, timeout=timeout, verify=False, proxies=proxies)
            
            if response.status_code == 200:
                return decode_spa_html(response.text)
            elif response.status_code == 429:
                if "google" in target or "bing" in target or "yandex" in target or "yahoo" in target or "duckduckgo" in target:
                    if not silent: print(f"[!] RATE LIMIT (429) pada {target}. Langsung rotasi tanpa menunggu lama.")
                    return None
                
                # v5.46: 429 COOLING SYSTEM (Lebih agresif) untuk portal berita
                wait_time = random.uniform(30, 60)
                if not silent: print(f"[!] RATE LIMIT (429) TERDETEKSI! Mendinginkan mesin selama {wait_time:.1f} detik...")
                time.sleep(wait_time)
                last_error = "Rate Limited (429)"
                continue
            elif response.status_code == 403:
                last_error = f"403 Forbidden ({urlparse(url).netloc})"
                # Jika 403, coba jeda lama karena kemungkinan kena firewall
                time.sleep(10)
            elif response.status_code == 500 and "yahoo" in target:
                if not silent: print(f"[!] Yahoo menyulut Error 500. Mengabaikan sisa percobaan...")
                return None
            else:
                last_error = f"Status Code {response.status_code}"
                
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.SSLError) as ce:
            if "certificate" in str(ce).lower() or "ssl" in str(ce).lower() or "connection" in str(ce).lower():
                if USE_CLOUDFLARE_DNS:
                    parsed = urlparse(url)
                    if not silent: print(f"[*] DNS/SSL ISSUE pada {parsed.netloc}. Mencoba DoH...")
                    ip = resolve_dns_cloudflare(parsed.netloc)
                    if ip:
                        new_url = url.replace(parsed.netloc, ip)
                        headers = get_human_headers(target=target)
                        headers['Host'] = parsed.netloc
                        try:
                            response = requests.get(new_url, headers=headers, timeout=timeout, verify=False)
                            if response.status_code == 200:
                                return decode_spa_html(response.text)
                        except: pass
                
                if not silent: print(f"[!] SSL/ISP INTERCEPTION DETECTED untuk {url[:30]}...")
                try:
                    response = requests.get(url, headers=get_human_headers(target=target), timeout=timeout, verify=False)
                    if response.status_code == 200:
                        return decode_spa_html(response.text)
                except: pass
            
            if "name resolution" in str(ce).lower() or "gaierror" in str(ce).lower():
                last_error = "DNS Failure"
                time.sleep(5)
            else:
                last_error = f"Connection Error: {str(ce)[:50]}"
        except requests.exceptions.Timeout:
            last_error = "Timeout"
        except Exception as e:
            last_error = str(e)
            
    if last_error and not silent:
        print(f"[!] Gagal unduh {url[:50]} setelah {max_retries} percobaan. Error: {last_error}")
    return None

def resilient_download_full(url, timeout=12, max_retries=2, target="generic"):
    """
    v5.4: Mendownload seluruh isi artikel meskipun terbagi dalam beberapa halaman (Pagination).
    Sangat krusial untuk portal seperti JawaPos/Detik di mana Editor ada di halaman terakhir.
    """
    main_html = resilient_download(url, timeout, max_retries, target)
    if not main_html: return None
    
    # Deteksi apakah ini situs dengan paginasi (JawaPos, Detik, dsb)
    # Cari link dengan teks "Halaman Selanjutnya", "Next", atau "2", "3" dsb.
    soup = BeautifulSoup(main_html, 'html.parser')
    
    # Cari pola link paginasi: ?page=2, /2/, dan teks 'Selanjutnya' atau angka halaman
    # v5.13: Ekspansi kata kunci deteksi paginasi
    next_pages = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text().lower().strip()
        
        is_pagination = False
        if 'page=' in href: is_pagination = True
        if re.search(r'/\d+/?$', href) and (len(text) < 5 or text.isdigit()): is_pagination = True
        if any(kw in text for kw in ['selanjutnya', 'next page', 'halaman selanjutnya', 'berikutnya']): is_pagination = True
        
        if is_pagination:
            if href.startswith('/'): href = urljoin(url, href)
            if href not in next_pages and href != url:
                next_pages.append(href)
    
    # Jika ditemukan halaman selanjutnya, unduh dan gabung body teksnya
    if next_pages:
        print(f"[*] Terdeteksi {len(next_pages)} halaman tambahan. Mengunduh untuk melengkapi metadata...")
        full_html = main_html
        # Batasi maksimal 3 halaman tambahan agar tidak lambat
        for p_url in sorted(list(set(next_pages)))[:3]:
            p_html = resilient_download(p_url, timeout, max_retries, target)
            if p_html:
                p_soup = BeautifulSoup(p_html, 'html.parser')
                # Ambil elemen body utama (div dengan id/class content)
                p_body = p_soup.find(['article', 'div'], attrs={'class': re.compile(r'content|body|entry', re.I)})
                if p_body:
                    full_html += "\n\n<!-- PAGE BREAK -->\n\n" + str(p_body)
        return full_html
        
    return main_html

# Kata kunci untuk mencari halaman profil/redaksi (v5.66: Ekspansi patterns)
KATA_KUNCI_PROFIL = [
    'redaksi', 'kontak', 'hubungi', 'contact', 'tentang', 'about', 
    'susunan', 'tim editorial', 'crew', 'person', 'editorial team',
    'profil', 'perusahaan', 'publisher', 'manajemen', 'dewan pers', 
    'corporate', 'informasi', 'bantuan', 'pusat bantuan', 'boks redaksi',
    'pedoman', 'visi-misi', 'sop', 'iklan', 'indeks', 'hak-jawab', 'struktur',
    'organisasi', 'biro', 'perwakilan', 'alamat', 'location'
]

def ekstrak_halaman_redaksi_global(soup, base_url):
    """
    v5.73: Mencari dan mengunjungi hingga 5 tautan potensial untuk mendapatkan profil media yang lengkap.
    Mendukung deteksi pada footer, header, dan body. Dilengkapi Hardcode Injection untuk 20+ jaringan media
    dan Full-Text Fallback jika Anchor Slicing gagal.
    """
    potensial_links = []
    links = soup.find_all('a', href=True)
    
    # Kriteria Pencarian (v5.73: Ekspansi Masif)
    patterns = ['/redaksi', '/editorial', '/about-us', '/kontak', '/contact-us', '/tentang-kami', '/susunan-redaksi',
                'kontak-kami', 'redaksi-radar-bangsa', 'kontak.html', 'about/', '/boks-redaksi', 'readstatik', '/page/',
                'profil-madu-tv', 'struktur-dalam-media', 'tentang-tagar', 'redaksi-tagar', 'hubungi-kami',
                'kabar-surabaya', '/redaksi-2', '/tentangkami', '/box-redaksi', '/pages/redaksi', '/pages/tentang',
                '/pages/kontak', 'pedoman-media', 'meet-us', 'meet']
    kw_texts = ['redaksi', 'editorial', 'susunan', 'tentang kami', 'kontak', 'hubungi', 'management', 'about us',
                'boks redaksi', 'redaksi kami', 'struktur dalam media', 'tim redaksi', 'informasi redaksi',
                'box redaksi', 'bok redaksi', 'meet us', 'tentang bhirawa', 'meet the team']

    for l in links:
        href = l['href'].lower()
        text = l.get_text().lower()
        
        if any(p in href for p in patterns) or any(kw in text for kw in kw_texts):
            full_url = urljoin(base_url, l['href'])
            if full_url not in potensial_links and full_url != base_url:
                potensial_links.append(full_url)
                
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.lower()
    
    # === INJEKSI HARDCODE URL PROFIL (Prioritas Tertinggi) v5.75 ===
    # Kompas Network (inside.kompas.com)
    if 'kompas.com' in base_domain:
        potensial_links.insert(0, "https://inside.kompas.com/about-us#meet")
        potensial_links.insert(0, "https://inside.kompas.com/about-us")
    # Kompas TV (berbeda domain dari kompas.com)
    elif 'kompas.tv' in base_domain:
        potensial_links.insert(0, "https://www.kompas.tv/contact-us")
        potensial_links.insert(0, "https://www.kompas.tv/about-us")
    # Espos / Solopos Network
    elif 'espos.id' in base_domain or 'solopos.com' in base_domain:
        potensial_links.insert(0, "https://www.espos.id/page/kontak")
        potensial_links.insert(0, "https://www.espos.id/page/about-us")
    # iNews Network (regional + fallback ke www.inews.id)
    elif 'inews.id' in base_domain:
        # Selalu fallback ke www.inews.id karena subdomain regional tidak punya halaman profil sendiri
        potensial_links.insert(0, "https://www.inews.id/page/kontak-kami")
        potensial_links.insert(0, "https://www.inews.id/page/redaksi")
        potensial_links.insert(0, "https://www.inews.id/page/tentang-kami")
    # Madu TV
    elif 'madu.tv' in base_domain:
        potensial_links.insert(0, "https://madu.tv/kontak/")
        potensial_links.insert(0, "https://madu.tv/struktur-dalam-media-madutv-nusantara/")
        potensial_links.insert(0, "https://madu.tv/profil-madu-tv/")
    # Tagar Jatim
    elif 'tagarjatim.id' in base_domain:
        potensial_links.insert(0, "https://tagarjatim.id/redaksi-tagar-jatim/")
        potensial_links.insert(0, "https://tagarjatim.id/tentang-tagar-jatim/")
    # Kabar Surabaya (Blogspot-style)
    elif 'kabarsurabaya.org' in base_domain:
        potensial_links.insert(0, "https://www.kabarsurabaya.org/2021/10/susunan-redaksi-kabar-surabaya.html")
        potensial_links.insert(0, "https://www.kabarsurabaya.org/p/hubungi-kami.html")
    # BeritaSatu
    elif 'beritasatu.com' in base_domain:
        potensial_links.insert(0, "https://www.beritasatu.com/tentang-kami")
        potensial_links.insert(0, "https://www.beritasatu.com/redaksi")
    # BiozTV
    elif 'bioztv.id' in base_domain:
        potensial_links.insert(0, "https://www.bioztv.id/contact-us/")
        potensial_links.insert(0, "https://www.bioztv.id/redaksi-2/")
    # Jawapos Radar Network
    elif 'jawapos.com' in base_domain:
        sub = parsed_base.netloc  # e.g. radarmojokerto.jawapos.com
        potensial_links.insert(0, f"https://{sub}/kontak")
        potensial_links.insert(0, f"https://{sub}/redaksi")
        potensial_links.insert(0, f"https://{sub}/about-us")
    # KlikJatim
    elif 'klikjatim.com' in base_domain:
        potensial_links.insert(0, "https://klikjatim.com/pages/kontak-kami")
        potensial_links.insert(0, "https://klikjatim.com/pages/redaksi")
    # Realita.co
    elif 'realita.co' in base_domain:
        potensial_links.insert(0, "https://realita.co/pages/tentang-kami")
        potensial_links.insert(0, "https://realita.co/pages/redaksi")
    # Harian Bhirawa
    elif 'harianbhirawa.co.id' in base_domain:
        potensial_links.insert(0, "https://harianbhirawa.co.id/tentangkami/")
    # Detik Network
    elif 'detik.com' in base_domain:
        potensial_links.insert(0, "https://www.detik.com/redaksi")
    # Memorandum / Disway Network
    elif 'disway.id' in base_domain or 'memorandum' in base_domain:
        sub = parsed_base.netloc  # e.g. memorandum.disway.id
        potensial_links.insert(0, f"https://{sub}/readstatik/115/kontak")
        potensial_links.insert(0, f"https://{sub}/readstatik/1/redaksi")
        potensial_links.insert(0, f"https://{sub}/readstatik/2/tentang-kami")
    # BuserJatim
    elif 'buserjatim.com' in base_domain:
        potensial_links.insert(0, "https://buserjatim.com/box-redaksi/")
    # Tribunnews Regional
    elif 'tribunnews.com' in base_domain:
        sub = parsed_base.netloc  # e.g. jatim.tribunnews.com
        if sub != 'www.tribunnews.com':
            potensial_links.insert(0, f"https://{sub}/contact-us/")
            potensial_links.insert(0, f"https://{sub}/redaksi/")
        potensial_links.insert(0, "https://www.tribunnews.com/about/")
    # JPNN
    elif 'jpnn.com' in base_domain:
        potensial_links.insert(0, "https://www.jpnn.com/page/tentang-kami")
        potensial_links.insert(0, "https://www.jpnn.com/page/redaksi")
    # === v5.76: Domain Baru dari Evaluasi ===
    # Kediri Tangguh
    elif 'kediritangguh.co' in base_domain:
        potensial_links.insert(0, "https://kediritangguh.co/tentang-kami/")
    # Jurnal Jatim
    elif 'jurnaljatim.com' in base_domain:
        potensial_links.insert(0, "https://jurnaljatim.com/tentang-kami/")
        potensial_links.insert(0, "https://jurnaljatim.com/redaksi/")
    # TargetNews
    elif 'targetnews.id' in base_domain:
        potensial_links.insert(0, "https://targetnews.id/redaksi/")
    # Media Kampung
    elif 'mediakampung.com' in base_domain:
        potensial_links.insert(0, "https://mediakampung.com/kontak-kami/")
        potensial_links.insert(0, "https://mediakampung.com/tentang-kami/")
        potensial_links.insert(0, "https://mediakampung.com/redaksi/")
    # Pena Bicara
    elif 'penabicara.com' in base_domain:
        potensial_links.insert(0, "https://www.penabicara.com/kontak")
        potensial_links.insert(0, "https://www.penabicara.com/redaksi")
        potensial_links.insert(0, "https://www.penabicara.com/about-us")
    # Okezone
    elif 'okezone.com' in base_domain:
        potensial_links.insert(0, "https://www.okezone.com/about-us")
        potensial_links.insert(0, "https://www.okezone.com/redaksi")
    # Menghapus duplikat sambil mempertahankan urutan (mengutamakan hasil hardcode)
    potensial_links = list(dict.fromkeys(potensial_links))
    
    hasil_gabungan = []
    # v5.73: Kunjungi maksimal 5 link (naik dari 3) untuk profiling lebih lengkap
    for target_url in potensial_links[:5]:
        print(f"[*] Menyelidiki profil media di: {target_url}")
        html = resilient_download(target_url, timeout=12, max_retries=2, target="redaksi")
        if html:
            rsoup = BeautifulSoup(html, 'html.parser')
            
            # v5.75: JAWAPOS SPA JSON PARSER — Ekstrak data kontak dari atribut data-page
            # Jawapos Radar menggunakan SPA (React/Vue) di mana data kontak ada di JSON, bukan teks HTML
            if 'jawapos.com' in target_url:
                data_div = rsoup.find('div', attrs={'data-page': True})
                if data_div:
                    try:
                        import json as _json
                        page_data = _json.loads(data_div['data-page'])
                        factory = page_data.get('props', {}).get('factory', {})
                        if factory:
                            jp_info = []
                            jp_info.append(f"Nama Media: {factory.get('PUBLISHER_NAME', factory.get('TITLE', ''))}")
                            jp_info.append(f"Alamat: {factory.get('ADDRESS', '-')}")
                            jp_info.append(f"Telepon: {factory.get('PHONE', '-')}")
                            jp_info.append(f"Fax: {factory.get('FAX', '-')}")
                            jp_info.append(f"Email: {factory.get('EMAIL', '-')}")
                            jp_info.append(f"WhatsApp: {factory.get('WHATSAPP', '-')}")
                            jp_info.append(f"WhatsApp Channel: {factory.get('WHATSAPP_CHANNEL', '-')}")
                            jp_info.append(f"Facebook: {factory.get('FACEBOOK', '-')}")
                            jp_info.append(f"Instagram: {factory.get('INSTAGRAM', '-')}")
                            jp_info.append(f"Twitter: {factory.get('TWITTER', '-')}")
                            jp_info.append(f"Copyright: {factory.get('COPYRIGHT', '-')}")
                            jp_fragment = "\n".join(jp_info)
                            if len(jp_fragment) > 50:
                                print(f"[+] Jawapos SPA JSON Parser: Berhasil ekstrak profil dari data-page!")
                                hasil_gabungan.append(jp_fragment)
                                if len(hasil_gabungan) >= 2: continue
                    except Exception as e_jp:
                        print(f"[-] Jawapos JSON Parser gagal: {str(e_jp)[:50]}")
            
            # Bersihkan elemen pengganggu
            for s in rsoup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'ins']): s.decompose()
            
            raw_text = rsoup.get_text(" ", strip=True)
            
            # v5.77: FULL CLEAN TEXT — Kirim seluruh teks bersih tanpa potongan
            # Setelah decompose(), teks biasanya hanya 3.000-10.000 karakter (jauh di bawah limit token Groq)
            # Tidak perlu anchor slicing yang berisiko memotong data kontak penting
            if len(raw_text) > 150:
                print(f"[+] Profil media ditemukan ({len(raw_text)} karakter bersih): {target_url[:50]}...")
                hasil_gabungan.append(raw_text)
                if len(hasil_gabungan) >= 2: break  # Cukup 2 sumber informasi
    
    # v5.77: Cross-Domain Fallback (Full Clean Text)
    if not hasil_gabungan:
        if 'tribunnews.com' in base_domain and base_domain != 'www.tribunnews.com':
            main_redaksi = "https://www.tribunnews.com/about/"
            print(f"[*] Cross-Domain Fallback (Tribun Network): {main_redaksi}")
            html_main = resilient_download(main_redaksi, timeout=10, max_retries=1, target="redaksi")
            if html_main:
                msoup = BeautifulSoup(html_main, 'html.parser')
                for s in msoup(['script', 'style', 'nav', 'iframe', 'ins']): s.decompose()
                hasil_gabungan.append(msoup.get_text(" ", strip=True))
        elif 'inews.id' in base_domain and base_domain != 'www.inews.id':
            for fallback_url in ["https://www.inews.id/page/redaksi", "https://www.inews.id/page/kontak-kami"]:
                print(f"[*] Cross-Domain Fallback (iNews Network): {fallback_url}")
                html_fb = resilient_download(fallback_url, timeout=10, max_retries=1, target="redaksi")
                if html_fb:
                    fbsoup = BeautifulSoup(html_fb, 'html.parser')
                    for s in fbsoup(['script', 'style', 'nav', 'iframe', 'ins']): s.decompose()
                    hasil_gabungan.append(fbsoup.get_text(" ", strip=True))
                    break

    return "\n---\n".join(hasil_gabungan) if hasil_gabungan else ""

def bersihkan_konten_kontak(teks):
    """Membersihkan teks sampah seperti [email protected] dari hasil scraping."""
    if not teks: return ""
    # Hapus obfusikasi email Cloudflare (umumnya '[email protected]')
    teks = re.sub(r'\[email\s+protected\]', '', teks, flags=re.I)
    teks = re.sub(r'email\s+protected', '', teks, flags=re.I)
    # Hapus whitespace berlebih
    teks = re.sub(r'\s+', ' ', teks).strip()
    return teks

# Kata kunci yang relevan isi teks kontak profil (v5.32: Diperluas ke Jakarta/Global)
KATA_KUNCI_KONTEN = [
    'jalan', 'jl.', 'jl ', '@', '(at)', '[at]', '08', '+62', '031', '033', '034', '035', '032', '036', '021', 'telp', 'fax', 'email', 
    'redaksi', 'editor', 'wartawan', 'reporter', 'pemimpin', 'direktur', 'penanggung jawab', 'penerbit', 'wa ', 'whatsapp', 
    'hubungi', 'kramat pela', 'selatan', 'jakarta', 'mediakonteks', 'independenmedia', 'wa.me', 't.me',
    'komisaris', 'sekretaris', 'bendahara', 'staf', 'pimpinan', 'dewan', 'pengurus', 'petugas', 'kantor',
    'pt ', 'cv ', 'yayasan ', 'persada', 'media tama', 'media grup', 'perkasa', 'nusantara', 'alamat', 'gedung', 'lantai',
    'kecamatan', 'kabupaten', 'provinsi', 'desa', 'dusun', 'kelurahan', 'rt ', 'rw ',
    'redaktur', 'kabiro', 'koordinator', 'kontributor', 'biro ', 'advokat', 'legal', 'penasehat', 'pembina', 'pendiri'
]

# Daftar Kantor Berita (Agency) - v5.4
KANTOR_BERITA = ['antara', 'reuters', 'afp', 'ap', 'bloomberg', 'cnbc', 'bbc', 'al jazeera']

# Jaringan Media Terpercaya (Cross-Domain Mapping)
TRUSTED_NETWORKS = {
    'malangtimes.com': ['jatimtimes.com', 'malangtimes.com'],
    'radarkediri.jawapos.com': ['jawapos.com', 'radarkediri.jawapos.com', 'radarmadiun.jawapos.com'],
    'gresiksatu.com': ['gresiksatu.com', 'klikjatim.com'],
    'tribunnews.com': ['tribunnews.com', 'kompas.com', 'tribunjatim.com', 'suryamalang.com', 'jatim.tribunnews.com', 'jatim-timur.tribunnews.com'],
    'rubicnews.com': ['rubicnews.com', 'promedia', 'jatimtimes.com'],
    'surabayapagi.com': ['surabayapagi.com'],
    'rri.co.id': ['rri.co.id'],
    'jawapos.com': [
        'jawapos.com', 'radarmadura.jawapos.com', 'radarsolo.jawapos.com', 
        'radarsurabaya.jawapos.com', 'radarsemarang.jawapos.com', 'radarkediri.jawapos.com',
        'radarsitubondo.jawapos.com', 'radarbanyuwangi.jawapos.com', 'radartulungagung.jawapos.com',
        'radarjombang.jawapos.com', 'radarbojonegoro.jawapos.com', 'radarmadiun.jawapos.com'
    ],
    'serambinews.com': ['serambinews.com', 'bangkapos.com'],
    'pojokbogor.com': ['pojokbogor.com', 'pojoksatu.id'],
}

def ekstrak_metadata_penulis_dari_html(soup):
    """
    Extrak detail penulis/editor langsung dari body teks artikel.
    V5.0: Fokus pada paragraf awal dan akhir (Byline Detection) 
    dan hapus peran korporat agar tidak mengotori Aktor.
    """
    metadata = []
    
    # Peran yang diizinkan masuk ke daftar jurnalis berita
    ALLOW_ROLES = ['penulis', 'reporter', 'wartawan', 'editor', 'redaktur', 'oleh', 'laporan', 'fotografer', 'cerita dari']
    # Peran yang DILARANG masuk ke daftar Aktor (Management/Corporate roles)
    BLACKLIST_ROLES = [
        'manager', 'marketing', 'it ', 'ict', 'iklan', 'direktur', 'pimpinan umum', 
        'sekretaris', 'admin', 'bendahara', 'keuangan', 'penanggung jawab', 
        'ketua dewan redaksi', 'sekretaris redaksi', 'ombudsman', 'pemimpin redaksi',
        'pemred', 'redaktur pelaksana', 'redpel', 'wakil pemimpin redaksi'
    ]

    # v5.10: SCAN DATA TERSTRUKTUR (LD+JSON) - PRIORITAS ABSOLUT
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            # LD+JSON bisa berupa list atau dict
            items = data if isinstance(data, list) else [data]
            for item in items:
                # Cari field 'author'
                author_data = item.get('author')
                if author_data:
                    authors = author_data if isinstance(author_data, list) else [author_data]
                    for auth in authors:
                        name = auth.get('name') if isinstance(auth, dict) else auth
                        if name and isinstance(name, str) and 3 < len(name) < 50:
                            # v5.37: Skip nama domain (misal: 'Jatimhariini.co.id', 'Redaksi Kompas')
                            if any(ext in name.lower() for ext in ['.co.id', '.com', '.net', '.id', '.org']):
                                continue
                            if any(nb in name.lower() for nb in ['redaksi', 'admin', 'tim ', 'desk ']):
                                continue
                            metadata.append(f"[BYLINE UTAMA (LDJSON)]: {name}")
                # Cari field 'editor' (opsional di LD+JSON)
                editor_name = item.get('editor')
                if editor_name and isinstance(editor_name, str) and 3 < len(editor_name) < 50:
                    metadata.append(f"[EDITOR BERITA (LDJSON)]: {editor_name}")
        except:
            continue

    # v5.37: SCAN META TAG content_Editor / content_Author (Jaringan Promedia, IDN Times, dll)
    # Format: <meta name="content_Editor" content="Fitroh Kurniadi">
    for meta_tag in soup.find_all('meta', attrs={'name': True, 'content': True}):
        meta_name = meta_tag.get('name', '').lower()
        meta_content = meta_tag.get('content', '').strip()
        if not meta_content or len(meta_content) < 3 or len(meta_content) > 60: continue
        if meta_name in ['content_editor', 'article:editor', 'dc.creator', 'dc.contributor']:
            # Pastikan ini nama orang, bukan nama domain/website
            if '.' not in meta_content or ' ' in meta_content:  # Nama orang tidak mengandung titik tanpa spasi
                metadata.append(f"[EDITOR BERITA (META)]: {meta_content}")
        elif meta_name in ['content_author', 'article:author', 'dc.author'] and meta_content != 'Jatimhariini.co.id':
            if '.' not in meta_content or ' ' in meta_content:  # Bukan nama domain
                if not any(kb in meta_content.lower() for kb in KANTOR_BERITA + ['redaksi', 'admin', '.co.id', '.net', '.com']):
                    metadata.append(f"[BYLINE UTAMA (META)]: {meta_content}")

    author_links = soup.find_all('a', href=True)
    for al in author_links:
        href = al['href'].lower()
        if any(pat in href for pat in ['/penulis/', '/author/', '/about/', '/editor/', '/wartawan/', '/reporter/']):
            name_text = al.get_text(" ", strip=True)
            # v5.8: Abaikan link dengan teks terlalu pendek atau terlalu panjang (Link sampah)
            if name_text and 3 < len(name_text) < 45:
                # v5.36: Filter teks navigasi generik (bukan nama orang)
                _nav_noise = ['tentang kami', 'about us', 'hubungi kami', 'contact us', 'redaksi', 'tim redaksi', 'tim editorial']
                if any(noise in name_text.lower() for noise in _nav_noise):
                    continue
                # v5.37: Filter nama domain
                if any(ext in name_text.lower() for ext in ['.co.id', '.com', '.net', '.id']):
                    continue
                # Cek apakah ini Agensi yang menyamar jadi link author
                if not any(kb in name_text.lower() for kb in KANTOR_BERITA):
                    metadata.append(f"[BYLINE UTAMA (LINK)]: {name_text}")

    # v5.36 GENIUS META-BAR SCAN — Diperluas untuk menangkap berbagai format portal Indonesia
    # Mencakup: single-author (SuaraSurabaya), post-author, article-author, content-author, writer, contributor
    meta_elements = soup.find_all(
        ['li', 'span', 'small', 'div', 'p', 'a'],
        attrs={'class': re.compile(r'meta|author|byline|credit|reporter|single.author|post.author|article.author|content.author|writer|contributor|penulis', re.I)}
    )
    for me in meta_elements[:30]:
        t = me.get_text(" ", strip=True)
        if any(kw in t.lower() for kw in ['editor', 'wartawan', 'penulis', 'oleh', 'laporan', 'cerita dari', 'reporter', 'ditulis']):
            # Bersihkan dan beri label prioritas
            if not any(br in t.lower() for br in BLACKLIST_ROLES):
                metadata.append(f"[BYLINE UTAMA]: {t}")

    # v5.36: DIRECT SCAN 'Laporan oleh' — Pola umum media Indonesia (SuaraSurabaya, Jawa Pos, dll)
    # Menangkap format: "Laporan oleh Billy Patoppoi" baik di dalam teks paragraf maupun elemen HTML
    # Negatif stop: Berhenti sebelum nama hari/bulan/kata bukan nama
    _STOP_WORDS = r'(?:senin|selasa|rabu|kamis|jumat|sabtu|minggu|januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember|\d)'
    pola_laporan_oleh = re.compile(
        r'(?:laporan\s+oleh|ditulis\s+oleh|ditulis\s*:\s*|teks\s*:\s*|foto\s*:\s*|oleh\s*:\s*)\s*'
        r'((?:(?!' + _STOP_WORDS + r')[A-Za-z])[A-Za-z\s\.]{2,50})',
        re.IGNORECASE
    )
    # Scan seluruh elemen teks artikel (termasuk paragraf terakhir)
    all_elements_for_byline = soup.find_all(['p', 'div', 'span', 'small', 'em', 'strong'])
    for el in all_elements_for_byline:
        el_teks = el.get_text(" ", strip=True)
        if not el_teks or len(el_teks) > 500: continue  # Lewati blok teks panjang
        hits = pola_laporan_oleh.findall(el_teks)
        for nama_raw in hits:
            # Potong di kata yang bukan nama (hari, bulan, angka)
            nama_bersih = re.split(r'\s+(?:senin|selasa|rabu|kamis|jumat|sabtu|minggu|januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember|\d)', nama_raw, flags=re.IGNORECASE)[0]
            nama_bersih = nama_bersih.strip().rstrip('.,')
            if 3 < len(nama_bersih) < 55 and not any(kb in nama_bersih.lower() for kb in KANTOR_BERITA):
                entri = f"[BYLINE LAPORAN OLEH]: {nama_bersih}"
                if entri not in metadata:
                    metadata.append(entri)

    # v5.12: NEIGHBOR-SCAN untuk Label Kredensial (VOI Style)
    # Jika ada tag yang isinya 'Reporter' atau 'Editor', ambil teks dari elemen sebelumnya atau sesudahnya.
    credential_labels = soup.find_all(['small', 'span', 'em'], string=re.compile(r'^Reporter$|^Editor$|^Wartawan$', re.I))
    for label in credential_labels:
        parent = label.parent
        if parent:
            # Cari link (<a>) di dalam parent yang sama (VOI style)
            name_link = parent.find('a')
            if name_link:
                name_text = name_link.get_text(" ", strip=True)
                if 3 < len(name_text) < 45:
                    metadata.append(f"[BYLINE UTAMA (NEIGHBOR)]: {name_text} (sebagai {label.string})")
            else:
                # Coba ambil teks langsung dari parent (jika link tidak ada)
                full_parent_text = parent.get_text(" ", strip=True)
                # Bersihkan label dari teks parent
                clean_name = full_parent_text.replace(label.string, "").strip()
                if 3 < len(clean_name) < 45:
                    metadata.append(f"[BYLINE UTAMA (NEIGHBOR)]: {clean_name} (sebagai {label.string})")

    # v5.37: ANCHOR NON-HREF SCANNER — Tangkap 'Editor: Nama' dalam <a> tanpa href (Promedia/iNews style)
    # Contoh: <a>Editor: Fitroh Kurniadi</a> di dalam div.read__info__author
    pola_editor_inline = re.compile(
        r'^(?:editor|redaktur)[:\s]+([A-Za-z][A-Za-z\s\.]{2,50})$',
        re.IGNORECASE
    )
    for anc in soup.find_all('a'):
        if anc.get('href'): continue  # Skip yang punya href (sudah ditangani di AUTHOR LINKS)
        anc_text = anc.get_text(" ", strip=True)
        match = pola_editor_inline.match(anc_text)
        if match:
            nama_editor = match.group(1).strip().rstrip('.,')
            if 3 < len(nama_editor) < 55:
                entri = f"[EDITOR BERITA (INLINE)]: {nama_editor}"
                if entri not in metadata:
                    metadata.append(entri)

    # Ambil semua paragraf, span, dsb
    elements = soup.find_all(['span', 'p', 'div', 'small', 'em', 'strong', 'a', 'li'])
    
    # v5.37: Perluas cakupan — 20 pertama + 40 terakhir (byline kadang ada di tengah artikel pendek)
    relevant_elements = elements[:20] + elements[-40:]
    
    # Pola v5.36: Diperkuat — Mendukung ALL-CAPS, nama mixed-case, dan berbagai format byline Indonesia
    pola_penulis = re.compile(
        r'(?:penulis|reporter|wartawan|editor|redaktur|oleh|laporan|laporan\s+oleh|kontributor|cerita dari|ditulis oleh|teks)[:\s]+([A-Z][A-Za-z\s\./,]{2,}|[A-Z\s]{4,60})',
        re.IGNORECASE
    )
    
    # v5.6: Pola Inisial (misal: (hud/mar) atau (abc)) di akhir artikel
    # v5.8: Dukung multiple initials (hud/mar/abc)
    pola_inisial = re.compile(r'\(([a-z]{2,4}(?:/[a-z]{2,4})+)\)', re.IGNORECASE)
    
    for tag in relevant_elements:
        teks = tag.get_text(" ", strip=True)
        if not teks: continue
        
        # Cek blacklist peran korporat
        if any(role in teks.lower() for role in BLACKLIST_ROLES):
            continue
            
        # Ekstrak Inisial (untuk verifikasi AI)
        inisial = pola_inisial.findall(teks)
        if inisial:
            for ini in inisial:
                metadata.append(f"[INISIAL JURNALIS DI AKHIR]: ({ini})")

        # v5.11: Deteksi Manajer/Pemred yang menyelinap di blok teks (Tag Hiper-Negatif)
        if any(role in teks.lower() for role in BLACKLIST_ROLES):
            metadata.append(f"[MANAJEMEN REDAKSI (DILARANG JADI AKTOR)]: {teks}")
            continue

        cocok = pola_penulis.findall(teks)
        for nama_raw in cocok:
            # v5.4: Pisahkan nama jika ada koma (misal: "Oleh: Latu, Antara")
            for nama in re.split(r'[,|/]', nama_raw):
                nama_bersih = nama.strip().rstrip('.,')
                
                # Cek apakah ini Agensi Toko/Kantor Berita (Bukan Aktor Manusia)
                if any(kb in nama_bersih.lower() for kb in KANTOR_BERITA):
                    if f"[AGENCY: {nama_bersih.upper()}]" not in metadata:
                        metadata.append(f"[AGENCY: {nama_bersih.upper()}]")
                    continue

                if 3 < len(nama_bersih) < 60:
                    # Pelabelan khusus jika mengandung kata 'Editor'
                    label = "[EDITOR BERITA]" if "editor" in teks.lower() else "[BYLINE]"
                    entri = f"{label}: {nama_bersih}"
                    if entri not in metadata:
                        metadata.append(entri)
                        
        # v5.7: HEURISTIK BIO PENULIS (Tempo/Kompas/IDN)
        # Cari pola biografi: "Lulusan", "Menekuni isu", "Bergabung sejak"
        if any(kw in teks.lower() for kw in ['lulusan ', 'menekuni isu', 'bergabung sejak', 'desk ', 'jurnalis tempo']):
            # Coba ambil kalimat pertama yang biasanya berisi nama jika tidak diawali kata ganti
            # Atau ambil teks link di sekitarnya
            bio_name = teks.split('.')[0].strip()
            if 3 < len(bio_name) < 60:
                 metadata.append(f"[BIO PENULIS ARTIKEL]: {bio_name}")
    
    return "\n".join(metadata[:12]) if metadata else ""


def is_menu_noise(teks, is_profile_page=False):
    """
    v5.30-v5.33: Deteksi teks navigasi menu yang menyusup ke data kontak.
    v5.33: Jika di halaman profil, tingkatkan toleransi terhadap daftar nama.
    """
    if len(teks) < 30:
        return False
    # Jika di halaman khusus redaksi, jangan terlalu restriktif terhadap daftar nama (noise level lowered)
    if is_profile_page and len(teks) < 150:
        return False
        
    # Jika mengandung tanda-tanda kontak asli, jangan blokir
    if any(c in teks.lower() for c in ['@', '+62', 'jl.', 'jln', '.com', '.co.id', 'jalan ', '021-', '031-', 'wa:']):
        return False
    # Jika mengandung angka dalam jumlah signifikan, kemungkinan alamat/kontak
    if sum(c.isdigit() for c in teks) > 5:
        return False
        
    # Cek rasio: banyak kata tapi tidak ada satupun tanda baca struktur kalimat
    tanda_baca = sum(1 for c in teks if c in ['.', ',', ':', ';', '(', ')'])
    kata_count = len(teks.split())
    # Jika > 10 kata dan tidak ada tanda baca sama sekali = sangat mungkin menu navigasi
    if kata_count > 10 and tanda_baca == 0:
        return True
    # Jika > 18 kata dan rasio tanda_baca sangat rendah = menu nav
    if kata_count > 18 and tanda_baca < 2:
        return True
    return False

def sniff_contact_and_editorial_board(soup, is_profile_page=False):
    """
    v5.88 Helper: Pemindaian cerdas untuk kontak, alamat, dan jajaran redaksi.
    Menggabungkan Table Sniffing, List Sniffing, dan Element Scanning.
    """
    captured_text = ""
    # v5.38: Prioritas pada Table (Susunan Redaksi) dan Address
    area_penting = soup.find_all(['header', 'footer', 'main', 'article', 'div', 'aside', 'table', 'section', 'ul', 'ol', 'dl'])
    
    # 1. v5.39: CLOUDFLARE BYPASS
    for cf_node in soup.find_all(attrs={"data-cfemail": True}):
        try:
            cf_hex = cf_node['data-cfemail']
            k = int(cf_hex[:2], 16)
            email_dec = "".join([chr(int(cf_hex[i:i+2], 16) ^ k) for i in range(2, len(cf_hex), 2)])
            cf_node.string = email_dec
        except: pass

    # 2. BLOK SNIFFING (Tabel, List, & Content Containers)
    for area in area_penting:
        area_raw = area.get_text(" ", strip=True)
        # v5.88: Pencarian keyword kontak lebih agresif
        is_contact_block = any(skw in area_raw.lower() for skw in ['susunan redaksi', 'dewan redaksi', 'redaksi kami', 'boks redaksi', 'jajaran redaksi', 'hubungi kami', 'contact us', 'telepon', 'whatsapp', 'wa:', 'telp:'])
        
        if area.name in ['table', 'ul', 'ol', 'dl'] or (is_contact_block and area.name in ['div', 'section', 'footer']):
            full_area_text = area.get_text(" ", strip=True)
            board_kws = ['redaksi', 'pimpinan', 'dewan', 'pengurus', 'editor', 'penulis', 'direktur', 'pemred', 'manajer', 'redaktur', 'kabiro', 'telepon', 'whatsapp', 'wa:', 'telp:']
            if is_contact_block or any(kw in full_area_text.lower() for kw in board_kws):
                teks_box = bersihkan_konten_kontak(full_area_text)
                if 10 < len(teks_box) < 8000:
                    prefix = "[BOX REDAKSI/KONTAK]"
                    if teks_box not in captured_text:
                        captured_text += f"{prefix}: {teks_box}\n"
                if is_contact_block: continue 
                if area.name in ['table', 'ul', 'ol', 'dl']: continue 

        # 3. ELEMENT SCANNING (P, LI, TD, dsb)
        for element in area.find_all(['p', 'address', 'li', 'td', 'span', 'div', 'b', 'strong', 'tr']):
            if element.name == 'div' and element.find(['p', 'div', 'span']):
                continue
                
            teks_el = element.get_text(" ", strip=True)
            # v5.88: Deteksi langsung link WA me di dalam elemen
            wa_in_el = element.find('a', href=re.compile(r'wa\.me|whatsapp', re.I))
            if wa_in_el:
                teks_el += f" (Link WA: {wa_in_el['href']})"

            if 8 <= len(teks_el) < 1500 and any(kw in teks_el.lower() for kw in KATA_KUNCI_KONTEN):
                if is_menu_noise(teks_el, is_profile_page=is_profile_page):
                    continue
                teks_bersih = bersihkan_konten_kontak(teks_el)
                if teks_bersih and teks_bersih not in captured_text:
                    captured_text += teks_bersih + "\n"
    
    return captured_text

def scrape_contact_page(domain, html_content=None):
    """
    Mencari halaman Redaksi/Kontak dari seluruh DOM (header+body+footer),
    lalu mengekstrak teks informatif dari setiap halaman yang ditemukan.
    v5.39: Full Genius Refactor dengan Sub-page Board Sniffing.
    """
    contact_text = ""
    try:
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
        else:
            # Gunakan resilient_download untuk domain utama
            html = resilient_download(domain, timeout=15, target="google")
            if not html: return ""
            soup = BeautifulSoup(html, 'html.parser')
        
        # v5.88: GIGA-AGGRESSIVE CONTACT SCANNER (Heuristic Layer)
        all_raw_text = soup.get_text(" ", strip=True)
        # 1. Email Scanner
        emails = re.findall(r'[a-zA-Z0-9._%+-]+(?:@|\(at\)|\[at\])[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', all_raw_text, re.I)
        
        # 2. Phone & WhatsApp Scanner (Optimized for Indonesian Formats)
        # Mendukung: 0812..., +62 812..., (021) ..., 031-..., WA: 08...
        pola_telp = [
            r'(?:\+62|62|0)(?:[2-9]\d{1,2}|\d{2,3})[\s\-\.]?\d{3,5}[\s\-\.]?\d{3,5}(?:\d{1,4})?', # Standard
            r'08[1-9]\d{1,2}[\s\-\.]?\d{3,5}[\s\-\.]?\d{3,5}', # Mobile 08...
            r'\(?0\d{2,3}\)?[\s\-\.]?\d{5,8}' # Landline (021) 123456
        ]
        phones = []
        for p in pola_telp:
            hits = re.findall(p, all_raw_text)
            phones.extend(hits)
        
        # 3. WA.ME Link Scanner (Direct WA)
        wa_links = []
        for a in soup.find_all('a', href=True):
            h = a['href'].lower()
            if 'wa.me/' in h or 'whatsapp.com/send' in h:
                wa_num = re.sub(r'\D', '', h.split('/')[-1])
                if len(wa_num) >= 10:
                    wa_links.append(f"WhatsApp: +{wa_num}")
        
        phones = [p.strip() for p in set(phones) if len(re.sub(r'\D', '', p)) >= 9]
        
        if emails or phones or wa_links:
            ext_contact = "\n[DATA KONTAK AKTUAL (HEURISTIK)]:\n"
            if emails: ext_contact += "Email: " + " | ".join(list(set(emails))) + "\n"
            if phones: ext_contact += "Telepon: " + " | ".join(phones) + "\n"
            if wa_links: ext_contact += "Link WA: " + " | ".join(list(set(wa_links))) + "\n"
            contact_text += ext_contact + "\n"
        
        # 1. v5.39: Sniff dari halaman utama/artikel
        contact_text += sniff_contact_and_editorial_board(soup, is_profile_page=False)

        # === v5.34: GENIUS LINK HARVESTER (Dual-Scoping: Article + Homepage) ===

        # === v5.34: GENIUS LINK HARVESTER (Dual-Scoping: Article + Homepage) ===
        target_urls_high = []
        target_urls_low  = []
        # Pola prioritas tinggi: Redaksi, Kontak, Tentang (v5.70 Expanded)
        PRIORITY_PATTERNS = [
            'readstatik', '/redaksi', '/kontak', '/tentang', '/about', '/contact', 
            '/hubungi', '/pedoman', '/sop-', '/iklan', '/profil', '/boks-redaksi',
            '/tentang-kami', '/susunan-redaksi', '/manajemen', '/editorial', '/page/'
        ]
        
        def harvest_links(current_soup):
            """Mencari link profil/redaksi dari soup yang diberikan."""
            for a in current_soup.find_all('a', href=True):
                teks_link = a.get_text().lower().strip()
                href = a['href'].lower()
                if any(kw in teks_link or kw in href for kw in KATA_KUNCI_PROFIL):
                    href_asli = a['href']
                    # Normalisasi URL
                    if href_asli.startswith('/'): full_url = urljoin(domain, href_asli)
                    elif href_asli.startswith('http'): full_url = href_asli
                    else: full_url = urljoin(domain, "/" + href_asli)
                    
                    parsed_target = urlparse(full_url).netloc.lower()
                    # Filter Social Media (Kecuali WhatsApp untuk kontak)
                    if any(sm in parsed_target for sm in ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'tiktok.com', 'linkedin.com', 'google.com', 'apple.com', 'play.google']):
                        continue
                        
                    if any(p in href_asli.lower() for p in PRIORITY_PATTERNS):
                        if full_url not in target_urls_high: target_urls_high.append(full_url)
                    else:
                        if full_url not in target_urls_low: target_urls_low.append(full_url)

        # 1. Panen dari halaman artikel saat ini
        harvest_links(soup)
        
        # 2. v5.34 Fallback: Jika link Redaksi/Kontak tidak ditemukan di artikel, panen dari Homepage
        if not target_urls_high:
            html_home = resilient_download(domain, timeout=10, max_retries=0, target="google", silent=True)
            if html_home:
                home_soup = BeautifulSoup(html_home, 'html.parser')
                harvest_links(home_soup)
        
        # Gabungkan hasil panen dan dedup
        target_urls = list(dict.fromkeys(target_urls_high + target_urls_low))
                    
        # v5.27: Dynamic WordPress Year Patterns & Extended Targets Fallback
        import datetime
        cur_year = str(datetime.datetime.now().year)
        site_name = urlparse(domain).netloc.replace('www.', '').split('.')[0]
        
        fallback_paths = [
            '/redaksi', '/tentang-kami', '/contact-us', '/about-us', '/kontak-kami',
            '/susunan-redaksi', '/info-redaksi', '/hubungi-kami', '/pedoman-siber', '/about', '/kontak',
            '/boks-redaksi', '/editorial', '/manajemen', '/profil-media', '/struktur-organisasi',
            '/page/tentang-kami', '/page/redaksi', '/page/kontak-kami', '/page/contact-us',
            f'/redaksi-{site_name}-{cur_year}', f'/susunan-redaksi-{cur_year}', f'/redaksi-{cur_year}'
        ]
        
        for p in fallback_paths:
            fallback_url = urljoin(domain, p)
            if fallback_url not in target_urls:
                target_urls.append(fallback_url)
                
        if "tribunnews" in domain:
            target_urls.append("https://www.tribunnews.com/about/")
            target_urls.append("https://www.tribunnews.com/contact-us/")
        
        # 3. Kunjungi halaman target (Redaksi/Kontak/About) jika ditemukan
        sub_page_text = ""
        # Pengecekan dimaksimalkan hingga 25 links (menghindari kelaparan target dan memprioritaskan cakupan)
        for target in target_urls[:25]:
            try:
                # Perpendek timeout agar pengecekan massal 15 links tidak membebani loop utama (7 detik max)
                html_redaksi = resilient_download(target, timeout=7, max_retries=0, target="google", silent=True)
                if not html_redaksi: continue
                
                page_soup = BeautifulSoup(html_redaksi, 'html.parser')
                
                # v5.39: Sniff menggunakan helper Genius (mendukung Table, TR, List, dan CF Bypass)
                is_it_profile = any(kw in target.lower() for kw in ['redaksi', 'tentang', 'about', 'contact', 'readstatik'])
                sub_page_text += sniff_contact_and_editorial_board(page_soup, is_profile_page=is_it_profile)
            except: 
                continue
            
        if sub_page_text:
            contact_text += "\n[PROFIL REDAKSI PORTAL - BUKAN PENULIS SPESIFIK BERITA INI]:\n" + sub_page_text
        
        return contact_text.strip()
        
    except Exception as e:
        print(f"[-] Gagal akses domain {domain} untuk info kontak: {e}")
        return ""

def decode_google_news_url_local(source_url):
    """
    v5.85: Instant Sniper Decoder (Offline/Zero-Request)
    Membongkar enkripsi Google News secara matematis tanpa mengirim traffic ke Google.
    """
    import base64
    from urllib.parse import urlparse
    
    try:
        url = urlparse(source_url)
        path = url.path.split("/")
        # Cek apakah ini URL Google News yang valid
        if url.hostname == "news.google.com" and len(path) > 1 and path[-2] in ["articles", "read"]:
            base64_str = path[-1]
            # 1. Normalisasi Base64 (Padding & URL-Safe)
            padding = '=' * (4 - len(base64_str) % 4)
            try:
                decoded_bytes = base64.urlsafe_b64decode(base64_str + padding)
            except:
                return None
            
            # 2. Sniper Decoding Logic (Binary Stream Analysis)
            # Google menyembunyikan URL di antara biner 0x01, 0x08, dll.
            # Kita cari pola http/https secara biner.
            decoded_str = decoded_bytes.decode('latin1', errors='ignore')
            
            # Cari semua pola URL yang mungkin terselip
            # Pola ini mencakup karakter biner yang sering menempel di awal URL Google
            matches = re.findall(r'https?://[^\s\x00-\x08\x0b-\x1f\x7f-\xff<>"]+', decoded_str)
            
            for potential_url in matches:
                # Bersihkan karakter sampah yang sering tersisa (v5.85 Cleaning)
                potential_url = re.split(r'[\x00-\x1f\\"\']', potential_url)[0].strip()
                
                # Validasi: Harus domain valid dan bukan internal Google
                if len(potential_url) > 15 and "." in potential_url and "google.com" not in potential_url:
                    # Pastikan bukan file asset
                    if not any(ext in potential_url.lower() for ext in ['.css', '.js', '.jpg', '.png', '.ico', '.woff']):
                        # Bersihkan & dari ekor jika ada parameter tracking google
                        if "?" in potential_url:
                            potential_url = potential_url.split("?")[0] if "ved=" in potential_url else potential_url
                        return potential_url
        return None
    except:
        return None

def extract_link_from_meta_tags(html):
    """
    v5.17: Meta-Tag Sniffing (Deep Link Discovery).
    Mencari tautan asli dari meta property og:url atau link canonical.
    """
    if not html: return None
    try:
        # 1. Canonical Link
        canonical = re.search(r'<link.*?rel=["\']canonical["\'].*?href=["\'](https?://[^"\' >]+)', html, re.I)
        if canonical:
            url = canonical.group(1).split('\\')[0].split('"')[0].split("'")[0].strip()
            if "google.com" not in url: return url
            
        # 2. OpenGraph URL
        og_url = re.search(r'<meta.*?property=["\']og:url["\'].*?content=["\'](https?://[^"\' >]+)', html, re.I)
        if og_url:
            url = og_url.group(1).split('\\')[0].split('"')[0].split("'")[0].strip()
            if "google.com" not in url: return url
    except: pass
    return None

def resolve_google_news_url_dotsplash(source_url):
    """
    Lapis 2.5: Menggunakan API batchexecute Google untuk memecahkan enkripsi berat AU_yqL (v4.20).
    """
    import base64
    from urllib.parse import urlparse
    
    try:
        # v4.20: WARM-UP SESSION
        if not SEARCH_SESSION.cookies:
            try: SEARCH_SESSION.get("https://news.google.com/", headers=get_human_headers(), timeout=5)
            except: pass
            
        url = urlparse(source_url)
        path = url.path.split("/")
        if url.hostname == "news.google.com" and len(path) > 1 and path[-2] in ["articles", "read"]:
            base64_str = path[-1]
            # v5.44: RPC ID Fallback Strategy
            rpc_ids = ["Fbv4je", "o009Wd", "m398dd"]
            headers = get_human_headers(target="google")
            headers["Content-Type"] = "application/x-www-form-urlencoded;charset=utf-8"
            
            for rpc_id in rpc_ids:
                try:
                    payload = f'f.req=%5B%5B%5B%22{rpc_id}%22%2C%22%5B%5C%22garturlreq%5C%22%2C%5B%5B%5C%22en-US%5C%22%2C%5B%5D%2C%5B%5D%2Cnull%2Cnull%2Cnull%2Cnull%2C1%5D%2C%5B%5C%22{base64_str}%5C%22%2Cnull%2Cnull%2C1%5D%5D%5D%22%2Cnull%2C%22generic%22%5D%5D%5D&'
                    
                    resp = SEARCH_SESSION.post(
                        "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=" + rpc_id,
                        headers=headers,
                        data={"f.req": payload},
                        timeout=10,
                        proxies=get_current_proxy() if (USE_AUTO_HARVESTER or USE_PROXY) else None
                    )
                    
                    if resp.status_code == 200 and '[\\"garturlres\\",' in resp.text:
                        text = resp.text
                        header_marker = '[\\"garturlres\\",\\"'
                        footer_marker = '\\",'
                        idx = text.find(header_marker)
                        if idx != -1:
                            start = idx + len(header_marker)
                            end = text.find(footer_marker, start)
                            if end != -1:
                                found_url = text[start:end].replace('\\\\', '\\').replace('\\/', '/')
                                try:
                                    return found_url.encode().decode('unicode_escape')
                                except:
                                    return found_url
                except: continue
        return None
    except:
        return None

def extract_unique_keywords(text, limit=6):
    """Mengambil kata kunci paling unik (minimal 5 huruf) dari teks."""
    words = re.findall(r'\w{5,}', text.lower())
    # Hapus stopwords umum bahasa Indonesia jika perlu, tapi \w{5,} sudah cukup menyaring banyak
    unique_words = []
    for w in words:
        if w not in unique_words and w not in ['news', 'google', 'update', 'berita', 'terbaru']:
            unique_words.append(w)
    return unique_words[:limit]

def search_original_url_fallback(title, publisher_name, publisher_url=""):
    """
    - [x] Implementasi Snippet Extraction (Link + Title + Content)
    - [x] Implementasi Low-Length Keyword Extraction (3+ chars)
    - [x] Implementasi Root Domain Penalization (-1.0 score)
    - [x] Implementasi Domain-Trust Logic (Threshold Bypass)
    - [x] Implementasi Multi-Network Awareness (Induk Jawapos/Kompas)
    - [x] Implementasi Early Redirection Head-Check (v4.18)
    - [x] Optimasi Urutan Search Engine (Google prioritized)
    - [x] Verifikasi Link Kompas/Radar Madura (100% Recovery)
    - [ ] Monitoring Stabilitas & Pembersihan Kode Junk
    cari judul artikel di mesin pencari.
    v4.4: Strategi Multi-Query (Synthesized Title Resilience).
    """
    import urllib.parse
    import time
    import re
    
    # 1. Bersihkan judul (Hapus embel-embel publisher)
    q_text = title.split(' - ')[0].split(' | ')[0].strip()
    q_text = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', q_text)
    
    # 2. Petunjuk domain & Trusted List
    domain_hint = ""
    trusted_list = []
    if publisher_url:
        try:
            parsed_hint = urllib.parse.urlparse(publisher_url)
            domain_hint = parsed_hint.netloc.replace('www.', '').lower()
            for key, network in TRUSTED_NETWORKS.items():
                if any(n in domain_hint for n in network) or any(n in publisher_name.lower() for n in network):
                    trusted_list.extend(network)
            parts = domain_hint.split('.')
            # SMART TRUNCATION (v4.14): Preservasi subdomain untuk trusted network
            is_in_trusted = any(n in domain_hint for network in TRUSTED_NETWORKS.values() for n in network)
            
            if len(parts) > 2 and not is_in_trusted:
                if parts[-2] in ['co', 'web', 'or', 'ac', 'my', 'biz', 'go', 'net']:
                    domain_hint = ".".join(parts[-3:])
                else:
                    domain_hint = ".".join(parts[-2:])
            
            if domain_hint not in trusted_list: trusted_list.append(domain_hint)
        except: pass

    # 3. Ekstraksi Kata Kunci Unik (v4.9 - 3+ chars)
    words = re.findall(r'\b\w{3,}\b', q_text.lower())
    ignore_list = [
        'sudah', 'kembali', 'dalam', 'dengan', 'untuk', 'yang', 'dari', ' news', 'portal', 
        'layak', 'tak', 'berita', 'video', 'terkini', 'seputar', 'peristiwa'
    ]
    unique_kw_list = [w for w in words if w not in ignore_list and len(w) >= 3]
    unique_kw = " ".join(unique_kw_list[:6])
    
    # 4. Bangun Kueri Bertingkat (v5.45 - Smart Quote & Fragment Resilience)
    title_parts = [p for p in q_text.split() if len(p) > 2]
    # Jika ada tanda petik, jadikan fokus kueri
    quotes = re.findall(r"['\"](.*?)['\"]", title)
    # 3. Optimasi Kueri (v5.59: Title Sanitizer v2.0)
    q_text = title
    # Buang nama media di belakang judul (misal: "Judul - Detikcom")
    q_text = re.split(r' [-|•] ', q_text)[0].strip()
    
    unique_kw_list = re.findall(r'\w{4,}', q_text)
    unique_kw = " ".join(unique_kw_list[:6])
    mid_fragment = " ".join(unique_kw_list[2:8])
    
    queries = [f'"{q_text}"', f'{q_text}']
    domain_hint = publisher_name.lower().split('.')[0].replace(' ', '')
    if domain_hint:
        queries.insert(1, f'site:{domain_hint} {unique_kw}')
        queries.insert(2, f'site:{domain_hint} {mid_fragment}')
            
    title_keywords = set([w.lower() for w in unique_kw_list])
    if not title_keywords: return None
    
    # 4. Eksekusi Pencarian (v5.59: Bing & DDG Priority)
    SEARCH_ENGINES_RESILIENT = ["www.bing.com", "lite.duckduckgo.com", "yandex.com", "search.yahoo.com", "www.google.com"]
    
    for q_text in queries:
        is_site_search = "site:" in q_text
        for netloc in SEARCH_ENGINES_RESILIENT:
            if "google" in netloc: search_url = f"https://{netloc}/search?q={urllib.parse.quote(q_text)}"
            elif "yandex" in netloc: search_url = f"https://{netloc}/search/?text={urllib.parse.quote(q_text)}"
            elif "yahoo" in netloc: search_url = f"https://{netloc}/search?p={urllib.parse.quote(q_text)}"
            else: search_url = f"https://{netloc}/search?q={urllib.parse.quote(q_text)}"
            
            try:
                # v4.17: Menggunakan SEARCH_SESSION dan rotasi headers dinamis
                search_headers = get_human_headers(target=netloc)
                time.sleep(random.uniform(1.8, 3.2))
                
                if "duckduckgo" in netloc:
                    search_url_final = f"https://{netloc}/lite/?q={urllib.parse.quote(q_text)}"
                elif "yandex" in netloc:
                    search_url_final = f"https://{netloc}/search/?text={urllib.parse.quote(q_text)}"
                else:
                    search_url_final = search_url
                
                # v5.61: Gunakan silent=True agar tidak spam log saat pencarian mesin pencari gagal
                body_content = resilient_download(search_url_final, timeout=12, target=netloc, silent=True)
                
                if not body_content:
                    continue
                
                # DETEKSI PEMBLOKIRAN ISP (v4.22: Internet Baik/Positif Bypass)
                if body_content and any(x in body_content.lower() for x in ["internetbaik", "internetpositif", "telkomsel"]):
                    continue
                
                # v5.18: Deteksi Malformed/Error 500 (Yahoo specific)
                if not body_content or "internal server error" in body_content.lower() or "500 error" in body_content:
                    continue
                
                # GREEDY LINK HARVEST (v5.45): Cari SELURUH link yang mengandung domain hint atau network besar
                network_patterns = ['radar', 'tribun', 'jawapos', 'kompas', 'detik', 'suryamalang', 'suarasurabaya', 'liputan6', 'merdeka', 'kumparan']
                if domain_hint or any(n in body_content.lower() for n in network_patterns):
                    # Cari semua link potensial
                    all_links = re.findall(r'https?://[^\s\x00-\x1f\x7f-\xff<>"]+', body_content)
                    for pot_link in all_links:
                        pot_link = pot_link.split('"')[0].split("'")[0].split(')')[0].split('>')[0].strip()
                        # Filter link sampah
                        if any(x in pot_link.lower() for x in ['google.com', 'yandex', 'facebook', 'twitter', 'linkedin', 'instagram', 'apple.com']): continue
                        
                        # Cek kecocokan dengan domain hint atau network
                        is_trusted = any(n in pot_link.lower() for n in network_patterns)
                        is_match = domain_hint and domain_hint in pot_link.lower()
                        
                        if (is_match or is_trusted) and len(pot_link) > 30:
                            # Verifikasi kata kunci judul ada di URL (Fuzzy Match)
                            link_slug = pot_link.lower()
                            match_count = sum(1 for kw in unique_kw_list[:4] if kw in link_slug)
                            if match_count >= 2 or is_match:
                                print(f"[+] Greedy Harvest Berhasil (Lapis 5 - v5.45): {pot_link[:50]}...")
                                return pot_link

                soup = BeautifulSoup(body_content, 'html.parser')
                # --- JUNK LINK SANITIZATION (v4.10) ---
                # 1. Buang header HTML tanpa merusak case (Penting untuk Base64)
                head_idx = body_content.lower().find("</head>")
                if head_idx != -1:
                    body_content = body_content[head_idx+7:]
                
                # Cari semua URL dan ambil teks di sekitarnya
                best_candidate = None
                max_score = 0
                
                matches = list(re.finditer(r'(https?://[^\s\x00-\x1f\x7f-\xff<>"]+)', body_content))
                for m in matches:
                    link = m.group(1)
                    try:
                        # --- DEEP REDIRECT DECODER (v4.8) ---
                        # 1. Bing Redirect Decoder (ck/a Base64)
                        if "bing.com/ck/a" in link and "u=a1" in link:
                            try:
                                b64_part = link.split("u=a1")[-1].split("&")[0].split("#")[0]
                                # Tambahkan padding jika perlu
                                b64_part += "=" * (-len(b64_part) % 4)
                                import base64
                                decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore')
                                if decoded.startswith('http'): link = decoded
                            except: pass
                            
                        # Clean link from basic search params or Yahoo redirects
                        link = urllib.parse.unquote(urllib.parse.unquote(link)).split('&url=')[-1].split('?url=')[-1].split('&')[0]
                        link = link.split('/RK=')[0].split('/RS=')[0].strip()
                        
                        # 2. Hardened Junk List (Check AFTER decoding)
                        junk_blacklist = [
                            'google.', 'bing.', 'yahoo.', 'facebook.', 'twitter.', '.js', '.css', 
                            'gstatic.com', 'w3.org', 'schema.org', 'xmlns', 'purl.org', 
                            'apple.com', 'microsoft.com', 'doubleclick.net', 'analytics'
                        ]
                        if not link.startswith('http') or len(link) < 22: continue
                        if any(x in link.lower() for x in junk_blacklist): continue
                        
                        # 3. Path-Depth & Specificity Validation (v4.12)
                        parsed_link = urllib.parse.urlparse(link)
                        path_raw = parsed_link.path.strip('/')
                        path_parts = [p for p in path_raw.split('/') if p]
                        path_len = len(path_parts)
                        
                        # Deteksi Pola Berita (ID Angka atau Slug Panjang)
                        is_news_path = any(x in parsed_link.path for x in ['/baca/', '/berita-', '/nasional/', '/read/', '/peristiwa/'])
                        has_numeric_id = any(p.isdigit() and len(p) > 5 for p in path_parts)
                        has_long_slug = any(len(p) > 20 for p in path_parts)
                        
                        # PENALTI BERAT UNTUK HOMEPAGE (Root Domain)
                        # Berita asli WAJIB punya path.
                        if path_len == 0:
                            score -= 1.0
                        elif path_len < 2 and not (is_news_path or has_numeric_id):
                            score -= 0.5
                            
                        # --- CONTEXT SNIFFING & SCORING ---
                        start, end = max(0, m.start() - 1200), min(len(body_content), m.end() + 1200)
                        window_content = body_content[start:end].lower()
                        window_content = re.sub(r'<[^>]+>', ' ', window_content)
                        
                        # SCORING (Judul RSS keywords vs Window Content)
                        match_count = sum(1 for kw in title_keywords if kw in window_content or kw in link.lower())
                        score += match_count / len(title_keywords)
                        
                        # Bonus Domain Terpercaya & News Path (v4.18 - Universal Trust)
                        is_trusted_match = any(t in link.lower() for t in trusted_list)
                        
                        # DOMAIN TRUST BYPASS (v4.18): Jika domain cocok 100%, langsung sikat!
                        if domain_hint and domain_hint in link.lower() and (is_news_path or has_numeric_id):
                            print(f"[+] Universal Trust Match (v4.18): {link[:50]}...")
                            return link

                        if is_trusted_match: 
                            score += 0.90 # v4.18 Maximum trust bonus
                        if is_news_path or has_numeric_id or has_long_slug: 
                            score += 0.40
                        
                        # MINIMAL THRESHOLD (v4.18): Threshold diturunkan untuk domain terpercaya
                        final_threshold = 0.25 if is_trusted_match else threshold
                        
                        if score > max_score and score > 0.3: 
                            max_score = score
                            best_candidate = link
                    except: continue
                
                if best_candidate and max_score >= threshold:
                    print(f"[+] Berhasil merenggut URL Asli (Greedy Score: {max_score:.2f}): {best_candidate[:50]}...")
                    return best_candidate
            except: continue
    return None

def extract_article(artikel_obj):
    """Mengekstrak teks berita, metadata penulis, dan profil media."""
    import time
    
    gnews_url = artikel_obj.get('url', '')
    gnews_title = artikel_obj.get('title', '')
    gnews_desc = artikel_obj.get('description', '')
    
    # Ekstrak Nama dan Link Publisher secara tepat
    pub_info = artikel_obj.get('publisher', {})
    gnews_publisher_name = pub_info.get('title', '')
    gnews_publisher_url = pub_info.get('href', gnews_url)
    
    print(f"[*] Memproses artikel: {gnews_title[:50]}...")
    try:
        # v4.21 URL CACHE CHECK
        if gnews_url in URL_CACHE:
            print(f"[+] URL ditemukan di Cache: {URL_CACHE[gnews_url][:50]}...")
            real_url = URL_CACHE[gnews_url]
        else:
            # BYPASS GOOGLE NEWS REDIRECT
            # Kita gunakan metode berlapis untuk menerjemahkan base64 payload ke URL Asli!
            real_url = gnews_url
        
        # LAPIS 0: Local Offline Decoder (Zero Request / Anti-Blokir)
        local_decoded = decode_google_news_url_local(gnews_url)
        if local_decoded:
            real_url = local_decoded
            print(f"[+] Berhasil merenggut URL via Local Decoder (Zero Request): {real_url[:50]}...")
            
        # LAPIS 0.5: Direct Safe Redirect (Resilient Session) - v5.69
        # Berjalan perlahan (karena ada jitter di worker) untuk menghindari 429 Too Many Requests
        if "news.google.com" in real_url:
            try:
                print("[*] Mencoba Lapis 0.5: Direct Safe Redirect...")
                # Gunakan timeout sedikit panjang dan tidak verify SSL agar lolos blokir
                _safe_res = SEARCH_SESSION.head(real_url, headers=get_human_headers(mode="mobile"), timeout=15, allow_redirects=True, verify=False)
                if "google.com" not in _safe_res.url:
                    real_url = _safe_res.url
                    print(f"[+] Lapis 0.5 Berhasil (HTTP Redirect): {real_url[:60]}...")
            except Exception as e:
                print(f"[-] Lapis 0.5 Gagal/Diblokir (429/SSL): {str(e)[:40]}")
            
        # LAPIS 1: googlenewsdecoder (Library Standar - Fallback)
        if "news.google.com" in real_url:
            try:
                from googlenewsdecoder import gnewsdecoder
                # Gunakan Smart Jittering (Jeda acak 2-4 detik)
                time.sleep(random.uniform(2.0, 4.0))
                decoded_result = gnewsdecoder(gnews_url, interval=2)
                if decoded_result.get('status') and decoded_result.get('decoded_url'):
                    real_url = decoded_result.get('decoded_url')
                    print(f"[+] Lapis 1 Berhasil: {real_url[:60]}...")
            except:
                pass
            
        # LAPIS 1.5: Decoder V4 dari Repositori Lokal (Batch Execute Logic)
        if "news.google.com" in real_url:
            try:
                from googlenewsdecoder.decoderv4 import decode_google_news_url as v4_decode
                # Smart Jittering (3-5 detik)
                time.sleep(random.uniform(3.0, 5.0))
                # v5.21: Removed invalid 'session' arg causing crash
                v4_results = v4_decode([gnews_url])
                if v4_results and v4_results[0].get('status'):
                    real_url = v4_results[0].get('url')
                    print(f"[+] Berhasil merenggut URL via Decoder V4 (Lokal): {real_url[:50]}...")
            except Exception as e:
                print(f"[!] Gagal Decoder V4: {str(e)}")
            
        # LAPIS 2.5: Deep Body Extraction (Membaca HTML Google News untuk mencari link asli)
        # LAPIS 2.5: Deep Body Sniffing (JS/Meta/JSON-LD)
        if "news.google.com" in real_url:
            try:
                with requests.Session() as s:
                    # Gunakan verify=False jika ISP membajak SSL
                    res_body = s.get(real_url, headers=HEADERS, timeout=12, verify=False)
                    if res_body.status_code == 200:
                        patterns = [
                            r'url=["\']?(https?://[^"\' >]+)', # Meta Refresh
                            r'window\.location\.replace\(["\'](https?://[^"\' >]+)', # JS Redirect
                            r'"url":\s*["\'](https?://[^"\' >]+)', # JSON-LD
                            r'data-url=["\'](https?://[^"\' >]+)', # Data-URL Attribute
                            r'href=["\'](https?://[^"\' >]+)', # standard tag
                            r'\["(https?://[^"\' >]+)"\]' # JS Array pattern
                        ]
                        for pattern in patterns:
                            matches = re.finditer(pattern, res_body.text, re.I)
                            for m in matches:
                                found_url = m.group(1).split('\\')[0].split('"')[0].split("'")[0].split("&amp;")[0].strip()
                                
                                # VALIDASI KETAT: Harus ada kemiripan domain dengan publisher atau trusted network (v5.72 Block Bing Leak)
                                if all(x not in found_url for x in ["google", "gstatic", "facebook", "twitter", "analytics", "doubleclick", "adservice", "bing", "yahoo"]):
                                    # v5.44: Greedy Trust - Jika mengandung domain hint atau jaringan Jatim, ambil!
                                    if any(t in found_url.lower() for t in trusted_list) or any(n in found_url.lower() for n in ["radar", "tribun", "jawapos", "kompas", "detik", "suryamalang", "surya.co.id"]):
                                        real_url = found_url
                                        print(f"[+] Deep Sniffing Berhasil (Lapis 2.5): {real_url[:50]}...")
                                        break
                            if "google.com" not in real_url: break
            except: pass

        # LAPIS 2: Pukul paksa dengan requests bypass (Follow Redirect)
        if "news.google.com" in real_url:
            try:
                # v4.19: Mobile-First Sniffing & DOM Link Miner
                mobile_headers = get_human_headers(mode="mobile")
                res_prime = requests.get(real_url, headers=mobile_headers, timeout=10, allow_redirects=True)
                
                if "google.com" not in res_prime.url and "bing.com" not in res_prime.url:
                    real_url = res_prime.url
                else:
                    # 1. JSON-LD & SCHEMA MINER (Lapis 2.8 - v4.20)
                    json_url = extract_link_from_json_ld(body_text, domain_hint)
                    if json_url:
                        real_url = json_url
                        print(f"[+] JSON-LD Miner Berhasil (v4.20): {real_url[:50]}...")
                    
                    # 2. DOM LINK MINER (Lapis 2.7): Cari URL asli di dalam tumpukan kode Google
                    if "google.com" in real_url and domain_hint:
                        miner_match = re.search(r'https?://(?:www\.)?'+re.escape(domain_hint)+r'/[^\s"\'<>]+', body_text)
                        if miner_match:
                            found_url = miner_match.group(0).split('"')[0].split("'")[0].split('\\')[0].strip()
                            if len(found_url) > 25:
                                real_url = found_url
                                print(f"[+] DOM Link Miner Berhasil (v4.19): {real_url[:50]}...")
                    
                    # 2. Cari Meta Refresh / JS Location jika miner gagal
                    if "google.com" in real_url:
                        meta_match = re.search(r'<meta.*?url=["\']?(https?://[^"\' >]+)', body_text, re.I)
                        if meta_match:
                            real_url = meta_match.group(1).split('\\')[0].split('"')[0].strip()
                        else:
                            js_match = re.search(r'window\.location\.replace\(["\'](https?://[^"\' >]+)', body_text, re.I)
                            if js_match:
                                real_url = js_match.group(1).split('\\')[0].split('"')[0].strip()
            except: pass
        
        # LAPIS 2.9: Python GNews Library Decode (v5.31 - URL baru AU_yqL)
        if "news.google.com" in real_url:
            try:
                from gnews import GNews
                _gn = GNews(language='id', country='ID')
                _decoded = _gn.get_news_by_url_decode(gnews_url) if hasattr(_gn, 'get_news_by_url_decode') else None
                if not _decoded:
                    # Alternatif: ambil URL dari GNews library langsung menggunakan method internal
                    import sys
                    sys.path.insert(0, '/home/user/antigravity/myenv/lib')
                    try:
                        from gnews.utils.utils import postprocess
                        _decoded = postprocess(gnews_url)
                    except: pass
                if _decoded and "google.com" not in _decoded:
                    real_url = _decoded
                    print(f"[+] Lapis 2.9 (GNews Lib): {real_url[:60]}")
            except: pass

        # LAPIS 3: DotsSplash Decoder (Official Server-Side Resolution) - v4.11
        if "news.google.com" in real_url:
            print("[*] Mencoba Lapis 3: DotsSplash Official Resolver...")
            dotsplash_url = resolve_google_news_url_dotsplash(gnews_url)
            if dotsplash_url:
                real_url = dotsplash_url
                print(f"[+] Berhasil mendapatkan URL Asli via DotsSplash: {real_url}")
        
        # LAPIS 3.5: Public Webhook Decoder (v5.31 - Cadangan saat DotsSplash rate-limited)
        if "news.google.com" in real_url:
            try:
                _b64_key = real_url.split("/articles/")[-1].split("?")[0] if "/articles/" in real_url else real_url.split("/rss/articles/")[-1].split("?")[0]
                _webhook_url = f"https://api.allorigins.win/raw?url=https://news.google.com/articles/{_b64_key}"
                _wh_resp = SEARCH_SESSION.get(_webhook_url, timeout=8, headers=get_human_headers(target="google"))
                if _wh_resp.status_code == 200 and "news.google.com" not in _wh_resp.url:
                    real_url = _wh_resp.url
                    print(f"[+] Lapis 3.5 (AllOrigins Redirect): {real_url[:60]}")
            except: pass
        
        # --- LAPIS 4: ORIGINAL URL RECOVERY (RESILIENT SEARCH) ---
        if not real_url or "google.com" in real_url:
            print(f"[!] Decoder Gagal/Limit (429). Menjalankan Lapis 4: Resilient Search...")
            recovered_url = search_original_url_fallback(gnews_title, gnews_publisher_name, gnews_publisher_url)
            if recovered_url:
                real_url = recovered_url
                print(f"[+] Berhasil mendapatkan Tautan Asli: {real_url}")

        if "news.google.com" not in real_url:
            print(f"[+] Berhasil mendapatkan Tautan Asli: {real_url}")
            # v4.21 SAVE TO CACHE
            if gnews_url not in URL_CACHE:
                URL_CACHE[gnews_url] = real_url
                save_url_cache(URL_CACHE)
            
        # Download artikel dari URL asli yang sudah final
        # v5.19: MOBILE REDIRECT BYPASS (Special Handshake for GNews)
        # Seringkali pengalihan via jalur mobile lebih jarang diblokir dan lebih cepat.
        # v5.59: MOBILE-IDENTITY SNIFFER (Special Handshake)
        # Menyamar sebagai iPhone/Android untuk memicu pengalihan asli via meta-refresh
        if "news.google.com" in real_url:
            try:
                mobile_headers = get_human_headers(mode="mobile")
                m_resp = requests.get(real_url, headers=mobile_headers, timeout=10, allow_redirects=True, verify=False)
                if "news.google.com" not in m_resp.url:
                    real_url = m_resp.url
                    print(f"[+] Mobile-Identity Sniffer Berhasil: {real_url[:60]}")
                else:
                    # Sniff via meta refresh di body
                    m_match = re.search(r'url=["\']?(https?://[^"\' >]+)', m_resp.text, re.I)
                    if m_match:
                        real_url = m_match.group(1).split('"')[0].split("'")[0]
                        print(f"[+] Meta-Refresh Sniffed (Mobile): {real_url[:60]}")
            except: pass
        
        # v5.17: Deep Link Discovery via Meta Tags
        try:
            temp_res_html = resilient_download(real_url, timeout=10, target="google")
            if temp_res_html:
                meta_url = extract_link_from_meta_tags(temp_res_html)
                if meta_url and "google.com" not in meta_url:
                    real_url = meta_url
                    print(f"[+] Deep-Link Terdeteksi (Meta Tag): {real_url}")
                else:
                    # Fallback to canonical regex if meta sniffer failed
                    canonical_match = re.search(r'<link.*?rel=["\']canonical["\'].*?href=["\'](https?://[^"\' >]+)', temp_res_html[:10000], re.I)
                    if canonical_match:
                        canonical_url = canonical_match.group(1).split('\\')[0].split('"')[0].split("'")[0].strip()
                        if "google.com" not in canonical_url:
                            real_url = canonical_url
                            print(f"[+] Canonical Link Terdeteksi Dini: {real_url}")
        except: pass
        
        # v5.75: FINAL URL VALIDATOR — Tolak URL mesin pencari yang bocor
        search_engine_leak = ['bing.com/search', 'google.com/search', 'yahoo.com/search', 'duckduckgo.com/?q', 'yandex.com/search']
        if any(se in real_url.lower() for se in search_engine_leak):
            print(f"[!] BLOCKED: URL final adalah halaman mesin pencari: {real_url[:60]}... -> DITOLAK.")
            return None
        
        # v5.4: FULL CONTENT DOWNLOAD WITH PAGINATION SUPPORT
        html_content = resilient_download_full(real_url, timeout=12, target="google")
        
        if not html_content:
            # v5.31: Coba AMP bypass untuk portal yang memblokir scraper pada URL normal
            amp_url = None
            _parsed_ru = urlparse(real_url)
            # Tribun/Surya group: /amp/ prefix setelah netloc
            if any(d in real_url for d in ['tribunnews.com', 'surya.co.id', 'jatimnow.com', 'detik.com', 'kompas.com']):
                if '/amp/' not in real_url:
                    amp_url = f"{_parsed_ru.scheme}://{_parsed_ru.netloc}/amp{_parsed_ru.path}"
            # Tempo.co: /amp/read/ format (terbukti berhasil 200)
            elif 'tempo.co' in real_url and '/amp/' not in real_url:
                amp_url = re.sub(r'/read/', '/amp/read/', real_url, count=1)
            if amp_url:
                html_content = resilient_download_full(amp_url, timeout=10, target="google")
                if html_content:
                    real_url = amp_url
                    print(f"[+] AMP Bypass berhasil: {amp_url[:60]}")
        
        if not html_content:
            # Jika gagal total, gunakan deskripsi GNews sebagai fallback darurat
            print(f"[!] Kegagalan fatal pengunduhan artikel: {real_url}")
            text = f"Judul Lengkap: {gnews_title}\nDeskripsi: {gnews_desc}\n\n[Warning: Gagal mengunduh isi teks asli setelah beberapa percobaan]."
            article = type('obj', (object,), {'title': gnews_title, 'text': text, 'authors': [], 'html': None})
        else:
            # Gunakan Newspaper3k untuk parsing HTML yang sudah berhasil diunduh manual
            article = Article(real_url, language='id')
            article.set_html(html_content)
            article.parse()
            
            # v5.54: ANTI-BOT SHIELD
            bot_keywords = ["bot verification", "cloudflare", "just a moment", "attention required", "ddos protection", "halaman tidak ditemukan", "access denied", "robot"]
            if any(kw in str(article.title).lower() for kw in bot_keywords):
                print(f"[!] Terdeteksi Halaman Blokir (Bot Challenge) pada {real_url}. Membatalkan profiling.")
                return None
        
        title = article.title if hasattr(article, 'title') and article.title and len(article.title) > 15 else gnews_title
        text = article.text if hasattr(article, 'text') else ""
        authors = ", ".join(article.authors) if hasattr(article, 'authors') and article.authors else "Tidak tercantum"
        
        # Tentukan Tautan Asli (Source URL)
        source_url = real_url
        # Ekstrak domain asal portal dari URL yang sudah final
        parsed_uri = urlparse(source_url)
        domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
        portal_name = parsed_uri.netloc.replace('www.', '')
        
        # v5.16: Inisialisasi awal untuk mencegah UnboundLocalError pada alur fallback
        contact_info_text = ""
        
        # Jika teks kosong, kemungkinan besar portalnya memblokir bot
        if not text or len(text) < 50:
            print("[!] Peringatan: Gagal mengekstrak teks asli, fallback ke metode deskripsi pintar (GNews fallback).")
            # v5.14: Penandaan Hiper-Jelas untuk AI & User
            marker = "[SNIPPET_ONLY: Teks Lengkap Tidak Terjangkau]"
            text = f"{marker}\nJudul Lengkap: {gnews_title}\nDeskripsi: {gnews_desc}\n\n[Catatan Intelijen: Sistem menemui proteksi link ganda atau blokir ISP. Lakukan evaluasi sebaik mungkin, JANGAN mengarang detail]."
            contact_info_text = f"{marker}\n"
        
        # === EKSTRAKSI PENULIS/EDITOR DARI HTML BODY ARTIKEL ===
        metadata_penulis = ""
        if article.html:
            soup_artikel = BeautifulSoup(article.html, 'html.parser')
            metadata_penulis = ekstrak_metadata_penulis_dari_html(soup_artikel)
        
        # Gabungkan: metadata dari newspaper + metadata dari DOM parsing (v5.3 Source Priority)
        semua_penulis_parts = []
        if article.authors:
            semua_penulis_parts.append(f"[DUGAAN PENULIS UTAMA: {', '.join(article.authors)}]")
        if metadata_penulis:
            semua_penulis_parts.append(f"[BYLINE ARTIKEL SPESIFIK:\n{metadata_penulis}]")
        
        if semua_penulis_parts:
            text = "\n".join(semua_penulis_parts) + "\n\n" + text
        
        # === SCRAPING HALAMAN PROFIL/REDAKSI PORTAL ===
        # --- SMART POST-SCRAPE FILTER (v5.63) ---
        from crawler import is_potensi_ancaman
        # Pengecekan ulang dengan teks artikel utuh. Jika positif/netral, langsung coret!
        if text and not is_potensi_ancaman(title, text[:1500]):
             print(f"[-] [Smart Post-Scrape] Sentimen aslinya Positif/Netral. Membatalkan Deep Profiling untuk '{title[:40]}'.")
             return None
             
        contact_info_text = scrape_contact_page(domain, html_content=article.html)
        
        return {
            "title": title,
            "text": text,
            "authors": authors,
            "source_url": source_url,
            "portal": portal_name,
            "contact_text": contact_info_text
        }
    except Exception as e:
        print(f"[-] Error scraping article {gnews_url}: {e}")
        return None

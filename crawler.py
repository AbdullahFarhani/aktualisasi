import os
import json
import time
import re
import warnings

# Penekanan pesan Pytorch/Transformers yang berisik
warnings.filterwarnings("ignore")

from gnews import GNews
from config import GNEWS_LANGUAGE, GNEWS_COUNTRY, GNEWS_PERIOD

# 1. Setup Rule-Based Regex (Satpam Cepat)
# FRASA_POSITIF_REJECT: Menghalau berita noise (hiburan, olahraga, seremoni, prestasi, promosi)
FRASA_POSITIF_REJECT = r"(sukses|berhasil|penghargaan|bebas dari|meraih|terbukti tidak|aman|damai|lancar|kondusif|bantuan|sumbangan|apresiasi|meningkat|positif|juara|bangga|prestasi|piala|liga|pertandingan|skor|atlet|turnamen|konser|musik|film|artis|hiburan|selebriti|wisata|kuliner|hotel|promosi|diskon|wisuda|hari jadi|ulang tahun|hari ulang tahun|peresmian|sholawat|shalawat|pengajian|pengukuhan|pesta|festival|pameran|bazar|fashion|kecantikan|lifestyle|gaya hidup|arema|persebaya|bonek|aremania|sepak bola|sepakbola|futsal|stadion|suporter|klub|derby|pelatih|latihan|pertandingan)"
# POLA_ANCAMAN: Fokus pada insiden, tindak pidana, konflik, kerawanan, krisis logistik, dan kegagalan sistem
POLA_ANCAMAN = r"(korup|suap|gratifikasi|pungli|ilegal|kriminal|terseret|tipu|kasus|tersangka|terdakwa|vonis|tangkap|adili|tuntut|gerebek|sita|razia|demo|unjuk rasa|rusuh|amuk|konflik|sengketa|tawur|keroyok|bacok|bunuh|tewas|narkoba|buron|ciduk|rugi|palsu|teror|makar|senjata|bom|ledak|hoaks|provokasi|geruduk|kepung|hukum|perkosa|cabul|curi|maling|ringsek|tabrak|mati|pidana|ancaman|separatis|radikal|sabotase|penculikan|penyekapan|begal|rampok|bajak|tak layak konsumsi|basi|bau|keracunan|muntah|sakit|dikembalikan|busuk|berulat|beracun|bingung|tak punya kendali|tak tahu|terbengkalai|sia-sia|mubazir|tak berfungsi|rusak|mangkrak|kecewa|protes|tolak|masalah|kendala|salah sasaran|keliru|tidak tepat|tak beroperasi|cerai|gugat|lgbt|gay|homo|lesbian|pamer|flexing|mewah|pesta|resepsi|selingkuh|zina|hina|hujat|bully|oknum|indisipliner|sanksi|pecat|pecat tni)"
# FRASA_REJECT_NASIONAL: Menghalau berita nasional/internasional murni agar tidak lolos hanya karena dimuat media AreaX
FRASA_REJECT_NASIONAL = r"(trump|biden|putin|zelensky|xi jinping|netanyahu|iran|israel|gaza|lebanon|palestina|ukraina|rusia|timur tengah|laut cina selatan|nato|pbb|hamas|hizbullah|jakarta|bandung|medan|makassar|ikn|nusantara|nasional|dunia|internasional|inter milan|ac milan|juventus|serie a|liga italia|liga inggris|liga spanyol|champions league|calciopoli|piala dunia|euro 202|piala asia|timnas indonesia|pssi)"

# 2. Setup Deep Learning AI (IndoRoBERTa Backend PyTorch)
print("\n[*] Menghidupkan Mesin AI Lokal (IndoRoBERTa)... Menginisialisasi Perangkat Keras...")
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from huggingface_hub import login
    import os
    
    # Login langsung agar warning hilang
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)
    
    # Load model Transformers yang dikhususkan untuk klasifikasi teks Bahasa Indonesia (0: Positif, 1: Netral, 2: Negatif)
    tokenizer = AutoTokenizer.from_pretrained("w11wo/indonesian-roberta-base-sentiment-classifier")
    indoroberta_model = AutoModelForSequenceClassification.from_pretrained("w11wo/indonesian-roberta-base-sentiment-classifier")
    AI_READY = True
    print("[+] IndoRoBERTa Berhasil Dimuat dan *Standby*!\n")
except Exception as e:
    print(f"[-] Peringatan: Gagal memuat Pustaka Deep Learning atau IndoRoBERTa: {e}")
    AI_READY = False

def is_potensi_ancaman(judul, deskripsi, strict_mode=False):
    """
    Sistem Penyaringan Hybrid Genius (v5.84)
    """
    teks = (str(judul) + " " + str(deskripsi)).lower()
    
    # --- LAPIS 0: UJI LOKASI JAWA TIMUR (v6.12: Nuanced) ---
    from config import KABKOTA_AREAX, PRIORITY_KATA_KUNCI
    
    # Deteksi isu prioritas (Bypass Geofence ketat)
    isu_prioritas = any(pk.lower() in teks for pk in PRIORITY_KATA_KUNCI)
    
    # Bersihkan nama media untuk deteksi lokasi murni
    teks_murni = teks
    media_names = ["radar jember", "radar kediri", "radar madura", "radar banyuwangi", "radar madiun", "radar tulungagung", "radar bojonegoro", "radar semeru", "radar gresik", "surya malang", "tribun areax", "radar surabaya"]
    for mn in media_names:
        teks_murni = teks_murni.replace(mn, " [MEDIA] ")
        
    lokasi_valid = False
    if "areax" in teks or "area operasional" in teks:
        lokasi_valid = True
    else:
        for kota in KABKOTA_AREAX:
            kota_low = kota.lower()
            # Kriteria 1: Kota muncul di luar nama media (Teks Murni)
            if kota_low in teks_murni:
                lokasi_valid = True
                break
            # Kriteria 2: Kota muncul di judul (Sangat Kuat)
            if kota_low in str(judul).lower():
                lokasi_valid = True
                break
            # Kriteria 3: Isu Prioritas (Berikan toleransi lebih tinggi)
            if isu_prioritas and kota_low in teks:
                lokasi_valid = True
                break
    
    if not lokasi_valid: return False
                
    # --- LAPIS 0.1: REJECT NASIONAL/INTERNASIONAL ---
    if re.search(FRASA_REJECT_NASIONAL, teks):
        return False

    # --- LAPIS 1: PEMERIKSAAN PRIORITAS (GENIUS BYPASS) ---
    # Jika berita tentang isu prioritas (TNI, Koperasi, MBG), kita JAUH lebih sensitif.
    isu_prioritas = False
    for pk in PRIORITY_KATA_KUNCI:
        if pk.lower() in teks:
            isu_prioritas = True
            break

    # --- LAPIS 2: PENGHAPUSAN PAKSA (SENTIMEN POSITIF) ---
    if re.search(FRASA_POSITIF_REJECT, teks):
        # Jika isu prioritas, JANGAN langsung buang (Bisa saja bantuan yang bermasalah)
        if not isu_prioritas:
            return False
        
    # --- LAPIS 3: PEMERIKSAAN INSIDEN (REGEX) ---
    indikasi_kasus = bool(re.search(POLA_ANCAMAN, teks))
    
    # --- LAPIS 4: KONFIRMASI AI ---
    if AI_READY:
        try:
            inputs = tokenizer(teks, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = indoroberta_model(**inputs)
            
            predicted_class = torch.argmax(outputs.logits, dim=-1).item()
            
            # 0=Pos, 1=Net, 2=Neg
            if predicted_class == 2:
                return True
                
            # Genius Logic: Jika isu prioritas DAN ada indikasi kasus (Regex), 
            # abaikan saja jika AI bilang "Netral" (1) atau "Positif" (0). Intelijen harus waspada.
            if isu_prioritas and indikasi_kasus:
                return True
                
            if not strict_mode and indikasi_kasus and predicted_class == 1:
                return True
                
            return False 
        except Exception as e:
            return indikasi_kasus
    else:
        return indikasi_kasus

def fetch_gnews_rss_resilient(query):
    """v6.70: Mengunduh RSS Google News secara manual dengan rotasi proxy jika terblokir."""
    import requests
    import xml.etree.ElementTree as ET
    from scraper import get_current_proxy
    from urllib.parse import quote
    
    # URL RSS Google News (Ditambah when:1d untuk membatasi 24 jam terakhir)
    encoded_query = quote(query + " when:1d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
    
    from scraper import get_human_headers
    
    # Cobalah beberapa kali (walau tanpa proxy, tetap dicoba dengan delay membesar jika gagal)
    for attempt in range(3):
        proxy = get_current_proxy()
        headers = get_human_headers()
        try:
            resp = requests.get(rss_url, headers=headers, proxies=proxy, timeout=15)
            if resp.status_code == 200:
                # Parsing RSS
                root = ET.fromstring(resp.text)
                articles = []
                for item in root.findall('.//item'):
                    articles.append({
                        'title': item.find('title').text if item.find('title') is not None else "",
                        'description': item.find('description').text if item.find('description') is not None else "",
                        'url': item.find('link').text if item.find('link') is not None else "",
                        'publisher': {'title': item.find('source').text if item.find('source') is not None else "Unknown"},
                        'published date': item.find('pubDate').text if item.find('pubDate') is not None else ""
                    })
                if articles:
                    conn_type = "Proxy" if proxy else "Direct"
                    print(f"[+] GNews Berhasil! ({conn_type}) - Menemukan {len(articles)} berita.")
                    return articles
            elif resp.status_code == 503:
                print(f"[*] Proxy/IP terblokir Google (503). Mencoba proxy lain ({attempt+1}/5)...")
                if not proxy:
                    print("[!] Peringatan: IP Asli diblokir GNews (503) & Proxy dimatikan. Beralih ke Lapis 2 (DDG).")
                    break
            else:
                print(f"[*] GNews RSS Status {resp.status_code}. Mencoba lagi...")
        except Exception as e:
            print(f"[*] Error fetching RSS with proxy: {e}")
        
        time.sleep(2)
        
    return []

def search_news(keyword, location):
    """Mencari berita dengan Google News (Resilient Proxy), fallback ke DuckDuckGo."""
    from datetime import datetime, timedelta
    from duckduckgo_search import DDGS
    
    query = f"{keyword} {location}"
    print(f"[*] Mencari berita untuk query: '{query}'")
    
    # --- LAPIS 1: GOOGLE NEWS (v6.70 Proxy Resilient) ---
    try:
        articles = fetch_gnews_rss_resilient(query)
        if articles:
            return articles
    except Exception as e:
        print(f"[!] GNews Resilient Error: {e}")
        
    # v6.81: Sesuai instruksi, jika GNews nihil, langsung lanjut ke kata kunci berikutnya tanpa fallback DDG
    return []

def filter_new_articles(articles, history_file='processed_urls.json'):
    """Memfilter URL agar yang sudah diproses atau lewat dari 24 jam dibuang."""
    import time
    import dateparser
    
    processed = set()
    try:
        with open(history_file, 'r') as f:
            processed = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
        
    new_articles = []
    sekarang_ts = time.time()
    
    for art in articles:
        url = art.get('url', '')
        
        # 0. v5.73: TOLAK URL Mesin Pencari (Bing/Google/Yahoo Search) — Bukan berita valid
        search_engine_patterns = ['bing.com/search', 'google.com/search', 'yahoo.com/search', 'duckduckgo.com/?q', 'yandex.com/search']
        if any(se in url.lower() for se in search_engine_patterns):
            print(f"[-] Terfilter (URL Mesin Pencari): '{art.get('title', '')[:40]}...' -> Dibuang.")
            continue
        
        # 1. Pastikan belum diproses
        if not url or url in processed:
            continue
            
        # 2. FILTER MANUAL WAKTU: Pastikan usianya < 25 Jam (toleransi 1 jam zona waktu)
        # Tanggal dari Google News biasanya 'Wed, 08 Apr 2026 12:30:00 GMT'
        published_str = art.get('published date', '')
        if not published_str:
            # v5.20: Strict Dropout -- jika tidak ada informasi tanggal, tolak.
            print(f"[-] Terfilter (Usang/Tanpa Tanggal): '{art.get('title', '')[:30]}...' -> Dibuang.")
            continue
            
        try:
            pub_date = dateparser.parse(published_str)
            if not pub_date:
                # Gagal melakukan parse tanggal
                continue
                
            age_seconds = sekarang_ts - pub_date.timestamp()
            
            # Buang jika usia berita > 90000 detik (25 jam) atau jika tanggal ada di masa depan terlalu jauh!
            if age_seconds > 90000 or age_seconds < -86400:
                print(f"[-] Terfilter (Usang {int(age_seconds/3600)} jam lalu): '{art.get('title', '')[:30]}...' -> Dibuang.")
                continue
        except Exception:
            # v5.20: Strict Dropout
            continue
                
        new_articles.append(art)
            
    return new_articles

def mark_as_processed(url, history_file='processed_urls.json'):
    """Menyimpan URL ke dalam history bahwa sudah diproses"""
    processed = []
    try:
        with open(history_file, 'r') as f:
            processed = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
        
    processed.append(url)
    
    with open(history_file, 'w') as f:
        json.dump(processed, f)

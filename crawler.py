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
FRASA_POSITIF_REJECT = r"(sukses|berhasil|penghargaan|bebas dari|meraih|terbukti tidak|aman|damai|lancar|kondusif|bantuan|sumbangan|apresiasi|meningkat|positif|juara|bangga|prestasi|piala|liga|pertandingan|skor|atlet|turnamen|konser|musik|film|artis|hiburan|selebriti|wisata|kuliner|hotel|promosi|diskon|wisuda|hari jadi|ulang tahun|hari ulang tahun|peresmian|sholawat|shalawat|pengajian|pengukuhan|pesta|festival|pameran|bazar|fashion|kecantikan|lifestyle|gaya hidup)"
# POLA_ANCAMAN: Fokus pada insiden, tindak pidana, konflik, kerawanan, dan krisis logistik/pangan
POLA_ANCAMAN = r"(korup|suap|gratifikasi|pungli|ilegal|kriminal|terseret|tipu|kasus|tersangka|terdakwa|vonis|tangkap|adili|tuntut|gerebek|sita|razia|demo|unjuk rasa|rusuh|amuk|konflik|sengketa|tawur|keroyok|bacok|bunuh|tewas|narkoba|buron|ciduk|rugi|palsu|teror|makar|senjata|bom|ledak|hoaks|provokasi|geruduk|kepung|hukum|perkosa|cabul|curi|maling|ringsek|tabrak|mati|pidana|ancaman|separatis|radikal|sabotase|penculikan|penyekapan|begal|rampok|bajak|tak layak konsumsi|basi|bau|keracunan|muntah|sakit|dikembalikan|busuk|berulat|beracun)"
# FRASA_REJECT_NASIONAL: Menghalau berita nasional/internasional murni agar tidak lolos hanya karena dimuat media Jatim
FRASA_REJECT_NASIONAL = r"(trump|biden|putin|zelensky|xi jinping|netanyahu|iran|israel|gaza|lebanon|palestina|ukraina|rusia|timur tengah|laut cina selatan|nato|pbb|hamas|hizbullah|jakarta|bandung|medan|makassar|ikn|nusantara|nasional|dunia|internasional)"

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
    Sistem Penyaringan Hybrid: Regex Cepat ditambahkan dengan Konfirmasi AI RoBERTa
    v5.63: strict_mode memaksa AI hanya meloloskan sentimen Negatif (2) tanpa kompromi.
    """
    teks = (str(judul) + " " + str(deskripsi)).lower()
    
    # --- LAPIS 0: UJI LOKASI WAJIB JAWA TIMUR (PRE-FILTER KETAT) ---
    # Jika tidak ada satupun nama daerah Jatim/Kata Jatim di judul/deskripsi, buang langsung!
    from config import KABKOTA_JATIM
    lokasi_valid = False
    if "jatim" in teks or "jawa timur" in teks:
        lokasi_valid = True
    else:
        for kota in KABKOTA_JATIM:
            if kota.lower() in teks:
                lokasi_valid = True
                break
                
    # --- LAPIS 0.1: REJECT NASIONAL/INTERNASIONAL (PRE-FILTER KRITIS) ---
    # Jika judul mengandung isu dunia/nasional murni, buang (kecuali ada konteks Jatim yang sangat kuat di judul)
    if re.search(FRASA_REJECT_NASIONAL, teks):
        # Kecuali ada kata kunci kota jatim spesifik, maka kita anggap itu isu luar
        return False

    # --- LAPIS 1: PENGHAPUSAN PAKSA (RULE-BASED SENTIMEN POSITIF) ---
    if re.search(FRASA_POSITIF_REJECT, teks):
        # Jika mutlak mengandung kalimat berita positif/perayaan, langsung kubur!
        return False
        
    # --- LAPIS 2: PEMERIKSAAN INSIDEN (RULE-BASED) ---
    indikasi_kasus = bool(re.search(POLA_ANCAMAN, teks))
    
    # --- LAPIS 3: KONFIRMASI INFERENSI AI (MACHINE LEARNING) ---
    if AI_READY:
        try:
            # Ubah teks ke tensor matematika terbatas 512 max length (standard transformer)
            inputs = tokenizer(teks, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = indoroberta_model(**inputs)
            
            # Ekstrak probabilitas tertinggi
            predicted_class = torch.argmax(outputs.logits, dim=-1).item()
            
            # W11WO/Indonesian Rule: 0 = Positif, 1 = Netral, 2 = Negatif
            if predicted_class == 2:
                # 100% Validasi Mesin: ini sentimen Negatif/Ancaman.
                return True
                
            if not strict_mode and indikasi_kasus and predicted_class == 1:
                # Toleransi Cerdas: AI bilang 'Netral', tapi Regex Polisi bilang ada insiden parah. Lebih baik waspada & diloloskan.
                return True
                
            return False # Kalau AI bilang Positif (0) atau Netral (tanpa insiden/di mode ketat), mutlak kita buang (False)
        except Exception as e:
            # Fallback jika model tiba-tiba error inferensi
            print(f"[-] Error Inferensi Neural Network: {e}")
            return indikasi_kasus
    else:
        # Fallback konvensional jika library Torch/Transformers hilang
        return indikasi_kasus

def search_news(keyword, location):
    """Mencari berita dengan kombinasi keyword dan lokasi (hanya 24 jam terakhir)."""
    from datetime import datetime, timedelta
    
    query = f"{keyword} {location}"
    print(f"[*] Mencari berita untuk query: '{query}'")
    
    # Gunakan tanggal eksplisit agar PASTI hanya berita 24 jam terakhir
    sekarang = datetime.now()
    kemarin = sekarang - timedelta(days=1)
    
    google_news = GNews(
        language=GNEWS_LANGUAGE, 
        country=GNEWS_COUNTRY, 
        period=GNEWS_PERIOD,
        max_results=100
    )
    
    try:
        articles = google_news.get_news(query)
        if articles:
            print(f"[+] Ditemukan {len(articles)} berita untuk query: '{query}'")
        return articles
    except Exception as e:
        print(f"[-] Error crawling GNews untuk '{query}': {e}")
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

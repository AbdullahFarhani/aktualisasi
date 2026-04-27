import os

# Konfigurasi HuggingFace Token (v5.65)
os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN_HERE"

# Konfigurasi Telegram
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

TELEGRAM_BOT_TOKEN_2 = "YOUR_BOT_TOKEN_2_HERE"
TELEGRAM_CHAT_ID_2 = "YOUR_CHAT_ID_2_HERE"

# API Key Google Gemini
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

# API Key OpenRouter (Gunakan Model Qwen / Llama Gratis)
OPENROUTER_API_KEY = "YOUR_OPENROUTER_API_KEY_HERE"

# API Key Groq (30 RPM, 14.400 RPD - Super Cepat & Longgar)
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"

# Daftar Model Groq untuk Rotasi (Menghindari 429)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
    "openai/gpt-oss-120b"
]

# Data Geografis
KABKOTA_JATIM = [
    "Bangkalan", "Banyuwangi", "Blitar", "Bojonegoro", "Bondowoso", "Gresik", 
    "Jember", "Jombang", "Kediri", "Lamongan", "Lumajang", "Madiun", "Magetan", 
    "Malang", "Mojokerto", "Nganjuk", "Ngawi", "Pacitan", "Pamekasan", "Pasuruan", 
    "Ponorogo", "Probolinggo", "Sampang", "Sidoarjo", "Situbondo", "Sumenep", 
    "Trenggalek", "Tuban", "Tulungagung", "Batu", "Surabaya", "Jawa Timur"
]

# Wilayah Perbatasan & Kota Besar yang WAJIB Ditolak (Luar Jawa Timur) - v5.35
REJECTED_REGIONS = [
    # Jawa Tengah & DIY
    "Blora", "Cepu", "Randublatung", "Sragen", "Solo", "Surakarta",
    "Yogyakarta", "Jogja", "DIY", "Daerah Istimewa Yogyakarta",
    "Gunungkidul", "Gunung Kidul", "Sleman", "Bantul", "Kulon Progo", "Kulonprogo",
    "Klaten", "Wonogiri", "Purworejo", "Magelang", "Wonosobo", "Temanggung",
    "Boyolali", "Karanganyar", "Sukoharjo", "Grobogan", "Pati", "Kudus",
    "Rembang", "Jepara", "Demak", "Kendal", "Batang", "Pekalongan",
    "Pemalang", "Tegal", "Brebes", "Purbalingga", "Banjarnegara", "Kebumen",
    "Cilacap", "Banyumas", "Purwokerto", "Jawa Tengah", "Jateng", "Semarang",
    # Bali
    "Bali", "Denpasar", "Badung", "Gianyar", "Tabanan", "Bangli",
    "Klungkung", "Karangasem", "Buleleng", "Jembrana",
    # Jabodetabek & Jawa Barat
    "Jakarta", "Bekasi", "Depok", "Bogor", "Tangerang", "Banten",
    "Bandung", "Jawa Barat", "Jabar", "Cirebon", "Sukabumi", "Cianjur",
    "Garut", "Tasikmalaya", "Ciamis", "Kuningan", "Majalengka",
    "Subang", "Purwakarta", "Karawang", "Indramayu",
    # Sumatera
    "Lampung", "Medan", "Sumatera", "Aceh", "Riau", "Palembang",
    "Padang", "Pekanbaru", "Jambi", "Tebo", "Bungo", "Muaro Jambi", "Kerinci", "Bengkulu", "Batam", "Bintan",
    "Bangka Belitung", "Belitung",
    # Sulawesi, Kalimantan, Maluku
    "Makassar", "Sulawesi", "Kalimantan", "Palu", "Gorontalo", "Manado",
    "Balikpapan", "Samarinda", "Banjarmasin", "Pontianak",
    "Maluku", "Ambon", "Ternate",
    # Papua & NTT/NTB
    "Papua", "Tolikara", "Jayapura", "Timika", "Sorong", "Merauke", "Manokwari",
    "NTT", "NTB", "Kupang", "Mataram", "Lombok", "Flores",
    # Institusi Pusat (Jakarta-Sentris)
    "Polda Metro Jaya", "Mabes Polri", "Kejagung", "Kejaksaan Agung", 
    "KPK Jakarta", "Gedung Merah Putih", "Senayan", "DPR RI", "MPR RI", "Kemenkeu"
]

# Kata kunci geografis yang memicu PENOLAKAN INSTAN (Ultra-Geofence) - v5.35
# HANYA untuk frasa yang PASTI 100% bukan Jawa Timur dan TIDAK MUNGKIN muncul sbg cross-report
# (Mis: Jakarta Selatan bisa muncul di berita KPK tentang Jatim, jadi masuk REJECTED_REGIONS saja)
FORBIDDEN_KEYWORDS = [
    # Bali (tidak mungkin cross-report dengan Jatim secara lokasi)
    "Kuta Bali", "Badung Bali", "Baturiti",
    # DIY (sangat spesifik, tidak mungkin salah sangka)
    "Daerah Istimewa Yogyakarta", "Provinsi DIY",
    # Tokoh Nasional (Jika tanpa konteks Jatim yang kuat - v5.49)
    "Polda Metro Jaya", "Mabes Polri", "Uya Kuya", "Artis Ibu Kota",
    "Kabupaten Gunungkidul", "Kabupaten Sleman", "Kabupaten Bantul",
    "Kabupaten Kulon Progo", "Kota Yogyakarta",
    # Jawa Tengah
    "Kabupaten Klaten", "Kabupaten Wonogiri", "Kabupaten Purworejo",
    "Kabupaten Cilacap", "Kabupaten Banyumas",
    # Jawa Barat
    "Kabupaten Bogor", "Kabupaten Bekasi", "Kabupaten Karawang",
    "Kota Bandung", "Kota Cirebon",
    # Papua & NTT/NTB
    "Kabupaten Tolikara", "Papua Pegunungan", "Papua Barat", "Papua Tengah",
    "Lanny Jaya", "Yahukimo", "Pegunungan Bintang",
]

# Kata Kunci Pencarian (Tema Ancaman Nasional / Isu Sosial / Direktif Komando Atas)
# KATA_KUNCI = [
#     "mbg",
#     "makan bergizi gratis",
#     "koperasi merah putih",
#     "jembatan",
#     "oknum TNI",
#     "oknum aparat",
#     "TNI bermasalah",
#     "keluarga TNI",
#     "istri TNI",
#     "anak TNI",
#     "persit",
#     "personel TNI",
#     "wanita tni",
#     "kowad",
#     "KDRT",
#     "TNI",
#     "TNI viral",
#     "Anggota TNI",
#     "prajurit tni",
#     "pengeroyokan tni",
#     "insiden tni",
#     "aparat",
#     "pungli",
#     "fiktif",
#     "modus",
#     "tentara nasional indonesia",
#     "sppg",
#     "keracunan",
#     "pupuk ilegal",
#     "rokok ilegal",
#     "koperasi",
#     "kdkmp",
#     "kopdes",
#     "kdmp",
#     "kmp",
#     "knmp",
#     "kampung nelayan",
#     "kampung nelayan merah putih",
#     "jembatan garuda",
#     "jembatan perintis",
#     "jembatan ambruk",
#     "jembatan rusak",
#     "jembatan putus",
#     "narkotika",
#     "sabu-sabu",
#     "narkoba",
#     "sampah",
#     "pengelolaan sampah",
#     "bbm",
#     "spbu",
#     "korupsi",
#     "penyuapan", 
#     "gratifikasi",
#     "buruh",
#     "bentrok",
#     "demo",
#     "konsolidasi",
#     "unjuk rasa",
#     "aksi damai",
#     "sengketa",
#     "oplosan",
#     "sesat",
#     "radikalisme",
#     "tambang ilegal",
#     "proyek fiktif",
#     "perjudian",
#     "prostitusi"
# ]

# v5.79: Reguler Ancaman Jatim (Optimized to 20)
KATA_KUNCI = [
    "korupsi dana desa", "pungli", "penyuapan", "gratifikasi",
    "demo anarkis", "bentrok warga", "sengketa lahan", "narkoba",
    "KDRT", "aparat", "fiktif", "modus",
    "pupuk ilegal", "rokok ilegal",
    "koperasi", "kdkmp", "kopdes", "kmp",
    "bbm", "spbu"
]

# v5.79: Daftar Kata Kunci PRIORITAS (Optimized to 55)
PRIORITY_KATA_KUNCI = [
    # MBG & SPPG
    "mbg", "makan bergizi gratis", "mbg keracunan", "kasus mbg", "sppg", "keracunan",
    # Koperasi
    "koperasi merah putih", "korupsi koperasi", "koperasi",
    # Jembatan
    "jembatan", "proyek jembatan",
    # TNI & Aparat (Expanded)
    "oknum TNI", "oknum aparat", "TNI bermasalah", "TNI viral",
    "Anggota TNI", "prajurit tni", "pengeroyokan tni", "insiden tni",
    "keluarga TNI", "istri TNI", "anak TNI", "persit", "personel TNI",
    "wanita tni", "kowad", "tentara nasional indonesia",
    # Yon TP (Batalyon Teritorial Pembangunan)
    "batalyon", "batalyon teritorial pembangunan",
    # --- ARAHAN PANGLIMA (Trending Kasad) ---
    # 1. Rencana Cerai Anggota
    "cerai TNI", "cerai anggota", "perceraian TNI", "perceraian prajurit",
    "gugat cerai TNI", "cerai tentara", "cerai militer",
    # 2. Isu LGBT
    "LGBT TNI", "LGBT tentara", "LGBT militer", "gay TNI", "gay tentara",
    "LGBT prajurit",
    # 3. Pernikahan Mewah
    "pernikahan mewah TNI", "nikah mewah TNI", "pesta mewah TNI",
    "resepsi mewah tentara", "pernikahan mewah prajurit", "pesta pernikahan TNI",
    # 4. Medsos Keluarga
    "medsos TNI", "medsos istri TNI", "medsos keluarga TNI",
    "viral istri TNI", "viral keluarga TNI", "flexing TNI", "pamer TNI",
]

# Pencarian akan mengkombinasikan setiap kata kunci dengan setiap kab/kota
# Misal: "pupuk ilegal Bangkalan"

# Konfigurasi Crawling
GNEWS_LANGUAGE = 'id'
GNEWS_COUNTRY = 'ID'
GNEWS_PERIOD = '1d' # Perayapan awal dalam kurun waktu 1 hari terakhir
CRAWL_INTERVAL_SECONDS = 3600 # Waktu tunggu jika siklus sudah selesai (1 jam)
# Konfigurasi Network & DNS (v5.43)
USE_CLOUDFLARE_DNS = True # Menggunakan DoH (DNS-over-HTTPS) Cloudflare 1.1.1.1
# --- STEALTH MODE CONFIG (v5.51) ---
# Mode 'Lambat tapi Selamat' (Slow is Okay)
DELAY_BETWEEN_REQUESTS = 25 # Jeda dasar ditingkatkan demi keamanan absolut
STEALTH_JITTER = (20, 60)    # Jeda tambahan acak untuk tugas berat

USE_PROXY = False # Set True jika ingin menggunakan proxy manual di bawah
PROXY_SETTING = {
    "http": "http://user:pass@host:port",
    "https": "http://user:pass@host:port"
}

# --- GENIUS AUTO-PROXY HARVESTER (v5.43) ---
# Jika diaktifkan, sistem akan otomatis mencari proxy gratis jika terblokir.
USE_AUTO_HARVESTER = True 
# -------------------------------------------

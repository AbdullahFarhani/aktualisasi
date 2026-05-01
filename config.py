import os

# Konfigurasi HuggingFace Token (v5.65)
os.environ["HF_TOKEN"] = "REDACTED_HF_TOKEN"

# Konfigurasi Telegram
TELEGRAM_BOT_TOKEN = "REDACTED_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "REDACTED_TELEGRAM_CHAT_ID"

TELEGRAM_BOT_TOKEN_2 = "REDACTED_TELEGRAM_BOT_TOKEN_2"
TELEGRAM_CHAT_ID_2 = "REDACTED_TELEGRAM_CHAT_ID_2"

# API Key Google Gemini
GEMINI_API_KEY = "REDACTED_GEMINI_API_KEY"

# API Key OpenRouter (Gunakan Model Qwen / Llama Gratis)
OPENROUTER_API_KEY = "REDACTED_OPENROUTER_API_KEY"

# API Key Groq (30 RPM, 14.400 RPD - Super Cepat & Longgar)
GROQ_API_KEY = "REDACTED_GROQ_API_KEY"

# Daftar Model Groq untuk Rotasi (Menghindari 429)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
    "openai/gpt-oss-120b"
]

# Data Geografis
KABKOTA_AREAX = [
    "Kota A", "Kota B", "Kota C", "Kota D", "Kota E", "Kota F", 
    "Kota G", "Kota H", "Kota I", "Kota J", "Kota K", "Kota L", "Kota M", 
    "Kota N", "Kota O", "Kota P", "Kota Q", "Kota R", "Kota S", "Kota T", 
    "Kota U", "Kota V", "Kota W", "Kota X", "Kota Y", "Kota Z", 
    "Kota AA", "Kota AB", "Kota AC", "Kota AD", "Ibu Kota Area", "Area Operasional"
]

# Wilayah Perbatasan & Kota Besar yang WAJIB Ditolak (Luar Area Operasional) - v5.35
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
# HANYA untuk frasa yang PASTI 100% bukan Area Operasional dan TIDAK MUNGKIN muncul sbg cross-report
# (Mis: Jakarta Selatan bisa muncul di berita KPK tentang AreaX, jadi masuk REJECTED_REGIONS saja)
FORBIDDEN_KEYWORDS = [
    # Bali (tidak mungkin cross-report dengan AreaX secara lokasi)
    "Kuta Bali", "Badung Bali", "Kota ADriti",
    # DIY (sangat spesifik, tidak mungkin salah sangka)
    "Daerah Istimewa Yogyakarta", "Provinsi DIY",
    # Tokoh Nasional (Jika tanpa konteks AreaX yang kuat - v5.49)
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
# v5.89: Reguler Ancaman AreaX (Optimized to 19)
KATA_KUNCI = [
    "korupsi", "pungli", "gratifikasi", "sengketa", "narkoba", "sabu-sabu",
    "sampah", "KDRT", "aparat", 
    "pupuk ilegal", "rokok ilegal", "tambang",
    "kdkmp", "kopdes", "kmp", "spbu", "bbm"
]

# v6.92: Daftar Kata Kunci PRIORITAS (Sesuai arahan user terbaru)
PRIORITY_KATA_KUNCI = [
    "mbg",
    "koperasi merah putih",
    "batalyon yang bermasalah",
    "rencana cerai anggota tni",
    "isu tni lgbt",
    "pernikahan mewah tni",
    "tni bermasalah",
    "oknum tni",
    "demo",
    "aksi damai",
    "unjuk rasa",
    "konsolidasi",
    "program pemerintah yang tni terlibat di dalamnya"
]

# Pencarian akan mengkombinasikan setiap kata kunci dengan setiap kab/kota
# Misal: "pupuk ilegal Kota A"

# Konfigurasi Crawling
GNEWS_LANGUAGE = 'id'
GNEWS_COUNTRY = 'ID'
GNEWS_PERIOD = '1d' # Perayapan awal dalam kurun waktu 1 hari terakhir
CRAWL_INTERVAL_SECONDS = 1800 # Waktu tunggu jika siklus sudah selesai (30 menit)
# v6.50: GIGA-THROTTLE (Anti-Lama Edition)
USE_CLOUDFLARE_DNS = True 
DELAY_BETWEEN_REQUESTS = 15 # Jeda dasar diperlambat (15 detik) untuk hindari blokir
STEALTH_JITTER = (10, 45)    # Jeda tambahan (10-45 detik) - Meniru perilaku manusia

USE_PROXY = False # Dimatikan sesuai instruksi: Jaringan user stabil
PROXY_SETTING = {
    "http": None,
    "https": None
}

# --- GENIUS AUTO-PROXY HARVESTER (v5.43) ---
# Dimatikan sesuai instruksi: Jaringan user stabil
USE_AUTO_HARVESTER = False 

# --- ATOMIC SNIPER: PLAYWRIGHT (v5.94) ---
# Aktifkan browser headless untuk membongkar URL yang paling sulit.
# Sangat akurat tetapi memakan banyak RAM/CPU.
USE_PLAYWRIGHT = True 
# -------------------------------------------

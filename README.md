# Sistem Crawling dan Profiling Berita Otomatis

Proyek ini adalah sistem intelijen berita otomatis (Automated News Intelligence) yang dirancang untuk melakukan *crawling*, *scraping*, dan *profiling* secara terus-menerus terhadap berita-berita bersentimen negatif terkait stabilitas nasional, program pemerintah, dan institusi/aktor negara di wilayah Area Operasional.

Sistem ini didukung oleh **Google Gemini API** untuk memahami konteks bahasa Indonesia yang rumit dan menyarikan ancaman secara intelijen (termasuk merangkum 5W+1H, ekstraksi aktor, dan perburuan kontak/nomor telepon redaktur/laman portal).

## Fitur Utama
1. **Automated Keyword-Geo Search**: Melakukan kombinasi pencarian berbasis GNews terhadap setiap *keyword* ancaman pada setiap Kota/Kabupaten di Area Operasional (misal: "Pupuk Ilegal Kota J").
2. **Double-layer Scraping**: Mengambil teks artikel murni dan mencari halaman rahasia/kontak redaksi untuk ekstraksi alamat/nomor HP.
3. **AI Profiling**: AI menyaring berita apakah benar-benar merupakan *ancaman* stabilitas nasional (sentimen negatif) atau bukan (false positive). False positive akan dihiraukan.
4. **Instant Notification**: Berita positif-ancaman langsung dikemas rapi dalam format *brief* dan dikirimkan secara langsung ke Telegram Channel bot.
5. **Continuous Mode**: Program dirancang berjalan 24/7 dan mencatat (*caching*) memori berita yang sudah diproses agar tidak ada *spamming* ke channel telegram.

## Prasyarat
Sistem berjalan pada OS Linux/Mac/Windows dengan Python 3.8+.
1. Pastikan memiliki Telegram Bot Token dan API Key Gemini.
2. Edit `config.py` dan sesuaikan interval atau key jika ingin diganti.

## Instalasi
1. Clone direktori ini.
2. Install dependensi dengan:
```bash
pip install -r requirements.txt
```

## Cara Menjalankan
Buka Terminal/Command Prompt, arahkan ke direktori ini, lalu eksekusi:
```bash
python main.py
```
Sistem akan mulai berjalan terus-menerus dan mencetak log operasinya di layar terminal. History URL akan disimpan ke `processed_urls.json`.

## Struktur Modul
- `config.py` : Master data konfigurasi.
- `crawler.py` : Berkomunikasi dengan search engine GNews.
- `scraper.py` : Berkomunikasi dengan website asal, menarik teks, dan memburu kontak.
- `profiler.py` : Berkomunikasi dengan Gemini LLM untuk menganalisis isi *raw text* lalu diubah jadi data terstruktur.
- `notifier.py` : Pengirim pesan via cURL request ke API Telegram.
- `main.py` : Orkestrator dari awal ke akhir dalam *continuous loop*.

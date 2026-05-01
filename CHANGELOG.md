# CHANGELOG — Sistem Crawling & Profiling Berita Otomatis

Riwayat perubahan lengkap dari awal pengembangan hingga versi terkini.

---

## [v6.91] — 2026-04-30
### Human-Stealth Mode & Delay Jitter
- **Anti-Bot Jitter**: Memperlambat siklus crawling GNews secara signifikan untuk menghindari deteksi sistem otomatis Google ("We're sorry... automated queries").
- **Dynamic Jitter**: Menyesuaikan `DELAY_BETWEEN_REQUESTS` ke 15 detik dan `STEALTH_JITTER` antara 10-45 detik untuk mensimulasikan perilaku pencarian manusia.
- Peningkatan keamanan jaringan dari pemblokiran IP saat rotasi keyword.

---

## [v6.90] — 2026-04-30
### Proxy Removal & Network Stability
- **Direct Connection Override**: Mematikan secara total penggunaan proxy (`USE_PROXY = False`) dan auto-harvester (`USE_AUTO_HARVESTER = False`) karena jaringan lokal stabil.
- **Log Cleansing**: Memperbarui pesan log crawler dari "GNews Proxy Berhasil!" menjadi status asli "(Direct)" untuk menghindari kebingungan.

---

## [v6.89] — 2026-04-30
### Genius Sniper Patch & Error Handling
- **Critical Fix (NoneType Error)**: Memperbaiki *bug* variabel `sub_page_text` yang tidak terinisialisasi pada `scrape_contact_page` yang menyebabkan kegagalan deteksi kontak pada portal bersarang.
- **Tribun Network Special Sniper**: Menambahkan pola khusus untuk membedah halaman redaksi Tribun Network (khususnya subdomain seperti jatim.tribunnews.com) secara langsung dan akurat.
- Peningkatan sistem prioritas URL profil: Menambahkan bobot prioritas tertinggi untuk keyword "redaksi" dan "kontak" dibandingkan halaman profil lain.

---

## [v5.89] — 2026-04-28
### Full Requirement Alignment
- **Cycle Optimization**: Menyesuaikan `DELAY_BETWEEN_REQUESTS` (8s) dan `STEALTH_JITTER` (2-8s) untuk memastikan 50 kata kunci di 32 kota (1600 query) selesai dalam target 6 jam.
- **Strict Geofencing v5.89**: Mengaktifkan kembali aturan penolakan tokoh nasional dan proteksi terhadap alamat redaksi di footer untuk mencegah False Positive lokasi.
- **Expanded Threat Intelligence**: Menambahkan pola ancaman indisipliner, sanksi, dan pecat TNI ke dalam `POLA_ANCAMAN`.
- **Media Profiling Detail**: Memperketat instruksi AI untuk mengekstrak jajaran redaksi secara lengkap (bukan ringkasan singkat).

---

## [v5.88] — 2026-04-28
### Intelligence Profiling & Contact Genius
- **Enhanced Contact Scraping**: Meningkatkan agresivitas deteksi nomor telepon/WA dengan regex baru yang mencakup format lokal (08..., (021)...) dan capture otomatis link `wa.me`.
- **Smart Footer/Header Sniffing**: Membedah blok footer dan header secara spesifik untuk mencari informasi profiling laman (Nama Laman, Alamat, Redaksi, Kontak).
- **AI Profiling Prompt v5.88**: Restrukturisasi prompt AI untuk memaksa ekstraksi data media secara terstruktur (Nama Laman, Alamat, Redaksi, Kontak) dan memisahkannya dari aktor berita.
- **Threat Pattern Expansion**: Memperluas `POLA_ANCAMAN` mencakup isu cerai, lgbt, flexing, dan pamer mewah sesuai arahan pimpinan.
- **Telegram Template v5.88**: Memperbarui format notifikasi untuk menampilkan profiling media secara lengkap dan rapi.
- **Trusted Network Expansion**: Menambahkan jaringan media lokal Jatim (Radar & Tribun Jatim Timur) untuk akurasi profiling yang lebih tinggi.

---

## [v5.87] — 2026-04-28
### Syntax Fix & Sniper 50 Final
- **Syntax Repair**: Memperbaiki error tanda koma pada daftar kata kunci yang berpotensi menyebabkan program *crash*.
- **Final Optimization**: Mengunci jumlah kata kunci di angka **tepat 50** (19 Reguler + 31 Prioritas) untuk mengejar target satu siklus 6 jam.
- Menghapus redundansi: *penyuapan* (korupsi), *narkotika* (narkoba), dan *unjuk rasa* (demo).
- Penyederhanaan kategori Medsos dan Cerai sesuai arahan terbaru.

---

## [v5.86] — 2026-04-28
### Sniper 50 — 6-Hour Cycle Optimization
- **Optimalisasi Kata Kunci**: Mengurangi total kata kunci dari 75 menjadi **tepat 50 kata kunci** untuk mengejar target penyelesaian 1 siklus dalam 6 jam.
- **Reguler (15)**: Menghapus redundansi korupsi/gratifikasi dan isu broad seperti BBM/Fiktif.
- **Prioritas (35)**: Mempertahankan isu atensi pimpinan dengan diksi paling efektif (MBG, Koperasi, TNI, Yon TP, LGBT, Cerai, Medsos).
- Mempertahankan keyword wajib: **sampah, aksi damai, yon tp, TNI, kmp, TNI cerai**.

---

## [v5.85] — 2026-04-28
### Instant Sniper Decoder (Offline Resolving)
- **Zero-Request Resolving**: Memperbarui `decode_google_news_url_local` dengan teknik *Binary Stream Analysis* untuk membongkar URL Google News secara offline.
- Menghilangkan ketergantungan pada HTTP Redirect Google yang sering kali terkena blokir 429 atau Captcha.
- **Speed Optimization**: URL asli kini bisa didapatkan dalam hitungan milidetik tanpa perlu melakukan "lompatan" antar server.
- **Cleaner URL**: Otomatis membersihkan parameter tracking Google (`ved`, `usg`, dll) agar link yang dikirim ke Telegram lebih bersih dan profesional.

---

## [v5.84] — 2026-04-27
### Genius Intel Mode (Enhanced Sentiment)
- **Priority Bypass**: Jika berita menyinggung isu prioritas (Koperasi, TNI, MBG), sistem menonaktifkan fitur *Auto-Reject* kata positif agar masalah manajerial di balik berita hibah/bantuan tetap terdeteksi.
- **Expansion Pola Ancaman**: Menambahkan diksi krisis manajerial seperti: *bingung, tak punya kendali, terbengkalai, mubazir, sia-sia, tak beroperasi, mangkrak*.
- **Machine Learning Override**: Jika isu prioritas terdeteksi oleh Regex, sistem akan mengabaikan klasifikasi "Netral/Positif" dari AI (IndoRoBERTa) demi kewaspadaan intelijen yang lebih tinggi.
- Memperbaiki kegagalan deteksi pada kasus "Hibah Truk Koperasi Tuban" yang sebelumnya dianggap berita positif.

---

## [v5.83] — 2026-04-27
### Priority Sorting & Genius Re-Classification
- **Priority Sorting**: Memastikan isu prioritas (TNI, MBG, Yon TP, LGBT, dll) diproses dan dikirim ke Telegram **sebelum** sistem mulai mencari isu reguler.
- **Genius Re-Classification**: Jika berita di siklus reguler (misal keyword "aparat") ternyata menyinggung isu prioritas, sistem otomatis menaikkan statusnya ke Prioritas 1 agar dikirim lebih dulu.
- Menjamin isu-isu yang menjadi atensi pimpinan (Panglima/Kasad) selalu menjadi laporan pembuka di setiap siklus.

---

## [v5.82] — 2026-04-27
### Penyesuaian User: kdmp & TNI cerai
- Memasukkan kembali **"kdmp"** ke daftar Reguler.
- Menghapus "cerai TNI" dan memprioritaskan keyword **"TNI cerai"**.
- Total kata kunci tetap di angka **75**.

---

## [v5.81] — 2026-04-27
### Fokus Sniper "kmp" & "TNI cerai"
- Memasukkan kata kunci spesifik **"kmp"** (Koperasi Merah Putih) dan **"TNI cerai"** sesuai arahan.
- Menjaga total kata kunci tetap di **75** untuk performa optimal.
- **Reguler (21)**: +kmp, -kdmp.
- **Prioritas (54)**: +TNI cerai, -nikah mewah TNI.

---

## [v5.80] — 2026-04-27
### Penyesuaian Keyword Wajib
- Memasukkan kembali kata kunci wajib sesuai instruksi: **"sampah"**, **"aksi damai"**, **"yon tp"**, dan **"TNI"**.
- Menyeimbangkan total kata kunci tetap di **75** dengan menghapus varian yang sangat redundan.
- **Reguler (21)**: +sampah, +aksi damai, -kmp.
- **Prioritas (54)**: +TNI, +yon tp, -cerai militer, -LGBT prajurit, -pesta mewah TNI.

---

## [v5.79] — 2026-04-27
### Optimalisasi Kata Kunci (75 Sniper Mode)
- Melakukan perampingan kata kunci dari 84 menjadi **tepat 75 kata kunci** untuk efisiensi perayapan.
- **Reguler (20)**: Menghapus keyword terlalu luas seperti "sampah" dan "aksi damai".
- **Prioritas (55)**: Menghapus "TNI" (terlalu luas), "yon tp" (sudah ada Batalyon), serta menggabungkan varian LGBT dan Medsos yang redundan.
- Fokus lebih tajam pada isu sensitif sesuai arahan pimpinan dengan volume query yang lebih terkendali.

---

## [v5.78] — 2026-04-27
### Arahan Panglima via Asintel — Trending Kasad
- Menambahkan **4 kategori keyword prioritas baru** sesuai arahan pimpinan:
  1. **Rencana Cerai Anggota**: cerai TNI, perceraian TNI, perceraian prajurit, gugat cerai TNI, dll.
  2. **Isu LGBT**: LGBT TNI, LGBT tentara, LGBT militer, gay TNI, lesbian TNI, transgender TNI, dll.
  3. **Pernikahan Mewah**: pernikahan mewah TNI, nikah mewah TNI, pesta mewah TNI, resepsi mewah tentara, dll.
  4. **Medsos Keluarga**: medsos TNI, medsos istri TNI, viral keluarga TNI, flexing TNI, pamer TNI, dll.
- Menambahkan keyword **Yon TP**: yon tp, yon tugas perbantuan, yonif.
- Total keyword prioritas naik dari 27 → 46.

---

## [v5.77] — 2026-04-27
### Full Clean Text Profiling
- **BREAKING**: Menghapus sistem **Anchor Slicing** (batas 5000 karakter) pada profiling halaman redaksi/kontak.
- Profiling kini mengirim **seluruh teks bersih** (setelah decompose script/style/nav/header/footer/iframe/ins) ke AI tanpa potongan.
- Cross-Domain Fallback (Tribun, iNews) juga menggunakan Full Clean Text.
- Menghilangkan risiko data kontak (telepon/WA/email) terpotong karena berada di bagian bawah halaman.

---

## [v5.76] — 2026-04-27
### +6 Domain Profiling Baru
- Hardcode injection ditambahkan untuk domain:
  - `kediritangguh.co` → `/tentang-kami/`
  - `jurnaljatim.com` → `/redaksi/`, `/tentang-kami/`
  - `targetnews.id` → `/redaksi/`
  - `mediakampung.com` → `/redaksi/`, `/tentang-kami/`, `/kontak-kami/`
  - `penabicara.com` → `/about-us`, `/redaksi`, `/kontak`
  - `okezone.com` → `/about-us`, `/redaksi`
- Total domain hardcoded: **28+ jaringan media**.

---

## [v5.75] — 2026-04-26
### Jawapos SPA JSON Parser & Bing Final Validator
- **Jawapos SPA JSON Parser**: Mengekstrak data kontak (PHONE, FAX, EMAIL, WHATSAPP, ADDRESS) dari atribut `data-page` JSON pada halaman Jawapos Radar Network (SPA berbasis React/Vue).
- **Final URL Validator**: Menambahkan validasi akhir sebelum download konten — menolak URL mesin pencari (Bing/Google/Yahoo/DuckDuckGo/Yandex) yang bocor sebagai hasil resolve.
- **Kompas TV**: Ditambahkan hardcode injection ke `/about-us` dan `/contact-us`.
- **iNews Fallback**: Subdomain regional kini langsung fallback ke `www.inews.id/page/redaksi` karena subdomain tidak punya halaman profil sendiri.
- **Expanded Keywords** (50 kata kunci):
  - Prioritas (27): MBG, SPPG, keracunan, TNI, persit, kowad, anggota TNI, keluarga TNI, dll.
  - Reguler (23): KDRT, aparat, fiktif, modus, pupuk ilegal, rokok ilegal, BBM, SPBU, dll.
- **Cleanup GitHub**: Menghapus file tidak penting (generate_docx.py, generate_notula.py, generate_paparan.py, debug_pipe.py, scrape_redaksi.py).
- **.gitignore** diperbarui agar file test, backup, output, dan cache tidak ter-push.

---

## [v5.73] — 2026-04-25
### Intelligence Profiling Overhaul
- **Anchor Slicing**: Daya tangkap diperluas dari 2500 → 5000 karakter setelah keyword ditemukan.
- **Trigger words** ditambahkan: "struktur dalam media", "tentang tagar", "kabar surabaya", "box redaksi".
- **Full-Text Fallback**: Mengambil seluruh teks bersih (maks 5000 karakter) jika anchor match gagal, dengan syarat konten mengandung keyword redaksional.
- **Link visit limit**: Ditingkatkan dari 3 → 5 link per media.
- **Hardcode Injection** ditambahkan untuk 20+ jaringan media:
  - Kompas (inside.kompas.com), Espos/Solopos, iNews Regional, Madu TV, Tagar Jatim, Kabar Surabaya, BeritaSatu, BiozTV, Jawapos Radar, KlikJatim, Realita.co, Harian Bhirawa, Detik, Memorandum/Disway, BuserJatim, Tribunnews Regional, JPNN.
- **Cross-Domain Fallback Tribun**: Subdomain regional fallback ke `www.tribunnews.com/about/`.

---

## [v5.71] — 2026-04-25
### Sniper Mode Keywords
- Mempersempit kata kunci menjadi mode "Sniper" — hanya kata kunci yang benar-benar menghasilkan berita ancaman.
- KATA_KUNCI: 10 kata kunci inti (korupsi dana desa, pungli, penyuapan, dll).
- PRIORITY_KATA_KUNCI: 14 kata kunci prioritas (MBG, koperasi merah putih, jembatan, oknum TNI).
- **Search Engine Filter**: Validasi di `crawler.py` menolak URL Bing/Google/Yahoo/Yandex Search agar tidak masuk pipeline.

---

## [v5.65] — 2026-04-24
### HuggingFace Token Integration
- Menambahkan HuggingFace Token ke environment variable untuk mendukung model AI lokal.

---

## [v5.61] — 2026-04-23
### Silent Search Mode
- Mode `silent=True` pada pencarian mesin pencari agar tidak spam log saat gagal.

---

## [v5.59] — 2026-04-22
### Mobile-Identity Sniffer
- Menyamar sebagai iPhone/Android untuk memicu pengalihan asli via meta-refresh pada Google News URL.
- Mendukung sniffing via `<meta http-equiv="refresh">` di body HTML mobile.

---

## [v5.54] — 2026-04-22
### Anti-Bot Shield
- Deteksi dan bypass halaman anti-bot (Cloudflare challenge, captcha page) pada portal berita.

---

## [v5.53] — 2026-04-21
### Intelligence Summary & Logging Overhaul
- **Intelligence Summary**: Laporan ringkas status intelijen di akhir setiap siklus crawling.
- **Logging Global**: Meredam peringatan berisik dari HuggingFace & Symlinks.
- **Daily Reset**: Jika tanggal berubah, counter berita di-reset ke 0.

---

## [v5.50] — 2026-04-20
### Daily Reset Counter
- Counter berita otomatis reset setiap pergantian hari.

---

## [v5.48] — 2026-04-20
### Crawling Prioritas dengan Randomisasi
- Tahap 1: Crawling keyword prioritas dengan randomisasi urutan keyword awal.
- Menghindari pola crawling yang terlalu teratur (anti-detection).

---

## [v5.46] — 2026-04-19
### Stealth Mode & 429 Cooling System
- **Stealth Jitter**: Jeda acak (20–60 detik) di antara request untuk menghindari deteksi bot.
- **429 Cooling System**: Pendinginan agresif (120 detik) saat menerima HTTP 429 (Too Many Requests).
- **Tahap 2 Crawling Reguler**: Acak & bervariasi untuk mengurangi pola terdeteksi.
- Delay dasar antar-request ditingkatkan ke 25 detik.

---

## [v5.44] — 2026-04-18
### Multi-Engine Search & RPC Fallback
- **Mesin Pencari Global**: Menambahkan DuckDuckGo Lite sebagai cadangan pencarian.
- **RPC ID Fallback Strategy**: Strategi rotasi RPC ID untuk Google News decoder saat endpoint utama gagal.
- **Greedy Trust**: Jika URL mengandung domain hint atau jaringan Jatim, langsung diambil.

---

## [v5.43] — 2026-04-18
### DNS-over-HTTPS & Auto Proxy Harvester
- **Cloudflare DoH**: Menggunakan DNS-over-HTTPS via Cloudflare 1.1.1.1 untuk bypass ISP blocking.
- **Genius Auto-Proxy Harvester**: Otomatis mencari proxy gratis jika terblokir.
- **Dynamic Proxy Selection**: Rotasi proxy otomatis pada setiap percobaan.

---

## [v5.41] — 2026-04-17
### Heuristik URL Agresif
- Pencarian URL lebih agresif pada halaman redaksi (sniff http/https pattern di teks).

---

## [v5.40] — 2026-04-17
### Super-Keyword Check
- Prioritas utama pada keyword "susunan redaksi" di halaman profil.
- Batas panjang ditingkatkan untuk menampung daftar kontributor daerah yang sangat panjang.
- Keyword jajaran redaksi diperluas.

---

## [v5.39] — 2026-04-17
### Genius Sniffing Helper
- Sniff menggunakan helper Genius (mendukung Table, TR, List, dan CF Bypass) pada halaman redaksi.

---

## [v5.38] — 2026-04-17
### Prioritas Table & Address
- Prioritas scraping pada elemen `<table>` (susunan redaksi) dan `<address>` untuk data kontak.

---

## [v5.37] — 2026-04-16
### Anchor Non-Href Scanner & Filter Domain
- **Anchor Non-Href Scanner**: Menangkap pola "Editor: Nama" dalam tag `<a>` tanpa href (Promedia/iNews style).
- **Filter nama domain**: Mengabaikan nama domain yang terdeteksi sebagai nama orang (misal: "Jatimhariini.co.id").
- **Scan META Tag**: Deteksi `content_Editor` / `content_Author` (Promedia, IDN Times).
- **Direct Scan**: Pola "Laporan oleh" (SuaraSurabaya, Jawa Pos style).
- Cakupan scan diperluas — 20 elemen pertama + 40 terakhir.

---

## [v5.36] — 2026-04-16
### Genius Meta-Bar Scan
- Scan meta-bar diperluas untuk menangkap berbagai format portal Indonesia.
- Filter teks navigasi generik (bukan nama orang) pada link byline.

---

## [v5.32] — 2026-04-15
### Ekstraksi Absolut Heuristik Regex (Genius Mode)
- Regex heuristik untuk menangkap pola byline yang sangat bervariasi di portal Indonesia.

---

## [v5.31] — 2026-04-15
### AMP Bypass
- Coba AMP bypass untuk portal yang memblokir scraper pada URL normal.

---

## [v5.30] — 2026-04-15
### Anti-Noise Filter
- Pembersihan teks navigasi menu dari hasil scraping redaksi.

---

## [v5.28] — 2026-04-14
### Profiler Limit Increase
- Menaikkan limit teks redaksi di profiler karena kontak asli sering terdorong ke bawah oleh sidebar/berita lain.

---

## [v5.27] — 2026-04-14
### Dynamic WordPress Year Patterns
- Pola URL WordPress dinamis berdasarkan tahun berjalan untuk fallback pencarian halaman redaksi.

---

## [v5.21] — 2026-04-14
### Redaksi Slicing & Bugfix
- Fix crash pada argumen `session` yang tidak valid.
- Penyempurnaan anchor slicing awal.

---

## [v5.20] — 2026-04-14
### Strict Dropout
- Jika tidak ada informasi tanggal pada artikel, langsung tolak (strict dropout).
- Mencegah artikel usang masuk pipeline.

---

## [v5.19] — 2026-04-14
### Mobile Redirect Bypass & Hyper Resilience
- Special Handshake untuk Google News — redirect via jalur mobile lebih jarang diblokir.

---

## [v5.18] — 2026-04-14
### Sanitization & Error Detection
- Deteksi Malformed/Error 500 (khusus Yahoo).
- Penyaringan teks HTML sampah.

---

## [v5.17] — 2026-04-14
### Deep Link Discovery
- Mengekstrak URL asli dari meta tags (`og:url`, `canonical`, `twitter:url`).

---

## [v5.16] — 2026-04-14
### Inisialisasi Safety
- Inisialisasi variabel awal untuk mencegah `UnboundLocalError` pada alur fallback.

---

## [v5.15] — 2026-04-14
### DNS Stealth Mode
- Konfigurasi DNS stealth untuk menghindari pemantauan ISP.

---

## [v5.14] — 2026-04-14
### Penandaan Hiper-Jelas & Warning Label
- Label peringatan `⚠️ [TEKS ASLI TIDAK TERJANGKAU]` jika scraping gagal.
- Penandaan hiper-jelas untuk output AI dan user.

---

## [v5.13] — 2026-04-14
### Ekspansi Kata Kunci Paginasi
- Menambahkan lebih banyak keyword untuk mendeteksi halaman berpaginasi (next page, lanjutkan, selanjutnya, dll).
- State Cleansing untuk sesi scraping.

---

## [v5.12] — 2026-04-13
### Neighbor-Scan & VOI Intel
- **Neighbor-Scan**: Scan elemen tetangga untuk label kredensial (VOI style).
- Deteksi pola byline yang dipisah oleh tag HTML.

---

## [v5.11] — 2026-04-13
### Management Shield
- Deteksi Manajer/Pemred yang menyelinap di blok teks (Tag Hiper-Negatif).

---

## [v5.10] — 2026-04-13
### Scan Data Terstruktur (LD+JSON) — Prioritas Absolut
- Prioritas utama mengekstrak penulis dari `LD+JSON` schema (Schema.org `author`).
- Lebih akurat dari scan HTML karena data terstruktur langsung dari CMS.
- Filter: skip nama domain yang terdeteksi sebagai author.

---

## [v5.9] — 2026-04-13
### Ultra Geofence
- Geofence ultra-ketat untuk memastikan hanya berita Jawa Timur yang diproses.

---

## [v5.8] — 2026-04-13
### Master Byline & Bio Intelligence
- **Pola Inisial**: Deteksi `(hud/mar)` atau `(abc)` di akhir artikel — multiple initials support.
- **Heuristik Bio Penulis**: Deteksi bio penulis ala Tempo/Kompas/IDN.
- Filter link sampah (teks terlalu pendek/panjang).

---

## [v5.7] — 2026-04-13
### Bio Intelligence
- Deteksi bio penulis dari blok teks di bawah artikel.

---

## [v5.6] — 2026-04-13
### Hyper Precision & Pola Inisial
- Pola inisial reporter di akhir artikel (misal: `(abc/def)`).

---

## [v5.5] — 2026-04-13
### Geofence Filter
- Filter geografis untuk memastikan hanya berita dari Jawa Timur yang diproses.

---

## [v5.4] — 2026-04-13
### Full Content Download & Pagination
- Download konten penuh dengan dukungan paginasi (multi-page article).
- Pisahkan nama jika ada koma (misal: "Oleh: Latu, Antara").

---

## [v5.3] — 2026-04-13
### Precision Improvements
- Peningkatan akurasi deteksi byline di berbagai format portal Indonesia.

---

## [v5.2] — 2026-04-13
### Resilience Improvements
- Peningkatan ketahanan pada koneksi gagal dan timeout.

---

## [v5.0] — 2026-04-13
### Major Rewrite — Intelligence Engine
- Restrukturisasi besar-besaran arsitektur scraper.
- Pemisahan modul: crawler.py, scraper.py, profiler.py, notifier.py, config.py, main.py.
- Integrasi Groq LLM sebagai alternatif/rotasi dari Gemini.

---

## [v4.21] — 2026-04-10
### URL Cache System
- Penyimpanan URL yang sudah di-decode ke cache lokal (url_cache.json).
- Menghindari decode ulang Google News URL yang sama.

---

## [v4.20] — 2026-04-10
### Warm-Up Session
- Session warming sebelum mulai crawling untuk membangun cookie dan fingerprint browser.

---

## [v4.19] — 2026-04-10
### Mobile-First Sniffing & DOM Link Miner
- Sniffing menggunakan User-Agent mobile terlebih dahulu.
- DOM Link Miner: Mencari URL asli dari elemen `<a>` di halaman Google News.

---

## [v4.18] — 2026-04-10
### Maximum Trust Bonus
- Scoring system untuk URL yang ditemukan dari multiple sumber — bonus trust maksimal.

---

## [v4.17] — 2026-04-10
### Search Session & Dynamic Headers
- Menggunakan session persisten untuk pencarian.
- Rotasi User-Agent headers dinamis di setiap request.

---

## [v1.0 — v4.0] — 2026-04-08 s/d 2026-04-09
### Fondasi Sistem
- Versi awal sistem crawling berita otomatis.
- Integrasi Google News API via GNews.
- Scraping dasar konten berita.
- Integrasi Telegram Bot untuk notifikasi.
- Integrasi Gemini AI untuk analisis sentimen dan ekstraksi fakta.
- Geofencing dasar wilayah Jawa Timur.
- URL deduplication via processed_urls.json.

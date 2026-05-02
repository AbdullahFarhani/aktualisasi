import os
# v5.53: Matikan peringatan berisik dari HuggingFace & Symlinks
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import time
import threading
import queue
import random
import logging
import json
import os

# v5.53: Konfigurasi Logging Global (Strictly Intelligence)
logging.basicConfig(level=logging.ERROR, format='%(message)s')
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("transformers").setLevel(logging.CRITICAL)
logging.getLogger("huggingface_hub").setLevel(logging.CRITICAL)

from config import KATA_KUNCI, PRIORITY_KATA_KUNCI, KABKOTA_JATIM, CRAWL_INTERVAL_SECONDS, DELAY_BETWEEN_REQUESTS, STEALTH_JITTER, REJECTED_REGIONS, FORBIDDEN_KEYWORDS
from crawler import search_news, filter_new_articles, mark_as_processed, is_potensi_ancaman
from scraper import extract_article
from profiler import profilasi_berita
from notifier import kirim_notifikasi_telegram
from datetime import datetime

antrean_berita = queue.PriorityQueue()
priority_lock = threading.Lock()
task_counter = 0 
STATS_FILE = "priority_stats.json"

def get_priority_count():
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(STATS_FILE): return 0, today
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            # v5.50: Jika tanggal berbeda, reset count ke 0 (Daily Reset)
            if data.get("date") != today:
                return 0, today
            return data.get("count", 0), today
    except: return 0, today

def save_priority_count(count):
    today = datetime.now().strftime("%Y-%m-%d")
    with open(STATS_FILE, 'w') as f: 
        json.dump({"count": count, "date": today}, f)

priority_sent_count, _current_date = get_priority_count()
save_priority_count(priority_sent_count) # Inisialisasi file jika belum ada

import re

def is_actually_priority(judul, teks):
    """v5.56: Validasi konten menggunakan Regex (Word Boundaries) agar lebih akurat."""
    judul_str = str(judul) if judul else ""
    teks_str = str(teks) if teks else ""
    combined = (judul_str + " " + teks_str).lower()
    
    # Keyword yang harus dicek secara ketat (Anti-Typo/Substring)
    for p in PRIORITY_KATA_KUNCI:
        p_low = p.lower()
        # Gunakan word boundary jika keyword pendek (misal: mbg, tni)
        if len(p_low) <= 4:
            pattern = rf"\b{re.escape(p_low)}\b"
            if re.search(pattern, combined): return True
        else:
            if p_low in combined: return True
    return False

def is_wilayah_jatim_smart_guard(judul, teks):
    """
    v5.54: Filter berlapis untuk memastikan berita benar-benar terjadi di Jawa Timur.
    """
    judul_str = str(judul) if judul else ""
    teks_str = str(teks) if teks else ""
    gabungan = (judul_str + " " + teks_str).lower()
    judul_low = judul_str.lower()
    
    # LAYER 6 (v5.54): STRICT TITLE GEOFENCE — Jika judul menyebut wilayah luar Jatim
    for r in REJECTED_REGIONS:
        if r.lower() in judul_low:
            # Pengecualian jika di judul juga disebut kota Jatim (sangat jarang tapi mungkin)
            if not any(k.lower() in judul_low for k in KABKOTA_JATIM):
                print(f"  [-] GeoFence L6 (Title Location Match): '{r}' ditemukan di judul.")
                return False
    
    # LAYER 1: IMMEDIATE REJECT — Kata kunci terlarang absolut (Pasti Luar Jatim)
    for kw in FORBIDDEN_KEYWORDS:
        if kw.lower() in gabungan:
            print(f"  [-] GeoFence L1 (Forbidden): '{kw}' terdeteksi.")
            return False
    
    # LAYER 2: IMMEDIATE REJECT — Wilayah blacklist besar
    terdeteksi_luar = []
    for reg in REJECTED_REGIONS:
        if reg.lower() in gabungan:
            terdeteksi_luar.append(reg)
    
    if terdeteksi_luar:
        # LAYER 3: CROSS-REPORT CHECK — Ada kota Jatim juga? (misal: berita Jatim tentang MBG nasional)
        ada_kota_jatim = False
        for kota in KABKOTA_JATIM:
            if kota.lower() in gabungan:
                ada_kota_jatim = True
                break
        
        if not ada_kota_jatim:
            print(f"  [-] GeoFence L2 (Rejected Region): {terdeteksi_luar}, dan TIDAK ada kota Jatim.")
            return False
        
        # LAYER 5 (v5.49): SPECIFIC REJECT FOR NATIONAL HUB — Polda Metro, Mabes, Senayan
        national_hubs = ["polda metro jaya", "mabes polri", "senayan", "dpr ri", "jakarta pusat"]
        for hub in national_hubs:
            if hub in gabungan:
                # Jika ada Hub Nasional, kita butuh bukti Jatim yang SANGAT KUAT (misal: nama kota disebut di awal teks)
                if not any(kota.lower() in gabungan[:1000] for kota in KABKOTA_JATIM):
                    print(f"  [-] GeoFence L5 (National Hub Detected): '{hub}' terdeteksi tanpa bukti Jatim di awal artikel.")
                    return False
        
        # LAYER 4: DOMINANCE CHECK — Jika wilayah luar Jatim disebut lebih banyak daripada wilayah Jatim
        #          Cegah artikel yang "numpang sebut" nama kota Jatim saja di akhir artikel
        hits_luar = sum(gabungan.count(r.lower()) for r in terdeteksi_luar)
        hits_jatim = sum(gabungan.count(k.lower()) for k in KABKOTA_JATIM)
        
        if hits_luar > hits_jatim * 2:
            print(f"  [-] GeoFence L4 (Dominance): Hits Luar={hits_luar} vs Hits Jatim={hits_jatim}. Artikel didominasi wilayah luar.")
            return False
    
    return True

def process_artikel(artikel, keyword_asli, lokasi):
    """Memproses satu artikel (scraping, profiling, notifikasi)."""
    # 1. Scrape teks murni & Profil Media (v5.13: Scoping Ketat)
    hasil_scrape = None
    profil = None
    
    hasil_scrape = extract_article(artikel)
    
    # Jika gagal scrape, return false
    if hasil_scrape is None:
        return False
        
    time.sleep(DELAY_BETWEEN_REQUESTS) # Jeda untuk etika scraping
    
    # 1.1 Smart-Guard Filter (v5.9): Cegah halusinasi AI sebelum diproses
    if not is_wilayah_jatim_smart_guard(hasil_scrape['title'], hasil_scrape['text']):
        print(f"[-] Smart-Guard: Berita diabaikan otomatis (Lokasi non-Jatim terdeteksi): {hasil_scrape['title'][:50]}...")
        return False

    # 2. Intelijen Teks & Sentimen via Gemini AI
    print(f"[*] Melakukan AI Profiling terhadap: {hasil_scrape['title']}")
    profil = profilasi_berita(
        judul=hasil_scrape['title'],
        teks=hasil_scrape['text'],
        laman_redaksi=hasil_scrape['contact_text'],
        keyword=keyword_asli,
        lokasi=lokasi,
        aktor_metadata=hasil_scrape.get('actors', "")
    )
    
    if profil is None:
        print("[-] Profilasi gagal/error.")
        return False
        
    # 3. Filter berdasarkan kriteria ancaman / sentimen negatif dan Lokasi Jawa Timur
    is_threat = profil.get("is_negative_threat", False)
    is_jatim = profil.get("is_in_east_java", True)
    
    if not is_threat:
        print(f"[-] Bukan ancaman sentimen negatif murni: {hasil_scrape['title']}")
        return False
        
    if not is_jatim:
        print(f"[-] Berita diabaikan karena wilayah kejadian di luar Jawa Timur: {hasil_scrape['title']}")
        return False
        
    print(f"[!] Ditemukan BERITA ANCAMAN: {hasil_scrape['title']}")
    # 4. Kirim ke Telegram Channel Kodam
    aktor = profil.get("actors_involved", "Aktor tidak diketahui")
    kontak = profil.get("contact_and_address", "Kontak tidak diketahui")
    fakta = profil.get("fakta_5w1h", "Fakta gagal diekstrak")
        
    # v5.14: Tambahkan label peringatan jika scraping gagal
    judul_tampil = hasil_scrape['title']
    if "[SNIPPET_ONLY" in hasil_scrape['text']:
        judul_tampil = "⚠️ [TEKS ASLI TIDAK TERJANGKAU] " + judul_tampil
        
    global priority_sent_count
    
    is_priority_topic = is_actually_priority(hasil_scrape['title'], hasil_scrape['text'])
    if "Bot Verification" in judul_tampil or "TEKS ASLI TIDAK TERJANGKAU" in judul_tampil:
        is_priority_topic = False 
    
    dikirim = kirim_notifikasi_telegram(
        judul=judul_tampil,
        tautan=hasil_scrape['source_url'],
        laman=hasil_scrape['portal'],
        aktor=aktor,
        kontak=kontak,
        w5_h1=fakta
    )
    
    if dikirim and is_priority_topic:
        with priority_lock:
            priority_sent_count += 1
            save_priority_count(priority_sent_count)
            print(f"[+] Berita Prioritas Terkirim! (Total Harian: {priority_sent_count})")
            
    return dikirim

def worker_profiling(thread_id):
    """Pekerja yang menarik berita dari antrean dan memprosesnya secara paralel."""
    global task_counter
    while True:
        try:
            target = antrean_berita.get()
            if target is None: break
                
            priority_val, t_id, data = target
            artikel, keyword_asli, lokasi = data
            
            print(f"[Worker-{thread_id}] Memproses artikel (Priority: {priority_val}): {artikel.get('title', '')[:40]}...")
            process_artikel(artikel, keyword_asli, lokasi)
            
            jitter = random.randint(STEALTH_JITTER[0], STEALTH_JITTER[1])
            print(f"[*] Stealth Mode: Beristirahat {jitter} detik...")
            time.sleep(jitter)
            
        except Exception as e:
            print(f"[Worker-{thread_id}] Error fatal saat memproses: {e}")
        finally:
            if 'target' in locals() and target is not None:
                antrean_berita.task_done()

def producer_crawling():
    """Tugas utama mencari berita siang/malam di beranda Google, berjalan sendirian mempercepat loop."""
    while True:
        try:
            # v5.48: TAHAP 1 - CRAWLING PRIORITAS (Dengan Randomisasi Keyword Awal)
            print("[*] Memulai Siklus Prioritas (MBG, Koperasi, Jembatan, TNI)...")
            prio_loc = list(KABKOTA_JATIM)
            prio_kw = list(PRIORITY_KATA_KUNCI)
            random.shuffle(prio_loc)
            random.shuffle(prio_kw) # Acak urutan keyword prioritas
            
            # v6.51: FASE 1 - PENCARIAN AGREGAT JAWA TIMUR (INSTAN)
            print("[*] FASE 1: Memulai Pencarian Agregat Jawa Timur (Target: Kecepatan)...")
            for keyword in prio_kw:
                # Cari langsung dengan wilayah induk "Jawa Timur" untuk hasil cepat
                artikel_baru = search_news(keyword, "Jawa Timur")
                artikel_belum_diproses = filter_new_articles(artikel_baru)
                if not artikel_belum_diproses: continue
                
                for artikel in artikel_belum_diproses:
                    mark_as_processed(artikel.get('url'))
                    if is_potensi_ancaman(artikel.get('title', ''), artikel.get('description', ''), strict_mode=True):
                        global task_counter
                        task_counter += 1
                        antrean_berita.put((1, task_counter, (artikel, keyword, "Jawa Timur")))
                        print(f"[!] PRIORITAS DITEMUKAN (AGREGAT): '{artikel.get('title','')[:30]}' -> Antrean 1")
                
                # v6.91: Jeda antar query diperlambat signifikan (Anti-Bot)
                from config import DELAY_BETWEEN_REQUESTS, STEALTH_JITTER
                time.sleep(DELAY_BETWEEN_REQUESTS + random.randint(STEALTH_JITTER[0], STEALTH_JITTER[1]))

            # v6.51: FASE 2 - PENCARIAN GRANULAR KAB/KOTA (DEEP SCAN)
            print("[*] FASE 2: Memulai Pencarian Granular Kab/Kota (Target: Kedalaman)...")
            for keyword in prio_kw:
                for lokasi in prio_loc:
                    artikel_baru = search_news(keyword, lokasi)
                    artikel_belum_diproses = filter_new_articles(artikel_baru)
                    if not artikel_belum_diproses: continue
                    
                    for artikel in artikel_belum_diproses:
                        mark_as_processed(artikel.get('url'))
                        if is_potensi_ancaman(artikel.get('title', ''), artikel.get('description', ''), strict_mode=True):
                            task_counter += 1
                            antrean_berita.put((1, task_counter, (artikel, keyword, lokasi)))
                            print(f"[!] PRIORITAS DITEMUKAN (GRANULAR): '{artikel.get('title','')[:30]}' -> Antrean 1")
                    
                    # v6.91: Jeda antar query diperlambat signifikan atas permintaan (Anti-Bot)
                    from config import DELAY_BETWEEN_REQUESTS, STEALTH_JITTER
                    time.sleep(DELAY_BETWEEN_REQUESTS + random.randint(STEALTH_JITTER[0], STEALTH_JITTER[1]))
            
            # [PENTING] TUNGGU SEMUA BERITA PRIORITAS SELESAI DIKIRIM SEBELUM LANJUT KE REGULER
            if not antrean_berita.empty():
                print(f"\n[*] TAHAP 1 (PRIORITAS) SELESAI. Memproses {antrean_berita.qsize()} berita utama...")
                antrean_berita.join()
                print("[*] Seluruh Berita Prioritas telah terkirim ke Telegram. Berlanjut ke isu reguler...\n")

            # v5.46: TAHAP 2 - CRAWLING REGULER (DIPROSES AKHIR)
            print("[*] Memulai Siklus Reguler (Sampah, Narkoba, KDRT, dll)...")
            kw_random = list(KATA_KUNCI)
            loc_random = list(KABKOTA_JATIM)
            random.shuffle(kw_random)
            random.shuffle(loc_random)
            
            for keyword in kw_random:
                # Lewati jika sudah ada di prioritas agar tidak double-hit
                if keyword.lower() in [pk.lower() for pk in PRIORITY_KATA_KUNCI]: continue
                
                for lokasi in loc_random:
                    artikel_baru = search_news(keyword, lokasi)
                    artikel_belum_diproses = filter_new_articles(artikel_baru)
                    if not artikel_belum_diproses: continue
                        
                    for artikel in artikel_belum_diproses:
                        mark_as_processed(artikel.get('url'))
                        if is_potensi_ancaman(artikel.get('title', ''), artikel.get('description', ''), strict_mode=True):
                            # v5.83: Genius Re-Classification
                            # Jika di siklus reguler ditemukan keyword prioritas, naikkan ke Antrean 1
                            if is_actually_priority(artikel.get('title', ''), artikel.get('description', '')):
                                p_val = 1
                                p_label = "RE-CLASSIFIED PRIORITY"
                            else:
                                p_val = 5 # Tetap di antrean akhir
                                p_label = "REGULER (DIKIRIM AKHIR)"
                                
                            task_counter += 1
                            antrean_berita.put((p_val, task_counter, (artikel, keyword, lokasi)))
                            print(f"[*] {p_label}: '{artikel.get('title','')[:30]}' -> Antrean {p_val}")
                    
                    time.sleep(random.randint(3, 8))
                        
            print(f"\n[!] Semua kombinasi keyword telah dicari.")
            if not antrean_berita.empty():
                print(f"[*] Menunggu seluruh antrean ({antrean_berita.qsize()} berita) diselesaikan oleh Profiler AI secara berurutan...")
                antrean_berita.join() # Sistem akan berhenti di fase ini menjeda siklus
            
            # v5.53: Intelligence Summary - Laporan ringkas status intelijen
            print("\n" + "="*50)
            print(f" INTELLIGENCE SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
            print("="*50)
            print(f" [+] Laporan Prioritas Terkirim : {priority_sent_count} (Harian)")
            print(f" [+] Sisa Antrean Berita        : {antrean_berita.qsize()}")
            print("="*50 + "\n")
            
            print(f"[!] Seluruh proses siklus telah tuntas! Crawler beristirahat {CRAWL_INTERVAL_SECONDS} detik sebelum siklus ke-2...\n")
            time.sleep(CRAWL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[!] Error fatal pada crawler: {e}")
            time.sleep(60)

def run_sistem():
    print("\033[94m" + "="*58)
    print(" SISTEM CRAWLING BERITA KODAM V/BRAWIJAYA (v7.25 GENIUS) ")
    print("       PARALLEL GIGA-INTEL SURGICAL SNIPER               ")
    print("="*58 + "\033[0m")
    
    # Menghidupkan 1 Pekerja Konsumen/Profiler (Groq API: 30 RPM, super cepat!)
    num_workers = 1
    threads = []
    for i in range(num_workers):
        t = threading.Thread(target=worker_profiling, args=(i+1,), daemon=True)
        t.start()
        threads.append(t)
        
    # Menjalankan Produsen Crawler di Teras Utama (berjalan tanpa henti)
    try:
        producer_crawling()
    except KeyboardInterrupt:
        print("\nSistem dihentikan pengguna.")
        
if __name__ == "__main__":
    run_sistem()

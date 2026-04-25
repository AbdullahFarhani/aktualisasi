import json
import time
import re
from openai import OpenAI
from config import GROQ_API_KEY, GROQ_MODELS, REJECTED_REGIONS

# Global index untuk rotasi model
current_model_index = 0

def profilasi_berita(judul, teks, laman_redaksi, keyword, lokasi):
    """
    Menggunakan Groq API dengan sistem Rotasi Model untuk mengekstrak 5W+1H, 
    aktor yang terlibat, dan menentukan sentimen negatif/ancaman.
    """
    global current_model_index
    import uuid
    request_id = str(uuid.uuid4())[:8] # ID unik untuk mencegah context leakage
    
    # Batasan untuk menjaga Groq Tokens Per Minute (TPM)
    teks_terpotong = teks[:7000] if len(teks) > 7000 else teks
    # v5.28: Naikkan limit redaksi karena sering tercampur news/sidebar yang mendorong kontak asli ke bawah
    redaksi_terpotong = laman_redaksi[:8000] if len(laman_redaksi) > 8000 else laman_redaksi
    
    prompt = f"""Kamu adalah analis intelijen ancaman strategis. (RequestID: {request_id})
    
PERINTAH ZERO-STATE:
1. LUPAKAN seluruh data jurnalis, portal, atau aktor dari berita-berita yang pernah kamu analisis sebelumnya. (PENGECUALIAN: JANGAN gunakan nama tim/jurnalis portal VOI untuk berita JPNN atau MetroTV).
2. FOKUS HANYA pada data yang disediakan di bawah ini.
3. JANGAN PERNAH MENULIS PLACEHOLDER seperti [Nama], [Tanggal], atau [Lokasi].
4. INTEGRITAS SNIPPET (v5.14): Jika teks diawali '[SNIPPET_ONLY]', JANGAN mencoba mengarang detail. Akui keberadaan keterbatasan informasi pada field fakta.
5. JIKA DATA TIDAK DITEMUKAN, tulis 'Informasi Nihil' atau 'Tidak Disebutkan'.

Berikut adalah data artikel hasil mesin perayap:
Kata Kunci Pencarian Awal: '{keyword}' (JANGAN TERKECOH! JIKA ISI BERITA TIDAK RELEVAN DENGAN KATA KUNCI INI MAUPUN LOKASINYA, ABAIKAN KATA KUNCI INI).

JUDUL BERITA: {judul}
==== ISI BERITA ====
{teks_terpotong}
==== INFORMASI HALAMAN KONTAK ====
{redaksi_terpotong}
================================

TUGASMU:
1. FILTER WILAYAH (V5.49 ULTRA-STRICT GEOFENCE):
   - LANGKAH 1 — CARI BUKTI POSITIF: Apakah ada nama Kabupaten/Kota Jawa Timur yang disebutkan sebagai LOKASI KEJADIAN?
   - LANGKAH 2 — ABAIKAN ALAMAT PORTAL (KRITIS!): JANGAN PERNAH menggunakan informasi dari 'INFORMASI HALAMAN KONTAK' atau footer berita (seperti alamat redaksi di Malang/Surabaya) untuk menentukan 'is_in_east_java'. Lokasi harus ada di dalam narasi BERITA UTAMA.
   - LANGKAH 3 — TOLAK JIKA TERBUKTI LUAR JATIM: 'is_in_east_java' HARUS False jika kejadian di: {', '.join(REJECTED_REGIONS[:25])}...
   - ATURAN TOKOH NASIONAL (v5.49): Jika berita membahas tokoh nasional (Uya Kuya, Pejabat Pusat, Artis Jakarta) dan dilaporkan ke Polda Metro Jaya, Mabes Polri, atau DPR RI, maka itu adalah BERITA NASIONAL. Set 'is_in_east_java' = false meskipun dimuat oleh media Jawa Timur.
   - ATURAN BUKU HITAM:
     * 'Gunungkidul', 'Sleman', 'Bantul', 'Kulon Progo' = DIY/YOGYAKARTA (Reject!)
     * 'Cakung', 'Senayan', 'Kebayoran', 'Setiabudi', 'Polda Metro Jaya' = JAKARTA (Reject!)
     * 'Kartasura', 'Sukoharjo', 'Boyolali', 'Klaten', 'Solo', 'Semarang' = JAWA TENGAH (Reject!)
   - ZERO-TRUST RULE: Jika tidak ada bukti eksplisit bahwa insiden fisik/kriminal terjadi di wilayah hukum Jawa Timur, set 'is_in_east_java' = false.
   - JIKA BUKAN JAWA TIMUR, MAKA 'is_in_east_java' = false DAN 'is_negative_threat' = false.
2. TENTUKAN SENTIMEN: Hanya jika lokasi di Jawa Timur, evaluasi apakah ini ANCAMAN/NEGATIF (misal: korupsi, kriminalitas, isu sosial). Jika Prestasi/Positif/Netral, 'is_negative_threat' = false.
3. EKSTRAK AKTOR & TIM PRODUKSI (V5.12 HUMAN-FIRST):
   - AKTOR UTAMA: Tokoh dalam peristiwa (Tersangka, Korban, Saksi, dsb).
   - TIM PRODUKSI (MAKSIMAL 3 NAMA): Fokus pada jurnalis lapangan. PRIORITAS TERTINGGI: Nama manusia jurnalis (misal: Muhammad Farid A.) yang berlabel 'Reporter' atau 'Wartawan'. 
   - HINDARI NAMA GENERIK: Gunakan nama tim generik (misal: Tim VOI) hanya jika TIDAK ADA nama manusia jurnalis yang terdeteksi.
   - JANGAN gunakan nama tim/jurnalis dari portal lain (misal: Tim VOI tidak boleh muncul di berita JPNN).
   > [!CAUTION]
> JANGAN PERNAH menyertakan manajemen dari [MANAJEMEN REDAKSI] atau [PROFIL REDAKSI PORTAL] ke dalam 'actors_involved'. 
> Mereka BUKAN pelaksana berita. Masukkan jajaran Pemred, Alamat, dan Kontak ke field 'contact_and_address' secara detail.
4. RANGKUM FAKTA: 2-3 paragraf narasi cerdas. Masukkan detail jajaran manajemen portal secara lengkap pada field 'contact_and_address' agar data aktor berita tetap bersih dan akurat.

KEMBALIKAN JSON:
{{
    "is_negative_threat": true/false,
    "is_in_east_java": true/false,
    "actors_involved": "Nama Tokoh (Peran), Nama (Reporter), Nama (Editor)... (Maksimal 3 Jurnalis!)",
    "contact_and_address": "Struktur Redaksi & Jajaran Manajemen Portal (MENGANDUNG ALAMAT, EMAIL, DAN TELP/WA PORTAL SECARA LENGKAP!)",
    "fakta_5w1h": "Narasi 5W1H"
}}
"""
    # Pilih model saat ini dari daftar rotasi
    active_model = GROQ_MODELS[current_model_index]
    max_retries = len(GROQ_MODELS) * 2
    
    for attempt in range(max_retries):
        try:
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=GROQ_API_KEY,
                max_retries=0
            )
            
            print(f"[*] Menggunakan model: {active_model} (Percobaan {attempt+1})")
            
            response = client.chat.completions.create(
                model=active_model,
                messages=[
                    {"role": "system", "content": "You are a threat intelligence analyst returning data in strict JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            output_text = response.choices[0].message.content
            if output_text is None:
                raise ValueError("Response dari Groq kosong.")
            
            # Bersihkan dan parsing JSON
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                output_text = json_match.group(0)
            
            hasil_json = json.loads(output_text)
            return hasil_json
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                # ROTASI MODEL: Pindah ke model berikutnya dalam daftar
                print(f"[-] Model {active_model} terkena limit (429).")
                current_model_index = (current_model_index + 1) % len(GROQ_MODELS)
                active_model = GROQ_MODELS[current_model_index]
                
                print(f"[!] Berpindah ke model berikutnya: {active_model}...")
                time.sleep(2) # Jeda singkat etiket API
            elif "413" in error_msg or "too large" in error_msg.lower():
                print(f"[-] Teks terlalu besar. Memotong dan mencoba ulang...")
                teks_terpotong = teks_terpotong[:2000]
                time.sleep(2)
            else:
                print(f"[-] Kesalahan Profiling Groq API: {e}")
                return None
    
    print("[-] Gagal melakukan profiling setelah mencoba strategi rotasi model.")
    return None

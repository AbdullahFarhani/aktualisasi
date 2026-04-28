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
    redaksi_terpotong = laman_redaksi[:8000] if len(laman_redaksi) > 8000 else laman_redaksi
    
    prompt = f"""Kamu adalah analis intelijen ancaman strategis tingkat tinggi. (RequestID: {request_id})
    
PERINTAH KRITIS (ZERO-TRUST):
1. LUPAKAN seluruh data jurnalis, portal, atau aktor dari berita-berita sebelumnya.
2. JANGAN PERNAH MENULIS PLACEHOLDER seperti [Nama], [Tanggal], dsb.
3. JIKA DATA TIDAK DITEMUKAN, tulis 'Informasi Nihil'.
4. EKSTRAKSI KONTAK (WAJIB): Cari nomor telepon, nomor WhatsApp, email, dan alamat fisik dari 'INFORMASI HALAMAN KONTAK'. UTAMAKAN NOMOR WHATSAPP/TELEPON!

Berikut adalah data hasil perayapan:
JUDUL BERITA: {judul}
==== ISI BERITA UTAMA ====
{teks_terpotong}
==== INFORMASI HALAMAN KONTAK & REDAKSI PORTAL ====
{redaksi_terpotong}
================================

TUGAS ANALISIS:
1. FILTER WILAYAH JAWA TIMUR (STRICT GEOFENCE):
   - Pastikan insiden fisik/kriminal terjadi di Jawa Timur. 
   - JANGAN PERNAH gunakan alamat redaksi di footer untuk menentukan lokasi.
   - JIKA BERITA NASIONAL (Pejabat Pusat/Artis Jakarta) dilaporkan di Jakarta/Polda Metro, set 'is_in_east_java' = false.
   - Jika lokasi tidak eksplisit di Jatim, set 'is_in_east_java' = false.
2. SENTIMEN NEGATIF: Tentukan apakah berita ini mengandung isu negatif/ancaman (korupsi, kriminal, KDKMP bermasalah, TNI bermasalah, mbg keracunan, isu internal TNI, dsb).
3. EKSTRAKSI PROFILING LAMAN (UTAMA):
   - Ambil Nama Laman, Alamat, Jajaran Redaksi (Detail: Pemred, Editor, Manajemen), dan KONTAK (WA/Telp/Email).
   - JANGAN masukkan jajaran redaksi/manajemen ke dalam field 'actors_involved'.
4. EKSTRAKSI AKTOR BERITA: Tokoh naratif (Tersangka, Korban, Reporter, Editor).

KEMBALIKAN JSON DENGAN STRUKTUR BERIKUT:
{{
    "is_negative_threat": true/false,
    "is_in_east_java": true/false,
    "actors_involved": "Nama Tokoh (Peran), Nama (Reporter), Nama (Editor)",
    "contact_and_address": {{
        "nama_laman": "Nama Media",
        "alamat": "Alamat Lengkap",
        "redaksi": "Jajaran Redaksi/Manajemen Lengkap",
        "kontak": "Nomor WA/Telepon (WAJIB!), Email, dsb",
        "info_lain": "Informasi tambahan lainnya"
    }},
    "fakta_5w1h": "Narasi Fakta Berita (2-3 Paragraf)"
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

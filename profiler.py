import json
import time
import re
from openai import OpenAI
from config import GROQ_API_KEY, GROQ_MODELS, REJECTED_REGIONS

# Global index untuk rotasi model
current_model_index = 0

def profilasi_berita(judul, teks, laman_redaksi, keyword, lokasi, aktor_metadata=""):
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
    
    # PERINTAH KRITIS (ZERO-TRUST):
    1. LUPAKAN seluruh data jurnalis, portal, atau aktor dari berita-berita sebelumnya.
    2. JANGAN PERNAH MENULIS PLACEHOLDER seperti [Nama], [Tanggal], atau angka palsu seperti 081..., 021...
    3. JANGAN PERNAH menulis kata 'Informasi Nihil', 'Tidak ditemukan', 'Unknown', dsb.
    4. JIKA DATA TIDAK DITEMUKAN PADA KUNCI TERTENTU, KOSONGKAN SAJA NILAINYA (empty string "").
    5. EKSTRAKSI KONTAK (SANGAT PENTING): 
       - HANYA ambil nomor WhatsApp/Telepon AKTUAL (Contoh: 081..., +62..., 021...).
       - JANGAN PERNAH mengarang nomor telepon atau menggunakan pola 081.../021... jika data tidak ada.
       - JANGAN PERNAH mengambil link WhatsApp Channel atau link Share.
    
    # DATA HASIL PERAYAPAN:
    JUDUL BERITA: {judul}
    
    # METADATA AKTOR (HASIL SNIFFER):
    {aktor_metadata}
    
    # ISI BERITA UTAMA:
    {teks_terpotong}
    
    # INFORMASI HALAMAN KONTAK & REDAKSI PORTAL:
    {redaksi_terpotong}
    
    # TUGAS ANALISIS INTELIJEN (v6.92):
    1. STRICT GEOFENCE JAWA TIMUR: Fokus kejadian fisik di AreaX. Abaikan olahraga, gosip, dan hiburan.
    2. SENTIMEN NEGATIF & ANCAMAN: Deteksi narasi negatif pada prioritas: mbg, koperasi merah putih, batalyon bermasalah, cerai anggota tni, lgbt tni, nikah mewah tni, tni bermasalah, oknum tni, demo, aksi damai, unjuk rasa, konsolidasi, program pemerintah dengan tni.
    3. PROFILING LAMAN (GENIUS SCAN - CARI SAMPAI DAPAT):
       - Halaman seperti "redaksi", "kontak", "tentang kami", footer, header, dan body laman harus dicari teliti.
       - Kontak Laman: NOMOR TELEPON ATAU NOMOR WA (WAJIB UTAMAKAN MENDAPATKAN NOMOR TELEPON ATAUPUN NOMOR WA). Ekstrak dari teks secara teliti.
    4. IDENTIFIKASI AKTOR: Pisahkan Aktor Berita vs Kru Media.
    
    KEMBALIKAN JSON (STRICT FORMAT):
    {{
        "is_negative_threat": true/false,
        "is_in_east_java": true/false,
        "actors_involved": "Nama Tokoh (Peran), Nama (Reporter), Nama (Editor)",
        "contact_and_address": {{
            "nama_laman": "Isi dengan Nama Laman",
            "alamat_laman": "Isi dengan Alamat Laman",
            "jajaran_redaksi_laman": "Isi dengan Jajaran Redaksi",
            "kontak_laman": "Isi dengan Nomor Telepon: [No], Nomor WA: [No], Email: [Email]. UTAMAKAN NOMOR WA/TELEPON!",
            "informasi_profiling_laman_lainnya": "Isi dengan Informasi Profiling Lainnya"
        }},
        "fakta_5w1h": "Analisis fakta mendalam (2-3 Paragraf)"
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

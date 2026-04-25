import requests
import datetime
import urllib.parse
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID_2


def kirim_notifikasi_telegram(judul, tautan, laman, aktor, kontak, w5_h1):
    """
    Mengirimkan pesan hasil intelijen berita ke Telegram sesuai format.
    """
    # Format pesan sesuai permintaan user (v5.55: Dict-to-Text Formatter)
    pesan = f"<b>{judul}</b>\n"
    pesan += f"Sumber : {tautan}\n"
    
    # [Aktor-aktor atau tokoh-tokoh]
    aktor_str = str(aktor) if aktor else ""
    if len(aktor_str) > 3 and not any(x in aktor_str.lower() for x in ['tidak', 'kosong', 'unknown', 'unavailable']):
        pesan += f"{aktor_str}\n\n"
    else:
        pesan += "\n"
    
    # [Profiling laman] - v5.55: Konversi Dict ke Teks Indah
    if isinstance(kontak, dict):
        kontak_beauty = []
        if 'nama_perusahaan' in kontak: kontak_beauty.append(f"Perusahaan: {kontak['nama_perusahaan']}")
        if 'alamat' in kontak: kontak_beauty.append(f"Alamat: {kontak['alamat']}")
        if 'kontak' in kontak: kontak_beauty.append(f"Kontak/WA: {kontak['kontak']}")
        if 'email' in kontak: kontak_beauty.append(f"Email: {kontak['email']}")
        if 'struktur_redaksi' in kontak:
            red = kontak['struktur_redaksi']
            if isinstance(red, dict):
                red_info = ", ".join([f"{k.replace('_',' ').title()}: {v}" for k,v in red.items() if v])
                kontak_beauty.append(f"Redaksi: {red_info}")
        kontak_str = "\n".join(kontak_beauty)
    else:
        kontak_str = str(kontak) if kontak else ""

    if len(kontak_str) > 3 and not any(x in kontak_str.lower() for x in ["tidak", "kosong", "unavailable"]):
        pesan += f"{kontak_str}\n\n"
        
    pesan += f"<b>Fakta-Fakta</b>\n{w5_h1}"
    
    url1 = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    url2 = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_2}/sendMessage"
    
    payload1 = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "HTML"
    }
    
    payload2 = {
        "chat_id": TELEGRAM_CHAT_ID_2,
        "text": pesan,
        "parse_mode": "HTML"
    }
    
    dikirim = False
    try:
        response1 = requests.post(url1, json=payload1, timeout=15)
        if response1.status_code == 200:
            print(f"[+] Berhasil mengirim ke Telegram (Bot 1): {judul}")
            dikirim = True
        else:
            print(f"[-] Error Bot 1 ({response1.status_code}): {response1.text}")
            
        try:
            response2 = requests.post(url2, json=payload2, timeout=15)
            if response2.status_code == 200:
                print(f"[+] Berhasil mengirim ke Telegram (Bot 2): {judul}")
                dikirim = True
            else:
                print(f"[-] Error Bot 2 ({response2.status_code}): {response2.text}")
        except Exception as e2:
            print(f"[-] Gagal akses Bot 2: {e2}")

        if dikirim:
            
            # Simpan log ke arsip lokal berdasarkan tanggal
            tanggal = datetime.datetime.now().strftime("%d-%m-%Y")
            nama_file = f"berita_negatif_{tanggal}.txt"
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            try:
                with open(nama_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{tanggal} {timestamp}] Notifikasi Terkirim:\n")
                    # Pesan sudah include tag HTML, kita bisa sanitize atau simpan as is
                    f.write(pesan.replace('<b>', '').replace('</b>', '') + "\n")
                    f.write("-" * 80 + "\n\n")
            except Exception as e_file:
                print(f"[-] Gagal menulis ke arsip {nama_file}: {e_file}")
                
            return True
        else:
            print(f"[-] Telegram Error ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[-] Gagal akses API Telegram: {e}")
        return False

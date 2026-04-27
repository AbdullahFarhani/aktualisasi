import requests
import datetime
import urllib.parse
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID_2


def kirim_notifikasi_telegram(judul, tautan, laman, aktor, kontak, w5_h1):
    """
    Mengirimkan pesan hasil intelijen berita ke Telegram sesuai format v5.88.
    Format ini dioptimalkan untuk Profiling Laman (Nama, Alamat, Redaksi, Kontak).
    """
    # 1. Judul & Sumber
    pesan = f"<b>{judul}</b>\n"
    pesan += f"Sumber : {tautan}\n"
    
    # 2. Aktor Berita (Tokoh/Reporter/Editor)
    aktor_str = str(aktor) if aktor else "Informasi Nihil"
    pesan += f"{aktor_str}\n\n"
    
    # 3. Profiling Laman (v5.88: Strict Structured Formatting)
    if isinstance(kontak, dict):
        p_nama = kontak.get('nama_laman', laman or 'Informasi Nihil')
        p_alamat = kontak.get('alamat', 'Informasi Nihil')
        p_redaksi = kontak.get('redaksi', 'Informasi Nihil')
        p_kontak = kontak.get('kontak', 'Informasi Nihil')
        p_lain = kontak.get('info_lain', '')

        pesan += f"Nama Laman: {p_nama}\n"
        pesan += f"Alamat: {p_alamat}\n"
        pesan += f"Redaksi: {p_redaksi}\n"
        pesan += f"Kontak: {p_kontak}\n"
        if p_lain and p_lain.lower() != 'informasi nihil':
            pesan += f"Info Lain: {p_lain}\n"
    else:
        # Fallback jika AI mengembalikan string
        pesan += f"{kontak if kontak else 'Informasi Profiling Nihil'}\n"
    
    pesan += "\n"
    
    # 4. Fakta 5W+1H
    pesan += f"<b>Fakta-Fakta</b>\n{w5_h1}"
    
    # Telegram Multi-Bot Dispatch
    targets = [
        (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID),
        (TELEGRAM_BOT_TOKEN_2, TELEGRAM_CHAT_ID_2)
    ]
    
    dikirim_apapun = False
    for token, chat_id in targets:
        if not token or not chat_id: continue
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": pesan,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                dikirim_apapun = True
        except: pass

    if dikirim_apapun:
        print(f"[+] Berhasil mengirim notifikasi v5.88: {judul[:50]}...")
        # Simpan log ke arsip lokal
        tanggal = datetime.datetime.now().strftime("%d-%m-%Y")
        nama_file = f"berita_negatif_{tanggal}.txt"
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            with open(nama_file, 'a', encoding='utf-8') as f:
                f.write(f"[{tanggal} {timestamp}] Notifikasi v5.88:\n")
                f.write(pesan.replace('<b>', '').replace('</b>', '') + "\n")
                f.write("-" * 80 + "\n\n")
        except: pass
        return True
    
    return False

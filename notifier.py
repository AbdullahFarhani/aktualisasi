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
    if aktor and not any(f in str(aktor).lower() for f in ['informasi nihil', 'gagal parsing']):
        pesan += f"{aktor}\n\n"
    
    # 3. Profiling Laman (v6.80: Exact User Formatting)
    if isinstance(kontak, dict):
        p_nama = kontak.get('nama_laman', laman)
        p_alamat = kontak.get('alamat_laman', '')
        p_redaksi = kontak.get('jajaran_redaksi_laman', '')
        p_kontak = kontak.get('kontak_laman', '')
        p_lain = kontak.get('informasi_profiling_laman_lainnya', '')

        def is_valid(val):
            if not val: return False
            forbidden = ['informasi nihil', 'tidak ditemukan', 'unknown', 'nihil', 'n/a']
            return not any(f in str(val).lower() for f in forbidden)

        if is_valid(p_nama): pesan += f"{p_nama}\n"
        if is_valid(p_alamat): pesan += f"{p_alamat}\n"
        if is_valid(p_redaksi): pesan += f"{p_redaksi}\n"
        if is_valid(p_kontak): pesan += f"{p_kontak}\n"
        if is_valid(p_lain): pesan += f"{p_lain}\n"
        pesan += "\n"
    else:
        # Fallback jika AI mengembalikan string
        if kontak and not any(f in str(kontak).lower() for f in ['informasi nihil', 'tidak ditemukan']):
            pesan += f"{kontak}\n\n"
    
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
        print(f"[+] Berhasil mengirim notifikasi v7.27: {judul[:50]}...")
        # Simpan log ke arsip lokal
        tanggal = datetime.datetime.now().strftime("%d-%m-%Y")
        nama_file = f"berita_negatif_{tanggal}.txt"
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            with open(nama_file, 'a', encoding='utf-8') as f:
                f.write(f"[{tanggal} {timestamp}] Notifikasi v7.27:\n")
                f.write(pesan.replace('<b>', '').replace('</b>', '') + "\n")
                f.write("-" * 80 + "\n\n")
        except: pass
        return True
    
    return False

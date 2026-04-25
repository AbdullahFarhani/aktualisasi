import requests
import re
import urllib.parse
import base64
import random

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x44) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def debug_v48_pipeline():
    title = "Meski Sudah Disanksi SPPG Boyolangu Diduga Kembali Sajikan Menu MBG tak layak konsumsi, Tempe Bakar Mentah dan Diduga Berjamur - Rubic News - Rubic News"
    publisher_name = "Rubic News"
    query_title = title.split(' - ')[0].strip()
    q_text = f'"{query_title}" {publisher_name}'
    
    search_url = f"https://www.bing.com/search?q={urllib.parse.quote(q_text)}"
    print(f"[*] Testing URL: {search_url}")
    
    r = requests.get(search_url, headers=HEADERS, timeout=12)
    print(f"[*] Response Status: {r.status_code}")
    
    body_content = r.text
    if "</head>" in r.text.lower():
        body_content = r.text.lower().split("</head>")[-1]
        print("[*] Head stripped.")
    else:
        print("[!] Head NOT stripped (not found).")

    matches = list(re.finditer(r'(https?://[^\s\x00-\x1f\x7f-\xff<>"]+)', body_content))
    print(f"[*] Found {len(matches)} raw links.")
    
    for m in matches:
        raw_link = m.group(1)
        link = raw_link
        
        # Decoding
        is_decoded = False
        if "bing.com/ck/a" in link and "u=a1" in link:
            try:
                b64_part = link.split("u=a1")[-1].split("&")[0].split("#")[0]
                b64_part += "=" * (-len(b64_part) % 4)
                decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore')
                if decoded.startswith('http'): 
                    link = decoded
                    is_decoded = True
            except: pass
            
        link = urllib.parse.unquote(urllib.parse.unquote(link)).split('&url=')[-1].split('?url=')[-1].split('&')[0]
        link = link.split('/RK=')[0].split('/RS=')[0].strip()
        
        if "rubicnews" in link.lower():
            print(f"[FOUND RUBIC] Link: {link} | Decoded: {is_decoded} | Raw: {raw_link[:50]}...")
            
    print("[*] Debug finished.")

if __name__ == "__main__":
    debug_v48_pipeline()

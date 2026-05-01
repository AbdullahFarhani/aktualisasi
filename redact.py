import os

REPLACEMENTS = {
    # Delete explicit references
    "": "",
    "Institusi": "Institusi",
    "Institusi": "Institusi",
    "Institusi": "Institusi",
    "Pusat": "Pusat",
    
    # Locations
    "Area Operasional": "Area Operasional",
    "area operasional": "area operasional",
    "AreaX": "AreaX",
    "AREAX": "AREAX",
    "areax": "areax",
    "Ibu Kota Area": "Ibu Kota Area",
    
    # Military terms
    "Pimpinan": "Pimpinan",
    "Pimpinan": "Pimpinan",

    # API Keys
    "REDACTED_HF_TOKEN": "REDACTED_HF_TOKEN",
    "REDACTED_TELEGRAM_BOT_TOKEN": "REDACTED_TELEGRAM_BOT_TOKEN",
    "REDACTED_TELEGRAM_CHAT_ID": "REDACTED_TELEGRAM_CHAT_ID",
    "REDACTED_TELEGRAM_BOT_TOKEN_2": "REDACTED_TELEGRAM_BOT_TOKEN_2",
    "REDACTED_TELEGRAM_CHAT_ID_2": "REDACTED_TELEGRAM_CHAT_ID_2",
    "REDACTED_GEMINI_API_KEY": "REDACTED_GEMINI_API_KEY",
    "REDACTED_OPENROUTER_API_KEY": "REDACTED_OPENROUTER_API_KEY",
    "REDACTED_GROQ_API_KEY": "REDACTED_GROQ_API_KEY",
    
    # Cities
    "Kota A": "Kota A",
    "Kota B": "Kota B",
    "Kota C": "Kota C",
    "Kota D": "Kota D",
    "Kota E": "Kota E",
    "Kota F": "Kota F",
    "Kota G": "Kota G",
    "Kota H": "Kota H",
    "Kota I": "Kota I",
    "Kota J": "Kota J",
    "Kota K": "Kota K",
    "Kota L": "Kota L",
    "Kota M": "Kota M",
    "Kota N": "Kota N",
    "Kota O": "Kota O",
    "Kota P": "Kota P",
    "Kota Q": "Kota Q",
    "Kota R": "Kota R",
    "Kota S": "Kota S",
    "Kota T": "Kota T",
    "Kota U": "Kota U",
    "Kota V": "Kota V",
    "Kota W": "Kota W",
    "Kota X": "Kota X",
    "Kota Y": "Kota Y",
    "Kota Z": "Kota Z",
    "Kota AA": "Kota AA",
    "Kota AB": "Kota AB",
    "Kota AC": "Kota AC",
    "Kota AD": "Kota AD"
}

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Redacted: {filepath}")
    except Exception as e:
        pass

for root, dirs, files in os.walk('.'):
    if '.git' in root or '__pycache__' in root or 'backup' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.md') or file.endswith('.txt'):
            process_file(os.path.join(root, file))

print("Redaction complete.")

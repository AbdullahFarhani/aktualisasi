import re
from collections import Counter

file_path = 'output.txt'
with open(file_path, 'r') as f:
    lines = f.readlines()

queries = []
results = {}

current_query = None
for line in lines:
    m_search = re.search(r"\[\*\] Mencari berita untuk query: '(.*)'", line)
    if m_search:
        current_query = m_search.group(1)
        queries.append(current_query)
        if current_query not in results:
            results[current_query] = 0
        continue
    
    m_found = re.search(r"\[\+\] Ditemukan (\d+) berita untuk query: '(.*)'", line)
    if m_found:
        count = int(m_found.group(1))
        q = m_found.group(2)
        results[q] = results.get(q, 0) + count
        current_query = None

# Hitung produktivitas keyword (tanpa lokasi)
keyword_stats = {}
for q, count in results.items():
    # Asumsi query adalah "Keyword Lokasi"
    # Kita perlu tahu daftar lokasi untuk memisahkannya
    # Atau kita tebak saja: bagian terakhir biasanya lokasi
    parts = q.split()
    if len(parts) > 1:
        keyword = " ".join(parts[:-1])
    else:
        keyword = q
    
    if keyword not in keyword_stats:
        keyword_stats[keyword] = {'found': 0, 'searches': 0}
    
    keyword_stats[keyword]['found'] += count
    keyword_stats[keyword]['searches'] += 1

print("=== STATISTIK PRODUKTIVITAS KEYWORD ===")
sorted_stats = sorted(keyword_stats.items(), key=lambda x: x[1]['found'])

for kw, stat in sorted_stats:
    print(f"Keyword: '{kw}' | Total Berita: {stat['found']} | Jumlah Pencarian: {stat['searches']} | Avg: {stat['found']/stat['searches']:.2f}")

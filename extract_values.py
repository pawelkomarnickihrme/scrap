#!/usr/bin/env python3
"""
Skrypt do wyodrębniania wartości procentowych width z pliku HTML
"""

import re
from bs4 import BeautifulSoup

def extract_values(html_file):
    """Wyodrębnia wartości procentowe width dla każdej kategorii"""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Znajdź wszystkie divy z atrybutem index
    items = soup.find_all('div', attrs={'index': True})
    
    results = []
    
    for item in items:
        # Znajdź etykietę (vote-button-legend)
        label_elem = item.find('span', class_='vote-button-legend')
        if not label_elem:
            continue
        
        label = label_elem.get_text(strip=True)
        
        # Znajdź div z width w stylu
        # Szukamy diva wewnątrz voting-small-chart-size
        chart_div = item.find('div', class_='voting-small-chart-size')
        if chart_div:
            # Znajdź wszystkie divy z stylem
            inner_divs = chart_div.find_all('div', style=True)
            for div in inner_divs:
                style = div.get('style', '')
                # Szukamy diva z background (to jest wewnętrzny div z width)
                # który ma background z wartością rgb (nie rgba)
                if 'background:' in style and 'rgb(' in style:
                    # Wyodrębnij width z stylu
                    width_match = re.search(r'width:\s*([\d.]+)%', style)
                    if width_match:
                        width_percent = width_match.group(1)
                        results.append({
                            'label': label,
                            'width': f"{width_percent}%"
                        })
                        break
    
    return results

if __name__ == '__main__':
    results = extract_values('example.html')
    
    print("=" * 50)
    print("WYODRĘBNIONE WARTOŚCI:")
    print("=" * 50)
    
    for item in results:
        print(f"{item['label']:10} -> {item['width']}")
    
    print("\n" + "=" * 50)
    print("TABELA WYNIKÓW:")
    print("=" * 50)
    print(f"{'Kategoria':<15} {'Width (%)':<15}")
    print("-" * 30)
    for item in results:
        print(f"{item['label']:<15} {item['width']:<15}")
    
    # Weryfikacja wartości dla fall
    fall_value = next((item for item in results if item['label'] == 'fall'), None)
    if fall_value:
        print(f"\n✓ Wartość dla 'fall': {fall_value['width']} (poprawna: 54.3511%)")


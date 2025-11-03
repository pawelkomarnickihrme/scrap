#!/usr/bin/env python3
"""
Skrypt do wyodrębniania pros z pliku HTML
"""

import json
from bs4 import BeautifulSoup

def extract_pros(html_file):
    """Wyodrębnia pros z sekcji Pros w HTML"""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Znajdź główny div z Pros (z klasą cell small-12 medium-6)
    # Szukamy diva który zawiera tekst "Pros" w nagłówku
    pros_section = None
    for div in soup.find_all('div', class_='cell small-12 medium-6'):
        header = div.find('h4', class_='header')
        if header and 'Pros' in header.get_text():
            pros_section = div
            break
    
    if not pros_section:
        return []
    
    # Znajdź wszystkie span wewnątrz divów z klasą "cell small-12"
    # które są wewnątrz sekcji pros (pomijając spany z liczbami w num-votes-sp)
    pros_list = []
    for item_div in pros_section.find_all('div', class_='cell small-12'):
        # Znajdź span który NIE jest wewnątrz num-votes-sp
        # Sprawdź wszystkie spany i wybierz ten który nie jest w strukturze z głosami
        all_spans = item_div.find_all('span')
        for span in all_spans:
            # Sprawdź czy span nie jest wewnątrz num-votes-sp
            parent_num_votes = span.find_parent('div', class_='num-votes-sp')
            if not parent_num_votes:
                text = span.get_text(strip=True)
                # Upewnij się że to nie jest liczba (czyli pros tekst)
                if text and not text.isdigit():
                    pros_list.append(text)
                    break  # Weź tylko pierwszy span który nie jest liczbą
    
    # Zwróć tylko pierwsze 5 pros
    return pros_list[:5]

if __name__ == '__main__':
    pros = extract_pros('example.html')
    
    print("=" * 50)
    print("WYODRĘBNIONE PROS:")
    print("=" * 50)
    
    for i, pro in enumerate(pros, 1):
        print(f"{i}. {pro}")
    
    # Zapisz do output.json
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(pros, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Zapisano {len(pros)} pros do output.json")


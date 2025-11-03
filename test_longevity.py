#!/usr/bin/env python3
"""Skrypt testowy do sprawdzenia czy scraper prawidłowo pobiera dane LONGEVITY."""

import re
from typing import Dict, List, Any
from bs4 import BeautifulSoup

# Skopiuj potrzebne funkcje z scraper.py
def clean_text(text: str) -> str:
    """Usuwa białe znaki i normalizuje tekst."""
    if not text:
        return ""
    return " ".join(text.split())


def extract_voting_data(soup: BeautifulSoup, category: str, options_mapping: Dict[str, List[str]]) -> Dict[str, Any]:
    """Wyciąga dane głosowania dla danej kategorii."""
    data = {}
    most_voted_value = None
    max_votes = 0
    
    # Mapowanie nazw kategorii na tytuły w HTML
    category_titles = {
        "longevity": ["LONGEVITY"],
        "gender": ["GENDER", "PŁEĆ"],
        "valueForMoney": ["VALUE FOR MONEY", "STOSUNEK JAKOŚĆ/CENA"],
        "season": ["SEASON", "PORA ROKU"],
        "timeOfDay": ["TIME OF DAY", "PORA DNIA"],
    }
    
    # Znajdź sekcję kategorii po tytule
    category_section = None
    titles = category_titles.get(category, [category.upper()])
    
    for title in titles:
        # Szukaj span lub innego elementu z tekstem tytułu
        title_elem = soup.find(lambda tag: tag.name in ["span", "h2", "h3", "h4", "div"] 
                               and clean_text(tag.get_text()).upper() == title.upper())
        if title_elem:
            # Znajdź kontener sekcji (zwykle rodzic lub dziadek)
            category_section = title_elem.find_parent(class_=re.compile(r"cell|section|container", re.I))
            if not category_section:
                category_section = title_elem.find_parent("div")
            if category_section:
                break
    
    # Jeśli nie znaleziono sekcji, szukaj w całym soup
    search_soup = category_section if category_section else soup
    
    # Znajdź wszystkie elementy vote-button-name w sekcji
    vote_names = search_soup.find_all(class_="vote-button-name")
    
    for vote_name_elem in vote_names:
        vote_name_text = clean_text(vote_name_elem.get_text()).lower()
        
        # Znajdź kontener grid-x który zawiera ten element
        grid_container = vote_name_elem.find_parent(class_=re.compile(r"grid", re.I))
        if not grid_container:
            grid_container = vote_name_elem.find_parent()
        
        # Znajdź odpowiadający element z liczbą głosów w tym samym kontenerze
        if grid_container:
            vote_legend = grid_container.find(class_="vote-button-legend")
            if vote_legend:
                vote_count_text = clean_text(vote_legend.get_text())
                numbers = re.findall(r"\d+", vote_count_text)
                if numbers:
                    vote_count = int(numbers[0])
                    
                    # Sprawdź, która opcja pasuje
                    for eng_option, variants in options_mapping.items():
                        for variant in variants:
                            if variant.lower() in vote_name_text:
                                data[eng_option] = vote_count
                                if vote_count > max_votes:
                                    max_votes = vote_count
                                    most_voted_value = eng_option
                                break
    
    if most_voted_value and max_votes > 0:
        data["mostVoted"] = most_voted_value
    
    return data


def extract_all_voting_data(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """Wyciąga wszystkie dane głosowania."""
    return {
        "longevity": extract_voting_data(
            soup,
            "longevity",
            {
                "veryWeak": ["very weak", "bardzo słaba"],
                "weak": ["weak", "słaba"],
                "moderate": ["moderate", "przeciętna"],
                "longLasting": ["long lasting", "długotrwała"],
                "eternal": ["eternal", "wieczna"],
            },
        ),
    }

# Wczytaj plik HTML
with open("reminad.html", "r", encoding="utf-8") as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "html.parser")

# Wyciągnij dane głosowania
voting_data = extract_all_voting_data(soup)

# Sprawdź dane longevity
longevity = voting_data.get("longevity", {})

print("Dane LONGEVITY:")
print(f"veryWeak: {longevity.get('veryWeak', 'BRAK')}")
print(f"weak: {longevity.get('weak', 'BRAK')}")
print(f"moderate: {longevity.get('moderate', 'BRAK')}")
print(f"longLasting: {longevity.get('longLasting', 'BRAK')}")
print(f"eternal: {longevity.get('eternal', 'BRAK')}")
print(f"mostVoted: {longevity.get('mostVoted', 'BRAK')}")

# Oczekiwane wartości
expected = {
    "veryWeak": 18,
    "weak": 12,
    "moderate": 73,
    "longLasting": 245,
    "eternal": 519,
}

print("\nSprawdzanie poprawności:")
all_correct = True
for key, expected_value in expected.items():
    actual_value = longevity.get(key)
    if actual_value == expected_value:
        print(f"✓ {key}: {actual_value} (OK)")
    else:
        print(f"✗ {key}: oczekiwano {expected_value}, otrzymano {actual_value}")
        all_correct = False

if all_correct:
    print("\n✓ Wszystkie wartości są poprawne!")
else:
    print("\n✗ Niektóre wartości są nieprawidłowe!")


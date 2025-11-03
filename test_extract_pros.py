#!/usr/bin/env python3
"""
Test funkcji extract_pros na example.html i zapisanie pełnych danych do output.json
"""

import json
from bs4 import BeautifulSoup
from scraper import (
    extract_perfume_name,
    extract_brand,
    extract_description,
    extract_main_image_url,
    extract_user_reviews,
    extract_rating,
    extract_rating_count,
    extract_notes,
    extract_similar_perfumes,
    extract_recommended_perfumes,
    extract_pros,
    extract_all_voting_data,
    remove_unwanted_elements,
    clean_text,
)

# Wczytaj plik HTML
with open("example.html", "r", encoding="utf-8") as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "html.parser")

# Znajdź element #main-content (jeśli istnieje) lub użyj całego soup
main_content = soup.find(id="main-content")
if not main_content:
    main_content = soup

# Usuń niechciane elementy
remove_unwanted_elements(main_content)

# Wyciągnij wszystkie dane
perfume_data = {
    "perfumeName": extract_perfume_name(main_content),
    "brand": extract_brand(main_content),
    "description": extract_description(main_content),
    "mainImageUrl": extract_main_image_url(main_content, ""),
    "userReviews": extract_user_reviews(main_content),
    "rating": extract_rating(main_content),
    "ratingCount": extract_rating_count(main_content),
    "notes": extract_notes(main_content),
    "similarPerfumes": extract_similar_perfumes(main_content),
    "recommendedPerfumes": extract_recommended_perfumes(main_content),
    "pros": extract_pros(main_content),
}

# Dodaj dane głosowania
voting_data = extract_all_voting_data(main_content)
perfume_data.update(voting_data)

# Zapisz do output.json
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(perfume_data, f, ensure_ascii=False, indent=2)

print("=" * 50)
print("WYODRĘBNIONE PROS:")
print("=" * 50)
for i, pro in enumerate(perfume_data.get("pros", []), 1):
    print(f"{i}. {pro}")

print(f"\n✓ Zapisano pełne dane do output.json")
print(f"✓ Znaleziono {len(perfume_data.get('pros', []))} pros")


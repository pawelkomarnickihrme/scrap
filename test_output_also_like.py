#!/usr/bin/env python3
"""Test sprawdzający sekcję 'People who like this also like' w output.js po scrapowaniu."""

import json
import sys
import os
from pathlib import Path


def normalize_name(name: str) -> str:
    """Normalizuje nazwę perfum do porównań (usuwa białe znaki, konwertuje na małe litery)."""
    if not name:
        return ""
    return " ".join(name.lower().split())


def test_also_like_perfumes(output_file: str = "output.js") -> bool:
    """Testuje czy plik output zawiera poprawne perfumy w sekcji 'People who like this also like'.
    
    Args:
        output_file: Ścieżka do pliku z danymi wyjściowymi
        
    Returns:
        True jeśli wszystkie perfumy są obecne, False w przeciwnym razie
    """
    if not os.path.exists(output_file):
        print(f"✗ Błąd: Plik {output_file} nie istnieje!")
        print("   Uruchom najpierw scrapowanie: python scraper.py")
        return False
    
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"✗ Błąd: Nie można sparsować pliku {output_file}: {e}")
        return False
    except Exception as e:
        print(f"✗ Błąd podczas czytania pliku {output_file}: {e}")
        return False
    
    # Oczekiwane perfumy z markami (z danych użytkownika)
    expected_perfumes = [
        {"name": "XJ 1861 Naxos", "brand": "Xerjoff"},
        {"name": "Bois Impérial", "brand": "Essential Parfums"},
        {"name": "Megamare", "brand": "Orto Parisi"},
        {"name": "Sex-Sea", "brand": "Lorenzo Pazzaglia"},
        {"name": "Dream Sea", "brand": "Lorenzo Pazzaglia"},
        {"name": "Hacivat", "brand": "Nishane"},
        {"name": "Van Py Rhum", "brand": "Lorenzo Pazzaglia"},
        {"name": "Summer Hammer", "brand": "Lorenzo Pazzaglia"},
        {"name": "Aventus", "brand": "Creed"},
        {"name": "Evil Angel a.k.a. 28.09", "brand": "Lorenzo Pazzaglia"},
        {"name": "Layton", "brand": "Parfums de Marly"},
        {"name": "Carbonara", "brand": "Lorenzo Pazzaglia"},
        {"name": "Ganymede", "brand": "Marc-Antoine Barrois"},
        {"name": "Sauvage Elixir", "brand": "Dior"},
        {"name": "Grand Soir", "brand": "Maison Francis Kurkdjian"},
        {"name": "Artik Sea", "brand": "Lorenzo Pazzaglia"},
        {"name": "Reflection Man", "brand": "Amouage"},
        {"name": "Red Tobacco", "brand": "Mancera"},
        {"name": "Dior Homme Intense 2011", "brand": "Dior"},
        {"name": "Black Afgano", "brand": "Nasomatto"},
    ]
    
    # Sprawdź czy istnieje sekcja recommendedPerfumes (lub też alsoLike)
    section_key = None
    for possible_key in ["recommendedPerfumes", "alsoLike", "also_like", "peopleAlsoLike"]:
        if possible_key in data:
            section_key = possible_key
            break
    
    if not section_key:
        print("✗ Błąd: Brak sekcji z perfumami 'People who like this also like' w danych!")
        print(f"   Dostępne sekcje: {list(data.keys())}")
        print("   Szukane sekcje: recommendedPerfumes, alsoLike, also_like, peopleAlsoLike")
        return False
    
    recommended_perfumes = data[section_key]
    
    print("\n=== Test sekcji 'People who like this also like' ===\n")
    print(f"Sprawdzanie pliku: {output_file}")
    print(f"Znaleziona sekcja: {section_key}\n")
    
    # Sprawdź czy sekcja jest pusta
    if not recommended_perfumes or len(recommended_perfumes) == 0:
        print("⚠️  Uwaga: Sekcja istnieje, ale jest pusta!")
        print("   To oznacza, że scraper nie znalazł danych sekcji 'People who like this also like'.")
        print("   Sprawdź czy strona zawiera tę sekcję lub czy struktura HTML się zmieniła.\n")
        return False
    
    # Przygotuj listę normalizowanych nazw perfum z output.js
    # Struktura może być różna: {"name": "..."} lub {"name": "...", "brand": "..."} lub po prostu stringi
    found_perfumes = []
    for item in recommended_perfumes:
        if isinstance(item, dict):
            name = item.get("name", "")
            brand = item.get("brand", "")
            if name:
                found_perfumes.append({
                    "name": normalize_name(name),
                    "brand": normalize_name(brand) if brand else "",
                    "original_name": name,
                    "original_brand": brand
                })
        elif isinstance(item, str):
            found_perfumes.append({
                "name": normalize_name(item),
                "brand": "",
                "original_name": item,
                "original_brand": ""
            })
    
    print(f"Znaleziono {len(found_perfumes)} perfum w sekcji")
    print(f"Oczekiwano {len(expected_perfumes)} perfum\n")
    
    # Sprawdź każde oczekiwane perfumy
    all_found = True
    missing_perfumes = []
    
    for expected in expected_perfumes:
        expected_name_normalized = normalize_name(expected["name"])
        expected_brand_normalized = normalize_name(expected["brand"])
        
        # Szukaj dopasowania - sprawdź czy nazwa perfum pasuje
        found = False
        matched_item = None
        
        for found_item in found_perfumes:
            found_name = found_item["name"]
            
            # Sprawdź dokładne dopasowanie nazwy
            if found_name == expected_name_normalized:
                found = True
                matched_item = found_item
                break
            
            # Sprawdź czy nazwa jest zawarta w znalezionym tekście (może być z marką)
            # lub odwrotnie - znaleziony tekst zawiera oczekiwaną nazwę
            if expected_name_normalized in found_name or found_name in expected_name_normalized:
                # Dodatkowo sprawdź markę, jeśli jest dostępna
                if expected_brand_normalized:
                    found_brand = found_item["brand"]
                    # Jeśli marka jest dostępna w znalezionym elemencie, sprawdź ją
                    if found_brand and expected_brand_normalized not in found_brand and found_brand not in expected_brand_normalized:
                        # Marka nie pasuje, ale nazwa tak - to może być inne perfumy o podobnej nazwie
                        # Zaakceptuj tylko jeśli nazwa jest bardzo podobna
                        if found_name == expected_name_normalized:
                            found = True
                            matched_item = found_item
                            break
                    else:
                        # Marka pasuje lub nie ma marki w znalezionym elemencie
                        found = True
                        matched_item = found_item
                        break
                else:
                    # Nie ma marki do sprawdzenia, nazwa pasuje
                    found = True
                    matched_item = found_item
                    break
        
        if found:
            brand_info = f" (marka: {matched_item['original_brand']})" if matched_item.get("original_brand") else ""
            print(f"✓ {expected['name']:30s} {expected['brand']:30s} - znaleziono: {matched_item['original_name']}{brand_info}")
        else:
            print(f"✗ {expected['name']:30s} {expected['brand']:30s} - BRAK")
            missing_perfumes.append(expected)
            all_found = False
    
    # Wyświetl podsumowanie
    print("\n" + "=" * 100)
    if all_found:
        print("✓ WSZYSTKIE PERFUMY ZOSTAŁY ZNALEZIONE!")
        print("=" * 100 + "\n")
        return True
    else:
        print(f"✗ BRAKUJE {len(missing_perfumes)} PERFUM!")
        print("=" * 100)
        if len(missing_perfumes) > 0:
            print("\nBrakujące perfumy:")
            for missing in missing_perfumes:
                print(f"  - {missing['name']} ({missing['brand']})")
        print()
        return False


if __name__ == "__main__":
    # Pozwól na podanie innego pliku jako argument
    output_file = sys.argv[1] if len(sys.argv) > 1 else "output.js"
    
    success = test_also_like_perfumes(output_file)
    sys.exit(0 if success else 1)


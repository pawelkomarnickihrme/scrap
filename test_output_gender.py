#!/usr/bin/env python3
"""Test sprawdzający wartości GENDER w output.js po scrapowaniu."""

import json
import sys
import os
from pathlib import Path


def test_gender_values(output_file: str = "output.js") -> bool:
    """Testuje czy plik output zawiera poprawne wartości GENDER.
    
    Args:
        output_file: Ścieżka do pliku z danymi wyjściowymi
        
    Returns:
        True jeśli wszystkie wartości są poprawne, False w przeciwnym razie
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
    
    # Oczekiwane wartości GENDER
    # Sprawdzamy różne możliwe nazwy kluczy (scraper może używać różnych wariantów)
    expected_values = {
        # Różne możliwe nazwy kluczy dla tych samych wartości
        "female": 12,
        "feminine": 12,  # scraper może używać "feminine"
        "moreFemale": 5,
        "more female": 5,
        "unisex": 302,
        "moreMale": 285,
        "more male": 285,
        "male": 232,
        "masculine": 232,  # scraper może używać "masculine"
    }
    
    # Sprawdź czy istnieje sekcja gender
    if "gender" not in data:
        print("✗ Błąd: Brak sekcji 'gender' w danych!")
        print(f"   Dostępne sekcje: {list(data.keys())}")
        return False
    
    gender = data["gender"]
    
    print("\n=== Test wartości GENDER ===\n")
    print(f"Sprawdzanie pliku: {output_file}\n")
    
    # Sprawdź czy sekcja gender jest pusta
    if not gender or len(gender) == 0:
        print("⚠️  Uwaga: Sekcja 'gender' istnieje, ale jest pusta!")
        print("   To oznacza, że scraper nie znalazł danych głosowania GENDER.")
        print("   Sprawdź czy strona zawiera sekcję GENDER lub czy struktura HTML się zmieniła.\n")
        return False
    
    # Wyświetl dostępne klucze w sekcji gender (dla debugowania)
    available_keys = list(gender.keys())
    print(f"Dostępne klucze w gender: {available_keys}\n")
    
    # Mapa oczekiwanych wartości - używamy standardowych nazw do wyświetlenia
    # Sprawdzamy różne możliwe warianty nazw kluczy (nowe i stare dla kompatybilności)
    checks_to_perform = [
        ("female", ["female", "feminine"], 12),
        ("moreFemale", ["moreFemale", "more female", "morefemale"], 5),
        ("unisex", ["unisex"], 302),
        ("moreMale", ["moreMale", "more male", "moremale"], 285),
        ("male", ["male", "masculine"], 232),
    ]
    
    all_correct = True
    
    # Sprawdź każdą wartość
    for display_name, possible_keys, expected_value in checks_to_perform:
        actual_value = None
        found_key = None
        
        # Znajdź wartość pod którąkolwiek z możliwych nazw kluczy
        for key in possible_keys:
            if key in gender:
                actual_value = gender[key]
                found_key = key
                break
        
        if actual_value is None:
            print(f"✗ {display_name:15s}: oczekiwano {expected_value:4d}, otrzymano (brak)")
            all_correct = False
        elif actual_value == expected_value:
            print(f"✓ {display_name:15s}: {actual_value:4d} (OK)")
        else:
            print(f"✗ {display_name:15s}: oczekiwano {expected_value:4d}, otrzymano {actual_value}")
            all_correct = False
    
    # Wyświetl podsumowanie
    print("\n" + "=" * 50)
    if all_correct:
        print("✓ WSZYSTKIE WARTOŚCI SĄ POPRAWNE!")
        print("=" * 50 + "\n")
        return True
    else:
        print("✗ NIEKTÓRE WARTOŚCI SĄ NIEPRAWIDŁOWE!")
        print("=" * 50 + "\n")
        return False


if __name__ == "__main__":
    # Pozwól na podanie innego pliku jako argument
    output_file = sys.argv[1] if len(sys.argv) > 1 else "output.js"
    
    success = test_gender_values(output_file)
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""Test sprawdzający wartości SILLAGE w output.js po scrapowaniu."""

import json
import sys
import os
from pathlib import Path


def test_sillage_values(output_file: str = "output.js") -> bool:
    """Testuje czy plik output zawiera poprawne wartości SILLAGE.
    
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
    
    # Oczekiwane wartości SILLAGE
    expected_values = {
        "intimate": 25,
        "moderate": 111,
        "strong": 304,
        "enormous": 406,
    }
    
    # Sprawdź czy istnieje sekcja sillage
    if "sillage" not in data:
        print("✗ Błąd: Brak sekcji 'sillage' w danych!")
        print(f"   Dostępne sekcje: {list(data.keys())}")
        return False
    
    sillage = data["sillage"]
    
    print("\n=== Test wartości SILLAGE ===\n")
    print(f"Sprawdzanie pliku: {output_file}\n")
    
    # Sprawdź czy sekcja sillage jest pusta
    if not sillage or len(sillage) == 0:
        print("⚠️  Uwaga: Sekcja 'sillage' istnieje, ale jest pusta!")
        print("   To oznacza, że scraper nie znalazł danych głosowania SILLAGE.")
        print("   Sprawdź czy strona zawiera sekcję SILLAGE lub czy struktura HTML się zmieniła.\n")
        return False
    
    # Wyświetl dostępne klucze w sekcji sillage (dla debugowania)
    available_keys = list(sillage.keys())
    print(f"Dostępne klucze w sillage: {available_keys}\n")
    
    all_correct = True
    
    # Sprawdź każdą wartość
    for key, expected_value in expected_values.items():
        actual_value = sillage.get(key)
        
        if actual_value == expected_value:
            print(f"✓ {key:15s}: {actual_value:4d} (OK)")
        else:
            if actual_value is None:
                print(f"✗ {key:15s}: oczekiwano {expected_value:4d}, otrzymano (brak)")
            else:
                print(f"✗ {key:15s}: oczekiwano {expected_value:4d}, otrzymano {actual_value}")
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
    
    success = test_sillage_values(output_file)
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""Test sprawdzający wartości PRICE VALUE (VALUE FOR MONEY) w output.js po scrapowaniu."""

import json
import sys
import os
from pathlib import Path


def test_price_value_values(output_file: str = "output.js") -> bool:
    """Testuje czy plik output zawiera poprawne wartości PRICE VALUE.
    
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
    
    # Oczekiwane wartości PRICE VALUE
    expected_values = {
        "wayOverpriced": 72,
        "way overpriced": 72,
        "priceTooHigh": 72,  # scraper może używać "priceTooHigh"
        "overpriced": 132,
        "ok": 280,
        "fair": 280,  # scraper może używać "fair" zamiast "ok"
        "goodValue": 144,
        "good value": 144,
        "goodQuality": 144,  # scraper może używać "goodQuality"
        "greatValue": 150,
        "great value": 150,
        "excellentQuality": 150,  # scraper może używać "excellentQuality"
    }
    
    # Sprawdź czy istnieje sekcja valueForMoney
    if "valueForMoney" not in data:
        print("✗ Błąd: Brak sekcji 'valueForMoney' w danych!")
        print(f"   Dostępne sekcje: {list(data.keys())}")
        return False
    
    value_for_money = data["valueForMoney"]
    
    print("\n=== Test wartości PRICE VALUE (VALUE FOR MONEY) ===\n")
    print(f"Sprawdzanie pliku: {output_file}\n")
    
    # Sprawdź czy sekcja valueForMoney jest pusta
    if not value_for_money or len(value_for_money) == 0:
        print("⚠️  Uwaga: Sekcja 'valueForMoney' istnieje, ale jest pusta!")
        print("   To oznacza, że scraper nie znalazł danych głosowania PRICE VALUE.")
        print("   Sprawdź czy strona zawiera sekcję VALUE FOR MONEY lub czy struktura HTML się zmieniła.\n")
        return False
    
    # Wyświetl dostępne klucze w sekcji valueForMoney (dla debugowania)
    available_keys = list(value_for_money.keys())
    print(f"Dostępne klucze w valueForMoney: {available_keys}\n")
    
    # Mapa oczekiwanych wartości - używamy standardowych nazw do wyświetlenia
    # Sprawdzamy różne możliwe warianty nazw kluczy
    checks_to_perform = [
        ("wayOverpriced", ["wayOverpriced", "way overpriced", "priceTooHigh"], 72),
        ("overpriced", ["overpriced"], 132),
        ("ok", ["ok", "fair"], 280),
        ("goodValue", ["goodValue", "good value", "goodQuality"], 144),
        ("greatValue", ["greatValue", "great value", "excellentQuality"], 150),
    ]
    
    all_correct = True
    
    # Sprawdź każdą wartość
    for display_name, possible_keys, expected_value in checks_to_perform:
        actual_value = None
        found_key = None
        
        # Znajdź wartość pod którąkolwiek z możliwych nazw kluczy
        for key in possible_keys:
            if key in value_for_money:
                actual_value = value_for_money[key]
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
    
    success = test_price_value_values(output_file)
    sys.exit(0 if success else 1)


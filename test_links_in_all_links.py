#!/usr/bin/env python3
"""Test sprawdzający czy wszystkie linki z links.json są w all-links.json."""

import json
import sys
import os


def test_links_in_all_links(links_file: str = "links.json", all_links_file: str = "all-links.json") -> bool:
    """Testuje czy wszystkie linki z links.json są w all-links.json.
    
    Args:
        links_file: Ścieżka do pliku links.json
        all_links_file: Ścieżka do pliku all-links.json
        
    Returns:
        True jeśli wszystkie linki są obecne, False w przeciwnym razie
    """
    # Sprawdź czy pliki istnieją
    if not os.path.exists(links_file):
        print(f"✗ Błąd: Plik {links_file} nie istnieje!")
        return False
    
    if not os.path.exists(all_links_file):
        print(f"✗ Błąd: Plik {all_links_file} nie istnieje!")
        return False
    
    # Wczytaj links.json
    try:
        with open(links_file, "r", encoding="utf-8") as f:
            links_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"✗ Błąd: Nie można sparsować pliku {links_file}: {e}")
        return False
    except Exception as e:
        print(f"✗ Błąd podczas czytania pliku {links_file}: {e}")
        return False
    
    # Wczytaj all-links.json
    try:
        with open(all_links_file, "r", encoding="utf-8") as f:
            all_links_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"✗ Błąd: Nie można sparsować pliku {all_links_file}: {e}")
        return False
    except Exception as e:
        print(f"✗ Błąd podczas czytania pliku {all_links_file}: {e}")
        return False
    
    # Pobierz listę linków z links.json
    if "links" not in links_data:
        print(f"✗ Błąd: Brak klucza 'links' w pliku {links_file}!")
        print(f"   Dostępne klucze: {list(links_data.keys())}")
        return False
    
    links = links_data["links"]
    
    # Sprawdź czy all-links.json jest tablicą
    if not isinstance(all_links_data, list):
        print(f"✗ Błąd: Plik {all_links_file} powinien zawierać tablicę!")
        print(f"   Typ danych: {type(all_links_data)}")
        return False
    
    # Funkcja normalizująca URL - zamienia /perfumy/ na /perfume/
    def normalize_url(url: str) -> str:
        """Normalizuje URL zamieniając /perfumy/ na /perfume/."""
        return url.replace("/perfumy/", "/perfume/")
    
    # Normalizuj linki z links.json
    normalized_links = [normalize_url(link) for link in links]
    
    # Normalizuj linki z all-links.json i konwertuj na set dla szybszego wyszukiwania
    normalized_all_links = [normalize_url(link) for link in all_links_data]
    all_links_set = set(normalized_all_links)
    
    print("\n=== Test obecności linków z links.json w all-links.json ===\n")
    print(f"Sprawdzanie pliku: {links_file}")
    print(f"Przeciwko plikowi: {all_links_file}\n")
    print(f"Liczba linków w {links_file}: {len(links)}")
    print(f"Liczba linków w {all_links_file}: {len(all_links_data)}\n")
    
    # Znajdź brakujące linki (używając znormalizowanych wersji)
    missing_links = []
    found_links = []
    
    for i, link in enumerate(links):
        normalized_link = normalized_links[i]
        if normalized_link in all_links_set:
            found_links.append(link)
        else:
            missing_links.append(link)
    
    # Wyświetl wyniki
    print("=" * 80)
    print(f"✓ Znaleziono: {len(found_links)}/{len(links)} linków")
    print(f"✗ Brakuje: {len(missing_links)}/{len(links)} linków")
    print("=" * 80 + "\n")
    
    if missing_links:
        print("Brakujące linki:")
        for i, link in enumerate(missing_links, 1):
            print(f"  {i}. {link}")
        print()
    
    # Wyświetl podsumowanie
    print("=" * 80)
    if len(missing_links) == 0:
        print("✓ WSZYSTKIE LINKI SĄ OBECNE W all-links.json!")
        print("=" * 80 + "\n")
        return True
    else:
        print(f"✗ BRAKUJE {len(missing_links)} LINKÓW W all-links.json!")
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    # Pozwól na podanie innych plików jako argumenty
    links_file = sys.argv[1] if len(sys.argv) > 1 else "links.json"
    all_links_file = sys.argv[2] if len(sys.argv) > 2 else "all-links.json"
    
    success = test_links_in_all_links(links_file, all_links_file)
    sys.exit(0 if success else 1)


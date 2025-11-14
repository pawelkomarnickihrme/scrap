#!/usr/bin/env python3
"""
Program do przetwarzania wszystkich linków z DATA.json.
Dla każdego linku uruchamia scraper.py i scrape_reviews.py,
a następnie zapisuje wyniki do osobnego pliku JSON.
"""

import asyncio
import json
import os
import random
import re
import sys
import time
import getpass
from urllib.parse import urlparse
from pathlib import Path

from scraper import scrape_perfume_data
from scrape_reviews import scrape_reviews
from vpn_manager import VPNManager


def get_sudo_password() -> str:
    """Pobiera hasło sudo z zmiennej środowiskowej lub pyta użytkownika."""
    # Najpierw sprawdź zmienną środowiskową
    sudo_password = os.getenv("SUDO_PASSWORD")
    if sudo_password:
        return sudo_password
    
    # Jeśli nie ma w zmiennej środowiskowej, zapytaj użytkownika
    try:
        sudo_password = getpass.getpass("🔐 Podaj hasło sudo (lub ustaw SUDO_PASSWORD w zmiennych środowiskowych): ")
        return sudo_password
    except KeyboardInterrupt:
        print("\n❌ Anulowano", file=sys.stderr)
        sys.exit(1)


def generate_filename_from_url(url: str) -> str:
    """Generuje nazwę pliku na podstawie URL."""
    # Format URL: https://www.fragrantica.com/perfumy/Brand/Name-ID.html
    match = re.search(r'/perfumy/([^/]+)/(.+?)-(\d+)\.html', url)
    if match:
        brand = match.group(1).replace("-", "_")
        name = match.group(2).replace("-", "_")
        perfume_id = match.group(3)
        # Usuń niebezpieczne znaki dla nazwy pliku
        filename = f"{brand}_{name}_{perfume_id}.json"
        # Zamień niebezpieczne znaki na podkreślniki
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        return filename
    
    # Fallback: użyj ostatniej części URL
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    if path_parts:
        filename = "_".join(path_parts[-2:]) if len(path_parts) >= 2 else path_parts[-1]
        filename = filename.replace('.html', '.json')
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        return filename
    
    # Ostateczny fallback
    return "perfume.json"


def generate_filename_from_perfume_name(perfume_name: str, brand: str = None) -> str:
    """Generuje nazwę pliku na podstawie nazwy perfum i marki."""
    if not perfume_name:
        return None
    
    # Normalizuj nazwę: usuń niebezpieczne znaki, zamień spacje na podkreślniki
    name = perfume_name.strip()
    name = re.sub(r'[^\w\s\-]', '', name)  # Usuń znaki specjalne
    name = re.sub(r'\s+', '_', name)  # Zamień spacje na podkreślniki
    name = name.lower()
    
    if brand:
        brand_normalized = brand.strip()
        brand_normalized = re.sub(r'[^\w\s\-]', '', brand_normalized)
        brand_normalized = re.sub(r'\s+', '_', brand_normalized)
        brand_normalized = brand_normalized.lower()
        filename = f"{brand_normalized}_{name}.json"
    else:
        filename = f"{name}.json"
    
    # Skróć jeśli zbyt długie
    if len(filename) > 200:
        filename = filename[:200] + ".json"
    
    return filename


async def process_single_link(url: str, output_dir: Path = None, vpn_manager: VPNManager = None) -> str:
    """Przetwarza pojedynczy link i zapisuje wyniki do pliku JSON.
    
    Zwraca ścieżkę do zapisanego pliku lub None w przypadku błędu.
    """
    if output_dir is None:
        output_dir = Path(".")
    
    print(f"\n{'='*80}")
    print(f"Przetwarzanie: {url}")
    print(f"{'='*80}")
    
    # Rozpocznij pomiar czasu
    start_time = time.time()
    
    try:
        # Krok 1: Scrapuj dane podstawowe z scraper.py
        print("✓ Scrapowanie danych podstawowych...")
        perfume_data = await scrape_perfume_data(url, vpn_manager=vpn_manager)
        
        # Krok 2: Scrapuj recenzje z scrape_reviews.py
        print("✓ Scrapowanie recenzji...")
        reviews = await scrape_reviews(url, vpn_manager=vpn_manager)
        
        # Krok 3: Połącz dane
        perfume_data["review"] = reviews
        
        # Krok 4: Wygeneruj nazwę pliku
        # Najpierw spróbuj na podstawie nazwy perfum i marki
        filename = generate_filename_from_perfume_name(
            perfume_data.get("perfumeName"),
            perfume_data.get("brand")
        )
        
        # Jeśli nie udało się wygenerować, użyj URL
        if not filename:
            filename = generate_filename_from_url(url)
        
        # Krok 5: Zapisz do pliku
        output_path = output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(perfume_data, f, ensure_ascii=False, indent=2)
        
        # Zakończ pomiar czasu
        elapsed_time = time.time() - start_time
        
        print(f"✓ Zapisano do: {output_path}")
        print(f"  - Nazwa perfum: {perfume_data.get('perfumeName', 'N/A')}")
        print(f"  - Marka: {perfume_data.get('brand', 'N/A')}")
        print(f"  - Liczba recenzji: {len(reviews)}")
        print(f"  - Czas scrapowania: {elapsed_time:.2f} sekund ({elapsed_time/60:.2f} minut)")
        
        return str(output_path)
        
    except Exception as e:
        # Zakończ pomiar czasu również w przypadku błędu
        elapsed_time = time.time() - start_time
        print(f"✗ Błąd podczas przetwarzania {url}: {e}", file=sys.stderr)
        print(f"  - Czas przed błędem: {elapsed_time:.2f} sekund ({elapsed_time/60:.2f} minut)", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Główna funkcja programu."""
    # Pobierz hasło sudo
    sudo_password = get_sudo_password()
    
    # Inicjalizuj VPN Manager z hasłem sudo
    vpn_manager = VPNManager(sudo_password=sudo_password)
    
    # Wczytaj linki z DATA.json
    data_file = Path("all-links.json")
    if not data_file.exists():
        print(f"Błąd: Plik {data_file} nie istnieje", file=sys.stderr)
        sys.exit(1)
    
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    links = data.get("links", [])
    if not links:
        print("Błąd: Brak linków w pliku DATA.json", file=sys.stderr)
        sys.exit(1)
    
    print(f"Znaleziono {len(links)} linków do przetworzenia")
    
    # Utwórz katalog na wyniki (opcjonalnie)
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Przetwórz każdy link
    success_count = 0
    error_count = 0
    processed_files = []
    
    # Iteruj po kopii listy, aby móc bezpiecznie modyfikować oryginalną listę
    links_to_process = links.copy()
    
    for i, url in enumerate(links_to_process, 1):
        if not url or not url.strip():
            continue
        
        url = url.strip()
        
        # # Odczekaj 60-90 sekund przed każdym zapytaniem (oprócz pierwszego) - aby uniknąć 429
        # if i > 1:
        #     wait_time = random.uniform(30, 60)
        #     print(f"\n⏳ Oczekiwanie {wait_time:.1f} sekund przed następnym zapytaniem...")
        #     await asyncio.sleep(wait_time)
        
        print(f"\n[{i}/{len(links_to_process)}] Przetwarzanie linku {i}...")
               
        result = await process_single_link(url, output_dir, vpn_manager)
        if result:
            success_count += 1
            processed_files.append(result)
            
            # Usuń przetworzony link z listy i zapisz zaktualizowany plik
            if url in links:
                links.remove(url)
                # Zapisz zaktualizowaną listę do pliku
                with open(data_file, "w", encoding="utf-8") as f:
                    json.dump({"links": links}, f, ensure_ascii=False, indent=2)
                print(f"✓ Usunięto link z listy. Pozostało {len(links)} linków.")
        else:
            error_count += 1
    
    # Podsumowanie
    print(f"\n{'='*80}")
    print("PODSUMOWANIE")
    print(f"{'='*80}")
    print(f"✓ Pomyślnie przetworzono: {success_count}")
    print(f"✗ Błędów: {error_count}")
    print(f"📁 Pliki zapisane w katalogu: {output_dir}")
    
    # Rozłącz VPN na końcu
    if vpn_manager:
        await vpn_manager.disconnect()
    
    if processed_files:
        print(f"\nPrzetworzone pliki:")
        for file_path in processed_files[:10]:  # Pokaż pierwsze 10
            print(f"  - {file_path}")
        if len(processed_files) > 10:
            print(f"  ... i {len(processed_files) - 10} więcej")


if __name__ == "__main__":
    asyncio.run(main())


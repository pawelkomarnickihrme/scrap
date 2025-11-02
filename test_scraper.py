#!/usr/bin/env python3
"""Test scrapera na rzeczywistej stronie."""

import asyncio
import sys
from scraper import scrape_perfume_data

async def test_scraper():
    url = "https://www.fragrantica.com/perfume/Lorenzo-Pazzaglia/Black-Sea-69652.html"
    
    print(f"Scrapowanie strony: {url}")
    print("...")
    
    try:
        data = await scrape_perfume_data(url)
        
        # Wyświetl tylko dane longevity
        longevity = data.get("longevity", {})
        
        print("\nDane LONGEVITY:")
        print(f"veryWeak: {longevity.get('veryWeak', 'BRAK')}")
        print(f"weak: {longevity.get('weak', 'BRAK')}")
        print(f"moderate: {longevity.get('moderate', 'BRAK')}")
        print(f"longLasting: {longevity.get('longLasting', 'BRAK')}")
        print(f"eternal: {longevity.get('eternal', 'BRAK')}")
        print(f"mostVoted: {longevity.get('mostVoted', 'BRAK')}")
        
        # Sprawdź czy są jakieś wartości
        has_values = any([
            longevity.get('veryWeak'),
            longevity.get('weak'),
            longevity.get('moderate'),
            longevity.get('longLasting'),
            longevity.get('eternal'),
        ])
        
        if has_values:
            print("\n✓ Scraper prawidłowo pobiera dane LONGEVITY!")
        else:
            print("\n✗ Scraper nie znalazł danych LONGEVITY")
            print("\nPełne dane głosowania:")
            print(data.get("longevity", {}))
        
    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_scraper())

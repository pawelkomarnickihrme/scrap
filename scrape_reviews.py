#!/usr/bin/env python3
"""
Program do scrapowania komentarzy/recenzji ze strony z sekcji #all-reviews.
Zapisuje komentarze do tablicy w pliku review.json.
"""

import json
import sys
import random
import asyncio
from typing import List, Optional, Dict

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from vpn_manager import VPNManager


# Lista User-Agent do rotacji (różne przeglądarki i systemy)
USER_AGENTS = [
    # Chrome na Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome na macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox na Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox na macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari na macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    # Edge na Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]


def get_random_headers() -> Dict[str, str]:
    """Generuje losowe nagłówki HTTP z rotacją User-Agent."""
    user_agent = random.choice(USER_AGENTS)
    
    # Różne Accept-Language w zależności od User-Agent
    if "Firefox" in user_agent:
        accept_language = random.choice([
            "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-US,en;q=0.9",
            "pl-PL,pl;q=0.9",
        ])
    else:
        accept_language = random.choice([
            "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-US,en;q=0.9,pl;q=0.8",
            "pl-PL,pl;q=0.9",
        ])
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": random.choice(["none", "same-origin"]),
        "Sec-Fetch-User": "?1",
        "Cache-Control": random.choice(["max-age=0", "no-cache", "no-store"]),
        "Referer": random.choice([
            "https://www.google.com/",
            "https://www.google.pl/",
            "https://www.fragrantica.com/",
            "",
        ]),
    }
    
    return headers


def clean_text(text: str) -> str:
    """Usuwa białe znaki i normalizuje tekst."""
    if not text:
        return ""
    return " ".join(text.split())


def extract_reviews(soup: BeautifulSoup) -> List[str]:
    """Wyciąga wszystkie recenzje z sekcji all-reviews jako tablicę stringów."""
    reviews = []
    
    # Szukaj elementów z itemprop="review" (recenzje są w elementach fragrance-review-box)
    review_elems = soup.find_all(itemprop="review")
    
    for review_elem in review_elems:
        # Wyciągnij tylko tekst recenzji
        review_body = review_elem.find(itemprop="reviewBody")
        if review_body:
            text = clean_text(review_body.get_text())
            if text and len(text) > 0:
                reviews.append(text)
    
    return reviews


async def scrape_reviews(url: str, vpn_manager: Optional[VPNManager] = None) -> List[str]:
    """Główna funkcja scrapująca recenzje.
    
    Args:
        url: URL strony do scrapowania
        vpn_manager: Opcjonalny menedżer VPN
    """
    # Dodaj #all-reviews do URL jeśli nie ma
    if "#all-reviews" not in url:
        url = url + "#all-reviews"
    
    # Upewnij się, że VPN jest połączony
    if vpn_manager:
        if not vpn_manager.is_connected():
            print("🔌 Łączenie z VPN przed scrapowaniem recenzji...")
            if not await vpn_manager.connect():
                print("⚠️  Nie udało się połączyć z VPN, kontynuowanie bez VPN...", file=sys.stderr)
    
    # Generuj losowe nagłówki
    headers = get_random_headers()
    
    # Dodaj losowe opóźnienie przed żądaniem (1-3 sekundy)
    delay = random.uniform(1.0, 3.0)
    await asyncio.sleep(delay)
    
    # Utwórz nowy crawler (czyści sesję i cookies)
    async with AsyncWebCrawler(
        headless=True,
        verbose=False,
        # Wyłącz cache i cookies aby uniknąć śledzenia
        cache_enabled=False,
    ) as crawler:
        # Użyj networkidle z dłuższym timeoutem i większym opóźnieniem
        # aby zapewnić pełne załadowanie JavaScript
        result = await crawler.arun(
            url=url,
            headers=headers,
            wait_for="networkidle",
            delay_before_return_html=0.0,  # Brak opóźnienia - maksymalna prędkość
        )
        
        # Sprawdź czy otrzymaliśmy błąd 429
        if result.status_code == 429:
            print("⚠️  Otrzymano błąd 429 (Too Many Requests).", file=sys.stderr)
            if vpn_manager:
                print("🔄 Zmienianie konfiguracji VPN...", file=sys.stderr)
                await vpn_manager.reconnect_with_new_config()
                # Dłuższe oczekiwanie po zmianie VPN (5-10 sekund)
                wait_time = random.uniform(5.0, 10.0)
                print(f"⏳ Oczekiwanie {wait_time:.1f}s po zmianie VPN...")
                await asyncio.sleep(wait_time)
            raise Exception("Błąd 429: Too Many Requests")
        
        if not result.success:
            # Sprawdź czy błąd zawiera informację o 429
            if "429" in str(result.error_message) or "too many" in str(result.error_message).lower():
                if vpn_manager:
                    print("🔄 Zmienianie konfiguracji VPN...", file=sys.stderr)
                    await vpn_manager.reconnect_with_new_config()
                    # Dłuższe oczekiwanie po zmianie VPN (5-10 sekund)
                    wait_time = random.uniform(5.0, 10.0)
                    print(f"⏳ Oczekiwanie {wait_time:.1f}s po zmianie VPN...")
                    await asyncio.sleep(wait_time)
            raise Exception(f"Nie udało się pobrać strony: {result.error_message}")
        
        html = result.html
        soup = BeautifulSoup(html, "html.parser")
        
        # Wyciągnij wszystkie recenzje
        reviews = extract_reviews(soup)
        
        return reviews


async def main():
    """Główna funkcja programu."""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Podaj URL strony do scrapowania: ").strip()
    
    if not url:
        print("Błąd: URL nie może być pusty", file=sys.stderr)
        sys.exit(1)
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    print(f"Scrapowanie recenzji ze strony: {url}")
    
    try:
        reviews = await scrape_reviews(url)
        
        # Zapisz do output.json (dodaj recenzje do istniejących danych)
        output_file = "output.json"
        
        # Załaduj istniejące dane z output.json jeśli istnieje
        existing_data = {}
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Plik {output_file} nie istnieje, tworzenie nowego pliku")
        except json.JSONDecodeError:
            print(f"⚠️  Błąd parsowania {output_file}, nadpisanie pliku")
        
        # Dodaj recenzje do danych jako klucz "review"
        existing_data["review"] = reviews
        
        # Zapisz zaktualizowane dane do output.json
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Znaleziono {len(reviews)} recenzji")
        print(f"✓ Recenzje zapisane do {output_file}")
        
    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(main())


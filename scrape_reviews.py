#!/usr/bin/env python3
"""
Program do scrapowania komentarzy/recenzji ze strony z sekcji #all-reviews.
Zapisuje komentarze do tablicy w pliku review.json.
"""

import json
import sys
import random
import asyncio
from typing import List, Optional

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from crawl4ai import ProxyConfig, BrowserConfig


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


async def scrape_reviews(url: str, proxy_config: Optional[ProxyConfig] = None) -> List[str]:
    """Główna funkcja scrapująca recenzje.
    
    Args:
        url: URL strony do scrapowania
        proxy_config: Opcjonalna konfiguracja proxy (ProxyConfig lub None)
    """
    # Dodaj #all-reviews do URL jeśli nie ma
    if "#all-reviews" not in url:
        url = url + "#all-reviews"
    
    # Konfiguracja nagłówków HTTP, aby uniknąć wykrycia
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    # Zwiększone opóźnienie przed requestem (5-10 sekund) - aby uniknąć 429
    await asyncio.sleep(random.uniform(5.0, 10.0))
    
    # Przygotuj BrowserConfig z proxy jeśli dostępne
    browser_config = None
    if proxy_config:
        browser_config = BrowserConfig(
            headless=True,
            proxy_config=proxy_config,
        )
    
    async with AsyncWebCrawler(
        headless=True,
        verbose=False,
        browser_config=browser_config,
    ) as crawler:
        # Użyj networkidle z dłuższym timeoutem i większym opóźnieniem
        # aby zapewnić pełne załadowanie JavaScript
        result = await crawler.arun(
            url=url,
            headers=headers,
            wait_for="networkidle",
            delay_before_return_html=random.uniform(3.0, 5.0),  # Dłuższe opóźnienie przed zwróceniem HTML (3-5 sekund)
        )
        
        # Dodatkowe opóźnienie po pobraniu strony (symulacja czytania strony)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        if not result.success:
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


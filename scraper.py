#!/usr/bin/env python3
"""
Program do scrapowania danych o perfumach ze strony.
Używa Crawl4AI i BeautifulSoup do pobrania i parsowania danych.
"""

import json
import re
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag, NavigableString
from crawl4ai import AsyncWebCrawler


def clean_text(text: str) -> str:
    """Usuwa białe znaki i normalizuje tekst."""
    if not text:
        return ""
    return " ".join(text.split())


def remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """Usuwa wszystkie skrypty, iframy i SVG z HTML."""
    # Usuń wszystkie skrypty
    for script in soup.find_all("script"):
        script.decompose()
    
    # Usuń wszystkie iframy
    for iframe in soup.find_all("iframe"):
        iframe.decompose()
    
    # Usuń wszystkie elementy SVG
    for svg in soup.find_all("svg"):
        svg.decompose()


def extract_perfume_name(soup: BeautifulSoup) -> str:
    """Wyciąga nazwę perfum."""
    # Spróbuj znaleźć w h1 z itemprop="name"
    h1 = soup.find("h1", itemprop="name")
    if h1:
        # Usuń small tag jeśli istnieje
        small = h1.find("small")
        if small:
            small.decompose()
        return clean_text(h1.get_text())
    
    # Alternatywnie w tytule strony
    title = soup.find("title")
    if title:
        return clean_text(title.get_text())
    
    return ""


def extract_brand(soup: BeautifulSoup) -> Optional[str]:
    """Wyciąga markę perfum."""
    # Spróbuj znaleźć w elemencie z itemprop="brand"
    brand_elem = soup.find(itemprop="brand")
    if brand_elem:
        brand_name = brand_elem.find(itemprop="name")
        if brand_name:
            return clean_text(brand_name.get_text())
        return clean_text(brand_elem.get_text())
    
    return None


def extract_description(soup: BeautifulSoup) -> str:
    """Wyciąga opis perfum."""
    # Spróbuj znaleźć w elemencie z itemprop="description"
    desc_elem = soup.find(itemprop="description")
    if desc_elem:
        return clean_text(desc_elem.get_text())
    
    # Alternatywnie szukaj w meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return clean_text(meta_desc.get("content"))
    
    return ""


def extract_main_image_url(soup: BeautifulSoup, base_url: str) -> str:
    """Wyciąga URL głównego obrazu."""
    # Spróbuj znaleźć obraz z itemprop="image"
    img = soup.find("img", itemprop="image")
    if img:
        src = img.get("src") or img.get("data-src")
        if src:
            return urljoin(base_url, src)
    
    # Alternatywnie znajdź pierwszy obraz w sekcji głównej
    picture = soup.find("picture")
    if picture:
        img = picture.find("img")
        if img:
            src = img.get("src") or img.get("data-src")
            if src:
                return urljoin(base_url, src)
    
    return ""


def extract_rating(soup: BeautifulSoup) -> Optional[float]:
    """Wyciąga ocenę perfum."""
    # Spróbuj znaleźć w elemencie z itemprop="ratingValue"
    rating_elem = soup.find(itemprop="ratingValue")
    if rating_elem:
        try:
            return float(clean_text(rating_elem.get_text()))
        except ValueError:
            pass
    
    # Szukaj w różnych formatach oceny
    rating_patterns = [
        r"rating[\"']?\s*[:=]\s*([\d.]+)",
        r"(\d+\.\d+)\s*/\s*\d+",
        r"(\d+)\s*z\s*\d+",
    ]
    text = soup.get_text()
    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    
    return None


def extract_rating_count(soup: BeautifulSoup) -> Optional[int]:
    """Wyciąga liczbę ocen."""
    # Spróbuj znaleźć w elemencie z itemprop="ratingCount" lub "reviewCount"
    count_elem = soup.find(itemprop=lambda x: x in ["ratingCount", "reviewCount"])
    if count_elem:
        try:
            # Najpierw sprawdź atrybut content (bardziej niezawodny)
            content = count_elem.get("content")
            if content:
                return int(content)
            
            # Jeśli nie ma content, spróbuj wyciągnąć z tekstu
            text = clean_text(count_elem.get_text())
            # Wyciągnij liczby z tekstu (usuń przecinki/separatory)
            numbers = re.findall(r"\d+", text.replace(",", "").replace(".", ""))
            if numbers:
                return int(numbers[0])
        except (ValueError, AttributeError):
            pass
    
    return None


def extract_user_reviews(soup: BeautifulSoup) -> List[str]:
    """Wyciąga recenzje użytkowników."""
    reviews = []
    
    # Szukaj elementów z itemprop="review"
    review_elems = soup.find_all(itemprop="review")
    
    for review_elem in review_elems:
        # Znajdź tekst recenzji - zwykle w elemencie z itemprop="reviewBody" lub w div z klasą
        review_body = review_elem.find(itemprop="reviewBody")
        if review_body:
            text = clean_text(review_body.get_text())
        else:
            # Spróbuj znaleźć główny tekst recenzji (pomiń ratingi i metadane)
            # Szukaj w elementach z klasą fragrance-review-box
            review_box = review_elem.find(class_=re.compile(r"review", re.I))
            if review_box:
                text = clean_text(review_box.get_text())
            else:
                # Pobierz cały tekst ale usuń ratingi
                text = clean_text(review_elem.get_text())
        
        # Filtruj recenzje (minimalna długość, nie tylko ratingi)
        if text and len(text) > 30:  # Minimum 30 znaków dla znaczącej recenzji
            # Usuń duplikaty
            if text not in reviews:
                reviews.append(text)
    
    return reviews[:50]  # Limit do 50 recenzji


def extract_notes(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Wyciąga nuty zapachowe (top, heart, base)."""
    notes = {
        "topNotes": [],
        "heartNotes": [],
        "baseNotes": [],
    }
    
    # Znajdź sekcję pyramid
    pyramid = soup.find(id="pyramid")
    if not pyramid:
        return notes
    
    # Mapowanie polskich nazw na klucze
    category_map = {
        "Nuty głowy": "topNotes",
        "Top notes": "topNotes",
        "Nuty serca": "heartNotes",
        "Heart notes": "heartNotes",
        "Middle notes": "heartNotes",
        "Nuty bazy": "baseNotes",
        "Base notes": "baseNotes",
    }
    
    # Znajdź wszystkie nagłówki h4 w sekcji pyramid
    h4_tags = pyramid.find_all("h4")
    current_category = None
    
    for h4 in h4_tags:
        h4_text = clean_text(h4.get_text())
        for key, category in category_map.items():
            if key.lower() in h4_text.lower():
                current_category = category
                break
        
        if current_category:
            # Znajdź wszystkie linki w następnym kontenerze po h4
            # Szukaj w następnych siblingach lub w kontenerach div
            container = h4.find_next_sibling()
            if not container:
                # Spróbuj znaleźć kontener w rodzicu
                parent = h4.find_parent()
                if parent:
                    # Szukaj w następnych elementach w tym samym kontenerze
                    for sibling in parent.find_next_siblings(limit=3):
                        if sibling.name == "div":
                            container = sibling
                            break
            
            if container:
                # Szukaj linków z nutami zapachowymi (typowo są w div z flexbox)
                links = container.find_all("a", href=re.compile(r"/nuty|/notes", re.I))
                
                for link in links:
                    # Tekst nuty jest często po linku (jako tekst w rodzicu)
                    parent_div = link.find_parent("div")
                    if parent_div:
                        # Pobierz cały tekst z div, ale usuń tekst z linka (link-span)
                        link_text = link.get_text()
                        parent_text = clean_text(parent_div.get_text())
                        # Usuń tekst z linka z tekstu rodzica
                        note_text = parent_text.replace(link_text, "").strip()
                        
                        # Jeśli nie ma tekstu, spróbuj pobrać bezpośrednio z linka
                        if not note_text:
                            # Usuń link-span z linka
                            link_copy = BeautifulSoup(str(link), "html.parser")
                            for span in link_copy.find_all(class_="link-span"):
                                span.decompose()
                            note_text = clean_text(link_copy.get_text())
                        
                        # Pomiń puste i krótkie teksty
                        if note_text and len(note_text) > 1 and note_text not in notes[current_category]:
                            notes[current_category].append(note_text)
                
                # Jeśli nie znaleziono linków, szukaj tekstu bezpośrednio w kontenerze
                if not links:
                    # Szukaj w div z nutami (czasem są wyświetlane jako tekst)
                    text_containers = container.find_all("div", recursive=True)
                    for text_container in text_containers:
                        text = clean_text(text_container.get_text())
                        if text and len(text) > 2 and len(text) < 100 and text not in notes[current_category]:
                            # Sprawdź czy to wygląda na nazwę nuty (nie za długi, nie za krótki)
                            if 2 < len(text) < 50:
                                notes[current_category].append(text)
    
    return notes


def extract_similar_perfumes(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Wyciąga podobne perfumy."""
    similar = []
    
    # Szukaj sekcji z podobnymi perfumami - typowe nazwy
    similar_keywords = ["podobne", "similar", "this reminds", "reminds me"]
    
    for keyword in similar_keywords:
        # Szukaj w nagłówkach, linkach, divach
        sections = soup.find_all(
            lambda tag: tag.name in ["h2", "h3", "h4", "div", "section"]
            and keyword.lower() in clean_text(tag.get_text()).lower()
        )
        
        for section in sections:
            # Znajdź wszystkie linki w sekcji lub w następnych elementach
            container = section.find_next_sibling() or section.parent
            if container:
                links = container.find_all("a", href=re.compile(r"/perfume|/perfumes", re.I))
                for link in links:
                    name = clean_text(link.get_text())
                    if name and len(name) > 2 and name not in [s["name"] for s in similar]:
                        similar.append({"name": name})
    
    return similar[:20]  # Limit do 20 podobnych


def extract_recommended_perfumes(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Wyciąga rekomendowane perfumy."""
    recommended = []
    
    # Szukaj sekcji z rekomendacjami - typowe nazwy
    rec_keywords = ["rekomendowane", "recommended", "suggested", "you may also like"]
    
    for keyword in rec_keywords:
        # Szukaj w nagłówkach, linkach, divach
        sections = soup.find_all(
            lambda tag: tag.name in ["h2", "h3", "h4", "div", "section"]
            and keyword.lower() in clean_text(tag.get_text()).lower()
        )
        
        for section in sections:
            # Znajdź wszystkie linki w sekcji lub w następnych elementach
            container = section.find_next_sibling() or section.parent
            if container:
                links = container.find_all("a", href=re.compile(r"/perfume|/perfumes", re.I))
                for link in links:
                    name = clean_text(link.get_text())
                    if name and len(name) > 2 and name not in [r["name"] for r in recommended]:
                        recommended.append({"name": name})
    
    return recommended[:20]  # Limit do 20 rekomendowanych


def extract_voting_data(soup: BeautifulSoup, category: str, options_mapping: Dict[str, List[str]]) -> Dict[str, Any]:
    """Wyciąga dane głosowania dla danej kategorii.
    
    options_mapping: Dict z angielską nazwą opcji jako kluczem i listą polskich wariantów jako wartością
    """
    data = {}
    most_voted_value = None
    max_votes = 0
    
    # Mapowanie nazw kategorii na tytuły w HTML
    category_titles = {
        "longevity": ["LONGEVITY"],
        "projection": ["PROJECTION", "SIŁA PROJEKCJI"],
        "gender": ["GENDER", "PŁEĆ"],
        "valueForMoney": ["VALUE FOR MONEY", "STOSUNEK JAKOŚĆ/CENA"],
        "emotionRating": ["EMOTION", "ODCZUCIA"],
        "season": ["SEASON", "PORA ROKU"],
        "timeOfDay": ["TIME OF DAY", "PORA DNIA"],
        "sillage": ["SILLAGE"],
    }
    
    # Znajdź sekcję kategorii po tytule
    category_section = None
    titles = category_titles.get(category, [category.upper()])
    
    for title in titles:
        # Szukaj span lub innego elementu z tekstem tytułu
        title_elem = soup.find(lambda tag: tag.name in ["span", "h2", "h3", "h4", "div"] 
                               and clean_text(tag.get_text()).upper() == title.upper())
        if title_elem:
            # Znajdź kontener sekcji (zwykle rodzic lub dziadek)
            category_section = title_elem.find_parent(class_=re.compile(r"cell|section|container", re.I))
            if not category_section:
                category_section = title_elem.find_parent("div")
            if category_section:
                break
    
    # Jeśli nie znaleziono sekcji, szukaj w całym soup
    search_soup = category_section if category_section else soup
    
    # Znajdź wszystkie elementy vote-button-name w sekcji
    vote_names = search_soup.find_all(class_="vote-button-name")
    
    for vote_name_elem in vote_names:
        vote_name_text = clean_text(vote_name_elem.get_text()).lower()
        
        # Znajdź kontener grid-x który zawiera ten element
        grid_container = vote_name_elem.find_parent(class_=re.compile(r"grid", re.I))
        if not grid_container:
            grid_container = vote_name_elem.find_parent()
        
        # Znajdź odpowiadający element z liczbą głosów w tym samym kontenerze
        if grid_container:
            vote_legend = grid_container.find(class_="vote-button-legend")
            if vote_legend:
                vote_count_text = clean_text(vote_legend.get_text())
                numbers = re.findall(r"\d+", vote_count_text)
                if numbers:
                    vote_count = int(numbers[0])
                    
                    # Sprawdź, która opcja pasuje
                    for eng_option, variants in options_mapping.items():
                        for variant in variants:
                            if variant.lower() in vote_name_text:
                                data[eng_option] = vote_count
                                if vote_count > max_votes:
                                    max_votes = vote_count
                                    most_voted_value = eng_option
                                break
    
    if most_voted_value and max_votes > 0:
        data["mostVoted"] = most_voted_value
    
    return data


def extract_all_voting_data(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """Wyciąga wszystkie dane głosowania."""
    return {
        "longevity": extract_voting_data(
            soup,
            "longevity",
            {
                "veryWeak": ["very weak", "bardzo słaba"],
                "weak": ["weak", "słaba"],
                "moderate": ["moderate", "przeciętna"],
                "longLasting": ["long lasting", "długotrwała"],
                "eternal": ["eternal", "wieczna"],
            },
        ),
        "projection": extract_voting_data(
            soup,
            "projection",
            {
                "soft": ["łagodna", "soft"],
                "average": ["przeciętna", "average"],
                "strong": ["duża", "strong"],
                "huge": ["olbrzymia", "huge"],
            },
        ),
        "gender": extract_voting_data(
            soup,
            "gender",
            {
                "feminine": ["kobieta", "feminine", "kobieta / unisex"],
                "unisex": ["unisex"],
                "masculine": ["mężczyzna", "masculine", "mężczyzna / unisex"],
            },
        ),
        "valueForMoney": extract_voting_data(
            soup,
            "valueForMoney",
            {
                "priceTooHigh": ["cena za wysoka", "price too high"],
                "overpriced": ["zawyżona cena", "overpriced"],
                "fair": ["ok", "fair"],
                "goodQuality": ["dobra jakość", "good quality"],
                "excellentQuality": ["doskonała jakość", "excellent quality"],
            },
        ),
        "emotionRating": extract_voting_data(
            soup,
            "emotionRating",
            {
                "loveIt": ["kocham", "love it"],
                "likeIt": ["lubię", "like it"],
                "okay": ["ok", "okay"],
                "dislike": ["nie lubię", "dislike"],
                "hateIt": ["nienawidzę", "hate it"],
            },
        ),
        "season": extract_voting_data(
            soup,
            "season",
            {
                "winter": ["zima", "winter"],
                "spring": ["wiosna", "spring"],
                "summer": ["lato", "summer"],
                "autumn": ["jesień", "autumn"],
            },
        ),
        "timeOfDay": extract_voting_data(
            soup,
            "timeOfDay",
            {
                "day": ["dzień", "day"],
                "evening": ["wieczór", "evening"],
            },
        ),
        "sillage": extract_voting_data(
            soup,
            "sillage",
            {
                "intimate": ["intimate"],
                "moderate": ["moderate"],
                "strong": ["strong"],
                "enormous": ["enormous"],
            },
        ),
    }


async def scrape_perfume_data(url: str) -> Dict[str, Any]:
    """Główna funkcja scrapująca dane o perfumach."""
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        
        if not result.success:
            raise Exception(f"Nie udało się pobrać strony: {result.error_message}")
        
        html = result.html
        soup = BeautifulSoup(html, "html.parser")
        
        # Znajdź element #main-content
        main_content = soup.find(id="main-content")
        if not main_content:
            raise Exception("Nie znaleziono elementu #main-content")
        
        # Usuń niechciane elementy
        remove_unwanted_elements(main_content)
        
        # Wyciągnij wszystkie dane
        perfume_data = {
            "perfumeName": extract_perfume_name(main_content),
            "brand": extract_brand(main_content),
            "description": extract_description(main_content),
            "mainImageUrl": extract_main_image_url(main_content, url),
            "userReviews": extract_user_reviews(main_content),
            "rating": extract_rating(main_content),
            "ratingCount": extract_rating_count(main_content),
            "notes": extract_notes(main_content),
            "similarPerfumes": extract_similar_perfumes(main_content),
            "recommendedPerfumes": extract_recommended_perfumes(main_content),
        }
        
        # Dodaj dane głosowania
        voting_data = extract_all_voting_data(main_content)
        perfume_data.update(voting_data)
        
        return perfume_data


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
    
    print(f"Scrapowanie strony: {url}")
    
    try:
        data = await scrape_perfume_data(url)
        
        # Zapisz do output.js
        output_file = "output.js"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Dane zapisane do {output_file}")
        
    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(main())


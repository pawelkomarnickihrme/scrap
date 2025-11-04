#!/usr/bin/env python3
"""
Program do scrapowania danych o perfumach ze strony.
Używa Crawl4AI i BeautifulSoup do pobrania i parsowania danych.
"""

import json
import re
import sys
import random
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag, NavigableString
from crawl4ai import AsyncWebCrawler
from crawl4ai import ProxyConfig, BrowserConfig
from crawl4ai.proxy_strategy import RoundRobinProxyStrategy


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


def extract_people_also_like(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Wyciąga perfumy z sekcji 'People who like this also like'."""
    perfumes = []
    
    # Znajdź span z tekstem "People who like this also like"
    title_span = soup.find("span", string=re.compile(r"People who like this also like", re.I))
    if not title_span:
        # Alternatywnie szukaj w span który zawiera ten tekst
        title_span = soup.find("span", string=lambda text: text and "People who like this also like" in text)
    
    if not title_span:
        return perfumes
    
    # Znajdź kontener strike-title (rodzic span)
    strike_title = title_span.find_parent(class_="strike-title")
    if not strike_title:
        # Jeśli nie ma klasy strike-title, użyj bezpośredniego rodzica
        strike_title = title_span.find_parent()
    
    if not strike_title:
        return perfumes
    
    # Znajdź następny element carousel (może być następnym siblingem lub w następnym div)
    carousel = strike_title.find_next_sibling(class_=re.compile(r"carousel", re.I))
    if not carousel:
        # Szukaj w następnych siblingach
        current = strike_title.next_sibling
        while current:
            if hasattr(current, 'get') and isinstance(current, Tag):
                if 'carousel' in current.get('class', []):
                    carousel = current
                    break
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
    
    if not carousel:
        # Spróbuj znaleźć carousel w rodzicu
        parent = strike_title.find_parent()
        if parent:
            carousel = parent.find(class_=re.compile(r"carousel", re.I))
    
    if not carousel:
        return perfumes
    
    # Znajdź wszystkie carousel-cell w carousel
    cells = carousel.find_all(class_="carousel-cell")
    
    for cell in cells:
        # Znajdź link w cell
        link = cell.find("a", href=re.compile(r"/perfume", re.I))
        if not link:
            continue
        
        # Wyciągnij markę
        brand_span = link.find("span", class_="brand")
        brand = ""
        if brand_span:
            brand = clean_text(brand_span.get_text())
        
        # Wyciągnij nazwę perfum (w span z klasą ztworowseclipse lub jako tekst linka)
        name_span = link.find("span", class_="ztworowseclipse")
        name = ""
        if name_span:
            name = clean_text(name_span.get_text())
        else:
            # Jeśli nie ma span z nazwą, spróbuj wyciągnąć z całego tekstu linka
            link_text = clean_text(link.get_text())
            # Usuń markę z tekstu
            if brand:
                link_text = link_text.replace(brand, "").strip()
            name = link_text
        
        # Jeśli nadal nie ma nazwy, spróbuj wyciągnąć z href lub alt obrazu
        if not name:
            img = link.find("img")
            if img and img.get("alt"):
                alt_text = img.get("alt")
                # Usuń markę z alt jeśli jest
                if brand and brand in alt_text:
                    name = alt_text.replace(brand, "").strip()
                else:
                    name = alt_text
        
        # Normalizuj nazwę i markę
        name = clean_text(name)
        brand = clean_text(brand)
        
        # Dodaj tylko jeśli mamy nazwę
        if name and len(name) > 1:
            # Sprawdź duplikaty (normalizując nazwy)
            name_normalized = name.lower().strip()
            brand_normalized = brand.lower().strip() if brand else ""
            
            is_duplicate = False
            for existing in perfumes:
                existing_name = existing.get("name", "").lower().strip()
                existing_brand = existing.get("brand", "").lower().strip()
                if (name_normalized == existing_name and 
                    (not brand_normalized or not existing_brand or brand_normalized == existing_brand)):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                perfume_data = {"name": name}
                if brand:
                    perfume_data["brand"] = brand
                perfumes.append(perfume_data)
    
    return perfumes


def extract_reminds_me_perfumes(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Wyciąga perfumy z sekcji 'This perfume reminds me of'."""
    perfumes = []
    
    # Szukaj span z tekstem "reminds me" lub podobnym (podobnie jak w extract_people_also_like)
    reminds_keywords = [
        "this perfume reminds me",
        "reminds me of",
        "this reminds me",
        "reminds me",
        "przypomina mi",
        "to perfum przypomina mi",
    ]
    
    title_span = None
    for keyword in reminds_keywords:
        # Najpierw szukaj span z dokładnym tekstem
        title_span = soup.find("span", string=re.compile(keyword, re.I))
        if not title_span:
            # Alternatywnie szukaj w span który zawiera ten tekst
            title_span = soup.find("span", string=lambda text: text and keyword.lower() in text.lower())
        if title_span:
            break
    
    # Jeśli nie znaleziono span, szukaj w div
    if not title_span:
        for keyword in reminds_keywords:
            title_div = soup.find(
                lambda tag: tag.name == "div"
                and keyword.lower() in clean_text(tag.get_text()).lower()
            )
            if title_div:
                # Znajdź span w tym div lub użyj div jako punktu odniesienia
                title_span = title_div.find("span")
                if not title_span:
                    # Użyj div jako punktu odniesienia
                    title_span = title_div
                break
    
    if not title_span:
        return perfumes
    
    # Znajdź kontener strike-title (rodzic span)
    strike_title = title_span.find_parent(class_="strike-title")
    if not strike_title:
        # Jeśli nie ma klasy strike-title, użyj bezpośredniego rodzica
        strike_title = title_span.find_parent()
    
    if not strike_title:
        return perfumes
    
    # Znajdź następny element carousel (może być następnym siblingem lub w następnym div)
    carousel = strike_title.find_next_sibling(class_=re.compile(r"carousel", re.I))
    if not carousel:
        # Szukaj w następnych siblingach
        current = strike_title.next_sibling
        while current:
            if hasattr(current, 'get') and isinstance(current, Tag):
                if 'carousel' in current.get('class', []):
                    carousel = current
                    break
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
    
    if not carousel:
        # Spróbuj znaleźć carousel w rodzicu
        parent = strike_title.find_parent()
        if parent:
            carousel = parent.find(class_=re.compile(r"carousel", re.I))
    
    if not carousel:
        # Szukaj flickity-slider (typowy kontener dla carousel)
        flickity = strike_title.find_next_sibling(class_="flickity-slider")
        if not flickity:
            flickity = strike_title.find_parent(class_="flickity-slider")
        if flickity:
            carousel = flickity
    
    # Jeśli nadal nie znaleziono, szukaj flickity-slider w następnych elementach po strike_title
    if not carousel:
        # Szukaj w następnych siblingach strike_title
        current = strike_title.next_sibling
        while current:
            if hasattr(current, 'get') and isinstance(current, Tag):
                if 'flickity-slider' in current.get('class', []):
                    carousel = current
                    break
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
    
    # Jeśli nadal nie znaleziono, szukaj wszystkich flickity-slider i sprawdź czy któryś jest w sekcji z "reminds me"
    if not carousel:
        all_flickity = soup.find_all(class_="flickity-slider")
        for flickity in all_flickity:
            # Sprawdź czy w okolicy tego flickity-slider jest tekst "reminds me"
            parent = flickity.find_parent()
            if parent:
                parent_text = clean_text(parent.get_text()).lower()
                if any(keyword in parent_text for keyword in ["reminds me", "this perfume reminds", "przypomina mi", "to perfum przypomina"]):
                    carousel = flickity
                    break
    
    if not carousel:
        return perfumes
    
    # Znajdź wszystkie carousel-cell w carousel
    cells = carousel.find_all(class_="carousel-cell")
    
    for cell in cells:
        # Znajdź link w cell
        link = cell.find("a", href=re.compile(r"/perfume", re.I))
        if not link:
            continue
        
        # Wyciągnij brand i name z href (format: /perfume/Brand/Name-ID.html)
        href = link.get("href", "")
        brand = ""
        name = ""
        
        if href:
            # Parsuj href: /perfume/Brand/Name-ID.html
            # Nazwa może zawierać myślniki, więc szukamy wszystkiego przed ostatnim -ID.html
            match = re.match(r"/perfume/([^/]+)/(.+?)-(\d+)\.html", href)
            if match:
                brand = match.group(1).replace("-", " ")
                name = match.group(2).replace("-", " ")
        
        # Jeśli nie udało się wyciągnąć z href, spróbuj z alt/title obrazu
        if not name or not brand:
            img = link.find("img")
            if img:
                alt_text = img.get("alt", "") or img.get("title", "")
                if alt_text:
                    # Format: "Name Brand" lub "Brand Name"
                    parts = alt_text.split()
                    if len(parts) >= 2:
                        # Często ostatnie słowa to brand, reszta to name
                        # Spróbuj znaleźć brand w ostatnich 2-3 słowach
                        if not brand:
                            # Sprawdź czy któryś z ostatnich elementów wygląda na brand
                            for i in range(max(1, len(parts) - 2), len(parts)):
                                potential_brand = " ".join(parts[i:])
                                if len(potential_brand) > 2:
                                    brand = potential_brand
                                    name = " ".join(parts[:i])
                                    break
                        if not name:
                            name = alt_text.replace(brand, "").strip() if brand else alt_text
        
        # Jeśli nadal nie ma nazwy, spróbuj wyciągnąć z tekstu linka
        if not name:
            link_text = clean_text(link.get_text())
            if link_text and len(link_text) > 2:
                name = link_text
                # Usuń markę z nazwy jeśli jest
                if brand and brand in name:
                    name = name.replace(brand, "").strip()
        
        # Normalizuj nazwę i markę
        name = clean_text(name)
        brand = clean_text(brand)
        
        # Dodaj tylko jeśli mamy nazwę
        if name and len(name) > 1:
            # Sprawdź duplikaty (normalizując nazwy)
            name_normalized = name.lower().strip()
            brand_normalized = brand.lower().strip() if brand else ""
            
            is_duplicate = False
            for existing in perfumes:
                existing_name = existing.get("name", "").lower().strip()
                existing_brand = existing.get("brand", "").lower().strip()
                if (name_normalized == existing_name and 
                    (not brand_normalized or not existing_brand or brand_normalized == existing_brand)):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                perfume_data = {"name": name}
                if brand:
                    perfume_data["brand"] = brand
                perfumes.append(perfume_data)
    
    return perfumes


def extract_recommended_perfumes(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Wyciąga rekomendowane perfumy z sekcji 'People who like this also like'."""
    # Użyj dedykowanej funkcji dla "People who like this also like"
    perfumes = extract_people_also_like(soup)
    
    # Jeśli nie znaleziono, spróbuj alternatywnych metod
    if not perfumes:
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
                        if name and len(name) > 2:
                            # Sprawdź duplikaty
                            if name not in [r["name"] for r in perfumes]:
                                perfumes.append({"name": name})
    
    return perfumes[:20]  # Limit do 20 rekomendowanych


def extract_pros(soup: BeautifulSoup) -> List[str]:
    """Wyciąga pros (zalety) z sekcji Pros w HTML."""
    pros_list = []
    
    # Znajdź główny div z Pros (z klasą cell small-12 medium-6)
    # Szukamy diva który zawiera tekst "Pros" w nagłówku
    pros_section = None
    for div in soup.find_all('div', class_='cell small-12 medium-6'):
        header = div.find('h4', class_='header')
        if header and 'Pros' in clean_text(header.get_text()):
            pros_section = div
            break
    
    if not pros_section:
        return pros_list
    
    # Znajdź wszystkie span wewnątrz divów z klasą "cell small-12"
    # które są wewnątrz sekcji pros (pomijając spany z liczbami w num-votes-sp)
    for item_div in pros_section.find_all('div', class_='cell small-12'):
        # Znajdź span który NIE jest wewnątrz num-votes-sp
        all_spans = item_div.find_all('span')
        for span in all_spans:
            # Sprawdź czy span nie jest wewnątrz num-votes-sp
            parent_num_votes = span.find_parent('div', class_='num-votes-sp')
            if not parent_num_votes:
                text = clean_text(span.get_text())
                # Upewnij się że to nie jest liczba (czyli pros tekst)
                if text and not text.isdigit():
                    pros_list.append(text)
                    break  # Weź tylko pierwszy span który nie jest liczbą
    
    # Zwróć tylko pierwsze 5 pros
    return pros_list[:5]


def extract_cons(soup: BeautifulSoup) -> List[str]:
    """Wyciąga cons (wady) z sekcji Cons w HTML."""
    cons_list = []
    
    # Znajdź główny div z Cons (z klasą cell small-12 medium-6)
    # Szukamy diva który zawiera tekst "Cons" w nagłówku
    cons_section = None
    for div in soup.find_all('div', class_='cell small-12 medium-6'):
        header = div.find('h4', class_='header')
        if header and 'Cons' in clean_text(header.get_text()):
            cons_section = div
            break
    
    if not cons_section:
        return cons_list
    
    # Znajdź wszystkie span wewnątrz divów z klasą "cell small-12"
    # które są wewnątrz sekcji cons (pomijając spany z liczbami w num-votes-sp)
    for item_div in cons_section.find_all('div', class_='cell small-12'):
        # Znajdź span który NIE jest wewnątrz num-votes-sp
        all_spans = item_div.find_all('span')
        for span in all_spans:
            # Sprawdź czy span nie jest wewnątrz num-votes-sp
            parent_num_votes = span.find_parent('div', class_='num-votes-sp')
            if not parent_num_votes:
                text = clean_text(span.get_text())
                # Upewnij się że to nie jest liczba (czyli cons tekst)
                if text and not text.isdigit():
                    cons_list.append(text)
                    break  # Weź tylko pierwszy span który nie jest liczbą
    
    # Zwróć tylko pierwsze 5 cons
    return cons_list[:5]


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
        "gender": ["GENDER", "PŁEĆ"],
        "valueForMoney": ["VALUE FOR MONEY", "STOSUNEK JAKOŚĆ/CENA"],
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
                    # Strategia: najpierw dokładne dopasowania, potem częściowe (najdłuższe najpierw)
                    matched = False
                    vote_name_lower = vote_name_text.lower()
                    vote_name_normalized = vote_name_lower.replace(" ", "")
                    
                    # KROK 1: Sprawdź dokładne dopasowania (po normalizacji spacji)
                    for eng_option, variants in options_mapping.items():
                        for variant in variants:
                            variant_normalized = variant.lower().replace(" ", "")
                            if variant_normalized == vote_name_normalized:
                                data[eng_option] = vote_count
                                if vote_count > max_votes:
                                    max_votes = vote_count
                                    most_voted_value = eng_option
                                matched = True
                                break
                        if matched:
                            break
                    
                    # KROK 2: Jeśli nie znaleziono dokładnego, sprawdź częściowe dopasowania
                    # Sortuj opcje od najdłuższych wariantów do najkrótszych (żeby "more female" pasowało przed "female")
                    if not matched:
                        sorted_options = sorted(
                            options_mapping.items(),
                            key=lambda x: max(len(v.replace(" ", "")) for v in x[1]),
                            reverse=True
                        )
                        for eng_option, variants in sorted_options:
                            # Sortuj warianty od najdłuższych do najkrótszych
                            sorted_variants = sorted(variants, key=lambda v: len(v.replace(" ", "")), reverse=True)
                            for variant in sorted_variants:
                                variant_lower = variant.lower()
                                # Sprawdź czy wariant jest zawarty w tekście (ale nie na odwrót!)
                                # To zapobiega dopasowaniu "kobieta" do "kobieta / unisex"
                                if variant_lower in vote_name_lower:
                                    data[eng_option] = vote_count
                                    if vote_count > max_votes:
                                        max_votes = vote_count
                                        most_voted_value = eng_option
                                    matched = True
                                    break
                            if matched:
                                break
    
    if most_voted_value and max_votes > 0:
        data["mostVoted"] = most_voted_value
    
    return data


def extract_percentage_width_data(soup: BeautifulSoup, category: str, options_mapping: Dict[str, List[str]]) -> Dict[str, Any]:
    """Wyciąga wartości procentowe width dla danej kategorii (season, timeOfDay).
    
    Szuka elementów z vote-button-legend i odpowiadających im wartości width w stylach.
    
    options_mapping: Dict z angielską nazwą opcji jako kluczem i listą wariantów jako wartością
    """
    data = {}
    most_voted_value = None
    max_percentage = 0.0
    
    # Mapowanie nazw kategorii na tytuły w HTML
    category_titles = {
        "season": ["SEASON", "PORA ROKU"],
        "timeOfDay": ["TIME OF DAY", "PORA DNIA"],
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
    
    # Znajdź wszystkie elementy vote-button-legend w sekcji
    vote_legends = search_soup.find_all(class_="vote-button-legend")
    
    for vote_legend in vote_legends:
        legend_text = clean_text(vote_legend.get_text()).lower()
        
        # Znajdź kontener który zawiera ten element (szukaj rodzica z index)
        container = vote_legend.find_parent(attrs={"index": True})
        if not container:
            # Jeśli nie ma index, szukaj w rodzicu
            container = vote_legend.find_parent()
        
        if container:
            # Znajdź div z voting-small-chart-size w tym kontenerze
            chart_div = container.find("div", class_="voting-small-chart-size")
            if chart_div:
                # Znajdź wszystkie divy z stylem
                inner_divs = chart_div.find_all("div", style=True)
                for div in inner_divs:
                    style = div.get("style", "")
                    # Szukamy diva z background rgb (nie rgba) - to jest wewnętrzny div z width
                    if "background:" in style and "rgb(" in style and "rgba(" not in style:
                        # Wyodrębnij width z stylu
                        width_match = re.search(r"width:\s*([\d.]+)%", style)
                        if width_match:
                            width_percent = float(width_match.group(1))
                            
                            # Sprawdź, która opcja pasuje
                            matched = False
                            legend_lower = legend_text.lower()
                            legend_normalized = legend_lower.replace(" ", "")
                            
                            # KROK 1: Sprawdź dokładne dopasowania
                            for eng_option, variants in options_mapping.items():
                                for variant in variants:
                                    variant_normalized = variant.lower().replace(" ", "")
                                    if variant_normalized == legend_normalized:
                                        data[eng_option] = width_percent
                                        if width_percent > max_percentage:
                                            max_percentage = width_percent
                                            most_voted_value = eng_option
                                        matched = True
                                        break
                                if matched:
                                    break
                            
                            # KROK 2: Jeśli nie znaleziono dokładnego, sprawdź częściowe dopasowania
                            if not matched:
                                sorted_options = sorted(
                                    options_mapping.items(),
                                    key=lambda x: max(len(v.replace(" ", "")) for v in x[1]),
                                    reverse=True
                                )
                                for eng_option, variants in sorted_options:
                                    sorted_variants = sorted(variants, key=lambda v: len(v.replace(" ", "")), reverse=True)
                                    for variant in sorted_variants:
                                        variant_lower = variant.lower()
                                        if variant_lower in legend_lower:
                                            data[eng_option] = width_percent
                                            if width_percent > max_percentage:
                                                max_percentage = width_percent
                                                most_voted_value = eng_option
                                            matched = True
                                            break
                                    if matched:
                                        break
                            break
    
    if most_voted_value and max_percentage > 0:
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
        "gender": extract_voting_data(
            soup,
            "gender",
            {
                # Ważne: kolejność i długość wariantów jest istotna - dłuższe/more specyficzne najpierw
                "moreFemale": ["more female", "morefemale", "more feminine"],
                "female": ["female", "kobieta", "feminine", "woman", "women", "kobiet", "for women"],
                "unisex": ["unisex", "uni-sex"],
                "moreMale": ["more male", "moremale", "more masculine"],
                "male": ["male", "mężczyzna", "masculine", "man", "men", "mężczyzn", "for men"],
            },
        ),
        "valueForMoney": extract_voting_data(
            soup,
            "valueForMoney",
            {
                "priceTooHigh": ["way overpriced", "cena za wysoka", "price too high"],
                "overpriced": ["overpriced", "zawyżona cena"],
                "fair": ["ok", "fair"],
                "goodQuality": ["good value", "dobra jakość", "good quality"],
                "excellentQuality": ["great value", "doskonała jakość", "excellent quality"],
            },
        ),
        "season": extract_percentage_width_data(
            soup,
            "season",
            {
                "winter": ["winter", "zima"],
                "spring": ["spring", "wiosna"],
                "summer": ["summer", "lato"],
                "fall": ["fall", "autumn", "jesień"],
            },
        ),
        "timeOfDay": extract_percentage_width_data(
            soup,
            "timeOfDay",
            {
                "day": ["day", "dzień"],
                "night": ["night", "noc", "evening", "wieczór"],
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


async def scrape_perfume_data(url: str, max_retries: int = 3, proxy_config: Optional[ProxyConfig] = None) -> Dict[str, Any]:
    """Główna funkcja scrapująca dane o perfumach.
    
    Args:
        url: URL strony do scrapowania
        max_retries: Maksymalna liczba prób przy błędach 429
        proxy_config: Opcjonalna konfiguracja proxy (ProxyConfig lub None)
    """
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
    
    for attempt in range(max_retries):
        try:
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
                    wait_for="networkidle",  # Czekaj na zakończenie ładowania sieci
                    delay_before_return_html=random.uniform(3.0, 5.0),  # Dłuższe opóźnienie przed zwróceniem HTML (3-5 sekund)
                )
                
                # Sprawdź czy otrzymaliśmy błąd 429
                if result.status_code == 429:
                    wait_time = (2 ** attempt) * random.uniform(30, 60)  # Exponential backoff: 30-60s, 60-120s, 120-240s
                    print(f"⚠️  Otrzymano błąd 429 (Too Many Requests). Czekam {wait_time:.1f} sekund przed ponowną próbą...", file=sys.stderr)
                    await asyncio.sleep(wait_time)
                    continue  # Spróbuj ponownie
                
                # Dodatkowe opóźnienie po pobraniu strony (symulacja czytania strony)
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                if not result.success:
                    # Sprawdź czy błąd zawiera informację o 429
                    if "429" in str(result.error_message) or "too many" in str(result.error_message).lower():
                        wait_time = (2 ** attempt) * random.uniform(30, 60)
                        print(f"⚠️  Wykryto błąd 429. Czekam {wait_time:.1f} sekund przed ponowną próbą...", file=sys.stderr)
                        await asyncio.sleep(wait_time)
                        continue
                    raise Exception(f"Nie udało się pobrać strony: {result.error_message}")
                
                # Jeśli dotarliśmy tutaj, request był udany
                break
                
        except Exception as e:
            # Jeśli to ostatnia próba, rzuć wyjątek
            if attempt == max_retries - 1:
                raise
            
            # Sprawdź czy błąd zawiera informację o 429
            error_str = str(e).lower()
            if "429" in error_str or "too many" in error_str or "rate limit" in error_str:
                wait_time = (2 ** attempt) * random.uniform(30, 60)
                print(f"⚠️  Wykryto błąd rate limiting. Czekam {wait_time:.1f} sekund przed ponowną próbą...", file=sys.stderr)
                await asyncio.sleep(wait_time)
                continue
            else:
                # Jeśli to inny błąd, rzuć wyjątek od razu
                raise
    
    # Jeśli dotarliśmy tutaj, oznacza to że request był udany
    # (gdyby wszystkie próby się nie powiodły, wyjątek zostałby rzucony wcześniej)
    html = result.html
    soup = BeautifulSoup(html, "html.parser")
    
    # Znajdź element #main-content - spróbuj kilka razy z opóźnieniem jeśli nie znaleziono
    main_content = soup.find(id="main-content")
    if not main_content:
        # Jeśli nie znaleziono, spróbuj użyć całego body jako fallback
        # lub sprawdź czy HTML w ogóle został pobrany
        if not html or len(html) < 100:
            raise Exception(f"Nie udało się pobrać zawartości strony. HTML ma tylko {len(html) if html else 0} znaków.")
        
        # Sprawdź czy strona została przekierowana lub czy jest błąd
        if "error" in html.lower() or "not found" in html.lower() or "404" in html.lower():
            raise Exception("Strona zwróciła błąd (404 lub podobny)")
        
        # Spróbuj użyć body jako fallback
        body = soup.find("body")
        if body:
            print("⚠️  Ostrzeżenie: Nie znaleziono #main-content, używam body jako fallback", file=sys.stderr)
            main_content = body
        else:
            raise Exception("Nie znaleziono elementu #main-content ani body. Strona może wymagać JavaScript lub być zablokowana.")
    
    # Usuń niechciane elementy
    remove_unwanted_elements(main_content)
    
    # Wyciągnij wszystkie dane (BEZ userReviews - będą w osobnym pliku)
    perfume_data = {
        "perfumeName": extract_perfume_name(main_content),
        "brand": extract_brand(main_content),
        "description": extract_description(main_content),
        "mainImageUrl": extract_main_image_url(main_content, url),
        "rating": extract_rating(main_content),
        "ratingCount": extract_rating_count(main_content),
        "notes": extract_notes(main_content),
        "similarPerfumes": extract_similar_perfumes(main_content),
        "recommendedPerfumes": extract_recommended_perfumes(main_content),
        "remindsMePerfumes": extract_reminds_me_perfumes(main_content),
        "pros": extract_pros(main_content),
        "cons": extract_cons(main_content),
    }
    
    # Dodaj dane głosowania
    voting_data = extract_all_voting_data(main_content)
    perfume_data.update(voting_data)
    
    return perfume_data


def load_proxy_config() -> Optional[ProxyConfig]:
    """Ładuje konfigurację proxy z zmiennej środowiskowej PROXY.
    
    Obsługiwane formaty:
    - http://username:password@ip:port
    - http://ip:port
    - socks5://ip:port
    - ip:port:username:password
    - ip:port
    
    Returns:
        ProxyConfig lub None jeśli proxy nie jest ustawione
    """
    import os
    proxy_str = os.getenv("PROXY")
    if not proxy_str:
        return None
    
    try:
        return ProxyConfig.from_string(proxy_str.strip())
    except Exception as e:
        print(f"⚠️  Błąd podczas ładowania proxy: {e}", file=sys.stderr)
        return None


def load_proxy_list() -> List[ProxyConfig]:
    """Ładuje listę proxy z zmiennej środowiskowej PROXIES (rozdzielone przecinkami).
    
    Returns:
        Lista ProxyConfig lub pusta lista jeśli proxy nie są ustawione
    """
    import os
    proxies_str = os.getenv("PROXIES")
    if not proxies_str:
        return []
    
    proxies = []
    for proxy_str in proxies_str.split(","):
        proxy_str = proxy_str.strip()
        if proxy_str:
            try:
                proxies.append(ProxyConfig.from_string(proxy_str))
            except Exception as e:
                print(f"⚠️  Błąd podczas ładowania proxy '{proxy_str}': {e}", file=sys.stderr)
    return proxies


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
    
    # Załaduj proxy jeśli dostępne
    proxy_config = load_proxy_config()
    if proxy_config:
        print(f"✓ Używam proxy: {proxy_config.server}")
    else:
        print("ℹ️  Proxy nie jest skonfigurowane (ustaw zmienną PROXY aby użyć proxy)")
    
    try:
        data = await scrape_perfume_data(url, proxy_config=proxy_config)
        
        # Zapisz do output.js
        output_file = "output.js"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Dane zapisane do {output_file}")
        
        # Zapisz również do output.json
        output_json_file = "output.json"
        with open(output_json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Dane zapisane do {output_json_file}")
        
        # Uruchom testy wartości LONGEVITY
        print("\n" + "=" * 50)
        print("Uruchamianie testów wartości LONGEVITY...")
        print("=" * 50)
        
        try:
            from test_output_longevity import test_longevity_values
            test_passed = test_longevity_values(output_file)
            if not test_passed:
                print("\n⚠️  Ostrzeżenie: Testy wartości LONGEVITY nie przeszły pomyślnie")
                print("   Sprawdź dane w pliku output.js\n")
        except ImportError:
            print("⚠️  Nie można zaimportować modułu testowego")
        except Exception as e:
            print(f"⚠️  Błąd podczas uruchamiania testów: {e}")
        
        # Uruchom testy wartości SILLAGE
        print("\n" + "=" * 50)
        print("Uruchamianie testów wartości SILLAGE...")
        print("=" * 50)
        
        try:
            from test_output_sillage import test_sillage_values
            test_passed = test_sillage_values(output_file)
            if not test_passed:
                print("\n⚠️  Ostrzeżenie: Testy wartości SILLAGE nie przeszły pomyślnie")
                print("   Sprawdź dane w pliku output.js\n")
        except ImportError:
            print("⚠️  Nie można zaimportować modułu testowego SILLAGE")
        except Exception as e:
            print(f"⚠️  Błąd podczas uruchamiania testów SILLAGE: {e}")
        
        # Uruchom testy wartości GENDER
        print("\n" + "=" * 50)
        print("Uruchamianie testów wartości GENDER...")
        print("=" * 50)
        
        try:
            from test_output_gender import test_gender_values
            test_passed = test_gender_values(output_file)
            if not test_passed:
                print("\n⚠️  Ostrzeżenie: Testy wartości GENDER nie przeszły pomyślnie")
                print("   Sprawdź dane w pliku output.js\n")
        except ImportError:
            print("⚠️  Nie można zaimportować modułu testowego GENDER")
        except Exception as e:
            print(f"⚠️  Błąd podczas uruchamiania testów GENDER: {e}")
        
        # Uruchom testy wartości PRICE VALUE
        print("\n" + "=" * 50)
        print("Uruchamianie testów wartości PRICE VALUE...")
        print("=" * 50)
        
        try:
            from test_output_price_value import test_price_value_values
            test_passed = test_price_value_values(output_file)
            if not test_passed:
                print("\n⚠️  Ostrzeżenie: Testy wartości PRICE VALUE nie przeszły pomyślnie")
                print("   Sprawdź dane w pliku output.js\n")
        except ImportError:
            print("⚠️  Nie można zaimportować modułu testowego PRICE VALUE")
        except Exception as e:
            print(f"⚠️  Błąd podczas uruchamiania testów PRICE VALUE: {e}")
        
        # Uruchom testy sekcji "People who like this also like"
        print("\n" + "=" * 50)
        print("Uruchamianie testów sekcji 'People who like this also like'...")
        print("=" * 50)
        
        try:
            from test_output_also_like import test_also_like_perfumes
            test_passed = test_also_like_perfumes(output_file)
            if not test_passed:
                print("\n⚠️  Ostrzeżenie: Testy sekcji 'People who like this also like' nie przeszły pomyślnie")
                print("   Sprawdź dane w pliku output.js\n")
        except ImportError:
            print("⚠️  Nie można zaimportować modułu testowego 'People who like this also like'")
        except Exception as e:
            print(f"⚠️  Błąd podczas uruchamiania testów 'People who like this also like': {e}")
        
        # Po zakończeniu wszystkich testów, uruchom scrape_reviews.py
        print("\n" + "=" * 50)
        print("Uruchamianie scrape_reviews.py...")
        print("=" * 50)
        
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "scrape_reviews.py", url],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                print(f"⚠️  Błąd: scrape_reviews.py zakończył się z kodem {result.returncode}")
        except Exception as e:
            print(f"⚠️  Błąd podczas uruchamiania scrape_reviews.py: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Błąd: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(main())


# Scraper Perfum

Program do scrapowania danych o perfumach ze strony internetowej przy użyciu BeautifulSoup i Crawl4AI.

## Wymagania

- Python 3.7+
- Zainstalowane pakiety z `requirements.txt`

## Instalacja

```bash
pip install -r requirements.txt
```

## Użycie

```bash
python scraper.py [URL]
```

Lub bez argumentu (program zapyta o URL):

```bash
python scraper.py
```

## Wynik

Program zapisuje dane do pliku `output.js` w formacie JSON zgodnym z interfejsem `PerfumeScrapedData`.

## Funkcjonalności

- Pobiera dane z elementu `#main-content`
- Usuwa wszystkie skrypty, iframy i elementy SVG
- Wyciąga następujące dane:
  - Nazwa perfum
  - Marka
  - Opis
  - URL głównego obrazu
  - Recenzje użytkowników
  - Ocena i liczba ocen
  - Nuty zapachowe (top, heart, base)
  - Podobne i rekomendowane perfumy
  - Dane głosowania (trwałość, projekcja, płeć, wartość za pieniądze, emocje, sezon, pora dnia)


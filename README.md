# Scraper Perfum

Program do scrapowania danych o perfumach ze strony internetowej przy użyciu BeautifulSoup i Crawl4AI.

## Wymagania

- Python 3.7+
- Zainstalowane pakiety z `requirements.txt`

## Instalacja

1. Utwórz środowisko wirtualne:
```bash
python3 -m venv venv
```

2. Aktywuj środowisko wirtualne:
```bash
source venv/bin/activate
```

3. Zainstaluj wymagane pakiety:
```bash
pip install -r requirements.txt
```

## Użycie

Pamiętaj, aby najpierw aktywować środowisko wirtualne:

```bash
source venv/bin/activate
python scraper.py [URL]
```

Lub bez argumentu (program zapyta o URL):

```bash
source venv/bin/activate
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




















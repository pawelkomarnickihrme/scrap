#!/usr/bin/env python3
"""
Test funkcji wykrywania błędów 404.
"""

from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """Usuwa białe znaki i normalizuje tekst."""
    if not text:
        return ""
    return " ".join(text.split())


def is_404_error_page(html: str, status_code: int = None) -> bool:
    """Sprawdza czy strona jest stroną błędu 404.

    Args:
        html: Zawartość HTML strony
        status_code: Kod statusu HTTP (jeśli dostępny)

    Returns:
        True jeśli strona jest błędem 404, False w przeciwnym razie
    """
    # Jeśli mamy kod statusu 404, to na pewno błąd
    if status_code == 404:
        return True

    # Jeśli mamy inny kod statusu błędu (4xx, 5xx), prawdopodobnie błąd
    if status_code and status_code >= 400:
        return True

    # Jeśli nie mamy kodu statusu lub jest 200, sprawdzamy zawartość HTML
    if not html:
        return False

    soup = BeautifulSoup(html, "html.parser")
    html_lower = html.lower()

    # Sprawdź tytuł strony
    title = soup.find("title")
    if title:
        title_text = clean_text(title.get_text()).lower()
        if "404" in title_text or "not found" in title_text or "page not found" in title_text:
            return True

    # Sprawdź czy strona zawiera charakterystyczne elementy błędów 404
    # Szukaj specyficznych wzorców błędów 404, nie tylko słów
    error_indicators = [
        "404 error",
        "page not found",
        "the page you are looking for",
        "this page doesn't exist",
        "error 404",
        "http 404",
        "404 - not found"
    ]

    for indicator in error_indicators:
        if indicator in html_lower:
            return True

    # Sprawdź czy strona jest bardzo krótka (typowe dla stron błędów)
    # ale zawiera słowa kluczowe błędów w widocznej treści (nie w JavaScript)
    if len(html) < 2000 and ("error" in html_lower or "not found" in html_lower):
        # Dodatkowe sprawdzenie - czy to nie jest normalna strona zawierająca te słowa
        # w JavaScript lub innych niewidocznych elementach
        body = soup.find("body")
        if body:
            # Usuń skrypty przed wyciągnięciem tekstu
            body_copy = BeautifulSoup(str(body), "html.parser")
            for script in body_copy.find_all("script"):
                script.decompose()
            for style in body_copy.find_all("style"):
                style.decompose()

            body_text = clean_text(body_copy.get_text()).lower()
            # Jeśli główna widoczna treść strony jest bardzo krótka i zawiera specyficzne błędy 404, to prawdopodobnie 404
            error_patterns_in_body = [
                "404 error", "404 not found", "page not found", "error 404",
                "http 404", "404 - not found", "the page you are looking for",
                "this page doesn't exist"
            ]
            if len(body_text) < 500 and any(pattern in body_text for pattern in error_patterns_in_body):
                return True

    # Sprawdź czy strona nie zawiera podstawowych elementów strony perfum
    # (np. brak nazwy perfum, opisu itp.)
    if not soup.find("h1", itemprop="name") and not soup.find(id="pyramid"):
        # Jeśli strona nie zawiera podstawowych elementów perfum
        # i jest krótka, prawdopodobnie to błąd
        if len(html) < 5000:
            return True

    return False


def test_404_detection():
    """Testuje funkcję wykrywania błędów 404."""

    # Test 1: Rzeczywista strona błędu 404
    test_html_404 = '''<!DOCTYPE html>
<html>
<head><title>404 - Page Not Found</title></head>
<body><h1>404 Error</h1><p>The page you are looking for does not exist.</p></body>
</html>'''

    # Test 2: Normalna strona perfum (zawierająca słowa "error" w JavaScript)
    test_html_normal = '''<!DOCTYPE html>
<html>
<head><title>Aramis Aramis 113</title></head>
<body>
<h1 itemprop="name">Aramis 113</h1>
<div id="pyramid">Some content about notes</div>
<script>
if (error) {
    console.log('error handling in javascript');
}
if (not_found) {
    console.log('not found handling');
}
</script>
<p>This perfume contains 404 different molecules or something</p>
</body>
</html>'''

    # Test 3: Strona z błędem w tytule
    test_html_title_error = '''<!DOCTYPE html>
<html>
<head><title>Error 404</title></head>
<body><p>Some content</p></body>
</html>'''

    # Test 4: Bardzo krótka strona z błędem
    test_html_short_error = '''<html><body><h1>Error</h1><p>Not found</p></body></html>'''

    print("Testing 404 detection function:")
    print("=" * 50)

    test_cases = [
        ("Real 404 page", test_html_404, True),
        ("Normal perfume page", test_html_normal, False),
        ("Page with error in title", test_html_title_error, True),
        ("Short page with error", test_html_short_error, True),
    ]

    for name, html, expected in test_cases:
        result = is_404_error_page(html)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{name}: {status} (expected: {expected}, got: {result})")

    # Test z kodem statusu
    print("\nTesting with status codes:")
    print(f"Status 404: {is_404_error_page('<html></html>', 404)}")
    print(f"Status 200: {is_404_error_page('<html></html>', 200)}")


if __name__ == "__main__":
    test_404_detection()

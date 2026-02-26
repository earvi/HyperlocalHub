import pytest
from bs4 import BeautifulSoup
from scraper import calculate_link_density, parse_smart_date, parse_generic
from unittest.mock import MagicMock, patch

def test_link_density():
    html = "<div><p>Some text</p><a href='#'>Link</a></div>"
    soup = BeautifulSoup(html, "html.parser")
    # text len = 9 ("Some text") + 4 ("Link") = 13? strip=True
    # div text: "Some textLink" -> 13
    # link text: "Link" -> 4
    # density: 4/13 ~= 0.3
    node = soup.find("div")
    density = calculate_link_density(node)
    assert 0 < density < 1

    html_links = "<div><a href='#'>A</a><a href='#'>B</a></div>"
    # text: "AB" (2), links: "A" (1) + "B" (1) = 2. Density 1.0
    soup = BeautifulSoup(html_links, "html.parser")
    assert calculate_link_density(soup.find("div")) == 1.0

def test_smart_date():
    assert parse_smart_date("Jan 01, 2025") is not None
    assert parse_smart_date("Posted: 2 days ago") is not None
    assert parse_smart_date("Not a date") is None

@patch("scraper.fetch_html")
def test_parse_generic_heuristics(mock_fetch):
    # Mock HTML with a "News List" structure
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>
                <a href="/home">Home</a>
                <a href="/about">About</a>
            </nav>
            <div class="news-container">
                <div class="card">
                    <a href="/news/1">Important Update about Campus</a>
                    <span class="date">Jan 29, 2026</span>
                </div>
                <div class="card">
                    <a href="/news/2">Traffic Alert: Road Closed</a>
                    <span class="date">Jan 28, 2026</span>
                </div>
                <div class="card">
                    <a href="/news/3">Weather Warning: Rain</a>
                </div>
            </div>
            <footer>
                <a href="/contact">Contact Us</a>
            </footer>
        </body>
    </html>
    """
    mock_fetch.return_value = BeautifulSoup(html, "html.parser")
    
    src = {"url": "http://test.com", "name": "Test Source", "category": "General"}
    results = parse_generic(src)
    
    # Should detect 3 articles
    # Should ignore nav and footer links
    assert len(results) == 3
    titles = [r["title"] for r in results]
    assert "Important Update about Campus" in titles
    assert "Traffic Alert: Road Closed" in titles
    assert "Weather Warning: Rain" in titles
    assert "Home" not in titles
    assert "Contact Us" not in titles
    
    # Check date parsing
    r1 = next(r for r in results if r["title"] == "Important Update about Campus")
    assert r1["published_at"].year == 2026

from unittest.mock import MagicMock, patch
from scraper import parse_generic
from bs4 import BeautifulSoup

def test_parse_generic_opengraph():
    html = """
    <html>
        <head>
            <meta property="og:title" content="Test Article Title">
            <meta property="og:description" content="This is a description.">
            <meta property="og:url" content="http://example.com/article">
        </head>
    </html>
    """
    
    with patch('scraper.fetch_html') as mock_fetch:
        mock_fetch.return_value = BeautifulSoup(html, "html.parser")
        
        src = {"url": "http://example.com", "name": "Test Source", "category": "News"}
        results = parse_generic(src)
        
        assert len(results) == 1
        assert results[0]["title"] == "Test Article Title"
        assert results[0]["summary"] == "This is a description."

def test_parse_generic_fallback_list():
    html = """
    <html>
        <body>
            <a href="/article1">Important News Story 1</a>
            <a href="/login">Login</a>
            <a href="/article2">Another Great Update 2</a>
        </body>
    </html>
    """
    
    with patch('scraper.fetch_html') as mock_fetch:
        mock_fetch.return_value = BeautifulSoup(html, "html.parser")
        
        src = {"url": "http://example.com", "name": "Test Source"}
        results = parse_generic(src)
        
        # Should catch the two articles but ignore login
        titles = [r["title"] for r in results]
        assert "Important News Story 1" in titles
        assert "Another Great Update 2" in titles
        assert "Login" not in titles

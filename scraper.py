import hashlib
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser
from urllib.parse import urljoin

from models import get_engine, get_session, Base, Alert, SourceHealth
from config_sources import SOURCES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

engine = get_engine()
Base.metadata.create_all(engine)
db = get_session(engine)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HyperlocalHub/1.0"
}


def uid_gen(source, title):
    return hashlib.sha256(f"{source}|{title}".encode("utf-8")).hexdigest()


def fetch_html(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def parse_mgu_archive(src):
    url = src["url"]
    soup = fetch_html(url)

    cards = soup.select("article.elementor-post") or soup.select("div.elementor-post")
    results = []

    for card in cards:
        title_tag = card.select_one(".elementor-post__title a") or card.find("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag.get("href")
        if link:
            link = urljoin(url, link)

        date_tag = card.select_one(".elementor-post-date") or card.select_one("time")
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            try:
                published = dateparser.parse(date_text, dayfirst=True)
            except Exception:
                published = datetime.utcnow()
        else:
            published = datetime.utcnow()

        summary_tag = card.select_one(".elementor-post__excerpt") or card.find("p")
        summary = summary_tag.get_text(strip=True) if summary_tag else None

        results.append(
            {
                "title": title,
                "url": link,
                "published_at": published,
                "summary": summary,
                "category": src.get("category", "University"),
                "source": src["name"],
            }
        )

    return results





def calculate_link_density(node):
    """Estimate how much of the node is link text vs plain text."""
    text_length = len(node.get_text(strip=True))
    if text_length == 0:
        return 0
    link_length = sum(len(a.get_text(strip=True)) for a in node.find_all("a"))
    return link_length / text_length


def parse_smart_date(text):
    """Attempt to parse a date string using dateutil."""
    if not text:
        return None
    try:
        # Filter out common noise words before parsing
        text = text.lower().replace("posted:", "").replace("published:", "").strip()
        return dateparser.parse(text, fuzzy=True)
    except Exception:
        return None


def parse_generic(src):
    url = src["url"]
    soup = fetch_html(url)
    results = []
    
    # 1. Metadata Strategy (Universal)
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    if og_title and len(og_title.get("content", "")) > 10:
        results.append({
            "title": og_title["content"],
            "url": soup.find("meta", property="og:url")["content"] if soup.find("meta", property="og:url") else url,
            "published_at": datetime.utcnow(),
            "summary": og_desc["content"] if og_desc else None,
            "category": src.get("category", "General"),
            "source": src["name"],
        })
        # If we found a specific article via metadata, we might still want to look for lists if it's a homepage
        # Deep path usually implies specific article, UNLESS it's a category/archive page
        is_archive = any(x in url for x in ["category", "archive", "page", "news", "events", "notifications"])
        if len(url.split("/")) > 4 and not is_archive: 
            return results

    # 2. List Detection Strategy
    # Find container with most relevant <a> tags
    candidates = []
    for node in soup.find_all(["div", "section", "ul", "main"]):
        # Heuristics for a "News List" container:
        # - Has many links
        # - Links have significant text length
        # - Container isn't a nav/footer
        
        classes = " ".join(node.get("class", [])).lower()
        if any(x in classes for x in ["nav", "menu", "footer", "sidebar", "header"]):
            continue

        links = node.find_all("a")
        valid_links = []
        for link in links:
            text = link.get_text(strip=True)
            href = link.get("href")
            if not text or not href or len(text) < 15: continue
            if href.startswith("javascript") or href.startswith("#"): continue
            valid_links.append(link)
            
        if len(valid_links) >= 3:
            candidates.append((node, valid_links))

    # Sort candidates by number of valid links, take top
    candidates.sort(key=lambda x: len(x[1]), reverse=True)
    
    seen_urls = set()
    added_count = 0
    
    if candidates:
        best_node, best_links = candidates[0]
        for link in best_links[:15]: # Limit to top 15 per source
            href = link.get("href")
            full_url = urljoin(url, href)
            
            if full_url in seen_urls: continue
            seen_urls.add(full_url)

            title = link.get_text(strip=True)
            
            # Try to find a date nearby
            published = datetime.utcnow()
            # Look at siblings or parent's siblings
            date_candidate = link.find_next_sibling(["span", "time", "small"])
            if not date_candidate:
                date_candidate = link.parent.find_next_sibling(["span", "time", "small"])
            
            if date_candidate:
                dt = parse_smart_date(date_candidate.get_text(strip=True))
                if dt: published = dt

            results.append({
                "title": title,
                "url": full_url,
                "published_at": published,
                "summary": None, # Could resolve 1 level deep to get summary
                "category": src.get("category", "General"),
                "source": src["name"],
            })
            added_count += 1

    # Fallback to pure link scan if no container found
    if added_count == 0:
        for tag in soup.find_all("a")[:50]:
            text = tag.get_text(strip=True)
            href = tag.get("href")
            if not text or not href or len(text) < 20: continue
            
            full_url = urljoin(url, href)
            if full_url in seen_urls: continue
            seen_urls.add(full_url)
            
            results.append({
                "title": text,
                "url": full_url,
                "published_at": datetime.utcnow(),
                "summary": None,
                "category": src.get("category", "General"),
                "source": src["name"],
            })

    return results


def log_health(source_key, status, message=""):
    record = SourceHealth(
        source_key=source_key,
        status=status,
        message=message[:500],
        checked_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()


def scrape(target_source=None):
    print("Scraping started...")

    sources_to_scrape = []
    
    if target_source:
        sources_to_scrape = [target_source]
    else:
        # Fetch from DB
        from models import Source
        db_sources = db.query(Source).all()
        for s in db_sources:
            sources_to_scrape.append({
                "key": s.key,
                "name": s.name,
                "url": s.url,
                "category": s.category
            })
        
        # Add config sources if any (legacy support)
        sources_to_scrape.extend(SOURCES)

    for src in sources_to_scrape:
        print(f"Checking source: {src['name']}")
        try:
            extracted = parse_generic(src)
            log_health(src["key"], "OK", f"Fetched {len(extracted)} alerts")
        except Exception as e:
            log_health(src["key"], "ERROR", str(e))
            print(f"  !! Error scraping {src['name']}: {e}")
            continue

        added = 0
        for item in extracted:
            unique = uid_gen(item["source"], item["title"])
            if db.query(Alert).filter_by(uid=unique).first():
                continue

            alert = Alert(
                uid=unique,
                title=item["title"],
                url=item["url"],
                summary=item["summary"],
                category=item["category"],
                source=item["source"],
                published_at=item["published_at"],
                fetched_at=datetime.utcnow(),
            )
            
            # Simple keyword-based dummy geocoding for demo
            title_lower = item["title"].lower()
            if "university" in title_lower or "mgu" in title_lower:
                alert.lat = 9.6548
                alert.lon = 76.5413
                alert.location = "MGU Campus"
            elif "traffic" in title_lower or "road" in title_lower:
                alert.lat = 9.5916
                alert.lon = 76.5222
                alert.location = "Kottayam Town"
            elif "library" in title_lower:
                alert.lat = 9.6580
                alert.lon = 76.5450
                alert.location = "University Library"
            
            db.add(alert)
            db.commit() # Commit to get ID
            
            # Index for Search
            try:
                from services.search_service import index_alert
                index_alert(alert)
            except Exception as e:
                print(f"  !! Indexing failed: {e}")

            # Trigger Push (Experimental)
            try:
                from services.push_service import send_push_to_all
                # Send push for every new alert (MVP)
                send_push_to_all(title=f"New Alert: {item['title']}", url=f"/?q={item['title']}")
            except Exception as e:
                print(f"  !! Push trigger failed: {e}")

            added += 1

        print(f"  -> Added {added} new alerts from {src['name']}")

    print("Scraping completed.")

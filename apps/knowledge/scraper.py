"""
Sayt scraping mexanizmi.
Berilgan URL dagi saytni crawl qilib, sahifalar kontentini matnli chunklarga ajratadi.
"""

import re
import ssl
import logging
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Scraping chegaralari
MAX_PAGES = 15
MAX_PAGE_SIZE = 500_000  # 500KB
REQUEST_TIMEOUT = 10
CHUNK_SIZE = 800  # so'zlar soni (taxminan)
CHUNK_OVERLAP = 100  # overlap so'zlar soni


def _make_request(url):
    """
    URL ga GET so'rov yuboradi va HTML kontentni qaytaradi.
    """
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uz,en;q=0.5',
        })
        resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx)
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'application/xhtml' not in content_type:
            return None
        data = resp.read(MAX_PAGE_SIZE)
        # Encoding aniqlash
        charset = 'utf-8'
        if 'charset=' in content_type:
            charset = content_type.split('charset=')[-1].strip().split(';')[0]
        try:
            return data.decode(charset)
        except (UnicodeDecodeError, LookupError):
            return data.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning("Sahifani yuklashda xatolik: %s — %s", url, e)
        return None


def _extract_text(html):
    """
    HTMLdan foydalanuvchiga ko'rinadigan asosiy kontentni ajratib oladi.
    Keraksiz elementlarni (nav, footer, script, style) olib tashlaydi.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Sahifa sarlavhasini olish
    title = ''
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Keraksiz elementlarni o'chirish
    for tag_name in ['script', 'style', 'nav', 'footer', 'header', 'aside',
                     'noscript', 'iframe', 'svg', 'form']:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Reklama / cookie / popup elementlarni o'chirish
    for attr_val in ['cookie', 'popup', 'modal', 'banner', 'advertisement', 'ad-']:
        for tag in soup.find_all(attrs={'class': re.compile(attr_val, re.I)}):
            tag.decompose()
        for tag in soup.find_all(attrs={'id': re.compile(attr_val, re.I)}):
            tag.decompose()

    # Asosiy kontentni olish (main yoki body)
    main = soup.find('main') or soup.find('article') or soup.find('body')
    if not main:
        main = soup

    # Matnni olish
    text = main.get_text(separator='\n', strip=True)

    # Bo'sh qatorlarni tozalash
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    clean_text = '\n'.join(lines)

    return title, clean_text


def _extract_links(html, base_url, base_domain):
    """
    HTMLdan faqat shu domendagi ichki havolalarni ajratib oladi.
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        # Fragment va javascript linklar o'tkazib yuboriladi
        if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
            continue
        full_url = urljoin(base_url, href)
        # Fragment olib tashlash
        full_url = full_url.split('#')[0]
        parsed = urlparse(full_url)
        # Faqat HTTP(S) va shu domen
        if parsed.scheme not in ('http', 'https'):
            continue
        link_domain = parsed.netloc.lower().replace('www.', '')
        if link_domain != base_domain:
            continue
        # Fayl linklar o'tkazib yuboriladi
        skip_ext = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
                     '.mp4', '.mp3', '.zip', '.rar', '.doc', '.docx', '.xls', '.xlsx')
        if any(parsed.path.lower().endswith(ext) for ext in skip_ext):
            continue
        links.add(full_url)
    return links


def _chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Matnni so'zlar bo'yicha overlapli chunklarga ajratadi.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= len(words):
            break
        start = end - overlap

    return chunks


def scrape_website(url, max_pages=MAX_PAGES):
    """
    Berilgan sayt URL-ini crawl qiladi va sahifalarning matn chunkalarini qaytaradi.

    Returns:
        list[dict]: Har bir element:
            - 'url': sahifa URL-i
            - 'title': sahifa sarlavhasi
            - 'chunks': list[str] — matn chunklari
    """
    # URL-ni normalizatsiya
    if not url.startswith('http://') and not url.startswith('https://'):
        url = f'https://{url}'

    parsed = urlparse(url)
    base_domain = parsed.netloc.lower().replace('www.', '')
    if not base_domain:
        logger.error("URL dan domen aniqlanmadi: %s", url)
        return []

    visited = set()
    to_visit = [url]
    results = []

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        # Normalizatsiya (trailing slash)
        normalized = current_url.rstrip('/')
        if normalized in visited:
            continue
        visited.add(normalized)

        logger.info("Scraping: %s (%d/%d)", current_url, len(visited), max_pages)

        html = _make_request(current_url)
        if not html:
            continue

        title, text = _extract_text(html)
        if not text or len(text.split()) < 20:
            # Juda qisqa sahifalarni o'tkazib yuborish
            continue

        chunks = _chunk_text(text)
        if chunks:
            results.append({
                'url': current_url,
                'title': title,
                'chunks': chunks,
            })

        # Yangi linklar qo'shish
        new_links = _extract_links(html, current_url, base_domain)
        for link in new_links:
            norm_link = link.rstrip('/')
            if norm_link not in visited and link not in to_visit:
                to_visit.append(link)

    logger.info("Scraping yakunlandi: %d sahifa, %d chunk",
                len(results),
                sum(len(r['chunks']) for r in results))

    return results

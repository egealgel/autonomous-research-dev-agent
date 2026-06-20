from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

USER_AGENT = "ARDA-Research-Bot/0.1 (+https://github.com/egealgel/autonomous-research-dev-agent)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
MAX_BODY_BYTES = 2_000_000


@dataclass
class ScrapedPage:
    url: str
    title: str
    text: str


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_url(url: str) -> str:
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        if len(response.content) > MAX_BODY_BYTES:
            raise ValueError(f"Response too large: {len(response.content)} bytes")
        return response.text


def extract_main_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return title, "\n".join(lines)


def scrape(url: str) -> ScrapedPage:
    html = fetch_url(url)
    title, text = extract_main_text(html)
    return ScrapedPage(url=url, title=title, text=text)


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    if not text:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks

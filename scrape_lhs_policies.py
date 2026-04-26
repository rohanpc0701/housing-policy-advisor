"""
Local Housing Solutions - Housing Policy Library Scraper
=========================================================
Scrapes all policy briefs from localhousingsolutions.org/housing-policy-library/
and outputs chunked text ready for ingestion into ChromaDB.

Usage:
    pip install requests beautifulsoup4 chromadb sentence-transformers
    python scrape_lhs_policies.py

Output:
    - lhs_policies_raw/        : one .txt file per policy brief
    - lhs_policies_chunks.json : chunked documents ready for ChromaDB ingestion
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# -- Config -------------------------------------------------------------------

LIBRARY_URL = "https://www.localhousingsolutions.org/housing-policy-library/"
RAW_DIR = "lhs_policies_raw"
CHUNKS_FILE = "lhs_policies_chunks.json"
CHUNK_SIZE = 500  # words per chunk
CHUNK_OVERLAP = 50  # words of overlap between chunks
DELAY = 1.5  # seconds between requests -- be polite to the server
USER_AGENT_EMAIL = os.getenv("LHS_USER_AGENT_EMAIL", "your_email@vt.edu")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ResearchBot/1.0; "
        f"VT Housing Research Project; contact: {USER_AGENT_EMAIL})"
    )
}


# -- Helpers ------------------------------------------------------------------

def get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_policy_links(library_soup: BeautifulSoup) -> list[dict[str, str]]:
    """Pull all policy brief URLs and titles from the library index page."""
    links: list[dict[str, str]] = []
    for anchor in library_soup.select("h5 a, h4 a, .entry-title a"):
        href = anchor.get("href", "")
        if not href:
            continue

        url = urljoin(LIBRARY_URL, href)
        title = anchor.get_text(strip=True)

        if "/housing-policy-library/" in url and title:
            links.append({"title": title, "url": url})

    # Deduplicate by URL
    seen = set()
    unique = []
    for item in links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique


def extract_policy_text(policy_soup: BeautifulSoup, title: str, url: str) -> dict[str, str]:
    """Extract the main content text from a policy brief page."""
    # Try common content containers
    content_div = (
        policy_soup.select_one(".elementor-widget-theme-post-content .elementor-widget-container")
        or policy_soup.select_one("article .entry-content")
        or policy_soup.select_one(".entry-content")
        or policy_soup.select_one(".elementor-location-single")
        or policy_soup.select_one("main")
        or policy_soup.select_one("article")
        or policy_soup.select_one("body")
    )
    if not content_div:
        return {"title": title, "url": url, "text": ""}

    # Remove nav, footer, sidebar noise
    for tag in content_div.select("nav, footer, .sidebar, script, style, .wp-block-buttons"):
        tag.decompose()

    text = content_div.get_text(separator="\n", strip=True)
    return {"title": title, "url": url, "text": text}


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    if size <= 0:
        raise ValueError("size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    words = text.split()
    chunks = []
    start = 0
    step = size - overlap
    while start < len(words):
        end = start + size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += step
    return chunks


def make_chunk_id(url: str, index: int) -> str:
    base = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"lhs_{base}_{index:04d}"


# -- Main ---------------------------------------------------------------------

def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)

    print("Fetching policy library index...")
    library_soup = get_soup(LIBRARY_URL)
    policy_links = extract_policy_links(library_soup)
    print(f"Found {len(policy_links)} policy briefs.")

    all_chunks: list[dict[str, object]] = []
    failed: list[str] = []

    for i, item in enumerate(policy_links):
        title = item["title"]
        url = item["url"]
        print(f"[{i + 1}/{len(policy_links)}] {title}")

        try:
            time.sleep(DELAY)
            policy_soup = get_soup(url)
            policy_data = extract_policy_text(policy_soup, title, url)
            text = policy_data["text"]

            if not text:
                print(f"  WARNING: No text extracted for {title}")
                failed.append(url)
                continue

            # Save raw text
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:80]
            raw_path = os.path.join(RAW_DIR, f"{safe_name}.txt")
            with open(raw_path, "w", encoding="utf-8") as file:
                file.write(f"Title: {title}\nSource: {url}\n\n{text}")

            # Chunk
            chunks = chunk_text(text)
            for j, chunk in enumerate(chunks):
                all_chunks.append(
                    {
                        "id": make_chunk_id(url, j),
                        "text": chunk,
                        "metadata": {
                            "title": title,
                            "source_url": url,
                            "category": "Housing Policy Brief",
                            "source": "Local Housing Solutions",
                            "chunk_index": j,
                            "total_chunks": len(chunks),
                        },
                    }
                )

        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")
            failed.append(url)

    # Save chunks JSON
    with open(CHUNKS_FILE, "w", encoding="utf-8") as file:
        json.dump(all_chunks, file, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(all_chunks)} chunks from {len(policy_links) - len(failed)} policies.")
    if failed:
        print(f"Failed ({len(failed)}): {failed}")
    print(f"Chunks saved to: {CHUNKS_FILE}")
    print(f"Raw text saved to: {RAW_DIR}/")


if __name__ == "__main__":
    main()

"""
Indian Tax Rules Web Scraper
Usage: python -m scripts.scraper --fy 2024-25 [--force-reingest]
"""
import argparse
import hashlib
import logging
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import httpx
import pdfplumber
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent.parent
TAX_RULES_PATH = BASE_DIR / "tax_rules.txt"
LOG_PATH = BASE_DIR / "logs" / "scraper.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

SOURCES = [
    {
        "url": "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1",
        "type": "html",
        "label": "ITR-1 Sahaj Instructions",
    },
    {
        "url": "https://www.cbdt.gov.in/",
        "type": "html",
        "label": "CBDT Home",
    },
]


def chunk_heading_hash(heading: str) -> str:
    return hashlib.md5(heading.strip().lower().encode()).hexdigest()[:12]


def build_chunk_header(url: str, fy: str) -> str:
    today = date.today().isoformat()
    return f"[SOURCE: {url}] [SCRAPED: {today}] [FY: {fy}]"


def parse_html_page(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return []

    chunks = []
    current_heading = "General"
    current_content = []

    for elem in main.descendants:
        if not hasattr(elem, "name"):
            continue
        if elem.name in ("h1", "h2", "h3", "h4"):
            if current_content:
                chunks.append({
                    "heading": current_heading,
                    "content": " ".join(current_content).strip(),
                    "url": url,
                })
                current_content = []
            current_heading = elem.get_text(strip=True)
        elif elem.name in ("p", "li", "td"):
            text = elem.get_text(strip=True)
            if text and len(text) > 20:
                current_content.append(text)

    if current_content:
        chunks.append({
            "heading": current_heading,
            "content": " ".join(current_content).strip(),
            "url": url,
        })

    return [c for c in chunks if len(c["content"]) > 50]


def parse_pdf_bytes(pdf_bytes: bytes, url: str) -> list[dict]:
    chunks = []
    try:
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            current_heading = "PDF Section"
            current_content = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Heuristic: short all-caps or numbered lines are headings
                    if len(line) < 80 and (line.isupper() or re.match(r"^\d+[\.\)]\s", line)):
                        if current_content:
                            chunks.append({
                                "heading": current_heading,
                                "content": " ".join(current_content).strip(),
                                "url": url,
                            })
                            current_content = []
                        current_heading = line
                    else:
                        current_content.append(line)
            if current_content:
                chunks.append({
                    "heading": current_heading,
                    "content": " ".join(current_content).strip(),
                    "url": url,
                })
    except Exception as e:
        log.warning(f"PDF parse error for {url}: {e}")
    return [c for c in chunks if len(c["content"]) > 50]


def deduplicate_chunks(new_chunks: list[dict], existing_text: str) -> list[dict]:
    existing_hashes = set()
    for line in existing_text.split("\n"):
        if line.startswith("## "):
            heading = line[3:].strip()
            existing_hashes.add(chunk_heading_hash(heading))

    return [
        c for c in new_chunks
        if chunk_heading_hash(c["heading"]) not in existing_hashes
    ]


def fetch_url(url: str, timeout: int = 30) -> bytes | None:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "TaxAgentScraper/1.0"})
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return None


def chunks_to_text(chunks: list[dict], fy: str) -> str:
    lines = []
    for chunk in chunks:
        header = build_chunk_header(chunk["url"], fy)
        lines.append(f"\n{header}\n## {chunk['heading']}\n{chunk['content']}\n")
    return "\n".join(lines)


def run_ingest():
    log.info("Running RAG ingest pipeline...")
    result = subprocess.run(
        [sys.executable, "-m", "app.rag.ingest"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error(f"Ingest failed: {result.stderr}")
    else:
        log.info("Ingest complete.")


def scrape(fy: str, force_reingest: bool = False):
    existing_text = TAX_RULES_PATH.read_text(encoding="utf-8") if TAX_RULES_PATH.exists() else ""

    all_new_chunks = []
    for source in SOURCES:
        log.info(f"Fetching: {source['url']}")
        content = fetch_url(source["url"])
        if content is None:
            continue

        if source["type"] == "html":
            chunks = parse_html_page(content.decode("utf-8", errors="ignore"), source["url"])
        elif source["type"] == "pdf":
            chunks = parse_pdf_bytes(content, source["url"])
        else:
            chunks = []

        log.info(f"  Parsed {len(chunks)} chunks from {source['label']}")
        all_new_chunks.extend(chunks)

    unique_chunks = deduplicate_chunks(all_new_chunks, existing_text)
    log.info(f"New unique chunks after dedup: {len(unique_chunks)}")

    if unique_chunks:
        new_text = chunks_to_text(unique_chunks, fy)
        with TAX_RULES_PATH.open("a", encoding="utf-8") as f:
            f.write(new_text)
        log.info(f"Appended {len(unique_chunks)} chunks to {TAX_RULES_PATH}")
        run_ingest()
    elif force_reingest:
        log.info("No new chunks but --force-reingest set, running ingest anyway.")
        run_ingest()
    else:
        log.info("No new content found. Skipping ingest.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Indian tax rules")
    parser.add_argument("--fy", default="2024-25", help="Fiscal year e.g. 2024-25")
    parser.add_argument("--force-reingest", action="store_true")
    args = parser.parse_args()
    scrape(args.fy, args.force_reingest)

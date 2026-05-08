import hashlib
import pytest
from unittest.mock import patch, MagicMock

# We'll import these once the module exists
# from scripts.scraper import chunk_heading_hash, deduplicate_chunks, parse_html_page, build_chunk_header


def test_chunk_heading_hash_is_deterministic():
    from scripts.scraper import chunk_heading_hash
    h1 = chunk_heading_hash("Section 87A Rebate")
    h2 = chunk_heading_hash("Section 87A Rebate")
    assert h1 == h2


def test_chunk_heading_hash_differs_for_different_headings():
    from scripts.scraper import chunk_heading_hash
    h1 = chunk_heading_hash("Section 87A Rebate")
    h2 = chunk_heading_hash("Standard Deduction")
    assert h1 != h2


def test_deduplicate_chunks_removes_known_headings():
    from scripts.scraper import deduplicate_chunks, chunk_heading_hash
    existing_text = "## Section 87A Rebate\nSome content here."
    new_chunks = [
        {"heading": "Section 87A Rebate", "content": "Different content"},
        {"heading": "New Section", "content": "Brand new content"},
    ]
    result = deduplicate_chunks(new_chunks, existing_text)
    assert len(result) == 1
    assert result[0]["heading"] == "New Section"


def test_build_chunk_header_format():
    from scripts.scraper import build_chunk_header
    header = build_chunk_header("https://incometax.gov.in/slabs", "2024-25")
    assert "[SOURCE: https://incometax.gov.in/slabs]" in header
    assert "[FY: 2024-25]" in header
    assert "[SCRAPED:" in header


def test_parse_html_page_extracts_text():
    from scripts.scraper import parse_html_page
    html = """
    <html><body>
      <main>
        <h2>Tax Slabs FY 2024-25</h2>
        <p>Under new regime, income up to Rs 3 lakh is exempt.</p>
      </main>
    </body></html>
    """
    chunks = parse_html_page(html, "https://incometax.gov.in/slabs")
    assert len(chunks) >= 1
    assert any("Tax Slabs" in c["heading"] for c in chunks)
    assert any("3 lakh" in c["content"] for c in chunks)

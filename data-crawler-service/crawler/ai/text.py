"""HTML / PDF -> plain text, links and tables (no AI). The text is what the AI reads and what its answers are
checked against."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from lxml import html as lxml_html

DROP_TAGS = ("script", "style", "noscript", "svg", "iframe", "template", "head")
BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "address", "table",
              "ul", "ol", "dd", "dt", "footer", "header", "td", "th"}  # fmt: skip


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]


def _doc(html: str):
    return lxml_html.fromstring(html or "<html></html>")


def html_to_text(html: str) -> str:
    """Readable text: one line per block element, mailto: / tel: targets kept next to their link text."""
    doc = _doc(html)
    for element in doc.xpath("|".join(f"//{tag}" for tag in DROP_TAGS)):
        element.drop_tree()
    for link in doc.xpath("//a[@href]"):
        href = link.get("href", "")
        if href.lower().startswith(("mailto:", "tel:")):
            target = href.split(":", 1)[1].split("?")[0]
            if target and target not in (link.text_content() or ""):
                link.tail = f" ({target}){link.tail or ''}"
    for element in doc.iter():
        if isinstance(element.tag, str) and element.tag.lower() in BLOCK_TAGS:
            element.tail = "\n" + (element.tail or "")
            if element.tag.lower() in ("td", "th"):
                element.tail = " | " + (element.tail or "").lstrip("\n")
    text = doc.text_content()
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line.strip(" |"))


def links(html: str, base_url: str) -> list[tuple[str, str]]:
    """(absolute URL, link text) for every http(s) link, in page order, without fragments."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in _doc(html).xpath("//a[@href]"):
        url = urljoin(base_url, anchor.get("href", "").strip()).split("#")[0]
        if urlsplit(url).scheme in ("http", "https") and url not in seen:
            seen.add(url)
            found.append((url, " ".join(anchor.text_content().split())))
    return found


def html_tables(html: str) -> list[Table]:
    """Every <table> as header + rows (header = first row with <th>, else the first row)."""
    tables: list[Table] = []
    for table in _doc(html).xpath("//table"):
        rows = []
        for tr in table.xpath(".//tr"):
            cells = [" ".join(cell.text_content().split()) for cell in tr.xpath("./th|./td")]
            if any(cells):
                rows.append((bool(tr.xpath("./th")), cells))
        if len(rows) < 2:
            continue
        header_index = next((i for i, (is_header, _) in enumerate(rows) if is_header), 0)
        tables.append(Table(headers=rows[header_index][1], rows=[cells for _, cells in rows[header_index + 1 :]]))
    return tables


def pdf_text_and_tables(content: bytes) -> tuple[str, list[Table]]:
    """Text and tables of a PDF (needs the optional pdfplumber package)."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("Reading PDFs needs pdfplumber: pip install -e .[pdf]") from exc
    texts: list[str] = []
    tables: list[Table] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            for raw in page.extract_tables():
                rows = [[" ".join(str(c or "").split()) for c in row] for row in raw if row and any(row)]
                if len(rows) >= 2:
                    tables.append(Table(headers=rows[0], rows=rows[1:]))
    return "\n".join(texts), tables


def normalise_for_match(text: str) -> str:
    return " ".join(re.sub(r"[^\w@.+/&-]+", " ", text.lower()).split())

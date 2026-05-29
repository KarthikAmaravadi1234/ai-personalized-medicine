"""Fetch knowledge-base content from open sources into ``data/knowledge/``.

This is a manual, network-using developer tool. The application and test suite stay
offline; run this only when you want to (re)build the RAG corpus.

Sources:
- ``wikipedia``   - plain-text article extracts (License: CC BY-SA 4.0, attribution required)
- ``medlineplus`` - NLM/NIH health topics (largely public domain)

Each topic becomes ``data/knowledge/<slug>.md`` with YAML frontmatter provenance.
A ``manifest.json`` and ``ATTRIBUTION.md`` are also written.

Usage:
    python scripts/fetch_knowledge.py --topics data/knowledge_topics.json
    python scripts/fetch_knowledge.py --source wikipedia --reindex
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

DEFAULT_TOPICS = _PROJECT_ROOT / "data" / "knowledge_topics.json"
DEFAULT_OUT_DIR = _PROJECT_ROOT / "data" / "knowledge"
USER_AGENT = "ai-personalized-medicine/0.1 (educational project)"

LICENSES = {
    "wikipedia": "CC BY-SA 4.0",
    "medlineplus": "Public domain (U.S. National Library of Medicine)",
}


# --------------------------------------------------------------------------- #
# HTTP (isolated so tests can monkeypatch ``_http_get``)
# --------------------------------------------------------------------------- #
_RETRY_STATUS = {429, 500, 502, 503, 504}


def _http_get(
    url: str,
    params: dict[str, str] | None = None,
    *,
    retries: int = 4,
    backoff: float = 2.0,
) -> str:
    import time

    import httpx

    for attempt in range(retries + 1):
        try:
            resp = httpx.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30.0
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if attempt >= retries:
                raise
            wait = backoff * (2**attempt)
            print(f"    .. {type(exc).__name__}, retrying in {wait:.0f}s")
            time.sleep(wait)
            continue
        if resp.status_code in _RETRY_STATUS and attempt < retries:
            retry_after = resp.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else backoff * (2**attempt)
            except ValueError:
                wait = backoff * (2**attempt)
            print(f"    .. {resp.status_code}, retrying in {wait:.0f}s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.text
    raise RuntimeError(f"exhausted retries for {url}")


# --------------------------------------------------------------------------- #
# Text cleaning helpers (pure)
# --------------------------------------------------------------------------- #
class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return re.sub(r"\n{3,}", "\n\n", parser.text()).strip()


def strip_math_markup(text: str) -> str:
    """Remove LaTeX/MathML noise that Wikipedia plain-text extracts leave behind.

    Two artifacts appear: balanced ``{\\displaystyle ...}`` / ``{\\textstyle ...}`` LaTeX
    blocks, and the rendered formula written as a long run of single characters
    (e.g. ``I F C C H B A 1 c ( ...``). Both are unreadable in an excerpt.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text.startswith("{\\displaystyle", i) or text.startswith("{\\textstyle", i):
            depth = 0
            while i < n:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
        else:
            out.append(text[i])
            i += 1
    cleaned = "".join(out)
    # Collapse long runs of space-separated single-character tokens (rendered formulas).
    cleaned = re.sub(r"(?:(?<=\s)|^)(?:\S ){4,}\S?", " ", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned)


def wiki_sections_to_markdown(text: str, *, max_words: int | None = 1200) -> str:
    """Convert Wikipedia plain-text section markers (== X ==) to markdown headers."""
    text = strip_math_markup(text)
    lines: list[str] = []
    for raw in text.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", raw.strip())
        if m:
            level = min(len(m.group(1)), 4)
            lines.append("\n" + "#" * level + " " + m.group(2))
        else:
            lines.append(raw)
    body = "\n".join(lines).strip()
    if max_words:
        words = body.split()
        if len(words) > max_words:
            body = " ".join(words[:max_words]).rstrip() + " \u2026"
    return re.sub(r"\n{3,}", "\n\n", body)


# --------------------------------------------------------------------------- #
# Source fetchers -> normalized dict {title, text, source, source_url, license}
# --------------------------------------------------------------------------- #
def fetch_wikipedia(title: str, *, max_words: int | None = 1200) -> dict:
    raw = _http_get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "redirects": "1",
            "format": "json",
            "titles": title,
        },
    )
    data = json.loads(raw)
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    extract = page.get("extract", "")
    resolved = page.get("title", title)
    return {
        "title": resolved,
        "text": wiki_sections_to_markdown(extract, max_words=max_words),
        "source": "wikipedia",
        "source_url": f"https://en.wikipedia.org/wiki/{resolved.replace(' ', '_')}",
        "license": LICENSES["wikipedia"],
    }


def fetch_medlineplus(query: str, *, max_words: int | None = 1200) -> dict:
    import xml.etree.ElementTree as ET

    raw = _http_get(
        "https://wsearch.nlm.nih.gov/ws/query",
        {"db": "healthTopics", "term": query, "retmax": "1"},
    )
    root = ET.fromstring(raw)
    doc = root.find(".//document")
    title, summary, url = query, "", ""
    if doc is not None:
        url = doc.get("url", "")
        for content in doc.findall("content"):
            name = content.get("name", "")
            value = "".join(content.itertext())
            if name == "title":
                title = html_to_text(value)
            elif name == "FullSummary":
                summary = html_to_text(value)
    body = summary
    if max_words and body:
        words = body.split()
        if len(words) > max_words:
            body = " ".join(words[:max_words]).rstrip() + " \u2026"
    return {
        "title": title,
        "text": body,
        "source": "medlineplus",
        "source_url": url,
        "license": LICENSES["medlineplus"],
    }


FETCHERS = {"wikipedia": fetch_wikipedia, "medlineplus": fetch_medlineplus}


# --------------------------------------------------------------------------- #
# Rendering / writing (pure, testable)
# --------------------------------------------------------------------------- #
def render_markdown(slug: str, fetched: dict, query: str, retrieved: str) -> str:
    front = [
        "---",
        f"title: {fetched['title']}",
        f"slug: {slug}",
        f"source: {fetched['source']}",
        f"source_url: {fetched['source_url']}",
        f"license: {fetched['license']}",
        f"retrieved: {retrieved}",
        f"query: {query}",
        "---",
        "",
        f"# {fetched['title']}",
        "",
        fetched["text"],
        "",
    ]
    return "\n".join(front)


def write_topic(topic: dict, fetched: dict, out_dir: Path, retrieved: str) -> dict:
    slug = topic["slug"]
    md = render_markdown(slug, fetched, topic.get("query", ""), retrieved)
    (out_dir / f"{slug}.md").write_text(md)
    return {
        "slug": slug,
        "title": fetched["title"],
        "source": fetched["source"],
        "source_url": fetched["source_url"],
        "license": fetched["license"],
        "retrieved": retrieved,
    }


def merge_manifest(existing: list[dict], new_entries: list[dict]) -> list[dict]:
    """Replace/insert ``new_entries`` into ``existing`` by slug, sorted by slug."""
    by_slug = {e["slug"]: e for e in existing}
    for entry in new_entries:
        by_slug[entry["slug"]] = entry
    return sorted(by_slug.values(), key=lambda e: e["slug"])


def render_attribution(entries: list[dict]) -> str:
    lines = [
        "# Attribution",
        "",
        "This knowledge base is assembled for educational use only and is not medical advice.",
        "",
        "Wikipedia content is licensed under CC BY-SA 4.0 and remains under that license.",
        "MedlinePlus content is provided by the U.S. National Library of Medicine.",
        "",
        "## Sources",
        "",
    ]
    for e in entries:
        lines.append(f"- **{e['title']}** ({e['slug']}) - {e['source']}, {e['license']} - {e['source_url']} (retrieved {e['retrieved']})")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch knowledge-base content from open sources.")
    parser.add_argument("--topics", type=Path, default=DEFAULT_TOPICS, help=f"Topics config (default: {DEFAULT_TOPICS})")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"Output dir (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--source", choices=sorted(FETCHERS), default=None, help="Override the source for all topics")
    parser.add_argument("--max-words", type=int, default=1200, help="Truncate each article (default: 1200; 0 disables)")
    parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N topics")
    parser.add_argument("--only", type=str, default=None, help="Comma-separated slugs to fetch (subset)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between requests (default: 1.0)")
    parser.add_argument("--reindex", action="store_true", help="Rebuild the vector index after fetching")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    import time

    args = parse_args(argv)
    config = json.loads(args.topics.read_text())
    topics = config.get("topics", config if isinstance(config, list) else [])

    is_subset = bool(args.limit or args.only)
    if args.limit:
        topics = topics[: args.limit]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        topics = [t for t in topics if t["slug"] in wanted]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    retrieved = date.today().isoformat()
    max_words = args.max_words or None

    entries: list[dict] = []
    for i, topic in enumerate(topics):
        if i > 0 and args.delay > 0:
            time.sleep(args.delay)
        source = args.source or topic.get("source", "wikipedia")
        fetcher = FETCHERS[source]
        try:
            if source == "wikipedia":
                fetched = fetcher(topic["title"], max_words=max_words)
            else:
                fetched = fetcher(topic.get("query", topic["title"]), max_words=max_words)
        except Exception as exc:  # keep going; report at the end
            print(f"  ! {topic['slug']}: failed ({exc})")
            continue
        if not fetched.get("text"):
            print(f"  ! {topic['slug']}: empty content, skipped")
            continue
        entry = write_topic(topic, fetched, args.out_dir, retrieved)
        entries.append(entry)
        print(f"  + {entry['slug']} <- {entry['source']} ({entry['title']})")

    # On subset runs, merge into the existing manifest so we don't wipe other topics.
    final_entries = entries
    if is_subset:
        manifest_path = args.out_dir / "manifest.json"
        existing: list[dict] = []
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text())
            except (ValueError, OSError):
                existing = []
        final_entries = merge_manifest(existing, entries)

    (args.out_dir / "manifest.json").write_text(json.dumps(final_entries, indent=2))
    (args.out_dir / "ATTRIBUTION.md").write_text(render_attribution(final_entries))
    print(
        f"Fetched {len(entries)} topic(s); manifest now has {len(final_entries)} entries "
        f"(+ ATTRIBUTION.md) in {args.out_dir}"
    )

    if args.reindex:
        from backend.rag.retriever import Retriever

        retriever = Retriever()
        count = retriever.index_directory(args.out_dir)
        retriever.save()
        print(f"Reindexed {count} chunks.")


if __name__ == "__main__":
    main()

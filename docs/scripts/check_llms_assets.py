#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree


def _duplicate_ratio(text: str) -> float:
    # Paragraph-level duplicate ratio (0.0 good, 1.0 bad)
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        return 0.0
    normalized = [" ".join(p.split()) for p in parts]
    unique_count = len(set(normalized))
    return max(0.0, 1.0 - (unique_count / len(normalized)))


def _base_url(llms_text: str) -> str:
    for line in llms_text.splitlines():
        if line.startswith("# Canonical base:"):
            return line.split(":", 1)[1].strip().rstrip("/") + "/"
    raise SystemExit("Missing '# Canonical base:' header in llms.txt")


def _llms_urls(llms_text: str) -> list[str]:
    urls = []
    for line in llms_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line.split(" | ", 1)[0].removeprefix("- "))
    return urls


def _sitemap_urls(sitemap_path: Path) -> list[str]:
    if not sitemap_path.exists():
        raise SystemExit(f"Missing sitemap.xml: {sitemap_path}")
    root = ElementTree.fromstring(sitemap_path.read_text(encoding="utf-8"))
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text.strip() for loc in root.findall(".//sm:loc", namespace) if loc.text]


def _html_path_for_url(html_root: Path, base_url: str, url: str) -> Path:
    if not url.startswith(base_url):
        raise SystemExit(f"Generated URL is outside canonical base: {url}")

    rel_url = url[len(base_url) :]
    parsed = urlparse(rel_url)
    rel_path = parsed.path
    if not rel_path or rel_path.endswith("/"):
        rel_path = rel_path + "index.html"

    html_path = (html_root / rel_path).resolve()
    try:
        html_path.relative_to(html_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"Generated URL escapes HTML root: {url}") from exc
    return html_path


def _validate_html_urls(html_root: Path, base_url: str, urls: list[str]) -> None:
    if not html_root.exists():
        raise SystemExit(f"HTML root does not exist: {html_root}")

    missing = [url for url in urls if not _html_path_for_url(html_root, base_url, url).exists()]
    if missing:
        formatted = "\n".join(f"- {url}" for url in missing)
        raise SystemExit(f"Generated URLs do not exist in built HTML:\n{formatted}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate llms.txt and llms-full.txt quality gates.")
    parser.add_argument("--llms", default="docs/source/_extra/llms.txt")
    parser.add_argument("--llms-full", default="docs/source/_extra/llms-full.txt")
    parser.add_argument("--sitemap", default="docs/source/_extra/sitemap.xml")
    parser.add_argument(
        "--html-root",
        default=None,
        help="Built HTML root used to verify generated URLs, for example docs/build/html.",
    )
    parser.add_argument("--max-bytes", type=int, default=2_097_152)
    parser.add_argument("--max-duplicate-ratio", type=float, default=0.35)
    args = parser.parse_args()

    llms_path = Path(args.llms)
    llms_full_path = Path(args.llms_full)
    sitemap_path = Path(args.sitemap)

    if not llms_path.exists():
        raise SystemExit(f"Missing llms.txt: {llms_path}")
    if not llms_full_path.exists():
        raise SystemExit(f"Missing llms-full.txt: {llms_full_path}")

    llms_text = llms_path.read_text(encoding="utf-8")
    llms_full_text = llms_full_path.read_text(encoding="utf-8")

    if not llms_text.strip():
        raise SystemExit("llms.txt is empty")

    lines = [ln.strip() for ln in llms_text.splitlines() if ln.strip()]
    item_lines = [ln for ln in lines if not ln.startswith("#")]
    if not item_lines:
        raise SystemExit("llms.txt has no item lines")

    base_url = _base_url(llms_text)
    llms_urls = _llms_urls(llms_text)
    sitemap_urls = _sitemap_urls(sitemap_path)
    if llms_urls != sitemap_urls:
        raise SystemExit("llms.txt URLs and sitemap.xml URLs are out of sync")

    for ln in item_lines:
        if not ln.startswith("- https://"):
            raise SystemExit(f"Invalid llms.txt line format: {ln}")
        if " | " not in ln:
            raise SystemExit(f"Missing ' | ' separator in llms.txt line: {ln}")

    if args.html_root:
        _validate_html_urls(Path(args.html_root), base_url, llms_urls)

    llms_full_size = len(llms_full_text.encode("utf-8"))
    if llms_full_size > args.max_bytes:
        raise SystemExit(
            f"llms-full.txt too large: {llms_full_size} bytes > {args.max_bytes} bytes"
        )

    dup_ratio = _duplicate_ratio(llms_full_text)
    if dup_ratio > args.max_duplicate_ratio:
        raise SystemExit(
            f"llms-full duplicate ratio too high: {dup_ratio:.4f} > {args.max_duplicate_ratio:.4f}"
        )

    print(
        "llms checks passed:",
        f"items={len(item_lines)}",
        f"llms_full_size={llms_full_size}",
        f"duplicate_ratio={dup_ratio:.4f}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

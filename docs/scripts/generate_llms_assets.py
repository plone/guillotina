#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Dict, List

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: pip install PyYAML") from exc


def _strip_markup(raw: str) -> str:
    text = raw

    # Remove simple markdown front-matter if present.
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5 :]

    # Remove fenced code blocks.
    text = re.sub(r"```.*?```", "\n", text, flags=re.S)

    # Remove reST directives and options lines.
    text = re.sub(r"^\s*\.\.\s+\S+::.*$", "", text, flags=re.M)
    text = re.sub(r"^\s*:[a-zA-Z0-9_-]+:.*$", "", text, flags=re.M)

    # Convert common inline links/references.
    text = re.sub(r"\{doc\}`([^`<]+)<[^`>]+>`", r"\1", text)
    text = re.sub(r"\{doc\}`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`_", r"\1", text)
    text = re.sub(r"``([^`]+)``", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove markup noise.
    text = re.sub(r"^[#=\-]{3,}\s*$", "", text, flags=re.M)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _canonical_url(base_url: str, path_value: str) -> str:
    p = path_value.lstrip("./")

    # Keep docs/source-relative canonical URLs; files outside docs/source stay root-style.
    p = p.replace("../", "")

    if p.endswith("/index.md") or p.endswith("/index.rst"):
        p = p.rsplit("/index.", 1)[0] + "/"
    elif p.endswith(".md") or p.endswith(".rst"):
        p = p.rsplit(".", 1)[0] + ".html"

    if p.startswith("/"):
        p = p[1:]

    return base_url.rstrip("/") + "/" + p


def generate(curation_path: Path, source_root: Path, output_root: Path) -> Dict[str, int]:
    config = yaml.safe_load(curation_path.read_text(encoding="utf-8"))

    site = config.get("site", {})
    base_url = str(site.get("base_url", "")).strip()
    max_bytes = int(site.get("llms_full_max_bytes", 2_097_152))
    project_name = str(site.get("project_name", "Project")).strip() or "Project"

    items: List[Dict[str, object]] = list(config.get("items", []))
    if not base_url:
        raise ValueError("site.base_url is required in curation.yml")
    if not items:
        raise ValueError("At least one item is required in curation.yml")

    output_root.mkdir(parents=True, exist_ok=True)

    llms_lines = [
        f"# {project_name} documentation index",
        f"# Generated: {dt.datetime.utcnow().replace(microsecond=0).isoformat()}Z",
        f"# Canonical base: {base_url}",
        "",
    ]

    full_parts = [
        f"# {project_name} llms-full",
        f"Generated: {dt.datetime.utcnow().replace(microsecond=0).isoformat()}Z",
        f"Canonical base: {base_url}",
        "",
    ]

    sitemap_urls: List[str] = []
    full_sections_added = 0

    for item in items:
        path_value = str(item.get("path", "")).strip()
        title = str(item.get("title", "")).strip() or path_value
        summary = str(item.get("summary", "")).strip()
        include_full = bool(item.get("include_full", False))

        if not path_value:
            continue

        url = _canonical_url(base_url, path_value)
        sitemap_urls.append(url)
        llms_lines.append(f"- {url} | {title} | {summary}")

        if not include_full:
            continue

        source_path = (source_root / path_value).resolve()
        if not source_path.exists():
            # Try from repo root for paths like ../CHANGELOG.rst
            source_path = (source_root.parent / path_value).resolve()
        if not source_path.exists() or not source_path.is_file():
            continue

        body = _strip_markup(source_path.read_text(encoding="utf-8", errors="ignore"))
        if not body:
            continue

        section = [
            f"## {title}",
            f"Source: {url}",
            f"Summary: {summary}",
            "",
            body,
            "",
        ]
        candidate = "\n".join(full_parts + section)
        if len(candidate.encode("utf-8")) > max_bytes:
            full_parts.append("## Truncated")
            full_parts.append(f"Stopped before exceeding max size budget of {max_bytes} bytes.")
            full_parts.append("")
            break

        full_parts.extend(section)
        full_sections_added += 1

    llms_text = "\n".join(llms_lines).rstrip() + "\n"
    llms_full_text = "\n".join(full_parts).rstrip() + "\n"

    robots_text = "\n".join(
        [
            "User-agent: GPTBot",
            "Allow: /",
            "",
            "User-agent: ChatGPT-User",
            "Allow: /",
            "",
            "User-agent: OAI-SearchBot",
            "Allow: /",
            "",
            "User-agent: ClaudeBot",
            "Allow: /",
            "",
            "User-agent: Claude-SearchBot",
            "Allow: /",
            "",
            "User-agent: anthropic-ai",
            "Allow: /",
            "",
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {base_url.rstrip('/')}/sitemap.xml",
            "",
        ]
    )

    unique_urls = []
    seen = set()
    for u in sitemap_urls:
        if u in seen:
            continue
        seen.add(u)
        unique_urls.append(u)

    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    sitemap_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in unique_urls:
        sitemap_parts.extend(["  <url>", f"    <loc>{u}</loc>", f"    <lastmod>{now}</lastmod>", "  </url>"])
    sitemap_parts.append("</urlset>")
    sitemap_text = "\n".join(sitemap_parts) + "\n"

    (output_root / "llms.txt").write_text(llms_text, encoding="utf-8")
    (output_root / "llms-full.txt").write_text(llms_full_text, encoding="utf-8")
    (output_root / "robots.txt").write_text(robots_text, encoding="utf-8")
    (output_root / "sitemap.xml").write_text(sitemap_text, encoding="utf-8")

    return {
        "items": len(items),
        "llms_full_sections": full_sections_added,
        "llms_bytes": len(llms_text.encode("utf-8")),
        "llms_full_bytes": len(llms_full_text.encode("utf-8")),
        "sitemap_urls": len(unique_urls),
        "max_bytes": max_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate llms/robots/sitemap docs assets.")
    parser.add_argument(
        "--curation",
        default="docs/source/_llm/curation.yml",
        help="Path to curation yaml file.",
    )
    parser.add_argument(
        "--source-root",
        default="docs/source",
        help="Docs source root path.",
    )
    parser.add_argument(
        "--output-root",
        default="docs/source/_extra",
        help="Output directory for generated root assets.",
    )
    args = parser.parse_args()

    stats = generate(Path(args.curation), Path(args.source_root), Path(args.output_root))
    print(
        "generated llms assets:",
        f"items={stats['items']}",
        f"full_sections={stats['llms_full_sections']}",
        f"llms_full_bytes={stats['llms_full_bytes']}/{stats['max_bytes']}",
        f"sitemap_urls={stats['sitemap_urls']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

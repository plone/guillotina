#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _normalize_text(raw: str) -> str:
    text = re.sub(r"```.*?```", " ", raw, flags=re.S)
    text = re.sub(r"^\s*\.\.\s+\S+::.*$", " ", text, flags=re.M)
    text = re.sub(r"\{doc\}`([^`<]+)<[^`>]+>`", r"\1", text)
    text = re.sub(r"\{doc\}`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return text


def load_benchmark(path: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            continue
        parts = [p.strip() for p in s.strip("|").split("|")]
        if len(parts) < 2:
            continue
        if parts[0] in {"query", "---"}:
            continue
        if set(parts[0]) == {"-"}:
            continue
        query, expected = parts[0], parts[1]
        if query and expected:
            rows.append((query, expected))
    if not rows:
        raise ValueError(f"No benchmark rows parsed from: {path}")
    return rows


def build_corpus(source_root: Path) -> Dict[str, Counter]:
    corpus: Dict[str, Counter] = {}
    for p in sorted(source_root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix not in {".md", ".rst"}:
            continue
        rel = p.as_posix()
        if "/_static/" in rel or rel.endswith("/conf.py"):
            continue
        text = _normalize_text(p.read_text(encoding="utf-8", errors="ignore"))
        counts = Counter(_tokens(text))

        # Boost path and filename lexical signals for practical retrieval ranking.
        path_tokens = _tokens(rel.replace("/", " ").replace(".", " "))
        for tok in path_tokens:
            counts[tok] += 40

        # Boost page title tokens (first markdown H1 / reST title line heuristic).
        first_line = text.splitlines()[0] if text.splitlines() else ""
        for tok in _tokens(first_line):
            counts[tok] += 12

        corpus[rel] = counts
    return corpus


def best_matches(query: str, corpus: Dict[str, Counter], top_k: int) -> List[str]:
    q_tokens = list(dict.fromkeys(_tokens(query)))
    scores: List[Tuple[int, str]] = []
    for path, counts in corpus.items():
        score = sum(counts.get(tok, 0) for tok in q_tokens)
        if score > 0:
            scores.append((score, path))
    scores.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, p in scores[:top_k]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check lexical retrieval benchmark coverage.")
    parser.add_argument(
        "--benchmark",
        default="docs/plan-artifacts/retrieval_benchmark_queries.md",
        help="Markdown benchmark table file.",
    )
    parser.add_argument(
        "--source-root",
        default="docs/source",
        help="Docs source root used as retrieval corpus.",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-coverage", type=float, default=0.90)
    parser.add_argument(
        "--report",
        default="docs/plan-artifacts/retrieval_benchmark_report.md",
        help="Output report path.",
    )
    args = parser.parse_args()

    benchmark = load_benchmark(Path(args.benchmark))
    corpus = build_corpus(Path(args.source_root))

    hits = 0
    rows = []
    for query, expected in benchmark:
        top_docs = best_matches(query, corpus, args.top_k)
        ok = expected in top_docs
        if ok:
            hits += 1
        rows.append((query, expected, top_docs, ok))

    total = len(rows)
    coverage = hits / total if total else 0.0

    report_lines = [
        "# Retrieval Benchmark Report",
        "",
        f"- Total queries: {total}",
        f"- Hits in top-{args.top_k}: {hits}",
        f"- Coverage: {coverage:.2%}",
        f"- Target: {args.min_coverage:.0%}",
        "",
        "| query | expected_doc | top_docs | hit |",
        "|---|---|---|---|",
    ]
    for query, expected, top_docs, ok in rows:
        tops = "<br>".join(top_docs) if top_docs else "(none)"
        report_lines.append(
            f"| {query} | {expected} | {tops} | {'yes' if ok else 'no'} |"
        )

    Path(args.report).write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "retrieval coverage:",
        f"hits={hits}/{total}",
        f"coverage={coverage:.4f}",
        f"target={args.min_coverage:.4f}",
    )
    if coverage < args.min_coverage:
        raise SystemExit(
            f"Coverage below threshold: {coverage:.2%} < {args.min_coverage:.0%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

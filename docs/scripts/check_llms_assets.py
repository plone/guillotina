#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def _duplicate_ratio(text: str) -> float:
    # Paragraph-level duplicate ratio (0.0 good, 1.0 bad)
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        return 0.0
    normalized = [" ".join(p.split()) for p in parts]
    unique_count = len(set(normalized))
    return max(0.0, 1.0 - (unique_count / len(normalized)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate llms.txt and llms-full.txt quality gates.")
    parser.add_argument("--llms", default="docs/source/_extra/llms.txt")
    parser.add_argument("--llms-full", default="docs/source/_extra/llms-full.txt")
    parser.add_argument("--max-bytes", type=int, default=2_097_152)
    parser.add_argument("--max-duplicate-ratio", type=float, default=0.35)
    args = parser.parse_args()

    llms_path = Path(args.llms)
    llms_full_path = Path(args.llms_full)

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

    for ln in item_lines:
        if not ln.startswith("- https://"):
            raise SystemExit(f"Invalid llms.txt line format: {ln}")
        if " | " not in ln:
            raise SystemExit(f"Missing ' | ' separator in llms.txt line: {ln}")

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

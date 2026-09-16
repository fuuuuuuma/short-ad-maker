#!/usr/bin/env python3
"""Fail when a public skill package contains likely local or secret material."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS = {
    "macOS user path": re.compile("/" + r"Users/(?!Shared/)[^/\s]+/"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "generic API key": re.compile(r"\b(?:sk|pk)_[A-Za-z0-9_-]{24,}\b"),
}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".html", ".css", ".js"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.path.expanduser().resolve()
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(root)}:{line}: {label}")
    if findings:
        print("\n".join(findings))
        return 1
    print("privacy check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

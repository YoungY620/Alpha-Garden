#!/usr/bin/env python3
"""Run mechanical PDF checks and render every page for visual inspection."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--render-dir", required=True, type=Path)
    args = parser.parse_args()
    issues: list[str] = []
    reader = PdfReader(str(args.pdf))
    if not reader.pages:
        issues.append("PDF has no pages")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(text.strip()) < 100:
        issues.append("too little extractable text")
    pdffonts = shutil.which("pdffonts")
    renderer = shutil.which("pdftoppm")
    if not pdffonts:
        issues.append("pdffonts is unavailable")
    else:
        result = subprocess.run([pdffonts, str(args.pdf)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            issues.append("pdffonts failed")
        elif " no " in result.stdout.lower():
            issues.append("one or more fonts are not embedded")
    args.render_dir.mkdir(parents=True, exist_ok=True)
    if not renderer:
        issues.append("pdftoppm is unavailable")
    else:
        result = subprocess.run([renderer, "-png", "-r", "150", str(args.pdf), str(args.render_dir / "page")], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            issues.append("PDF rendering failed")
    rendered = sorted(args.render_dir.glob("page-*.png"))
    if renderer and len(rendered) != len(reader.pages):
        issues.append("rendered page count does not match PDF page count")
    report = {"accepted": not issues, "issues": issues, "pages": len(reader.pages), "rendered_pages": len(rendered)}
    print(json.dumps(report))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

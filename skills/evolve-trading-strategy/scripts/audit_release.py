#!/usr/bin/env python3
"""Reject likely machine identifiers, private endpoints, and secrets."""

from __future__ import annotations

import argparse
import getpass
import re
from pathlib import Path


TEXT_SUFFIXES = {"", ".md", ".py", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".txt", ".csv", ".svg", ".html", ".css", ".js"}
EXCLUDED_PARTS = {".git", ".venv", "venv", "tmp", "output", "dist", "build", "node_modules", "__pycache__"}


def patterns() -> list[tuple[str, re.Pattern[str]]]:
    mac_home = "/" + "Users" + "/"
    linux_home = "/" + "home" + "/"
    windows_home = "C:" + "\\" + "Users" + "\\"
    return [
        ("machine-specific home path", re.compile(rf"(?:{re.escape(mac_home)}|{re.escape(linux_home)}|{re.escape(windows_home)})[^\s\"']+", re.I)),
        ("IP address", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
        ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
        ("private key", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
        ("API-like token", re.compile(r"\b(?:sk|pk|api)[-_][A-Za-z0-9_-]{16,}\b", re.I)),
        ("assigned secret", re.compile(r"\b(?:password|passwd|secret|api_key|access_token)\s*[:=]\s*[\"'][^\"']+[\"']", re.I)),
        ("private endpoint", re.compile(r"https?://[^\s/]*(?:\.internal|\.local)(?:/|\b)", re.I)),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    findings: list[str] = []
    current_user = getpass.getuser()
    generic_users = {"root", "user", "runner", "admin"}
    for path in sorted(args.root.rglob("*")):
        if not path.is_file() or EXCLUDED_PARTS.intersection(path.parts) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(args.root)
        if len(current_user) > 3 and current_user.lower() not in generic_users and re.search(rf"\b{re.escape(current_user)}\b", content, re.I):
            findings.append(f"{relative}: local username")
        for label, pattern in patterns():
            for match in pattern.finditer(content):
                findings.append(f"{relative}:{content.count(chr(10), 0, match.start()) + 1}: {label}")
    if findings:
        print("release audit failed")
        print("\n".join(findings))
        return 1
    print("release audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

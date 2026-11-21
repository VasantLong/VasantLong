#!/usr/bin/env python3
"""Turn a local SVG/PNG into a shields.io badge logo parameter.

shields.io only accepts simple-icons slugs or a base64 data URI as ?logo=.
Remote URLs are silently ignored, URL-safe base64 is rejected, and logoColor
does not recolor a custom image -- so the file you feed in must already be
the colour you want at 14x14 px.

Usage:
    python3 scripts/badge_logo.py assets/pi.svg
    python3 scripts/badge_logo.py assets/pi.svg --label pi --color 4D6BFE

Prints the query fragment plus a ready-to-paste markdown snippet.
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path

MAX_SAFE_B64 = 1500  # keep the whole badge URL comfortably short


def minify_svg(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<\?xml.*?\?>", "", text, flags=re.S)
    text = re.sub(r"<!DOCTYPE.*?>", "", text, flags=re.S)
    text = re.sub(r">\s+<", "><", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def build(path: Path, minify: bool) -> str:
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or ""
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
        if minify:
            data = minify_svg(data.decode("utf-8")).encode()
    if mime not in ("image/svg+xml", "image/png"):
        raise SystemExit(f"error: {path} is {mime or 'unknown'}; only svg and png work")
    return base64.b64encode(data).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--label", default="BADGE")
    ap.add_argument("--color", default="6B7280")
    ap.add_argument("--no-minify", action="store_true")
    args = ap.parse_args()

    if not args.image.is_file():
        raise SystemExit(f"error: no such file: {args.image}")

    b64 = build(args.image, minify=not args.no_minify)
    mime = "image/svg+xml" if args.image.suffix.lower() == ".svg" else "image/png"
    if len(b64) > MAX_SAFE_B64:
        print(
            f"warning: base64 payload is {len(b64)} chars; "
            "simplify the graphic or the badge URL may be truncated",
            file=sys.stderr,
        )

    url = (
        f"https://img.shields.io/badge/{args.label}-{args.color}"
        f"?style=flat-square&logo=data:{mime};base64,{b64}"
    )
    print(f"<!-- {args.image} -> {len(b64)} chars of base64 -->")
    print(f'<img src="{url}" alt="{args.label}" />')
    return 0


if __name__ == "__main__":
    sys.exit(main())

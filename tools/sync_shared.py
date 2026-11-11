#!/usr/bin/env python3
"""Keeps the shared code blocks in the games the same as their master copy.

Some code is copied into several games, because every game stays a single HTML file.
In the games such a block sits between two markers:

    /* @shared olvaso-kit */
    ...the block, exactly as in tools/shared/olvaso-kit.js...
    /* @end olvaso-kit */

Fix a shared block in tools/shared/<name>.js, then run this script to copy it into every game.
`python3 tools/build_site.py --check` fails when a game's block differs from its master copy.

Usage:
  python3 tools/sync_shared.py           # update every marked block from tools/shared/
  python3 tools/sync_shared.py --check   # only report differences (exit 1 if any)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "tools" / "shared"
BLOCK = re.compile(r"/\* @shared ([a-z0-9-]+) \*/\n(.*?)/\* @end \1 \*/", re.S)


def read(f):
    return f.read_text(encoding="utf-8").replace("\r\n", "\n")


def masters():
    return {f.stem: read(f) for f in sorted(SHARED.glob("*.js"))}


def pages():
    return sorted(p for p in ROOT.glob("*/index.html") if p.parent.name not in {"tools", "assets", "_site"})


def differences():
    """Yields (page, block name, message) for every marked block that differs from its master."""
    m = masters()
    for page in pages():
        text = read(page)
        rel = page.relative_to(ROOT).as_posix()
        if text.count("/* @shared ") != len(BLOCK.findall(text)):
            yield rel, "?", "a '/* @shared name */' marker has no matching '/* @end name */'"
        for b in BLOCK.finditer(text):
            name, body = b.group(1), b.group(2)
            if name not in m:
                yield rel, name, f"no master copy tools/shared/{name}.js"
                continue
            if body == m[name]:
                continue
            got, want = body.split("\n"), m[name].split("\n")
            n = next((i for i in range(max(len(got), len(want)))
                      if i >= len(got) or i >= len(want) or got[i] != want[i]), 0)
            line = text.count("\n", 0, b.start(2)) + n + 1
            yield rel, name, f"line {line} differs from tools/shared/{name}.js line {n + 1}"


def sync():
    m, changed = masters(), 0
    for page in pages():
        text = read(page)
        new = BLOCK.sub(lambda b: b.group(0) if b.group(1) not in m else
                        f"/* @shared {b.group(1)} */\n{m[b.group(1)]}/* @end {b.group(1)} */", text)
        if new != text:
            page.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
            print(f"updated {page.relative_to(ROOT).as_posix()}")
    print(f"{changed} page(s) updated")


if __name__ == "__main__":
    if "--check" in sys.argv:
        bad = list(differences())
        for rel, name, msg in bad:
            print(f"{rel}: shared block '{name}': {msg}")
        sys.exit(1 if bad else 0)
    sync()

#!/usr/bin/env python3
"""Browser smoke test for every page (see AGENTS.md).

Opens the start page and each game at phone size (400×860) in headless Chromium and checks:
  - no JavaScript error and no console error
  - no request to any host except the allowed font hosts
  - no sideways scrolling, and no button or link cut off at the screen edge
It does not play the games. Look at the screenshots, and play the changed game by hand.

Screenshots go to _site/smoke/ (ignored by git).

Usage:
  pip install playwright && python3 -m playwright install chromium   # once
  python3 tools/smoke_test.py            # all pages
  python3 tools/smoke_test.py falbonto   # one game
"""
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"fonts.googleapis.com", "fonts.gstatic.com"}
SHOTS = ROOT / "_site" / "smoke"


def pages(only):
    out = [ROOT / "index.html"] if not only else []
    for d in sorted(ROOT.iterdir()):
        if (d / "index.html").exists() and d.name not in {"tools", "_site"} and not d.name.startswith("."):
            if not only or d.name in only:
                out.append(d / "index.html")
    return out


def main():
    only = set(sys.argv[1:])
    SHOTS.mkdir(parents=True, exist_ok=True)
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for page_file in pages(only):
            name = page_file.parent.name if page_file.parent != ROOT else "index"
            ctx = browser.new_context(viewport={"width": 400, "height": 860}, has_touch=True)
            pg = ctx.new_page()
            problems = []
            pg.on("pageerror", lambda e: problems.append(f"JS error: {e}"))
            pg.on("console", lambda m: m.type == "error" and "net::" not in m.text
                  and problems.append(f"console error: {m.text}"))

            def on_request(req):
                host = urlparse(req.url).hostname
                if req.url.startswith(("http://", "https://")) and host not in ALLOWED:
                    problems.append(f"request to {host}")
            pg.on("request", on_request)
            pg.goto(page_file.as_uri())
            pg.wait_for_timeout(1200)
            pg.evaluate("window.scrollTo(300, 0)")
            if pg.evaluate("window.scrollX") > 0:
                problems.append("the page scrolls sideways at a 400px screen")
            cut = pg.evaluate("""() => [...document.querySelectorAll('button, a, input, select')]
                .filter(e => e.offsetParent !== null && getComputedStyle(e).visibility !== 'hidden')
                .filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > innerWidth + 1 || r.left < -1); })
                .map(e => (e.id ? '#' + e.id : e.tagName.toLowerCase()) + ' ' + (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 20))""")
            for c in cut:
                problems.append(f"control cut off at the screen edge: {c}")
            pg.screenshot(path=str(SHOTS / f"{name}.png"))
            ctx.close()
            status = "OK  " if not problems else "FAIL"
            print(f"{status} {name}" + "".join(f"\n       {x}" for x in problems))
            failed += bool(problems)
        browser.close()
    print(f"\n{failed} failed. Screenshots: {SHOTS.relative_to(ROOT)}/")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

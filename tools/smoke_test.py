#!/usr/bin/env python3
"""Browser smoke test for every page (see AGENTS.md).

Opens the start page and each game at two phone sizes (400×860 and the small 360×640) in headless
Chromium and checks:
  - no JavaScript error and no console error
  - no request to any host except the allowed font hosts
  - no sideways scrolling, and no button or link cut off at the screen edge
  - the top bar (back link and fullscreen button) does not cover any visible text or control
  - a control below the visible area can be scrolled to (it has a scrolling ancestor)
  - every visible control is a touch target of at least 44×44 px (exceptions: TOUCH_EXCEPTIONS)
It does not play the games. Look at the screenshots, and play the changed game by hand.

Screenshots go to _site/smoke/<page>-<width>x<height>.png (ignored by git).

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
SIZES = [(400, 860), (360, 640)]
MIN_TOUCH = 44

# Controls that may stay smaller than 44 px, each with its reason. Keys are "page selector";
# the selector is matched with Element.matches(). Do not lower MIN_TOUCH instead.
TOUCH_EXCEPTIONS = {
    "index .card>a": "the link's ::after layer covers the whole card, the real target is the card",
}

CHECKS = r"""
({minTouch, exceptions}) => {
  const out = [];
  const visible = e => {
    if (e.offsetParent === null && getComputedStyle(e).position !== 'fixed') return false;
    for (let a = e; a; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) return false;
    }
    const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0;
  };
  const name = e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/)[0] : ''))
    + ' "' + (e.getAttribute('aria-label') || e.textContent || e.value || '').trim().replace(/\s+/g, ' ').slice(0, 20) + '"';
  const controls = [...document.querySelectorAll('button, a[href], input:not([type=hidden]), select, textarea')].filter(visible);

  // 1. cut off at the side
  const sideScroll = e => { for (let a = e.parentElement; a && a !== document.body; a = a.parentElement)
    if (['auto', 'scroll'].includes(getComputedStyle(a).overflowX)) return true; return false; };
  for (const e of controls) { const r = e.getBoundingClientRect();
    if ((r.right > innerWidth + 1 || r.left < -1) && !sideScroll(e)) out.push('control cut off at the screen edge: ' + name(e)); }

  // 2. the top bar covers something
  const bar = document.querySelector('.top-bar');
  if (bar && visible(bar)) {
    const things = [...document.querySelectorAll('button, a[href], input, select, h1, h2, h3, p, label, li, td, th, .title')]
      .filter(e => !bar.contains(e) && visible(e));
    for (const e of things) {
      // only the part that is not clipped away by a scrolling or clipping ancestor can be covered
      const b0 = e.getBoundingClientRect();
      const r = {left: b0.left, right: b0.right, top: b0.top, bottom: b0.bottom};
      for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
        if (getComputedStyle(a).overflowY === 'visible') continue;
        const c = a.getBoundingClientRect();
        r.left = Math.max(r.left, c.left); r.right = Math.min(r.right, c.right);
        r.top = Math.max(r.top, c.top); r.bottom = Math.min(r.bottom, c.bottom);
      }
      if (r.right - r.left < 4 || r.bottom - r.top < 4) continue;
      for (const b of bar.children) {
        if (!visible(b)) continue;
        const q = b.getBoundingClientRect();
        const x0 = Math.max(r.left, q.left), x1 = Math.min(r.right, q.right), y0 = Math.max(r.top, q.top), y1 = Math.min(r.bottom, q.bottom);
        if (x1 - x0 < 4 || y1 - y0 < 4) continue;
        const hit = document.elementFromPoint((x0 + x1) / 2, (y0 + y1) / 2);
        if (hit && bar.contains(hit)) { out.push('the top bar covers ' + name(e)); break; }
      }
    }
  }

  // 3. below the visible area and nothing scrolls to it
  const canScroll = (a) => {
    const s = getComputedStyle(a);
    if (a === document.documentElement || a === document.body) {
      const d = document.scrollingElement;
      return d.scrollHeight > innerHeight + 1 && !['hidden', 'clip'].includes(getComputedStyle(document.documentElement).overflowY)
        && !['hidden', 'clip'].includes(getComputedStyle(document.body).overflowY);
    }
    return ['auto', 'scroll'].includes(s.overflowY) && a.scrollHeight > a.clientHeight + 1;
  };
  for (const e of controls) {
    const r = e.getBoundingClientRect();
    if (r.bottom <= innerHeight + 1 && r.top >= -1) continue;
    let ok = false, fixed = false;
    for (let a = e.parentElement; a; a = a.parentElement) {
      if ((a === document.body || a === document.documentElement) && fixed) break;
      if (canScroll(a)) { ok = true; break; }
      if (getComputedStyle(a).position === 'fixed') fixed = true;
    }
    if (!ok) out.push('control outside the screen and nothing scrolls to it: ' + name(e));
  }

  // 4. touch target size
  const skip = e => Object.keys(exceptions).some(sel => { try { return e.matches(sel); } catch (_) { return false; } });
  const seen = new Set();
  for (const e of controls) {
    let t = e;
    const lab = e.closest('label');
    if (e.tagName === 'INPUT' && lab) t = lab;
    if (seen.has(t) || skip(e) || skip(t)) continue;
    seen.add(t);
    // a link inside running text is not a touch control of its own
    if (e.tagName === 'A' && getComputedStyle(e).display === 'inline' && e.closest('p, li, footer, small')) continue;
    const r = t.getBoundingClientRect();
    if (r.width < minTouch - 0.5 || r.height < minTouch - 0.5)
      out.push(`touch target ${Math.round(r.width)}×${Math.round(r.height)} px is under ${minTouch} px: ` + name(e));
  }
  return out;
}
"""


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
            exceptions = {sel.split(" ", 1)[1]: why for sel, why in TOUCH_EXCEPTIONS.items()
                          if sel.split(" ", 1)[0] == name}
            problems = []
            for w, h in SIZES:
                ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True)
                pg = ctx.new_page()
                found = []
                pg.on("pageerror", lambda e: found.append(f"JS error: {e}"))
                pg.on("console", lambda m: m.type == "error" and "net::" not in m.text
                      and found.append(f"console error: {m.text}"))

                def on_request(req):
                    host = urlparse(req.url).hostname
                    if req.url.startswith(("http://", "https://")) and host not in ALLOWED:
                        found.append(f"request to {host}")
                pg.on("request", on_request)
                pg.goto(page_file.as_uri())
                pg.wait_for_timeout(1200)
                pg.evaluate("window.scrollTo(300, 0)")
                if pg.evaluate("window.scrollX") > 0:
                    found.append(f"the page scrolls sideways at a {w}px screen")
                pg.evaluate("window.scrollTo(0, 0)")
                found += pg.evaluate(CHECKS, {"minTouch": MIN_TOUCH, "exceptions": exceptions})
                pg.screenshot(path=str(SHOTS / f"{name}-{w}x{h}.png"))
                ctx.close()
                problems += [f"{w}×{h}: {x}" for x in dict.fromkeys(found)]
            status = "OK  " if not problems else "FAIL"
            print(f"{status} {name}" + "".join(f"\n       {x}" for x in problems), flush=True)
            failed += bool(problems)
        browser.close()
    print(f"\n{failed} failed. Screenshots: {SHOTS.relative_to(ROOT)}/")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

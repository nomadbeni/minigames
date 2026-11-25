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
  - the fullscreen button works: a tap enters fullscreen and the label changes to „Kilépés”. Headless
    Chromium enters fullscreen but keeps the window size, so the test then makes the screen taller, as
    a phone does when the browser bars go away, and runs the checks above again, plus: the biggest
    canvas is on the screen and its picture is not stretched. A second tap leaves fullscreen, the label
    changes back, and the checks run once more at the normal size.
It does not play the games. Look at the screenshots, and play the changed game by hand.

Screenshots go to _site/smoke/<page>-<width>x<height>.png, in fullscreen <page>-<width>x<height>-fs.png
(ignored by git).

Usage:
  pip install playwright && python3 -m playwright install chromium   # once
  python3 tools/smoke_test.py            # all pages
  python3 tools/smoke_test.py falbonto   # one game
"""
import base64
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"fonts.googleapis.com", "fonts.gstatic.com"}
SHOTS = ROOT / "_site" / "smoke"
SIZES = [(400, 860), (360, 640)]
FS_EXTRA = 80          # px a phone gains in fullscreen when the address bar and the bottom bar go away
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


# The biggest visible canvas (the playing field) must be on the screen and not stretched: the aspect ratio of
# its picture (width × height attributes) must match the aspect ratio it is shown at. A canvas that is not
# redrawn after a resize shows a squashed or blurred picture, or hangs off the screen.
CANVAS = r"""
() => {
  const out = [];
  const cs = [...document.querySelectorAll('canvas')].filter(c => {
    const r = c.getBoundingClientRect(), s = getComputedStyle(c);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && c.closest('[hidden]') === null;
  });
  if (!cs.length) return out;
  const area = c => { const r = c.getBoundingClientRect(); return r.width * r.height; };
  const c = cs.sort((a, b) => area(b) - area(a))[0];
  const r = c.getBoundingClientRect();
  if (r.width < 40 || r.height < 40) return out;                 // a small icon, not a playing field
  const nm = 'canvas' + (c.id ? '#' + c.id : '');
  if (r.left < -1 || r.right > innerWidth + 1) out.push(`${nm} hangs off the side of the screen (${Math.round(r.left)}…${Math.round(r.right)} px)`);
  const fit = getComputedStyle(c).objectFit;
  if (c.width && c.height && !['contain', 'cover', 'scale-down'].includes(fit)) {
    const want = c.width / c.height, shown = r.width / r.height;
    if (Math.abs(shown / want - 1) > 0.015)
      out.push(`${nm} is stretched: picture ${c.width}×${c.height}, shown at ${Math.round(r.width)}×${Math.round(r.height)} px`);
  }
  return out;
}
"""


def check_layout(pg, w):
    """The checks that run at every screen size: sideways scrolling, CHECKS and CANVAS."""
    found = []
    pg.evaluate("window.scrollTo(300, 0)")
    if pg.evaluate("window.scrollX") > 0:
        found.append(f"the page scrolls sideways at a {w}px screen")
    pg.evaluate("window.scrollTo(0, 0)")
    return found


def is_fs(pg):
    return pg.evaluate("!!(document.fullscreenElement || document.webkitFullscreenElement)")


def fs_label(pg):
    return pg.evaluate("(b => b ? (b.getAttribute('aria-label') || '') + ' | ' + b.textContent : null)"
                       "(document.querySelector('.fs-btn'))")


# counts fullscreenchange events: the button label changes on that event, after fullscreenElement is set
FS_COUNT = """window.__fsChanges = 0;
document.addEventListener('fullscreenchange', () => window.__fsChanges++);"""


def tap(loc):
    """Click like a finger would. Returns why it could not, e.g. which element covers the button."""
    try:
        loc.click(timeout=3000)
        return ""
    except Exception as e:
        why = [ln.strip() for ln in str(e).splitlines() if "intercepts pointer events" in ln]
        return why[0] if why else str(e).splitlines()[0]


def wait_changes(pg, n, timeout=3000):
    """Wait until n fullscreenchange events came. (wait_for_function would need eval, the page's CSP forbids it.)"""
    for _ in range(timeout // 50):
        if pg.evaluate("window.__fsChanges") >= n:
            return True
        pg.wait_for_timeout(50)
    return False


def set_size(pg, w, h):
    """Resize the page. While the window is in fullscreen Playwright cannot resize it, so use the DevTools
    protocol to change only the size the page sees."""
    cdp = pg.context.new_cdp_session(pg)
    cdp.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})
    cdp.detach()


def check_fullscreen(pg, w, h, shot, run_checks):
    """Tap the fullscreen button, check the page at the taller fullscreen size, tap again to leave."""
    found = []
    btn = pg.locator(".fs-btn")
    if not btn.count() or not btn.first.is_visible():
        return []                       # the start page has none; a game removes it where the browser cannot do it
    pg.evaluate(FS_COUNT)
    if (err := tap(btn.first)):
        return [f"the fullscreen button cannot be tapped: {err}"]
    if not wait_changes(pg, 1) or not is_fs(pg):
        return ["tapping the fullscreen button does not enter fullscreen"]
    lab = fs_label(pg)
    if "Kilépés" not in lab:
        found.append(f"in fullscreen the button does not say „Kilépés”: {lab!r}")
    set_size(pg, w, h + FS_EXTRA)
    pg.wait_for_timeout(600)
    found += [f"fullscreen {w}×{h + FS_EXTRA}: {x}" for x in run_checks()]
    # Playwright would cut the picture at the old height, the DevTools protocol takes it at the new one
    cdp = pg.context.new_cdp_session(pg)
    shot.write_bytes(base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "png"})["data"]))
    cdp.detach()
    if (err := tap(btn.first)):
        found.append(f"in fullscreen the button cannot be tapped: {err}")
    wait_changes(pg, 2)
    if is_fs(pg):
        found.append("tapping the button again does not leave fullscreen")
        pg.evaluate("document.exitFullscreen && document.exitFullscreen().catch(() => {})")
    lab = fs_label(pg)
    if "Kilépés" in lab or "Teljes képernyő" not in lab:
        found.append(f"after leaving fullscreen the button does not say „Teljes képernyő” again: {lab!r}")
    set_size(pg, w, h)
    pg.wait_for_timeout(600)
    found += [f"after fullscreen: {x}" for x in run_checks()]
    return found


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

                def run_checks(pg=pg, w=w):
                    return (check_layout(pg, w) + pg.evaluate(CHECKS, {"minTouch": MIN_TOUCH, "exceptions": exceptions})
                            + pg.evaluate(CANVAS))
                found += run_checks()
                pg.screenshot(path=str(SHOTS / f"{name}-{w}x{h}.png"))
                found += check_fullscreen(pg, w, h, SHOTS / f"{name}-{w}x{h}-fs.png", run_checks)
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

#!/usr/bin/env python3
"""Cover pictures for the start page cards (assets/covers/<folder>.webp).

Opens every game at phone size with an empty save, starts it the way the play test does (main button,
a few taps and keys), photographs the play area and saves a small WebP (400×240, under 30 KB).
This is a tool to run by hand after adding or visibly changing a game, not a build step: the pictures
are committed, and `tools/build_site.py --check` fails when a game has none.

Usage:
  pip install playwright pillow && python3 -m playwright install chromium   # once
  python3 tools/make_covers.py              # every game
  python3 tools/make_covers.py falbonto     # one game
Look at the pictures afterwards; a game that needs a better moment gets an entry in SHOTS.
"""
import asyncio
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from play_test import Run, list_games, poke, start_server  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "covers"
W, H = 400, 240
MAX_BYTES = 30_000
AREA = "canvas, #board, #field, #stage, #game, .board, .grid, main"

# Games that need something other than the default:
#   "poke": False   do not start the game the play test way
#   "clicks"        selectors clicked one after the other (to start it the right way)
#   "js"            a script run after that (e.g. step a build plan to its top layer)
#   "wait"          extra time in ms before the photo (an intro or a countdown)
#   "area"          the element to photograph;  "align": "top" keeps its top instead of its middle
PLAN = {"poke": False, "area": "#isocv",
        "js": "(() => { const b = document.querySelector('#next'); for (let i = 0; i < 99 && b && !b.disabled; i++) b.click(); })()"}
SHOTS = {
    "falbonto": {"align": "top", "wait": 300},
    "flipper": {"poke": False, "clicks": ['#card button[data-act="new"]', '#card button[data-act="go"]'], "align": "top",
                "js": "__flipper.G.ball.state = 'play'; __flipper.G.ball.x = 200; __flipper.G.ball.y = 180; __flipper.G.ball.vy = 300", "wait": 400},
    "teglatoro": {"poke": False, "clicks": ['[data-diff="normal"]', "#cv"], "align": "top", "wait": 900},
    "gyemantbanya": {"poke": False, "clicks": ["#d-easy"], "area": "#board"},
    "kocka-kert": {"area": "#field"},
    "bringa-futam": {"wait": 3500},
    "cornholescore": {"poke": False, "area": "body", "align": "top",
                      "js": "document.querySelector('.top-bar').style.display = 'none'"},
    "kertvedo": {"wait": 9000},
    "pasziansz": {"poke": False, "clicks": ['[data-v="k1"]'], "area": "#board", "align": "top", "wait": 2500},
    **{g: PLAN for g in ["coloptorony", "feketevar-lovagerod", "hegyormi-var", "kokastely-arokkal", "rejtekhaz",
                         "sasfeszek-sziklavar", "tundervar"]},
}


async def shoot(browser, base, game):
    opt = SHOTS.get(game, {})
    async with Run(browser, base, mobile=True) as r:
        await r.goto(f"{game}/index.html")
        await r.page.wait_for_timeout(600)
        if opt.get("poke", True):
            await poke(r.page, mobile=True)
        for sel in opt.get("clicks", []):
            btn = r.page.locator(sel).filter(visible=True).first
            if await btn.count():
                await btn.click(timeout=3000)
            await r.page.wait_for_timeout(300)
        if opt.get("js"):
            await r.page.evaluate(opt["js"])
        await r.page.wait_for_timeout(opt.get("wait", 400))
        # the back link and the fullscreen button are on every page, they are not part of the picture
        await r.page.evaluate("document.querySelectorAll('.top-bar').forEach(e => e.style.visibility = 'hidden')")
        box = await r.page.evaluate("""sel => {
            const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
              return r.width > 120 && r.height > 80 && s.visibility !== 'hidden' && s.display !== 'none'; };
            const all = [...document.querySelectorAll(sel)].filter(vis);
            all.sort((a, b) => { const p = a.getBoundingClientRect(), q = b.getBoundingClientRect(); return q.width * q.height - p.width * p.height; });
            const e = all[0]; if (!e) return null;
            if (e !== document.body) e.scrollIntoView({block: e.getBoundingClientRect().height > innerHeight ? 'start' : 'center'});
            const r = e.getBoundingClientRect();
            return {x: Math.max(0, r.left), y: Math.max(0, r.top), w: Math.min(r.width, innerWidth), h: Math.min(r.height, innerHeight - Math.max(0, r.top))};
        }""", opt.get("area", AREA))
        vw, vh = 390, 780
        if not box:
            box = {"x": 0, "y": 60, "w": vw, "h": vh - 60}
        # the largest 5:3 window inside the area, centred on it
        w = min(box["w"], box["h"] * W / H)
        h = w * H / W
        top = box["y"] if opt.get("align") == "top" else box["y"] + (box["h"] - h) / 2
        clip = {"x": box["x"] + (box["w"] - w) / 2, "y": top, "width": w, "height": h}
        png = await r.page.screenshot(clip=clip)
    img = Image.open(io.BytesIO(png)).convert("RGB").resize((W, H), Image.LANCZOS)
    for q in range(80, 20, -5):
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=q, method=6)
        if buf.tell() <= MAX_BYTES:
            break
    (OUT / f"{game}.webp").write_bytes(buf.getvalue())
    return buf.tell(), q


async def main():
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    httpd, base = start_server()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for game in list_games():
            if only and game not in only:
                continue
            size, q = await shoot(browser, base, game)
            print(f"{game:24} {size / 1000:5.1f} KB  (quality {q})", flush=True)
        await browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

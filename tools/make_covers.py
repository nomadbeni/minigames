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
    "bombasz": {"poke": False, "clicks": ['#card button[data-act="new"]'], "area": "#cv", "wait": 150,
                "js": "(() => { const b = __bombasz, G = b.G; G.phase = 'play'; [[3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7],[7,6],[7,8],[3,8],[3,9]].forEach(([x,y]) => { if (G.map[b.idx(x,y)] === 2) G.map[b.idx(x,y)] = 0; }); G.p.x = G.p.tx = 3; G.p.y = G.p.ty = 7; G.p.face = [0, 1]; G.pw.fire = 2; G.bombs.push({x: 3, y: 9, t: 9, age: 0, range: 2, pass: false}); const e = {x: 7, y: 7, t: 9, age: 0, range: 2, pass: false}; G.bombs.push(e); b.explode(e); b.draw(); })()"},
    "falbonto": {"align": "top", "wait": 300},
    "flipper": {"poke": False, "clicks": ['#card button[data-act="new"]', '#card button[data-act="go"]'], "align": "top",
                "js": "__flipper.G.ball.state = 'play'; __flipper.G.ball.x = 200; __flipper.G.ball.y = 180; __flipper.G.ball.vy = 300", "wait": 400},
    "nyilak": {"poke": False, "clicks": ['#card button[data-act="play"]'], "area": "#cv",
               "js": "(() => { __nyilak.startLevel(14); __nyilak.draw(); })()"},
    "pici-gyumolcsvago": {"poke": False, "area": "#cv", "js": "__baba.demo()"},
    "kigyo": {"poke": False, "clicks": ['#card button[data-act="new"]'], "area": "#cv",
              "js": "(() => { const G = __kigyo.G; G.s = [[9,7],[8,7],[7,7],[6,7],[5,7],[4,7],[4,8],[4,9],[5,9],[6,9],[7,9],[8,9],[9,9],[10,9],[11,9]]; G.d = [1,0]; G.food = [13,7]; G.gold = {p: [14,10], t: 40}; G.phase = 'play'; G.score = 17; __kigyo.draw(); })()"},
    "teglatoro": {"poke": False, "clicks": ['[data-diff="normal"]', "#cv"], "align": "top", "wait": 900},
    "gyemantbanya": {"poke": False, "clicks": ["#d-easy"], "area": "#board"},
    "kocka-kert": {"area": "#field"},
    "bringa-futam": {"wait": 3500},
    "cornholescore": {"poke": False, "area": "body", "align": "top",
                      "js": "document.querySelector('.top-bar').style.display = 'none'"},
    "kertvedo": {"wait": 9000},
    "kozapor": {"poke": False, "clicks": ['#card button[data-act="new"]'], "wait": 300,
                "js": "(() => { const G = __kozapor.G, h = __kozapor.H, s = G.ship; G.banner = null; s.inv = 0; s.a = -1.1; "
                      "[[70, -70], [290, -40], [250, 95], [95, 85]].forEach(([x, y], i) => Object.assign(G.rocks[i], {x, y: h / 2 + y})); "
                      "for (let i = 1; i < 4; i++) G.bullets.push({x: s.x + Math.cos(s.a) * 24 * i, y: s.y + Math.sin(s.a) * 24 * i, vx: 0, vy: 0, t: 9}); "
                      "G.phase = 'pause'; })()"},
    "urflotta": {"poke": False, "clicks": ['#card button[data-act="new"]'], "align": "top", "wait": 2200,
                 "js": "(() => { const G = __urflotta.G; G.aliens.splice(13, 3); G.aliens.splice(30, 2); })()"},
    "szarnycsapas": {"poke": False, "clicks": ['#card button[data-act="new"]'],
                     "js": "(() => { const G = __szarny.G; G.phase = 'pause'; G.score = 7; G.y = __szarny.floorY() * .5; G.rot = -.25; "
                           "G.pipes = [{x: 10, top: __szarny.floorY() * .5 - 100, gap: 160, w: 58}, {x: 206, top: __szarny.floorY() * .5 - 20, gap: 160, w: 58}]; })()"},
    "duplazo": {"poke": False, "clicks": ['#card button[data-act="new"]'], "area": "#cv", "wait": 500,
                "js": "(() => { __duplazo.G.g = [2,0,4,2, 8,16,32,4, 128,64,16,8, 256,512,1024,2048].map(v => v ? {id: Math.random(), v} : null); __duplazo.draw(); })()"},
    "kardvihar": {"poke": False, "clicks": ['#card button[data-act="new"]'], "wait": 200,
                  "js": "(() => { const K = __kardvihar, G = K.G, p = G.pl; G.banner = null; G.toSpawn = []; G.en = []; p.inv = 0; p.face = 0.3; "
                        "[['slime', 70, -60], ['bat', -80, -40], ['boar', -60, 70], ['shroom', 110, 50], ['slime', 20, 95]].forEach(([k, dx, dy]) => { K.spawn(k); Object.assign(G.en[G.en.length - 1], {x: p.x + dx, y: p.y + dy, born: 0}); }); "
                        "G.parts = []; K.attack(); G.phase = 'pause'; })()"},
    "szigetrepulo": {"poke": False, "clicks": ['#card button[data-act="new"]'], "wait": 900,
                     "js": "(() => { const T = __szigetrepulo, G = T.G; T.S.view = 1; G.inv = 0; G.alt = Math.max(G.alt, 70); G.roll = 0.35; "
                           "G.rings.push({x: (G.x + Math.cos(G.yaw) * 90 + 1024) % 1024, y: (G.y + Math.sin(G.yaw) * 90 + 1024) % 1024, alt: G.alt + 4, ang: G.yaw}); "
                           "T.K.boost = 1; })()"},
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

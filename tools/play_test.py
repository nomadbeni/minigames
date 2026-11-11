#!/usr/bin/env python3
"""Plays the games in a headless browser (see AGENTS.md). Goes further than tools/smoke_test.py:

  every game    loads and is played a little on a desktop (keyboard, mouse) and on a phone (touch):
                no JavaScript error, no request to a host other than the allowed font hosts,
                no sideways scrolling; then five kinds of broken saved data are written into
                localStorage, and the game must still start and play without an error
  scenarios     short real play-throughs of the reading games that check the outcome
                (paid, delivered, quest taken, level cleared, death counted, save written)
  generators    the Gyémántbánya and Kincsvadász level generators (and the E-Útvesztő maze generator), taken from the published pages,
                make hundreds of levels; each must be found, be a valid puzzle and have exactly one
                solution (checked by an independent solver)

Usage:
  pip install playwright && python3 -m playwright install chromium   # once
  python3 tools/play_test.py                 # everything (a few minutes)
  python3 tools/play_test.py --quick         # fewer generated levels
  python3 tools/play_test.py horda csapda    # only these games (and their scenarios)
  python3 tools/play_test.py --only generators
"""
import asyncio
import json
import re
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
SKIP = {"tools", "assets", "_site"}
PARALLEL = 4


# ---------------------------------------------------------------- server and pages

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def list_games():
    return [d.name for d in sorted(ROOT.iterdir())
            if d.is_dir() and not d.name.startswith(".") and d.name not in SKIP and (d / "index.html").exists()]


class Run:
    """One browser context with everything that went wrong in it."""

    def __init__(self, browser, base, mobile=False, seed=None):
        self.browser, self.base, self.mobile, self.seed = browser, base, mobile, seed
        self.errors, self.external = [], []

    async def __aenter__(self):
        size = {"width": 390, "height": 780} if self.mobile else {"width": 1280, "height": 800}
        self.ctx = await self.browser.new_context(viewport=size, has_touch=self.mobile, is_mobile=self.mobile)
        if self.seed is not None:
            # Written once per tab, before any game script runs; a reload keeps what the game saved.
            await self.ctx.add_init_script(
                "(e=>{if(!sessionStorage.getItem('seeded')){sessionStorage.setItem('seeded','1');"
                "for(const [k,v] of Object.entries(e))localStorage.setItem(k,v)}})(" + json.dumps(self.seed) + ")")

        async def route(r):
            u = urlparse(r.request.url)
            if r.request.url.startswith(self.base) or u.scheme in ("data", "blob"):
                await r.continue_()
            elif u.hostname in ALLOWED_HOSTS:
                await r.fulfill(status=200, body="")   # allowed, but never wait on the network
            else:
                self.external.append(r.request.url)
                await r.fulfill(status=200, body="")
        await self.ctx.route("**/*", route)
        self.page = await self.ctx.new_page()
        self.page.on("pageerror", lambda e: self.errors.append(f"JS error: {e}"))
        self.page.on("console", lambda m: m.type == "error" and self.errors.append(f"console error: {m.text}"))
        self.page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))
        return self

    async def goto(self, route):
        await self.page.goto(f"{self.base}/{route}", wait_until="load", timeout=20000)

    async def __aexit__(self, *exc):
        await self.ctx.close()


async def poke(page, mobile=False):
    """Plays a little without knowing the game: main button, taps or clicks, the usual keys."""
    for _ in range(2):
        btn = page.locator(", ".join([
            "#ov:not([hidden]) .btn.hot", "dialog[open] button", ".modal:not([hidden]) button",
            "button.hot", "button.primary", ".btn.primary", 'button:has-text("Start")', 'button:has-text("Indul")',
            'button:has-text("Kezd")', 'button:has-text("Játék")', 'button:has-text("Új")',
        ])).filter(visible=True).first
        if await btn.count():
            try:
                await btn.click(timeout=2000)
            except Exception:
                pass
        await page.wait_for_timeout(300)
    area = page.locator("canvas, #board, #field, #stage, main").filter(visible=True).first
    if await area.count():
        box = await area.bounding_box()
        if box:
            for fx, fy in [(.5, .5), (.3, .6), (.7, .4), (.5, .8)]:
                x, y = box["x"] + box["width"] * fx, box["y"] + box["height"] * fy
                try:
                    await (page.touchscreen.tap(x, y) if mobile else page.mouse.click(x, y))
                except Exception:
                    pass
                await page.wait_for_timeout(120)
    for key in ["ArrowRight", "ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Space", "Enter", "KeyJ", "KeyK"]:
        await page.keyboard.down(key)
        await page.wait_for_timeout(70)
        await page.keyboard.up(key)
    await page.wait_for_timeout(800)


# ---------------------------------------------------------------- every game

# The reading games' saves are named here so they are always tested; other keys are found at run time.
KNOWN_KEYS = ["olvaso:xp", "olvaso:mastery", "olvaso:settings", "olvaso:sound", "bringa-muhely:save", "bringa:own",
              "bringa:penz", "bringa-futam:best", "betu-csata:best", "bunyo:save", "csapda:save", "horda:save",
              "kalandor:save", "kertvedo:save", "kocka-kert:save", "dobozmester:save", "tankorseg:save", "kokori-kaland:save"]
BROKEN = {
    "not JSON": '{"half":',
    "a string": '"szöveg"',
    "a huge number": "1e308",
    "an array": '[1,"x",null]',
    "wrong shapes": json.dumps({
        "day": "x", "served": -3, "lv": "ab", "dayStars": "q", "szin": "red;}", "szinek": 5,
        "tiles": [1, None, {"s": "crop", "c": "zz", "g": "x"}], "orders": [{}, {"items": "x"}],
        "inv": {"repa": "x", "zz": 1}, "got": 5, "dead": {}, "unlocked": "ricsi", "have": 7, "done": [1],
        "deaths": "x", "total": "x", "best": "<b>x</b>", "wave": None, "won": 99, "x": 999, "y": -4, "hp": "x",
        "q": 1e9, "qs": "x", "v": 1, "split": "<img>", "size": 77, "seed": "zz", "lvl": -1, "money": "sok",
        "__proto__": {"polluted": 1}}),
}


async def test_game(browser, base, game):
    problems = []
    route = f"{game}/index.html"
    async with Run(browser, base) as r:
        await r.goto(route)
        if not (await r.page.title()).strip():
            problems.append("no <title>")
        if await r.page.locator('a.home-link[href="../index.html"]').count() != 1:
            problems.append("no back link")
        await poke(r.page)
        keys = set(KNOWN_KEYS) | set(await r.page.evaluate("Object.keys(localStorage)"))
        problems += [f"desktop: {e}" for e in r.errors] + [f"request to another site: {u}" for u in r.external]
    async with Run(browser, base, mobile=True) as r:
        await r.goto(route)
        await poke(r.page, mobile=True)
        overflow = await r.page.evaluate("document.documentElement.scrollWidth - innerWidth")
        if overflow > 1:
            problems.append(f"phone: scrolls sideways ({overflow}px)")
        problems += [f"phone: {e}" for e in r.errors]
    for name, value in BROKEN.items():
        async with Run(browser, base, seed={k: value for k in keys}) as r:
            await r.goto(route)
            await poke(r.page)
            await r.page.reload()
            await poke(r.page)
            if await r.page.evaluate("({}).polluted") is not None:
                problems.append(f"saves as {name}: saved data reached the object prototype")
            problems += [f"saves as {name}: {e}" for e in r.errors]
    return problems


async def test_start_page(browser, base, games):
    problems = []
    async with Run(browser, base) as r:
        await r.goto("index.html")
        await r.page.wait_for_timeout(300)
        hrefs = await r.page.locator("a[href]").evaluate_all("as => as.map(a => a.getAttribute('href'))")
        for g in games:
            if not any(h.lstrip("./").startswith(f"{g}/") for h in hrefs):
                problems.append(f"no link to {g}")
        problems += r.errors + [f"request to another site: {u}" for u in r.external]
    return problems


# ---------------------------------------------------------------- scenarios

class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def save(**kv):
    return {k: json.dumps(v) for k, v in kv.items()}


async def hold(page, key, ms):
    await page.keyboard.down(key)
    await page.wait_for_timeout(ms)
    await page.keyboard.up(key)


async def txt(page, sel):
    return (await page.locator(sel).first.inner_text()).replace("·", "")


async def sc_kit(page):
    k = await page.evaluate("({xp:K.xp, split:K.settings.split, sound:K.sound, lv:K.level('fék'), rank:K.rank().name})")
    check(k == {"xp": 0, "split": "auto", "sound": True, "lv": 2, "rank": "Bronz"}, f"broken shared saves repaired: {k}")
    m = json.loads(await page.evaluate("K.seen('fék'), localStorage.getItem('olvaso:mastery')"))
    check(m == {"fék": 4}, f"only valid word counts are kept: {m}")
    steps = await page.evaluate("""(() => { const out = []; for (let i = 0; i < 9; i++) { const h = K.word('gyors|tüzelés');
        out.push(h.includes('class="dot"') ? 2 : h.includes('class="p1"') ? 1 : 0); K.seen('gyors|tüzelés'); } return out; })()""")
    check(steps == [2, 2, 2, 2, 1, 1, 1, 1, 0], f"long words are split until mastered: {steps}")


async def sc_bike_shop(page):
    zones = {"első gumi": "elso", "hátsó gumi": "hatso", "küllő": "hatso", "fék": "fek", "lánc": "lanc", "nyereg": "nyereg",
             "kormány": "kormany", "váltó": "valto", "lámpa": "lampa", "pedál": "pedal", "csengő": "csengo", "akku": "akku"}
    complaint = await txt(page, "#complaint")
    zone = next((z for k, z in zones.items() if k in complaint), None)
    check(zone, f"complaint understood: {complaint}")
    await page.locator(f'.zone[data-z="{zone}"]').dispatch_event("click")
    await page.locator(".box").first.wait_for()
    for box in await page.locator(".box").all():
        if await page.locator(".box.yes").count():
            break
        await box.click()
        await page.wait_for_timeout(80)
    await page.locator("#fixb").wait_for()
    for _ in range(3):
        await page.keyboard.press("Space")
        await page.wait_for_timeout(250)
    await page.locator("#nx").wait_for(timeout=8000)
    check(int(await txt(page, "#money")) > 0, "the repair was paid")


async def sc_farm_delivery(page):
    await page.locator('[data-o="0"]').click()
    await page.locator('[data-k="repa"]').click()
    await page.locator('[data-k="repa"]').click()
    await page.locator("#give").click()
    check(await txt(page, "#money") == "24", "an exact delivery pays double")
    check("×1" in await txt(page, "#basket"), "two carrots left the stock")


async def sc_farm_tile(page):
    tile = page.locator(".tile").first
    for _ in range(3):
        await tile.click()
    check(await txt(page, "#money") == "18", "the seed was paid for")
    check(await page.locator(".tile").first.locator(".drop").count() == 0, "the tile was watered")


async def sc_dungeon(page):
    for k in ["ArrowUp", "ArrowLeft", "ArrowUp"]:
        await hold(page, k, 60)
        await page.wait_for_timeout(200)
    await page.locator('.icons button[data-e="gomba"]').click()
    check("Iránytű" in await txt(page, "#ovc"), "the right picture turns on the compass")
    await page.locator("#ok").click()
    check("Hozz 3 gombát" in await txt(page, "#quest"), "the quest shows in the quest bar")


async def sc_invasion(page):
    await page.locator('[data-w="0"]').click()
    await page.wait_for_timeout(200)
    before = int(await txt(page, "#sun"))
    box = await page.locator("#cv").bounding_box()
    cs, after = box["width"] / 5, before
    # The sun counter is redrawn by the game loop, so wait for it. A falling sun may sit on the tapped
    # cell (the tap then collects it instead of planting), so a second empty cell is tried.
    for c, r in [(2, 6), (1, 7), (3, 5)]:
        card = page.locator('[data-k="borso"]')
        if await card.is_disabled():
            break
        await card.click()
        await page.mouse.click(box["x"] + cs * (c + .5), box["y"] + cs * .6 + cs * (r + .5))
        try:
            await page.wait_for_function(f"+document.querySelector('#sun').textContent <= {before - 75}", timeout=3000)
        except Exception:
            pass
        after = int(await txt(page, "#sun"))
        if after <= before - 75:
            break
    check(before - 100 <= after <= before - 75, f"planting costs sun: {before} -> {after}")


async def sc_brawl(page):
    await page.locator('[data-d="0"]').click()
    await page.locator("#go").click()
    await page.wait_for_timeout(2600)
    for _ in range(12):
        await hold(page, "d", 150)
        await hold(page, "j", 60)
        await hold(page, "k", 60)
    hp = float(await page.locator("#h1").evaluate("e => parseFloat(e.style.width)"))
    check(hp < 100, f"hits take the opponent's health ({hp}%)")


async def sc_sokoban(page):
    await page.locator('[data-l="0"]').click()
    await page.keyboard.press("ArrowRight")
    await page.keyboard.press("ArrowRight")
    await page.locator("#ovc", has_text="PÁLYA KÉSZ").wait_for(timeout=3000)
    saved = json.loads(await page.evaluate("localStorage.getItem('dobozmester:save')"))
    check(0 in saved["won"], f"the first Sokoban level is saved: {saved}")


async def sc_tank(page):
    await page.locator("#go").click()
    await hold(page, "Space", 500)
    shots = await page.locator("#score").get_attribute("data-shots")
    check(int(shots or 0) >= 1, f"the tank fires: {shots}")


async def sc_tank_over(page):
    await page.locator("#go").click()
    await page.evaluate("__tank.S.lives = 1; __tank.S.player.shield = 0")
    await page.evaluate("(() => { const S = __tank.S; S.bullets.push({x: S.player.x + 6, y: S.player.y + 6, dir: 0, spd: .1, owner: null, enemy: true, steel: false}); })()")
    await page.locator("#ovc", has_text="VÉGE").wait_for(timeout=6000)
    await page.locator("#ovNew").click()
    check(await page.locator("#ov").is_hidden(), "New game closes the game-over window")


async def sc_caveman(page):
    await page.locator("#ovNew").click()
    x0 = await page.evaluate("__kk.S.p.x")
    await hold(page, "ArrowRight", 1200)
    x1 = await page.evaluate("__kk.S.p.x")
    check(x1 > x0 + 40, f"the caveman walks right ({x0} -> {x1})")
    saved = json.loads(await page.evaluate("localStorage.getItem('kokori-kaland:save')"))
    check(saved["cur"]["lvl"] == 0, f"the run is saved: {saved}")


async def sc_horde(page):
    await page.locator("#go").click()
    await page.wait_for_timeout(3500)
    check(int(await txt(page, "#men")) >= 1, "the squad is alive")
    await page.locator("#pauseBtn").click()
    check("Szünet" in await txt(page, "#ovc"), "pause opens")


async def sc_horde_ultra(page):
    await page.locator('[data-df="ultra"]').click()
    check(await page.locator('[data-df="ultra"]').get_attribute("aria-pressed") == "true", "Ultra is selected")
    saved = json.loads(await page.evaluate("localStorage.getItem('horda:save')"))
    check(saved.get("diff") == "ultra", f"difficulty saved: {saved}")
    await page.reload()
    check(await page.locator('[data-df="ultra"]').get_attribute("aria-pressed") == "true", "Ultra kept after reload")
    await page.locator("#go").click()
    await page.locator("#ovc", has_text="ELESTETEK").wait_for(timeout=60000)
    check("Ultra" in await txt(page, "#ovc"), "game over shows the level")
    saved = json.loads(await page.evaluate("localStorage.getItem('horda:save')"))
    check(saved["rec"]["ultra"]["best"] > 0 and saved["best"] == 0, f"Ultra record kept apart from Alap: {saved}")


async def sc_trap_1(page):
    await page.locator("#go").click()
    await page.wait_for_timeout(200)
    await page.keyboard.down("ArrowRight")      # game time follows the frame rate, so wait for the result
    await page.locator("#ovc", has_text="PÁLYA 1 · KÉSZ").wait_for(timeout=15000)
    await page.keyboard.up("ArrowRight")
    saved = json.loads(await page.evaluate("localStorage.getItem('csapda:save')"))
    check(saved["done"].get("0") == 0, f"level 1 saved as done with 0 deaths: {saved}")


async def sc_trap_2(page):
    await page.locator('[data-l="1"]').click()
    await page.wait_for_timeout(200)
    await page.keyboard.down("ArrowRight")
    await page.wait_for_function("document.querySelector('#deaths').textContent === '1'", timeout=15000)
    await page.keyboard.up("ArrowRight")


async def sc_arena(page):
    await page.locator('[data-m="0"]').click()
    await page.wait_for_timeout(300)
    await hold(page, "d", 1200)
    check(re.fullmatch(r"\d+", await txt(page, "#left")), "the robot counter shows")


async def sc_downhill(page):
    await page.locator('[data-t="0"]').click()
    await page.wait_for_function("+document.querySelector('#time').textContent > 0", timeout=20000)
    await hold(page, "ArrowLeft", 100)


FARM = dict(money=20, xp=0, lvl=1, size=0, tiles=[], inv={}, orders=[], seed="repa", intro=True, seen={}, t=0)

async def sc_maze_timeout(page):
    await page.click("#bResume")
    await page.wait_for_timeout(1500)
    check(await txt(page, "#lives") == "♥♥", "running out of time does not take a life")
    check(await page.locator("#ovOver").is_hidden(), "the game ended with lives left")


async def sc_maze_over(page):
    await page.click("#bResume")
    await page.wait_for_timeout(1500)
    check(await page.locator("#ovOver").is_visible(), "no end window after the last life")
    await page.click("#bNew")
    await page.wait_for_timeout(300)
    check(await page.locator("#ovOver").is_hidden(), "New game does not close the end window")
    check(await txt(page, "#lives") == "♥♥♥", "a new game does not start with three lives")


async def sc_maze_walk(page):
    await page.click("#bStart")
    for key in ["ArrowRight", "ArrowDown", "ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"] * 3:
        await hold(page, key, 260)
    await page.wait_for_timeout(1300)
    before = json.loads(await page.evaluate("localStorage.getItem('e-utveszto-save')"))
    check((before["px"], before["py"]) != (1, 1), "the keys do not move the player")
    await page.reload()
    await page.wait_for_timeout(400)
    after = json.loads(await page.evaluate("localStorage.getItem('e-utveszto-save')"))
    check(await page.locator("#ovPause").is_visible(), "a saved game does not come back paused")
    check((after["px"], after["py"], after["seed"]) == (before["px"], before["py"], before["seed"]),
          "the saved position or maze is not restored")


MAZE = {"v": 1, "lvl": 1, "lives": 3, "score": 0, "seed": 12345, "px": 1, "py": 1, "time": 0.5, "got": [], "map": 0}

SCENARIOS = [
    ("horda", "reading kit repairs broken shared saves and splits long words", sc_kit,
     save(**{"olvaso:xp": -50, "olvaso:settings": {"split": "<img src=x>"}, "olvaso:sound": "igen",
             "olvaso:mastery": {"fék": 3, "rossz": "x", "negatív": -2, "x" * 80: 1}})),
    ("bringa-muhely", "Bike Shop: a full repair job pays", sc_bike_shop,
     save(**{"bringa-muhely:save": {"intro": True}, "bringa:penz": 0})),
    ("kocka-kert", "Farm Empire: an exact delivery pays double", sc_farm_delivery,
     save(**{"kocka-kert:save": {**FARM, "money": 0, "inv": {"repa": 3},
                                 "orders": [{"who": "Piac", "items": [{"c": "repa", "n": 2}], "pay": 12}]}})),
    ("kocka-kert", "Farm Empire: dig, sow and water", sc_farm_tile, save(**{"kocka-kert:save": FARM})),
    ("kalandor", "Dungeon: the right picture turns on the compass", sc_dungeon,
     save(**{"kalandor:save": dict(v=1, x=16, y=14, hp=20, lvl=1, xp=0, gold=0, pot=1, sword=0, shield=0, q=0, qs="new",
                                   prog=0, compass=False, got=[], dead=[], intro=True)})),
    ("kertvedo", "Invasion: planting costs sun", sc_invasion, None),
    ("bunyo", "Brawl: hits take health", sc_brawl, None),
    ("horda", "Horde: the squad fights, pause works", sc_horde, None),
    ("dobozmester", "Sokoban: push the crate onto the target and save the level", sc_sokoban, None),
    ("tankorseg", "Tank Guard: start a battle and fire a shot", sc_tank, None),
    ("tankorseg", "Tank Guard: losing the last tank ends the game, New game closes the window", sc_tank_over, None),
    ("kokori-kaland", "Stone Age Quest: the caveman walks and the run is saved", sc_caveman, None),
    ("horda", "Horde: Ultra level is saved, swarms the squad, keeps its own record", sc_horde_ultra, None),
    ("csapda", "Trap: level 1 cleared and saved", sc_trap_1, None),
    ("csapda", "Trap: the weak floor kills and the death is counted", sc_trap_2,
     save(**{"csapda:save": {"done": {"0": 0}, "deaths": {}, "total": 0, "intro": True}})),
    ("betu-csata", "Arena: a casual round runs", sc_arena, None),
    ("bringa-futam", "Downhill: the race clock starts after the countdown", sc_downhill, None),
    ("e-utveszto", "E-Maze: running out of time takes a life", sc_maze_timeout, save(**{"e-utveszto-save": MAZE})),
    ("e-utveszto", "E-Maze: the last life ends the game, New game restarts", sc_maze_over,
     save(**{"e-utveszto-save": {**MAZE, "lives": 1}})),
    ("e-utveszto", "E-Maze: the player moves and the save survives a reload", sc_maze_walk, None),
]


async def run_scenario(browser, base, game, fn, seed):
    async with Run(browser, base, seed=seed) as r:
        await r.goto(f"{game}/index.html")
        try:
            await fn(r.page)
        except Fail as e:
            return [str(e)] + r.errors
        except Exception as e:
            return [f"{type(e).__name__}: {str(e).splitlines()[0]}"] + r.errors
        return r.errors


# ---------------------------------------------------------------- generators

GEN_CHECK = r"""
({n, runs}) => {
  const generate = window.__generate;
  function validate(reg, sol) {
    if (reg.length !== n*n || !reg.every(g => Number.isInteger(g) && g >= 0 && g < n)) return 'bad region map';
    for (let k = 0; k < n; k++) {
      const cells = reg.flatMap((g, i) => g === k ? [i] : []);
      if (!cells.length) return `region ${k} is empty`;
      const seen = new Set([cells[0]]), st = [cells[0]];
      while (st.length) { const i = st.pop(), r = Math.floor(i/n), c = i % n;
        for (const [dr, dc] of [[1,0],[-1,0],[0,1],[0,-1]]) { const rr = r+dr, cc = c+dc, j = rr*n+cc;
          if (rr>=0 && rr<n && cc>=0 && cc<n && reg[j]===k && !seen.has(j)) { seen.add(j); st.push(j); } } }
      if (seen.size !== cells.length) return `region ${k} is not one piece`;
    }
    if (new Set(sol).size !== n) return 'two in one column';
    if (new Set(sol.map((c, r) => reg[r*n+c])).size !== n) return 'two in one region';
    for (let r = 1; r < n; r++) if (Math.abs(sol[r]-sol[r-1]) <= 1) return 'two touching';
    let count = 0; const cols = Array(n).fill(false), regs = Array(n).fill(false);
    (function place(r, prev) { if (count >= 2) return; if (r === n) { count++; return; }
      for (let c = 0; c < n; c++) { const g = reg[r*n+c]; if (cols[c] || regs[g] || (r && Math.abs(c-prev) <= 1)) continue;
        cols[c] = regs[g] = true; place(r+1, c); cols[c] = regs[g] = false; } })(0, -9);
    return count === 1 ? null : `${count} solutions`;
  }
  let total = 0, slowest = 0;
  for (let i = 0; i < runs; i++) {
    const t0 = performance.now(), pz = generate(n), ms = performance.now() - t0;
    total += ms; slowest = Math.max(slowest, ms);
    if (!pz) return {error: `run ${i+1}: no level within the time budget`};
    const bad = validate(pz.reg, pz.sol);
    if (bad) return {error: `run ${i+1}: ${bad}`};
  }
  return {avg: total/runs, slowest};
}
"""


async def test_generators(browser, quick):
    runs = {6: 50, 8: 50, 10: 10} if quick else {6: 300, 8: 300, 10: 60}
    problems = []
    page = await browser.new_page()
    for game in ["gyemantbanya", "kincsvadasz"]:
        html = (ROOT / game / "index.html").read_text(encoding="utf-8")
        start = html.find("// ---------- Pálya-generátor ----------")
        if start < 0:
            problems.append(f"{game}: generator section not found")
            continue
        src = html[start:html.find("// ----------", start + 10)]
        budget = int(re.search(r"GEN_BUDGET_MS=(\d+)", src).group(1))
        await page.set_content("<!doctype html><title>gen</title>")
        await page.add_script_tag(content=src + "\nwindow.__generate = generate;")
        for n, k in runs.items():
            res = await page.evaluate(GEN_CHECK, {"n": n, "runs": k})
            if "error" in res:
                problems.append(f"{game} {n}×{n}: {res['error']}")
            elif res["avg"] > budget / 4:
                problems.append(f"{game} {n}×{n}: average {res['avg']:.0f} ms is too close to the {budget} ms budget")
            else:
                print(f"     {game} {n}×{n}: {k} levels OK, average {res['avg']:.1f} ms, slowest {res['slowest']:.0f} ms")
    await page.close()
    return problems


MAZE_CHECK = r"""
({lvl, runs}) => {
  let total = 0, slowest = 0;
  for (let i = 0; i < runs; i++) {
    const seed = (i * 2654435761 + lvl * 97) >>> 0, t0 = performance.now(), m = window.__generate(lvl, seed), ms = performance.now() - t0;
    total += ms; slowest = Math.max(slowest, ms);
    if (!m) return {error: `run ${i+1}: no maze within the time budget`};
    const {w, h, g} = m, open = (x, y) => x >= 0 && y >= 0 && x < w && y < h && !g[y*w+x];
    for (let x = 0; x < w; x++) if (!g[x] || !g[(h-1)*w+x]) return {error: `run ${i+1}: hole in the outer wall`};
    for (let y = 0; y < h; y++) if (!g[y*w] || !g[y*w+w-1]) return {error: `run ${i+1}: hole in the outer wall`};
    const seen = new Set(['1,1']), st = [[1, 1]];
    while (st.length) { const [x, y] = st.pop();
      for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) { const k = (x+dx)+','+(y+dy);
        if (open(x+dx, y+dy) && !seen.has(k)) { seen.add(k); st.push([x+dx, y+dy]); } } }
    const targets = [[m.ex, m.ey], ...m.coins];
    if (!targets.every(([x, y]) => seen.has(x+','+y))) return {error: `run ${i+1}: exit or a coin cannot be reached`};
    if (m.enemies.some(([x, y]) => (x === 1 && y === 1) || !open(x, y))) return {error: `run ${i+1}: a shadow starts in a wall or on the player`};
    const again = window.__generate(lvl, m.seed);
    if (!again || again.seed !== m.seed || again.ex !== m.ex) return {error: `run ${i+1}: a saved maze does not come back the same`};
  }
  return {avg: total/runs, slowest};
}
"""


async def test_maze_generator(browser, quick):
    problems = []
    page = await browser.new_page()
    html = (ROOT / "e-utveszto" / "index.html").read_text(encoding="utf-8")
    start = html.find("// ---------- Pálya-generátor ----------")
    if start < 0:
        return ["e-utveszto: generator section not found"]
    src = html[start:html.find("// ----------", start + 10)]
    budget = int(re.search(r"GEN_BUDGET_MS=(\d+)", src).group(1))
    await page.set_content("<!doctype html><title>gen</title>")
    await page.add_script_tag(content=src + "\nwindow.__generate = generate;")
    for lvl in (1, 3, 6, 9, 20):
        k = 40 if quick else 200
        res = await page.evaluate(MAZE_CHECK, {"lvl": lvl, "runs": k})
        if "error" in res:
            problems.append(f"e-utveszto level {lvl}: {res['error']}")
        elif res["avg"] > budget / 4:
            problems.append(f"e-utveszto level {lvl}: average {res['avg']:.0f} ms is too close to the {budget} ms budget")
        else:
            print(f"     e-utveszto level {lvl}: {k} mazes OK, average {res['avg']:.1f} ms, slowest {res['slowest']:.0f} ms")
    await page.close()
    return problems


# ---------------------------------------------------------------- main

async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    if only:
        args = [a for a in args if a != only]
    games = list_games()
    chosen = [g for g in games if not args or g in args]
    httpd, base = start_server()
    failed = 0
    t0 = time.time()

    def report(name, problems):
        nonlocal failed
        failed += bool(problems)
        print(("OK   " if not problems else "FAIL ") + name + "".join(f"\n       {p}" for p in problems), flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        sem = asyncio.Semaphore(PARALLEL)

        async def limited(name, coro):
            async with sem:
                try:
                    report(name, await coro)
                except Exception as e:
                    report(name, [f"{type(e).__name__}: {str(e).splitlines()[0]}"])

        if only in (None, "games"):
            print("== every game: desktop, phone, broken saves")
            await asyncio.gather(*(limited(g, test_game(browser, base, g)) for g in chosen))
            if not args:
                report("start page", await test_start_page(browser, base, games))
        if only in (None, "scenarios"):
            print("== scenarios")
            await asyncio.gather(*(limited(name, run_scenario(browser, base, g, fn, seed))
                                   for g, name, fn, seed in SCENARIOS if not args or g in args))
        if only in (None, "generators") and (not args or {"gyemantbanya", "kincsvadasz"} & set(args)):
            print("== level generators")
            report("generators", await test_generators(browser, quick))
        if only in (None, "generators") and (not args or "e-utveszto" in args):
            print("== maze generator")
            report("maze generator", await test_maze_generator(browser, quick))
        await browser.close()
    httpd.shutdown()
    print(f"\n{failed} failed ({time.time() - t0:.0f} s).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())

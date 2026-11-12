#!/usr/bin/env python3
"""Plays the games in a headless browser (see AGENTS.md). Goes further than tools/smoke_test.py:

  every game    loads and is played a little on a desktop (keyboard, mouse) and on a phone (touch):
                no JavaScript error, no request to a host other than the allowed font hosts,
                no sideways scrolling; then five kinds of broken saved data are written into
                localStorage, and the game must still start and play without an error
  scenarios     short real play-throughs that check the outcome
                (paid, delivered, quest taken, level cleared, death counted, save written)
  generators    the Gyémántbánya and Kincsvadász level generators (and the E-Útvesztő maze generator), taken from the published pages,
                make hundreds of levels; each must be found, be a valid puzzle and have exactly one
                solution (checked by an independent solver)
  sokoban       every Dobozmester level is proven solvable by a push-level breadth-first search with
                dead-square and frozen-block pruning (--quick: the first 10 levels); hitting the state
                or time limit is reported as a failure, never as a silent pass

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


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass   # the browser closing a connection early is not a test failure


def start_server():
    httpd = QuietServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
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
        # every card shows its cover picture, and the pictures really load
        covers = await r.page.locator("section:not(.fav):not(.recent) img.cover").evaluate_all(
            "is => Promise.all(is.map(i => (i.loading = 'eager', i.decode().then(() => i.naturalWidth, () => 0))))")
        if len(covers) != len(games) or 0 in covers:
            problems.append(f"cover pictures: {len(covers)} cards with a picture of {len(games)}, {covers.count(0)} do not load")
        problems += r.errors + [f"request to another site: {u}" for u in r.external]
    # search: accent- and case-insensitive, Hungarian and English
    async with Run(browser, base) as r:
        await r.goto("index.html")
        q, shown = r.page.locator("#q"), "document.querySelectorAll('section:not(.recent) .card').length"
        for word, must in [("BUNYO", "bunyo"), ("zombie", "horda"), ("vár", "tundervar")]:
            await q.fill(word)
            slugs = await r.page.locator("section:not(.recent) .star").evaluate_all("bs => bs.map(b => b.dataset.slug)")
            if must not in slugs or len(slugs) >= len(games):
                problems.append(f"search '{word}' should find {must} and filter the rest: {slugs}")
        await q.fill("qqqxxx")
        if await r.page.evaluate(shown) != 0 or not await r.page.locator(".nomatch").count():
            problems.append("a search with no match does not say so")
        await q.fill("")
        if await r.page.evaluate(shown) < len(games):
            problems.append("clearing the search does not bring every game back")
        # "Folytatás" shelf: the opened game comes first, the list keeps at most 3
        for slug in ["csapda", "horda", "bunyo", "horda"]:
            await r.page.locator(f'section:not(.recent):not(.fav) .card:has(.star[data-slug="{slug}"]) > a').click()
            await r.page.go_back()
        rec = await r.page.locator("section.recent .star").evaluate_all("bs => bs.map(b => b.dataset.slug)")
        if rec != ["horda", "bunyo", "csapda"]:
            problems.append(f"the Continue shelf is wrong: {rec}")
        problems += r.errors + [f"request to another site: {u}" for u in r.external]
    async with Run(browser, base, seed={"games-recent": '["horda",5,"nincs-ilyen","<b>","horda","bunyo","csapda","kalandor"]'}) as r:
        await r.goto("index.html")
        rec = await r.page.locator("section.recent .star").evaluate_all("bs => bs.map(b => b.dataset.slug)")
        if rec != ["horda", "bunyo", "csapda"]:
            problems.append(f"a broken games-recent value is not cleaned: {rec}")
        problems += r.errors
    async with Run(browser, base, seed={"games-recent": '{"a":1}'}) as r:
        await r.goto("index.html")
        if await r.page.locator("section.recent").count():
            problems.append("a games-recent value that is not a list still shows a shelf")
        problems += r.errors
    return problems


# ---------------------------------------------------------------- scenarios

class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def save(**kv):
    return {k: json.dumps(v) for k, v in kv.items()}


async def wait_js(page, expr, timeout=5000):
    """Waits until a JavaScript expression is true. Polls with evaluate(), because the pages' Content-Security-Policy
    (rightly) blocks the string evaluation that page.wait_for_function() uses."""
    t0 = time.time()
    while True:
        if await page.evaluate(expr):
            return
        if (time.time() - t0) * 1000 > timeout:
            raise Fail(f"timed out after {timeout} ms waiting for: {expr}")
        await page.wait_for_timeout(50)


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


async def sc_kit_weighting(page):
    # 'ritka' was never read right, the others 8 times: it must come much more often, and never twice in a row
    res = await page.evaluate("""(() => { const L = ['ritka', 'fék', 'lánc', 'nyereg'];
        let n = 0, prev = null, twice = 0;
        for (let i = 0; i < 400; i++) { const w = K.pickWord(L); if (w === 'ritka') n++; if (w === prev) twice++; prev = w; }
        return {n, twice}; })()""")
    check(res["twice"] == 0, f"the same word came twice in a row {res['twice']} times")
    check(res["n"] > 150, f"the rarely read word should come most often: {res['n']} of 400")


async def sc_bike_shop(page):
    zones = {"első gumi": "elso", "hátsó gumi": "hatso", "küllő": "hatso", "fék": "fek", "lánc": "lanc", "nyereg": "nyereg",
             "kormány": "kormany", "váltó": "valto", "lámpa": "lampa", "pedál": "pedal", "csengő": "csengo", "akku": "akku",
             "első kerék": "elso", "első szelep": "elso", "macska": "lampa"}
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
    check("a célhoz bekapcsolva" in await txt(page, "#ovc"), "the right picture turns on the compass")
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
            await wait_js(page, f"+document.querySelector('#sun').textContent <= {before - 75}", timeout=3000)
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


PAD = """window.__pad = {id: 'test pad', index: 0, connected: true, mapping: 'standard', axes: [0, 0, 0, 0],
  buttons: Array.from({length: 17}, () => ({pressed: false, value: 0}))};
Object.defineProperty(navigator, 'getGamepads', {value: () => [window.__pad], configurable: true});"""


async def pad(page, button, ms=120):
    await page.evaluate(f"__pad.buttons[{button}].pressed = true; __pad.buttons[{button}].value = 1")
    await page.wait_for_timeout(ms)
    await page.evaluate(f"__pad.buttons[{button}].pressed = false; __pad.buttons[{button}].value = 0")
    await page.wait_for_timeout(120)


async def sc_tank_gamepad(page):
    await page.add_init_script(PAD)
    await page.reload()
    await page.evaluate("dispatchEvent(new Event('gamepadconnected'))")
    await page.wait_for_timeout(200)
    check(await page.locator("text=Kontroller csatlakoztatva").count() == 1, "the connected note shows")
    await pad(page, 0)                                   # A in the menu presses the highlighted button
    check(await page.locator("#ov").is_hidden(), "the A button starts the battle from the menu")
    await page.wait_for_timeout(1500)
    x0 = await page.evaluate("__tank.S.player.x")
    await pad(page, 15, 700)                             # d-pad right drives the tank
    check(await page.evaluate("__tank.S.player.x") != x0, "the d-pad moves the tank")
    await pad(page, 0, 500)                              # A fires
    shots = await page.locator("#score").get_attribute("data-shots")
    check(int(shots or 0) >= 1, f"the A button fires: {shots}")


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


async def sc_caveman_calm(page):
    await page.locator("#ovNew").click()
    await page.evaluate("__kk.hurt()")
    check(await page.evaluate("__kk.S.shake") > 0, "a hit shakes the screen with normal motion")
    await page.emulate_media(reduced_motion="reduce")
    await page.reload()
    await page.locator("#ovNew, #ovGo, #ov .btn.hot").first.click()
    await page.evaluate("__kk.S.p.inv = 0; __kk.S.shake = 0; __kk.hurt()")
    check(await page.evaluate("__kk.S.shake") == 0, "reduced motion: a hit does not shake the screen")


async def sc_bricks_swipe(page):
    await page.locator('[data-diff="normal"]').click()
    before = int(await txt(page, "#level"))
    box = await page.locator("#cv").bounding_box()
    x, y = box["x"] + box["width"] * .5, box["y"] + box["height"] * .95
    await page.mouse.move(x, y)
    await page.mouse.down()
    await page.mouse.move(x - box["width"] * .2, y - box["height"] * .5, steps=6)
    await page.mouse.up()
    await wait_js(page, f"+document.querySelector('#level').textContent > {before}", timeout=30000)
    saved = json.loads(await page.evaluate("localStorage.getItem('tegla-save')"))
    check(saved["level"] == before + 1, f"the round is saved: {saved.get('level')}")
    await page.reload()
    await page.wait_for_timeout(300)
    check(int(await txt(page, "#level")) == before + 1, "the saved round comes back after a reload")


async def sc_bricks_keys(page):
    await page.locator('[data-diff="normal"]').click()
    await page.evaluate("document.activeElement && document.activeElement.blur()")
    before = int(await txt(page, "#level"))
    for _ in range(6):
        await page.keyboard.press("ArrowLeft")
    await page.keyboard.press("Space")
    await wait_js(page, f"+document.querySelector('#level').textContent > {before}", timeout=30000)
    await page.locator("#sndBtn").click()
    check(await page.evaluate("localStorage.getItem('tegla-sound')") == "0", "muting is saved")
    await page.reload()
    check(await page.locator("#sndBtn").get_attribute("aria-pressed") == "false", "the game stays muted after a reload")


async def sc_breakout(page):
    await page.locator('#card button[data-act="new"]').click()
    check(await page.locator("#ov").is_hidden(), "New game closes the menu")
    for lives in (2, 1, 0):
        await page.keyboard.press("Space")
        await page.wait_for_timeout(150)
        # the ball is sent past the paddle, the real physics has to notice it falling out
        await page.evaluate("""(() => { const F = __falbonto, G = F.G, pd = G.paddle;
            G.balls.forEach(b => { b.stuck = false; b.x = pd.x > 5 ? 0.5 : 9.5; b.y = F.PY + F.PH + 0.5; b.vx = 0; b.vy = 12; }); })()""")
        await wait_js(page, f"__falbonto.G.lives === {lives}", timeout=5000)
        hearts = (await txt(page, "#lives")).count("♥")
        check(hearts == lives, f"the lives counter shows {lives}: {hearts}")
    await page.locator("#ov h2", has_text="Vége").wait_for(timeout=3000)
    check(await page.evaluate("localStorage.getItem('falbonto-save')") is None, "the save is cleared at game over")
    await page.locator('#card button[data-act="new"]').click()
    check(await page.locator("#ov").is_hidden(), "New game closes the end window")
    check(await txt(page, "#lives") == "♥♥♥", "a new game starts with three lives")


def solve_region_puzzle(n, reg):
    """Independent solver for Gyémántbánya and Kincsvadász: one per row, column and region,
    none touching. Returns every solution (stops at two)."""
    out = []

    def place(r, prev, cols, regs, sol):
        if len(out) > 1:
            return
        if r == n:
            out.append(sol[:])
            return
        for c in range(n):
            g = reg[r * n + c]
            if c in cols or g in regs or (r and abs(c - prev) <= 1):
                continue
            place(r + 1, c, cols | {c}, regs | {g}, sol + [c])
    place(0, -9, frozenset(), frozenset(), [])
    return out


async def sc_region_puzzle(page, win_text):
    # the board is generated behind a short "drawing the map" window; wait until it is ready
    await wait_js(page, "document.querySelectorAll('#board .cell').length > 0 && document.getElementById('overlay').hidden", 15000)
    labels = await page.locator("#board .cell").evaluate_all("cs => cs.map(c => c.getAttribute('aria-label'))")
    n = int(len(labels) ** .5)
    check(n * n == len(labels) and n >= 6, f"a square board: {len(labels)} cells")
    names = [lab.split(", ")[2] for lab in labels]
    ids = {nm: k for k, nm in enumerate(dict.fromkeys(names))}
    check(len(ids) == n, f"{n} regions on the board: {len(ids)}")
    sols = solve_region_puzzle(n, [ids[nm] for nm in names])
    check(len(sols) == 1, f"the board has exactly one solution: {len(sols)}")
    sol = sols[0]
    cells = page.locator("#board .cell")
    wrong = next(r * n + c for r in range(n) for c in range(n) if c != sol[r])
    await cells.nth(wrong).click()
    check(await page.locator("#hearts").get_attribute("aria-label") == "2 élet", "a wrong cell takes a heart")
    if await page.locator("#overlay").is_visible():
        await page.locator("#overlay button").first.click()
    for r, c in enumerate(sol):
        await cells.nth(r * n + c).click()
    await page.locator("#overlay", has_text=win_text).wait_for(timeout=4000)


async def sc_gems(page):
    await sc_region_puzzle(page, "Megvan mind!")


async def sc_treasure(page):
    await sc_region_puzzle(page, "TELJESÍTVE")


async def sc_letter_mine(page):
    await page.locator('[data-a="start"][data-v="r1"]').first.click()
    for _ in range(12):
        if await page.evaluate("view") != "play":
            break
        kind = await page.evaluate("P.task.type")
        if await page.locator('[data-a="pick"]').count():
            ok = await page.evaluate("P.opts.findIndex(o => o.ok)")
            await page.locator(f'[data-a="pick"][data-v="{ok}"]').click()
        elif await page.locator('[data-a="put"]').count():
            for k in range(await page.evaluate("P.task.s.length")):
                await page.locator(f'[data-a="put"][data-v="{k}"]').click()
            await page.locator('[data-a="check"]').click()
        elif await page.locator('[data-a="mword"]').count():
            for i in range(await page.evaluate("P.task.pairs.length")):
                await page.locator(f'[data-a="mword"][data-v="{i}"]').click()
                await page.locator(f'[data-a="mpic"][data-v="{i}"]').click()
        else:
            raise Fail(f"unknown task type on screen: {kind}")
        await page.locator('[data-a="next"]').click()
    check(await page.evaluate("view") == "sum", "the round ends on the summary screen")
    xp = json.loads(await page.evaluate("localStorage.getItem('betubanya_v1')"))["xp"]
    check(xp == 50, f"five right first answers give 50 XP: {xp}")
    await page.reload()
    check(json.loads(await page.evaluate("localStorage.getItem('betubanya_v1')"))["xp"] == 50, "XP kept after a reload")
    check(await page.evaluate("S.xp") == 50, "the game reads the saved XP back")
    # teacher PIN: set it twice, then it must be asked again and a wrong one refused
    for pin in ("2468", "2468"):
        if await page.evaluate("view") != "pin":
            await page.evaluate("ACT.go('pin')")
        for d in pin:
            await page.locator(f'[data-a="pin"][data-v="{d}"]').click()
        await page.wait_for_timeout(300)
    check(await page.evaluate("view") == "teacher", "the PIN is set after typing it twice")
    await page.reload()
    await page.evaluate("ACT.go('pin')")
    for d in "1111":
        await page.locator(f'[data-a="pin"][data-v="{d}"]').click()
    await page.wait_for_timeout(300)
    check(await page.evaluate("view") == "pin", "a wrong PIN is refused")
    for d in "2468":
        await page.locator(f'[data-a="pin"][data-v="{d}"]').click()
    await page.wait_for_timeout(300)
    check(await page.evaluate("view") == "teacher", "the saved PIN opens the teacher view")


async def sc_cornhole(page):
    await page.locator("#start-button").click()
    hole = page.locator('.bag-btn[data-team="0"][data-type="0"][data-delta="1"]')
    await hole.click()                                  # red: 1 in the hole = 3
    await page.locator('.bag-btn[data-team="1"][data-type="1"][data-delta="1"]').click()   # blue: 1 on board = 1
    await page.locator("#save-round-button").click()
    await hole.click()
    await page.locator("#save-round-button").click()
    scores = [await txt(page, "#g-score1"), await txt(page, "#g-score2")]
    check(scores == ["5", "0"], f"ACL scoring after two rounds: {scores}")
    await page.locator("#undo-button").click()
    await page.wait_for_timeout(200)
    check(await txt(page, "#g-score1") == "2", "undo takes back the last round")
    await page.reload()
    await page.wait_for_timeout(300)
    check(await txt(page, "#g-score1") == "2", "the match goes on after a reload")


async def sc_cornhole_broken(page):
    check(await page.locator("#screen-setup").is_visible(), "a broken save starts at the new match screen")
    await page.locator("#start-button").click()
    check(await txt(page, "#g-score1") == "0", "the new match starts from zero")


async def sc_rotate(page):
    # a phone held upright: start a battle, then turn the phone on its side and back
    ctx = await page.context.browser.new_context(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    try:
        p = await ctx.new_page()
        await p.goto(page.url)
        hint = p.locator(".rotate-hint")
        check(await hint.count() == 1 and await hint.is_hidden(), "no turn-the-phone hint when the phone is upright")
        await p.locator("#go").click()
        await p.wait_for_timeout(600)
        await p.set_viewport_size({"width": 780, "height": 390})
        await hint.wait_for(state="visible", timeout=3000)
        check("Szünet" in await txt(p, "#ovc"), "the game pauses while the phone lies on its side")
        await p.set_viewport_size({"width": 390, "height": 780})
        await hint.wait_for(state="hidden", timeout=3000)
    finally:
        await ctx.close()
    # a wide desktop window never shows it
    await page.set_viewport_size({"width": 1280, "height": 400})
    await page.wait_for_timeout(200)
    check(await page.locator(".rotate-hint").is_hidden(), "no hint in a wide desktop window")


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
    await wait_js(page, "document.querySelector('#deaths').textContent === '1'", timeout=15000)
    await page.keyboard.up("ArrowRight")


async def sc_arena(page):
    await page.locator('[data-m="0"]').click()
    await page.wait_for_timeout(300)
    await hold(page, "d", 1200)
    check(re.fullmatch(r"\d+", await txt(page, "#left")), "the robot counter shows")


async def sc_downhill(page):
    await page.locator('[data-t="0"]').click()
    await wait_js(page, "+document.querySelector('#time').textContent > 0", timeout=20000)
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
    # stop at the first step that moved the player (a walk could lead back to the start in some mazes);
    # a busy test machine drops frames, so the keys are held longer on each round
    moved = "(()=>{const s=JSON.parse(localStorage.getItem('e-utveszto-save')||'{}');return s.px!==1||s.py!==1})()"
    for ms in (260, 400, 600):
        for key in ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"] * 2:
            await hold(page, key, ms)
            await page.wait_for_timeout(250)
            if await page.evaluate(moved):
                break
        if await page.evaluate(moved):
            break
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
    ("bunyo", "reading kit: a rarely read word comes more often, never twice in a row", sc_kit_weighting,
     save(**{"olvaso:mastery": {"fék": 8, "lánc": 8, "nyereg": 8}})),
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
    ("horda", "Horde: turning the phone on its side shows a hint and pauses the game", sc_rotate, None),
    ("dobozmester", "Sokoban: push the crate onto the target and save the level", sc_sokoban, None),
    ("tankorseg", "Tank Guard: start a battle and fire a shot", sc_tank, None),
    ("tankorseg", "Tank Guard: losing the last tank ends the game, New game closes the window", sc_tank_over, None),
    ("tankorseg", "Tank Guard: a game controller starts the battle, drives and fires", sc_tank_gamepad, None),
    ("kokori-kaland", "Stone Age Quest: the caveman walks and the run is saved", sc_caveman, None),
    ("kokori-kaland", "Stone Age Quest: reduced motion turns off the screen shake", sc_caveman_calm, None),
    ("falbonto", "Breakout: a lost ball takes a life, the last one ends the game, New game restarts", sc_breakout, None),
    ("gyemantbanya", "Diamond Mine: a wrong cell costs a heart, the solver's solution wins", sc_gems, None),
    ("kincsvadasz", "Treasure Hunter: a wrong cell costs a heart, the solver's solution wins", sc_treasure, None),
    ("betubanya", "Letter Mine: a reading round gives XP that survives a reload, the teacher PIN works", sc_letter_mine, None),
    ("cornholescore", "Cornhole: two ACL rounds, undo, the match survives a reload", sc_cornhole, None),
    ("cornholescore", "Cornhole: a broken save starts a new match", sc_cornhole_broken,
     {"cornhole-score-state-v1": '{"rounds":[[99,"x"],null],"gameActive":true,"targetScore":"<b>","gameMode":"zz"}'}),
    ("teglatoro", "Bricks: a swipe shoots, the round counter grows, the save survives a reload", sc_bricks_swipe, None),
    ("teglatoro", "Bricks: arrow keys aim, Space shoots, muting is kept after a reload", sc_bricks_keys, None),
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


# ---------------------------------------------------------------- Sokoban levels

SOKO_MAX_STATES = 400_000
SOKO_MAX_SECONDS = 20


def solve_sokoban(rows):
    """Push-level breadth-first search. Returns the number of pushes of a shortest solution,
    None when the level has no solution, or 'limit' when the state or time limit is reached."""
    walls, goals, boxes, player = set(), set(), set(), None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                walls.add((x, y))
            if ch in ".*+":
                goals.add((x, y))
            if ch in "$*":
                boxes.add((x, y))
            if ch in "@+":
                player = (x, y)
    if player is None or not boxes or len(boxes) != len(goals):
        return None
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    # Live squares: a box can only reach a goal from squares it can be pulled to from a goal.
    live, todo = set(goals), list(goals)
    while todo:
        x, y = todo.pop()
        for dx, dy in dirs:
            b, p = (x + dx, y + dy), (x + 2 * dx, y + 2 * dy)
            if b not in walls and p not in walls and b not in live:
                live.add(b)
                todo.append(b)

    def reach(start, bx):
        seen, st = {start}, [start]
        while st:
            x, y = st.pop()
            for dx, dy in dirs:
                n = (x + dx, y + dy)
                if n not in walls and n not in bx and n not in seen:
                    seen.add(n)
                    st.append(n)
        return seen

    def frozen_square(bx):
        # four boxes/walls in a 2×2 block with a box off its goal can never move again
        for (x, y) in bx:
            sq = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
            if all(c in walls or c in bx for c in sq) and any(c in bx and c not in goals for c in sq):
                return True
        return False

    start_boxes = frozenset(boxes)
    r0 = reach(player, start_boxes)
    seen = {(min(r0), start_boxes)}
    frontier, pushes, t0 = [(r0, start_boxes)], 0, time.time()
    while frontier:
        if start_boxes and all(b in goals for b in frontier[0][1]):
            return pushes
        nxt = []
        for region, bx in frontier:
            if bx <= goals:
                return pushes
            for (x, y) in bx:
                for dx, dy in dirs:
                    to = (x + dx, y + dy)
                    if (x - dx, y - dy) not in region or to in walls or to in bx or to not in live:
                        continue
                    nb = (bx - {(x, y)}) | {to}
                    if frozen_square(nb):
                        continue
                    nr = reach((x, y), nb)
                    key = (min(nr), nb)
                    if key in seen:
                        continue
                    seen.add(key)
                    if nb <= goals:
                        return pushes + 1
                    nxt.append((nr, nb))
            if len(seen) > SOKO_MAX_STATES or time.time() - t0 > SOKO_MAX_SECONDS:
                return "limit"
        frontier, pushes = nxt, pushes + 1
    return None


def test_sokoban_levels(quick):
    html = (ROOT / "dobozmester" / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const LEVELS=(\[.*?\n\]);", html, re.S)
    if not m:
        return ["dobozmester: LEVELS not found"]
    levels = json.loads(m.group(1))
    problems = []
    chosen = levels[:10] if quick else levels
    t0 = time.time()
    for i, rows in enumerate(chosen):
        res = solve_sokoban(rows)
        if res is None:
            problems.append(f"dobozmester level {i + 1}: no solution")
        elif res == "limit":
            problems.append(f"dobozmester level {i + 1}: the solver hit its limit "
                            f"({SOKO_MAX_STATES} states or {SOKO_MAX_SECONDS} s), solvability not proven")
    print(f"     dobozmester: {len(chosen)} of {len(levels)} levels checked in {time.time() - t0:.1f} s")
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
        if only in (None, "generators") and (not args or "dobozmester" in args):
            print("== Sokoban levels (solver)")
            report("sokoban levels", test_sokoban_levels(quick))
        await browser.close()
    httpd.shutdown()
    print(f"\n{failed} failed ({time.time() - t0:.0f} s).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())

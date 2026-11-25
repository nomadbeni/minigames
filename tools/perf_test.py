#!/usr/bin/env python3
"""Measures frame times of the effect-heavy action games on a slow phone profile (issue #51, see also #40).

Each game is started at phone size (390×780, touch) with the processor slowed down 20× (Chrome DevTools CPU
throttling; on a fast laptop this is roughly a cheap Android phone), a busy scene is set up, and the time between frames is recorded.
It prints, per game: the average frame time and the frame rate, the 95th percentile, the share of frames that
took longer than 33 ms (below 30 fps), the main-thread work per frame (from Chrome's TaskDuration metric; the
steadiest number of these), and the decorative quality level the game chose (Kepesseg.quality).

It is a measuring tool, not a pass/fail test: numbers depend on the machine. Compare runs on the same machine.

Usage:
  python3 tools/perf_test.py                    # all four games, 20× slower processor
  python3 tools/perf_test.py kardvihar --rate 6 --seconds 10
  python3 tools/perf_test.py --quality 2         # always full effects (as before adaptive quality)
"""
import asyncio
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from play_test import Run, async_playwright, start_server  # noqa: E402

FRAMES = """ms => new Promise(res => { const d = []; let last = performance.now(); const t0 = last;
  function f(now) { d.push(now - last); last = now; if (now - t0 < ms) requestAnimationFrame(f); else res(d); }
  requestAnimationFrame(f); })"""

# How each game gets busy: (start, keep busy every 300 ms). Only test hooks and the usual keys are used.
SCENES = {
    "kardvihar": ('document.querySelector(\'#card button[data-act="new"]\').click(); __kardvihar.startWave(9)',
                  "(() => { const K = __kardvihar, G = K.G; if (!G || G.phase !== 'play') return; G.pl.inv = 9; G.hp = G.maxhp;"
                  " G.xp = 0; G.perkQ = 0; K.attack(); if (G.en.length < 25) K.spawn(['slime', 'bat', 'boar'][G.en.length % 3]); })()"),
    "kozapor": ('document.querySelector(\'#card button[data-act="new"]\').click(); __kozapor.startWave(7)',
                "(() => { const K = __kozapor, G = K.G; if (!G || G.phase !== 'play') return; G.ship.inv = 9; G.lives = 3;"
                " K.keys.fire = true; K.keys.thrust = true; K.keys.left = true; if (G.rocks.length < 8) K.startWave(G.wave + 1); })()"),
    "kokori-kaland": ("document.getElementById('ovNew').click()",
                      "(() => { const S = __kk.S; if (S.mode !== 'play') return; S.p.inv = 90; S.hp = 3; __kk.atk();"
                      " dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', code: 'ArrowRight'}));"
                      " if (performance.now() % 1000 < 300) __kk.jump(); })()"),
    "horda": ("document.querySelector('[data-df=\"ultra\"]').click(); document.getElementById('go').click()",
              "(() => { const k = performance.now() % 2000 < 1000 ? 'ArrowLeft' : 'ArrowRight';"
              " dispatchEvent(new KeyboardEvent('keydown', {key: k, code: k}));"
              " setTimeout(() => dispatchEvent(new KeyboardEvent('keyup', {key: k, code: k})), 250); })()"),
}


async def measure(browser, base, game, rate, seconds, force=None):
    async with Run(browser, base, mobile=True) as r:
        # the same "random" numbers every run, so the scenes match and runs can be compared
        await r.ctx.add_init_script("(() => { let a = 12345; Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0;"
                                    " let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;"
                                    " return ((t ^ t >>> 14) >>> 0) / 4294967296; }; })()")
        await r.goto(f"{game}/index.html")
        cdp = await r.ctx.new_cdp_session(r.page)
        start, busy = SCENES[game]
        await r.page.evaluate(start)
        await r.page.evaluate(f"setInterval(() => {{ try {{ {busy} }} catch (e) {{}} }}, 300)")
        if force is not None:
            await r.page.evaluate(f"Kepesseg.setQuality({force})")
        await r.page.wait_for_timeout(1500)                       # the scene fills up
        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": rate})
        await r.page.wait_for_timeout(12000)                      # time to settle on a quality level
        await cdp.send("Performance.enable")
        busy0 = {m["name"]: m["value"] for m in (await cdp.send("Performance.getMetrics"))["metrics"]}["TaskDuration"]
        d = await r.page.evaluate(FRAMES, seconds * 1000)
        busy1 = {m["name"]: m["value"] for m in (await cdp.send("Performance.getMetrics"))["metrics"]}["TaskDuration"]
        q = await r.page.evaluate("window.Kepesseg ? Kepesseg.quality() : null")
        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        d = d[1:]
        avg = statistics.mean(d)
        p95 = sorted(d)[int(len(d) * .95)]
        slow = sum(x > 33.4 for x in d) / len(d)
        work = (busy1 - busy0) * 1000 / len(d)                   # main-thread work per frame, ms (steadier than fps)
        return avg, p95, slow, work, q, r.errors


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    rate, seconds, force = float(opt("--rate", 20)), float(opt("--seconds", 8)), opt("--quality", None)
    force = int(force) if force is not None else None
    args = [a for a in args if a not in sys.argv[1:] or sys.argv[sys.argv.index(a) - 1] not in ("--rate", "--seconds", "--quality")]
    games = [g for g in SCENES if not args or g in args]
    httpd, base = start_server()
    print(f"CPU {rate:g}× slower, 390×780 touch, {seconds:g} s per game"
          + ("" if force is None else f", quality forced to {force}"))
    print(f"{'game':<15}{'avg ms':>8}{'fps':>7}{'p95 ms':>8}{'>33 ms':>8}{'work ms':>9}{'quality':>9}")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for g in games:
            avg, p95, slow, work, q, errors = await measure(browser, base, g, rate, seconds, force)
            print(f"{g:<15}{avg:8.1f}{1000 / avg:7.1f}{p95:8.1f}{slow * 100:7.0f}%{work:9.1f}{'' if q is None else q:>9}")
            for e in errors:
                print("     ", e)
        await browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

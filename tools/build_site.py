#!/usr/bin/env python3
"""Build the games start page and the GitHub Pages site.

Every top-level folder that contains an index.html is treated as a game.
Its card on the start page is built from tags in that page's <head>:

  <title>Name</title>
  <meta name="description" content="Hungarian description">
  <meta name="games:category" content="jatek | minecraft">   (optional, default: jatek)
  <meta name="games:title-en" content="English name">        (optional)
  <meta name="games:description-en" content="English text">  (optional)

Usage:
  python3 tools/build_site.py            # refresh the game list inside index.html
  python3 tools/build_site.py --check      # also run the policy check (AGENTS.md) and the script syntax check
  python3 tools/build_site.py --out _site  # check, then copy a deployable site to _site/
                                           # (only '_site' inside the repo is accepted)

Every game needs a cover picture, assets/covers/<folder>.webp (make it with tools/make_covers.py).
The published copy also gets a page icon and share tags (og:*) on every page, and the offline cache
(sw.js) gets its file list and version.
"""
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"tools", "assets", "_site"}
SITE = "https://nomadbeni.github.io/minigames/"
COVERS = ROOT / "assets" / "covers"
COVER_MAX_BYTES = 40_000
# Apps with an offline cache of their own; the site-wide one (sw.js) leaves them alone.
OWN_WORKER = {"cornholescore"}
HOME_LINK = (
    '<a class="home-link" href="../index.html" style="display:inline-flex;'
    'align-self:flex-start;width:fit-content;align-items:center;gap:6px;'
    'margin:0 0 10px;min-height:44px;box-sizing:border-box;padding:6px 14px;border-radius:999px;border:1px solid currentColor;'
    'color:inherit;opacity:.75;text-decoration:none;'
    'font:600 14px/1.2 system-ui,sans-serif">← Összes játék</a>'
)


class HeadReader(HTMLParser):
    """Reads <title> and <meta name=... content=...> regardless of attribute order or quoting."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self._in_title, self.scripts, self._script = "", {}, False, [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") and a.get("content") is not None:
            self.meta.setdefault(a["name"].lower(), a["content"])
        elif tag == "script" and "src" not in a and a.get("type", "text/javascript") in ("", "text/javascript", "module"):
            self._script = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._script is not None:
            self._script.append(data)


def game_pages():
    """The index.html of every game folder (never the built _site or the tools)."""
    return sorted(p for p in ROOT.glob("*/index.html") if p.parent.name not in SKIP and not p.parent.name.startswith("."))


def read_page(page):
    r = HeadReader()
    r.feed(page.read_text(encoding="utf-8"))
    return r


def collect():
    games = []
    for d in sorted(ROOT.iterdir()):
        page = d / "index.html"
        if not d.is_dir() or d.name.startswith(".") or d.name in SKIP or not page.exists():
            continue
        r = read_page(page)
        m = r.meta
        title = r.title.strip() or d.name
        games.append({
            "slug": d.name,
            "category": m.get("games:category") or "jatek",
            "title": title,
            "title_en": m.get("games:title-en") or title,
            "desc": m.get("description", ""),
            "desc_en": m.get("games:description-en") or m.get("description", ""),
            "cover": (COVERS / f"{d.name}.webp").exists(),
        })
    return games


def write_index(games):
    index = ROOT / "index.html"
    src = index.read_text(encoding="utf-8")
    data = json.dumps(games, ensure_ascii=False, indent=1).replace("</", "<\\/")
    new = re.sub(
        r'(<script id="games-data" type="application/json">).*?(</script>)',
        lambda m: m.group(1) + "\n" + data + "\n" + m.group(2),
        src, count=1, flags=re.S,
    )
    if new != src:
        index.write_text(new, encoding="utf-8", newline="\n")


def safe_out(out):
    """Only a single folder directly inside the repo is accepted, and never a source folder."""
    target = (ROOT / out).resolve()
    if target.parent != ROOT or target.name.startswith(".") or target.name != "_site":
        sys.exit(f"Refusing to use {target} as output: only '_site' inside the repository is allowed.")
    if target.is_symlink():
        sys.exit(f"Refusing to use {target}: it is a symbolic link.")
    return target


def check_scripts():
    """Fails the build if an inline script in any page has a JavaScript syntax error."""
    node = shutil.which("node")
    if not node:
        sys.exit("Node.js is required for the script check (--check / --out) but 'node' was not found.")
    pages = [ROOT / "index.html"] + game_pages()
    errors = 0
    with tempfile.TemporaryDirectory() as tmp:
        for page in pages:
            for i, code in enumerate(read_page(page).scripts):
                f = Path(tmp) / f"s{i}.js"
                f.write_text(code, encoding="utf-8")
                res = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
                if res.returncode:
                    errors += 1
                    print(f"Syntax error in {page.relative_to(ROOT)} (script {i + 1}):\n{res.stderr}")
    if errors:
        sys.exit(1)


# ---- Repository rules (see AGENTS.md). Every rule here fails the build. ----
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com", "github.com"}
POLICY = [
    (r"[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com)[A-Za-z0-9-]+\.[A-Za-z0-9.-]*[A-Za-z]{2,}",
     "e-mail address"),
    (r"claude\.ai/|chatgpt\.com/|chat\.openai\.com/|session_[A-Za-z0-9]{8,}|utm_source=", "chat or tracking link"),
    (r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|new\s+WebSocket|EventSource\s*\(", "network request from script"),
    (r"navigator\.geolocation|getUserMedia|getDisplayMedia", "camera, microphone or location access"),
    (r"document\.cookie", "cookie"),
    (r"google-analytics|googletagmanager|gtag\(|plausible|matomo|hotjar|facebook\.net|doubleclick|adsbygoogle",
     "analytics or ads"),
    (r"\beval\s*\(|new\s+Function\s*\(", "eval / new Function"),
    (r"\.src\s*=\s*[`'\"]\s*(?:https?:)?//", "image or media loaded from another site"),
    (r"window\.open\s*\(", "window.open"),
    (r"navigator\.clipboard\.read|readText\s*\(", "reading the clipboard"),
    (r"\bimport\s*\(", "dynamic import()"),
    (r"url\(\s*['\"]?\s*(?:https?:)?//|@import\s", "CSS loaded from another site (url(http…) or @import)"),
    (r"navigator\.serviceWorker|importScripts\s*\(", "service worker"),
]
# A file may use one rule's pattern on purpose; the reason is written next to it.
POLICY_ALLOW = {
    ("cornholescore/index.html", "service worker"): "installable offline app, caches only its own files (sw.js)",
    ("cornholescore/sw.js", "service worker"): "the offline cache itself, it requests nothing from other sites",
    ("index.html", "service worker"): "registers the site-wide offline cache (sw.js) and offers its updates",
    ("sw.js", "service worker"): "the site-wide offline cache: only this site's own, listed files",
}

# Every Minecraft build plan page, the start page and the README say the project is not an official Minecraft product.
MC_NOTE = "Nem hivatalos Minecraft-termék"

# Every page carries this Content-Security-Policy, so the browser itself blocks requests to other sites.
# 'unsafe-inline' is needed because every game is a single HTML file with inline script and style.
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; media-src 'self' data: blob:; font-src 'self'; connect-src 'none'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'; worker-src 'none'")
# Pages that may use more (the owner's decision): Google Fonts, and the Cornhole offline app.
CSP_EXTRA = {
    "falbonto/index.html": {"style-src": "https://fonts.googleapis.com", "font-src": "https://fonts.gstatic.com"},
    "kincsvadasz/index.html": {"style-src": "https://fonts.googleapis.com", "font-src": "https://fonts.gstatic.com"},
    "betubanya/index.html": {"style-src": "https://fonts.googleapis.com", "font-src": "https://fonts.gstatic.com"},
    "cornholescore/index.html": {"worker-src": "'self'", "manifest-src": "'self'"},
    "index.html": {"worker-src": "'self'", "manifest-src": "'self'"},
}


def csp_for(rel):
    parts = dict(d.split(" ", 1) for d in CSP.split("; "))
    for k, v in CSP_EXTRA.get(rel, {}).items():
        parts[k] = v if parts.get(k, "'none'") == "'none'" else parts[k] + " " + v
    return "; ".join(f"{k} {v}" for k, v in parts.items())


def csp_meta(rel):
    return f'<meta http-equiv="Content-Security-Policy" content="{csp_for(rel)}">'


def check_policy():
    """Fails the build if any published file breaks the privacy and safety rules."""
    errors = []
    files = [f for f in ROOT.rglob("*") if f.is_file()
             and not any(part in {".git", "_site", "tools"} for part in f.relative_to(ROOT).parts)
             and f.suffix in {".html", ".js", ".css", ".md", ".json", ".svg", ".txt", ".yml"}]
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        for pattern, what in POLICY:
            if rel in {"AGENTS.md", "CLAUDE.md"}:
                break  # the rules document names the forbidden things on purpose
            if (rel, what) in POLICY_ALLOW:
                continue
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                errors.append(f"{rel}:{line}: {what}: {m.group(0)[:60]}")
        if f.suffix == ".html":
            for host in set(re.findall(r"""(?:src|href)\s*=\s*["']https?://([^/"'\s]+)""", text)):
                if host not in ALLOWED_HOSTS:
                    errors.append(f"{rel}: external host not allowed: {host}")
            if re.search(r"<script[^>]+src\s*=", text):
                errors.append(f"{rel}: external <script src> is not allowed, inline the code")
    for page in game_pages():
        rel = page.relative_to(ROOT).as_posix()
        text = page.read_text(encoding="utf-8")
        r = read_page(page)
        for name in ("description", "games:category", "games:title-en", "games:description-en"):
            if not r.meta.get(name):
                errors.append(f"{rel}: missing <meta name=\"{name}\">")
        if r.meta.get("games:category") not in (None, "", "jatek", "minecraft"):
            errors.append(f"{rel}: games:category must be jatek or minecraft")
        if 'class="home-link"' not in text:
            errors.append(f"{rel}: missing the '← Összes játék' home link")
        if 'class="fs-btn"' not in text:
            errors.append(f"{rel}: missing the '⛶ Teljes képernyő' fullscreen button (copy it from an existing game)")
        uses_hidden = re.search(r"\.hidden\s*=|\shidden[\s>]", text)
        if uses_hidden and not re.search(r"\[hidden\]\s*\{\s*display\s*:\s*none", text):
            errors.append(f"{rel}: uses the hidden attribute but has no [hidden]{{display:none!important}} rule")
        if r.meta.get("games:category") == "minecraft" and MC_NOTE not in text:
            errors.append(f"{rel}: a Minecraft page must say it is not official: {MC_NOTE}…")
        if 'lang="hu"' not in text[:300]:
            errors.append(f"{rel}: <html lang=\"hu\"> missing")
    for page in [ROOT / "index.html", ROOT / "404.html"] + game_pages():
        rel = page.relative_to(ROOT).as_posix()
        if not page.exists():
            continue
        if csp_meta(rel) not in page.read_text(encoding="utf-8"):
            errors.append(f"{rel}: missing or changed Content-Security-Policy meta; it must be exactly:\n      "
                          + csp_meta(rel) + "\n      (the rules are CSP and CSP_EXTRA in tools/build_site.py)")
    # Code shared by several games must match its master copy in tools/shared/ (see tools/sync_shared.py).
    sys.path.insert(0, str(ROOT / "tools"))
    import sync_shared
    for rel, name, msg in sync_shared.differences():
        errors.append(f"{rel}: shared block '{name}': {msg} (fix the master copy, then run tools/sync_shared.py)")
    # Every game has a small cover picture for its start page card, and no cover is left over.
    folders = {g["slug"] for g in collect()}
    for slug in sorted(folders):
        f = COVERS / f"{slug}.webp"
        if not f.exists():
            errors.append(f"assets/covers/{slug}.webp: missing cover picture (run: python3 tools/make_covers.py {slug})")
        elif f.stat().st_size > COVER_MAX_BYTES:
            errors.append(f"assets/covers/{slug}.webp: {f.stat().st_size // 1000} KB, keep it under {COVER_MAX_BYTES // 1000} KB")
        elif f.read_bytes()[:4] != b"RIFF" or f.read_bytes()[8:12] != b"WEBP":
            errors.append(f"assets/covers/{slug}.webp: not a WebP picture")
    for f in sorted(COVERS.glob("*")):
        if f.stem not in folders or f.suffix != ".webp":
            errors.append(f"assets/covers/{f.name}: no game folder of that name")
    # The offline cache must keep its placeholders: the file list and the version are written when publishing.
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    if not re.search(SW_FILES, sw) or not re.search(SW_CACHE, sw):
        errors.append("sw.js: the FILES or CACHE line is missing (build_site.py fills them in when publishing)")
    for rel in ("index.html", "README.md"):
        if MC_NOTE not in (ROOT / rel).read_text(encoding="utf-8"):
            errors.append(f"{rel}: the note '{MC_NOTE}…' is missing")
    # The README table lists exactly the game folders.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\|\s*\[[^\]]+\]\(([a-z0-9-]+)/\)\s*\|", readme, re.M))
    for slug in sorted(folders - listed):
        errors.append(f"README.md: the game table has no row for {slug}/")
    for slug in sorted(listed - folders):
        errors.append(f"README.md: the game table lists {slug}/, but there is no such game folder")
    if errors:
        print("Policy check failed:\n  " + "\n  ".join(errors))
        sys.exit(1)


ICON = ("data:image/svg+xml," + (ROOT / "assets" / "icon.svg").read_text(encoding="utf-8").strip()
        .replace("#", "%23").replace('"', "'").replace("<", "%3C").replace(">", "%3E"))
SW_FILES = r"var FILES = \[[^\n]*\];"
SW_CACHE = r"var CACHE = '[^'\n]*';"


def head_extras(page, rel):
    """Page icon and share tags for a published page, made from its own <head> (skipped where the page has its own)."""
    src = page.read_text(encoding="utf-8")
    r = read_page(page)
    folder = rel.split("/")[0] if "/" in rel else ""
    url = SITE + (folder + "/" if folder else "")
    has_cover = folder and (COVERS / f"{folder}.webp").exists()
    image = SITE + (f"assets/covers/{folder}.webp" if has_cover else "assets/icon-512.png")
    tags = []
    if 'rel="icon"' not in src:
        tags.append(f'<link rel="icon" href="{ICON}">')
    if 'property="og:' not in src:
        def e(v):
            return html.escape(v.strip(), quote=True)
        tags += [
            '<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{e(r.title)}">',
            f'<meta property="og:description" content="{e(r.meta.get("description", ""))}">',
            f'<meta property="og:url" content="{url}">',
            f'<meta property="og:image" content="{image}">',
            '<meta name="twitter:card" content="' + ("summary_large_image" if has_cover else "summary") + '">',
        ]
    if tags and "</head>" in src:
        page.write_text(src.replace("</head>", "\n".join(tags) + "\n</head>", 1), encoding="utf-8", newline="\n")


def offline_files(out):
    """Everything the site-wide offline cache stores: the start page, the icons, the fonts, the covers and
    every game page (not the apps with an offline cache of their own)."""
    files = ["index.html", "manifest.json", "assets/icon.svg", "assets/icon-192.png", "assets/icon-512.png"]
    files += sorted(f.relative_to(out).as_posix() for f in (out / "assets" / "fonts").glob("*")
                    if f.suffix in {".css", ".woff2"})
    files += sorted(f.relative_to(out).as_posix() for f in (out / "assets" / "covers").glob("*.webp"))
    files += sorted(p.relative_to(out).as_posix() for p in out.glob("*/index.html")
                    if p.parent.name not in SKIP | OWN_WORKER)
    return files


def write_worker(out):
    """Fills in the offline cache's file list, and a version that changes whenever any listed file changes."""
    files = offline_files(out)
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.encode() + b"\0" + (out / f).read_bytes())
    sw = out / "sw.js"
    src = sw.read_text(encoding="utf-8")
    src = re.sub(SW_FILES, lambda m: "var FILES = " + json.dumps(files) + ";", src, count=1)
    src = re.sub(SW_CACHE, lambda m: f"var CACHE = 'jatektar-{digest.hexdigest()[:12]}';", src, count=1)
    sw.write_text(src, encoding="utf-8", newline="\n")


def build_site(out):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(
        ROOT, out,
        # Tests and the folders' own README files are for the repository, not for the published site.
        ignore=shutil.ignore_patterns(".git", ".github", "tools", "_site", "*.py", "AGENTS.md", "CLAUDE.md",
                                      "README.md", "tests", "*.test.*"),
    )
    # A game added without a back link still gets one on the published site.
    for page in out.glob("*/index.html"):
        src = page.read_text(encoding="utf-8")
        if 'class="home-link"' in src:
            continue
        m = re.search(r"<body[^>]*>", src)
        if m:
            src = src[:m.end()] + "\n" + HOME_LINK.replace(
                "margin:0 0 10px;", "position:fixed;z-index:999;"
                "top:calc(8px + env(safe-area-inset-top,0px));"
                "left:calc(8px + env(safe-area-inset-left,0px));margin:0;"
                "background:rgba(20,20,30,.7);color:#fff;"
            ) + src[m.end():]
            page.write_text(src, encoding="utf-8", newline="\n")
    for page in [out / "index.html", out / "404.html"] + sorted(out.glob("*/index.html")):
        if page.exists():
            head_extras(page, page.relative_to(out).as_posix())
    write_worker(out)


if __name__ == "__main__":
    # Validate everything before touching any file.
    out = None
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        if i + 1 >= len(sys.argv):
            sys.exit("--out needs a value: --out _site")
        out = safe_out(sys.argv[i + 1])
    if "--check" in sys.argv or out:
        check_policy()
        check_scripts()
    games = collect()
    write_index(games)
    if out:
        build_site(out)
    print(f"{len(games)} games listed")

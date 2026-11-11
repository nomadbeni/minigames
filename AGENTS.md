# Utasítás MI-ügynököknek (Claude, Codex, Copilot stb.)

Ez a tároló nyilvános, és minden, ami a `main` ágra kerül, néhány percen belül kint van a GitHub Pages-en (`nomadbeni.github.io/minigames`). Úgy dolgozz, mintha minden sorodat idegenek, köztük gyerekek is olvasnák.

## Mi ez a tároló

- Böngészőben futó, **egyfájlos** HTML játékok és Minecraft építési tervek, magyar nyelven.
- Minden játék a saját mappájában van: `<mappa>/index.html`. Minden CSS és JS ebben az egy fájlban van.
- A startlap (`index.html`) játéklistáját a `tools/build_site.py` generálja a játékok `<head>`-jéből. Kézzel ne szerkeszd a `games-data` blokkot.
- Közzététel: `.github/workflows/pages.yml`, minden push után a `main` ágra.
- A célközönség része: lassan, nem szívesen olvasó, diszlexiás kamaszok. Erről a README ír.

## Kötelező szabályok

### Adatvédelem, nincs adatgyűjtés
- **Nincs hálózati kérés a játékból:** nincs `fetch`, XHR, `sendBeacon`, WebSocket, külső API, analitika, hirdetés, követőpixel, süti.
- **Nincs eszközhozzáférés:** kamera, mikrofon, helyzet és vágólap-olvasás nincs.
- **Csak helyi mentés:** állás, rekord és beállítás csak a `localStorage`-ba kerülhet, a játék saját előtagjával (pl. `falbonto-save`). Minden olvasást és írást `try/catch` vesz körül, és a betöltött mentést mezőnként ellenőrizni kell. Sérült mentésnél új játék indul, nem omlik össze.
- **Nincs személyes adat bekérése:** név, e-mail, kor, iskola nem kérhető. Ha a játék nevet kér (pl. ranglistához), az csak helyben tárolódhat.
- **Külső forrás:** a betűtípus elsősorban helyből jön: `<link rel="stylesheet" href="../assets/fonts/fonts.css">` (Fontsource, csak latin + latin-ext, woff2; új betűcsaládot ide tegyél, a licencével együtt). Ha egy betűtípus licencében vagy fájljában e-mail cím van, az nem kerülhet a tárolóba; ilyenkor a Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) használható. Mindig legyen rendszer-tartalék. Külső `<script src>` és más domainről kép vagy hang nem tölthető. A grafika canvasra rajzolt vagy beágyazott `data:` URI, a hang Web Audio.

### Személyes adat és chat-nyomok a tárolóban
- **E-mail cím:** semmilyen fájlban, commit üzenetben, szerzőben vagy commitolóban nem lehet e-mail cím. Az egyetlen megengedett cím:
  `nomadbeni <29810786+nomadbeni@users.noreply.github.com>`.
  Commit előtt: `git config user.name nomadbeni` és `git config user.email 29810786+nomadbeni@users.noreply.github.com`.
- **Linkek:** nem lehet benne chat- vagy munkamenet-link (claude.ai, chatgpt.com, `Claude-Session:`), `utm_` paraméter, belső elérési út, gépnév, IP-cím, token vagy jelszó.
- **Hivatkozás valós személyre:** nincs valós személyre utaló adat (családtag neve, kora, iskolája, egészségi adata). A célközönséget csak általánosan írd le.
- **Commit üzenet:** magyarul írd, és a végén egyetlen MI-jelölő sor álljon:
  ```
  AI-generated: Claude (Anthropic)
  ```
  Ne legyen benne `Co-Authored-By`, se e-mail cím. Más modell a saját nevét írja.

### MI-jelölés
- A README-ben és a startlap láblécében (magyarul és angolul) szerepelnie kell: a tárolóban minden kódot, játékot és leírást teljes egészében MI készített, az ellenőrzést egy másik MI végezte. Ezt nem szabad eltávolítani vagy gyengíteni.
- A licenc MIT (`LICENSE`), ez marad.

### Tartalom
- Gyerekbarát: nincs vér, nincs valós fegyvermárka, nincs szerencsejáték valódi pénzzel, nincs vásárlás az alkalmazáson belül, nincs reklám.
- Nincs védett karakter, márka vagy logó (pl. Mario, Minecraft-figurák, Sonic). A szereplők saját kitalálásúak. A „Minecraft építési terv” csak blokkok és építési lépések leírása.
- Nincs `eval` és `new Function`. Felhasználói szöveg HTML-be csak escape-elve kerülhet.

## Új játék vagy módosítás: kötelező elemek

1. Mappa és `index.html` legyen kisbetűs, ékezet nélküli, kötőjeles névvel (`uj-jatek/index.html`).
2. Az oldal `<!doctype html>` és `<html lang="hu">` kezdetű, legyen benne viewport meta (`viewport-fit=cover`), és közvetlenül a `<meta charset>` után a Content-Security-Policy meta. Ezzel a böngésző maga tiltja a más helyre menő kérést. Pontos szövegét a `tools/build_site.py` `CSP` állandója adja (a kivételeket a `CSP_EXTRA`); másold egy meglévő játékból, a `--check` betűre ellenőrzi.
3. A `<head>`-be ezek kellenek:
   ```html
   <title>Játék neve</title>
   <meta name="description" content="Rövid magyar leírás">
   <meta name="games:category" content="jatek">   <!-- vagy: minecraft -->
   <meta name="games:title-en" content="English name">
   <meta name="games:description-en" content="Short English description">
   ```
4. Az oldal tetején kell lennie a vissza gombnak (`class="home-link"`, `href="../index.html"`, felirat: `← Összes játék`), mellette a teljes képernyő gombnak (`class="fs-btn"`, felirat: `⛶ Teljes képernyő`), a kettő egy `class="top-bar"` sávban. A gombhoz tartozó rövid szkript a `</body>` előtt van, a `<head>`-ben pedig a `mobile-web-app-capable` és `apple-mobile-web-app-capable` meta. Mindet egy meglévő játékból másold. (iPhone-on a böngésző nem támogatja a teljes képernyőt, ott a gomb eltűnik; kezdőképernyőre tett oldalként viszont teljes képernyőn fut.)
5. Ha bármit a `hidden` attribútummal rejtesz, kell a `[hidden]{display:none!important}` szabály. Enélkül a `display:grid/flex` felülírja, és a rejtett ablak mindig látszik.
6. Álló telefonra készüljön (kb. 400×860), érintéssel játszható legyen. Oldalirányú görgetés nincs, minden gomb a képernyőn belül marad. Gépen egér vagy billentyű is működjön.
7. A README táblázatába új sor kell a játékkal (magyar leírás).
8. Ha a játék a közös olvasásfejlesztő rendszert használja (rang, XP, felolvasó súgó), a meglévő játékokból vedd át, ne írj újat.
9. A több játékba bemásolt közös kód (`/* @shared név */ … /* @end név */` közötti blokk, pl. `olvaso-kit`, `terv-nezegeto`) mintapéldánya a `tools/shared/<név>.js`. Ezt javítsd, utána futtasd a `python3 tools/sync_shared.py` parancsot, amely minden játékba bemásolja. A `--check` leáll, ha egy játék blokkja eltér a mintától.

## Kötelező ellenőrzés commit és push előtt

Mindet futtasd le, és csak akkor pusholj, ha mind átment:

```bash
# 1. Szabályellenőrzés + JS-szintaxis (e-mail, chat-link, hálózati kérés, külső domain,
#    kötelező meta, vissza gomb, [hidden] szabály). A közzététel is ezt futtatja.
python3 tools/build_site.py --check

# 2. Böngészős füstteszt telefonméretben: nincs JS-hiba, nincs tiltott kérés,
#    nincs oldalirányú görgetés, nincs képernyőről lelógó gomb.
python3 tools/smoke_test.py            # vagy: python3 tools/smoke_test.py <mappa>

# 3. Játékteszt: minden játék gépen és érintéssel, öt féle sérült mentéssel; valódi játékmenetek
#    az olvasós játékokban; a pályagenerátorok több száz pályával. Új olvasós játékhoz írj
#    ide egy rövid jelenetet (SCENARIOS), új generátorhoz vedd fel a generátor-tesztbe.
python3 tools/play_test.py             # vagy: python3 tools/play_test.py <mappa>, --quick

# 4. A commitok szerzője és üzenete tiszta:
git log origin/main..HEAD --format='%an <%ae> | %cn <%ce>%n%B' \
  | grep -iE '@|claude\.ai|session|co-authored' | grep -v 'users.noreply.github.com'
#    → ennek üresnek kell lennie
```

Ezen felül:
- **Játszd is végig, ne csak töltsd be:** egy Playwright-szkripttel indíts el egy kört, lőj vagy ütközz, veszíts életet, és ellenőrizd, hogy a vége ablak megjelenik, az „Új játék” pedig eltünteti.
- **Nézd meg a képernyőképeket** a `_site/smoke/` mappában.
- **Mentés:** töltsd újra az oldalt játék közben, és nézd meg, hogy a mentés helyesen áll-e vissza. Rontsd el kézzel a `localStorage`-ot, és ellenőrizd, hogy új játék indul.
- **Pályagenerátor:** ha a játék véletlen pályát készít, a generátor csak ellenőrzött (pl. egyértelmű megoldású) pályát adjon vissza, és legyen időkorlátja.

## Mit ne csinálj

- Ne írd át a git előzményeket, és ne force pusholj, hacsak a tulajdonos kifejezetten nem kéri.
- Ne kapcsold ki és ne gyengítsd a `tools/build_site.py` ellenőrzéseit azért, hogy átmenjen a build. Javítsd a játékot.
- Ne tegyél be build-lépést, csomagkezelőt vagy keretrendszert. Minden játék egy önálló HTML fájl marad.
- Ne módosíts más játékot, mint amit kértek. Kivétel, ha az ellenőrzés hibát talál benne: akkor javítsd, és írd bele a commit üzenetbe.

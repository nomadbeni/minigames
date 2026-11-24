# Modern böngészőképességek: kompatibilitás és ellenőrzési lista

A játékok néhány újabb böngészőképességet használnak a közös `kepesseg` blokkon keresztül
(mintapéldány: [`tools/shared/kepesseg.js`](../tools/shared/kepesseg.js)). Mind **opcionális**: ha a
böngésző nem ismeri, elutasítja vagy hibát dob, a modul csendben nem csinál semmit, a játék ugyanúgy
játszható. Egyik sem kér semmit a hálózatról, és a játék soha nem vár rájuk.

| Képesség | Mire jó | Hol van | Ha nincs |
|---|---|---|---|
| Rezgés: `navigator.vibrate` és kontroller (`vibrationActuator`) | rövid jelzés találatra, sérülésre, robbanásra, jutalomra | Gyémántbánya, Kincsvadász, Nyilak, Falbontó, Téglatörő (telefon); Páncélos őrség, Kőkori Kaland, Kőzápor, Kardvihar, Bombász, Flipper (telefon + kontroller) | nincs rezgés; a 📳 kapcsoló sem látszik |
| Screen Wake Lock | játék közben nem alszik el a kijelző | Kardvihar, Kőzápor, Páncélos őrség, Flipper | a kijelző a szokásos módon elalhat |
| View Transitions | finom (0,15 mp) megjelenés: menü, pályaválasztó, eredmény | Pasziánsz, Mahjong, Gyémántbánya | az ablak azonnal megjelenik |
| Screen Orientation lock | teljes képernyőn nem fordul el véletlenül | a 20 álló játék (`games:orientation` = `portrait`) | marad a CSS-es elrendezés és a „Fordítsd el a telefont” jelzés |
| Adaptív grafika (+ Compute Pressure, ha van) | gyenge gépen kevesebb díszítő effekt | Horda, Kardvihar, Kőkori Kaland, Kőzápor | csak a képkockaidőt méri |

## Szabályok, amelyekre a modul vigyáz

- **Rezgés:** csak a játékos első érintése vagy gombnyomása után; egy minta legfeljebb 400 ms, egy
  szakasz legfeljebb 200 ms; két rezgés között legalább 70 ms, és gyengébb jelzés nem szakítja meg az
  erősebbet. A telefon csak érintőképernyős eszközön rezeg. A 📳 kapcsoló közös minden játékban
  (`localStorage`: `kepesseg:rezges`), és mindkét kimenetre (telefon, kontroller) érvényes.
- **Wake Lock:** csak a játékos által indított játék közben. Menü, szünet, játék vége és háttérbe tett
  lap elengedi; visszatéréskor csak akkor kéri újra, ha a játék fut. Két perc tétlenség után magától is
  elengedi, a következő érintésre újrakéri.
- **View Transitions:** csak ablak megjelenésekor. Átmenet közben a Chromium nem ad át érintést (ezt a
  `pointer-events` sem oldja fel, 2026 novemberében Chromium 159-cel mérve), ezért a játékba visszavezető
  bezárás azonnali, és bármilyen érintés vagy gombnyomás azonnal befejezi a futó átmenetet. Csökkentett
  mozgásnál és betöltéskor nincs átmenet.
- **Tájolás:** csak teljes képernyőn (az a játékos gombnyomása), és csak abba a tájolásba zárol, ahogy
  a készülék már áll. Így soha nem forgatja el a képet, fekvő kijelzős kézikonzolon sem.
- **Adaptív grafika:** 3 lassú (24 ms feletti átlagú) másodperc után lép le egy szintet, utána 4 mp-ig
  nem lép újra; fölfelé csak 15 jó másodperc után, és legfeljebb kétszer, hogy ne villogjon. Csak a
  látvány változik, a játéklogika, az ütközés és az időzítés nem. Csökkentett mozgásnál legfeljebb 1. szint.

## Automatikus tesztek

A `tools/play_test.py` része, minden push előtt lefut:

- `--only capabilities`: a modul önmagában, mockolt API-kkal, négy módban: működik / hiányzik /
  elutasít (rejected promise) / hibát dob. Ellenőrzi: nincs rezgés az első érintés előtt, időkorlát,
  minta hossza, kikapcsolás és annak megjegyzése, Wake Lock elengedése és újrakérése, View Transition
  és csökkentett mozgás, tájolás zárolása teljes képernyőn (és fekvő készüléken nem), a minőségszintek
  lépései, Compute Pressure.
- Játékmenetek: Kardvihar (kontroller rezeg, kapcsoló, Wake Lock a játék menetében), Mahjong (View
  Transition, érintés közvetlenül bezárás után, csökkentett mozgás), és hat játék meglévő végigjátszása
  hiányzó, elutasító és hibát dobó API-kkal; négy játék a legalacsonyabb grafikai szinten.
- `--only compat`: hat játék öt képernyőn (álló és fekvő telefon, 640×480-as és 720×720-as kézikonzol,
  gép): nincs szkripthiba, nincs oldalra görgetés, a felső sáv gombjai a képernyőn vannak, a „Fordítsd el”
  jelzés csak ott látszik, ahol kell, és a tájolászár csak álló készüléken lép életbe. Offline: elkészíti
  a közzétett oldalt (`_site`), megvárja az offline tárat, kikapcsolja a hálózatot, és úgy játszik.

Teljesítmény: `python3 tools/perf_test.py` (telefonméret, 20× lassított processzor; nem pass/fail).

## Ellenőrzési lista valódi eszközön

Minden sorban: a játék elindul, végigjátszható, nincs hibaüzenet; utána a képességre jellemző pont.

**Android, Chrome (és más Chromium alapú, pl. Samsung Internet, Edge)**
- [ ] Telefonon a 📳 kapcsoló látszik; ütközésnél rövid rezgés; kikapcsolva semmi, újratöltés után is ki.
- [ ] Bluetooth-kontrollerrel (Xbox / DualShock / DualSense) a Kardviharban találatra rezeg a kontroller.
- [ ] Kardvihar: játék közben 1–2 percig nem érünk a képernyőhöz, a kijelző nem alszik el; menüben igen.
- [ ] Teljes képernyő álló telefonon egy álló játékban, utána a telefon elforgatása: a kép nem fordul el.
      Kilépés után újra forog.
- [ ] Pasziánsz / Mahjong: a menü finoman jelenik meg; Beállítások → Kisegítő lehetőségek → animációk
      kikapcsolása után azonnal.
- [ ] Gyengébb telefonon a Horda sok zombival is folyamatos marad (kevesebb díszítő effekttel).

**Asztali Chrome / Edge**
- [ ] A 📳 kapcsoló csak csatlakoztatott, rezgő kontrollerrel látszik.
- [ ] Teljes képernyőben nincs hibaüzenet (a tájolászárat a gép elutasítja, ez rendben van).

**Firefox (Android és asztali)**
- [ ] Ahol nincs rezgés, View Transition vagy tájolászár, a játék ugyanúgy működik, hibaüzenet nélkül.

**Korlátozott böngészők** (iPhone Safari, alkalmazásba épített böngészők, iskolai / szülői felügyelet)
- [ ] Nincs teljes képernyő gomb (iPhone), nincs rezgés; a játék végigjátszható.
- [ ] Kezdőképernyőre tett oldalként is indul, internet nélkül is.

**Anbernic és más Android kézikonzol (640×480, 720×720, 1920×1152)**
- [ ] A beépített gombokkal (kontrollerként) lehet menüzni és játszani.
- [ ] Teljes képernyőn a kép nem fordul el (fekvő kijelzőn nem zárol álló tájolásba).
- [ ] Ha a konzol rezgőmotorja Gamepad API-n látszik, a Kardvihar találatra rezeg; ha nem, semmi baj.
- [ ] Ismert, korábbi viselkedés: 640×480-as érintőképernyős konzolon az álló játékok a „Fordítsd el a
      telefont” jelzést mutatják (a kijelző fekvő és 500 px-nél alacsonyabb). Ez nem új, de érdemes külön
      eldönteni, hogy kontrollerrel ott is játszhatók legyenek-e.

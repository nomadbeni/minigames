# WebGPU és WebAssembly: döntési feljegyzés (#54)

Mérve 2026 novemberében. Gép: AMD Ryzen 7 PRO 5850U, Linux, headless Chromium 159 (Playwright 1.65).
Valódi Android-eszközön és Anbernic konzolon nem mértünk; az ott várható viselkedés becslés.

## Döntés röviden

| | Döntés | Indok |
|---|---|---|
| **WebGPU** | **Elhalasztva** | Nincs olyan játék, amelyet a Canvas 2D korlátoz; a tesztkörnyezetben nincs WebGPU-adapter, így automatikusan nem tesztelhető; WebGL2 / Canvas 2D tartalék mindenképp kellene. |
| **WebAssembly** | **Most nem** | Nincs képkockánként futó, számításigényes rész; a CSP tiltja; fordító kellene (build-lépés), és a bináris base64-ként 33%-kal nagyobb lenne. |
| Prototípus | Nem készült | Nincs mérhető eset, ahol előnyt adna (lásd lent). |

## Mérések

**1. Böngészőtámogatás a tesztkörnyezetben** (egy játék oldalán, a saját CSP-jével):

| Képesség | Eredmény |
|---|---|
| `navigator.gpu` | van |
| `navigator.gpu.requestAdapter()` | **nincs adapter** (headless, GPU nélkül) |
| WebGL2 | van |
| WebAssembly a játék oldalán | **CompileError**: a CSP (`script-src 'self' 'unsafe-inline'`) nem engedi |
| WebAssembly CSP nélküli üres lapon | működik (egy 41 bájtos összeadó modul: 2 + 3 = 5) |

**2. Hol megy el az idő?**

- *Képkockánként* (`tools/perf_test.py`, 390×780, 20× lassított processzor, főszál-munka képkockánként,
  teljes effektekkel): Horda 37–48 ms, Kardvihar 33–37 ms, Kőzápor 22–24 ms, Kőkori Kaland 7–11 ms
  (60 fps-sel fut). A munka nagy része Canvas 2D rajzolás (részecskék, szűrők, sok sprite) és egyszerű
  játéklogika. Az adaptív grafika (#51) ugyanitt 20–45%-ot spórolt a Hordában és a Kardviharban, új
  technológia nélkül.
- *Egyszeri számítás* (új pálya, leosztás; a `tools/play_test.py` generátortesztje, lassítás nélkül):
  Pasziánsz leosztás-ellenőrzése átlag 23–368 ms, a leglassabb 930 ms (2 színű pók); Gyémántbánya és
  Kincsvadász 10×10 átlag 50–85 ms, leglassabb ~200 ms; Mahjong legfeljebb 49 ms; Nyilak ~1 ms.
  Ezek nem képkockánként futnak, hanem új játék indításakor egyszer.

**3. Méret:** a legnagyobb játékfájl 106 KB. Egy Wasm-modul egyfájlos játékban csak base64-ként fér el
(+33%), és a forrásához fordító kellene, ami az AGENTS.md szerint tiltott build-lépés.

## Lehetséges előnyök

- WebGPU: sok ezer részecske, 3D vagy shaderes effekt. Jelenleg egyik játéknak sincs rá szüksége, és ahol
  kevés volt a teljesítmény, ott a díszítő rajzolás csökkentése segített.
- WebAssembly: a Pasziánsz-megoldó vagy egy jövőbeli, nagy keresési terű generátor gyorsulhatna. Gyenge
  telefonon a 930 ms-os legrosszabb eset több másodperc is lehet; ezt érdemes valódi eszközön megmérni,
  mielőtt bármit átírunk.

## Kompatibilitási kockázatok

- WebGPU Androidon csak újabb Chrome-mal és megfelelő GPU-meghajtóval érhető el; régebbi telefonokon,
  sok kézikonzolon (régebbi Mali / PowerVR GPU) és korlátozott böngészőkben nem, ezért teljes WebGL2 vagy
  Canvas 2D tartalék kellene, vagyis két rajzoló kód ugyanahhoz.
- A CI-ben (headless) nincs WebGPU-adapter: a WebGPU-ág automatikusan nem tesztelhető.
- WebAssemblyhez a CSP-be `'wasm-unsafe-eval'` kellene; ez a tulajdonos döntése (`CSP_EXTRA`), és gyengíti
  a mostani szigorú szabályt.
- Offline tár: a játékfájllal együtt tárolódna, ez rendben volna; a méretnövekedés a lassú első
  betöltést rontja.
- Karbantartás: egy második nyelv és fordító a tárolóban, amelyet MI-ügynökök és ellenőrző MI-k olvasnak:
  nehezebb átnézni, mint a mostani, egy fájlban olvasható JavaScriptet.

## Javaslat

1. **WebGPU: elhalasztva.** Akkor érdemes újra elővenni, ha egy *új* játék tervéből látszik, hogy a
   Canvas 2D nem elég (pl. 3D), és akkor is csak WebGL2 / Canvas 2D tartalékkal.
2. **WebAssembly: most nem.** Előbb valódi gyenge telefonon kell mérni a Pasziánsz leosztás-ellenőrzését.
   Ha zavaróan lassú, az első lépés a számítás darabolása (a felület ne álljon meg közben), nem a Wasm.
3. **Meglévő játékot nem írunk át** új technológia kedvéért; a teljesítményt az adaptív grafika (#51) és
   a `tools/perf_test.py` mérése kezeli.

# Betűbánya

Blokkos, pixeles stílusú olvasás- és matekgyakorló játék magyarul, lassan olvasó, diszlexiás vagy figyelemzavarral küzdő gyerekeknek és kamaszoknak. Egyetlen HTML fájl, telefonra méretezve.

## Mit tud

- **30 napos kaland**, naponta egy új nap nyílik meg (az első megnyitástól számítva).
- **Olvasás:** napi 5 feladat (feleletválasztás, igaz/hamis, mondatsorrend, hiányzó szó, szó–kép párosítás), 150 rövid szöveg, fokozatosan nehezedve.
- **Matek:** napi 5 feladat (receptek, kötegek, vásárlás, idő, terület, kerület stb.), hatnaponta emelkedő szinttel; a számok minden játéknál újak.
- **Könnyítések:** szótagonként színezett szöveg, állítható betűméret és sorköz, felolvasás (mondatonként is), azonnali visszajelzés, XP és szintek, szünetjavaslat.
- **Olvasóvonalzó:** a 📏 gombbal kapcsolható; egyetlen sort emel ki és a többit halványítja, a ▲/▼ gombokkal vagy a szövegre koppintva mozgatható.
- **Okos ismétlés:** az elrontott feladatok 1, majd 3, majd 7 nap múlva visszatérnek (napi küldetésenként legfeljebb 2), amíg háromszor egymás után elsőre nem sikerülnek.
- **Becenév (nem kötelező):** a Beállításokban megadható, a játék ezzel köszönti a játékost. Csak az adott böngészőben tárolódik.
- **Tanári nézet** PIN kóddal (Beállítások → Tanári nézet): eredmények feladattípusonként, matek témánként, naponként, hibalista, napok feloldása, adatok másolása.

## Használat

Nyisd meg az `index.html`-t böngészőben. A haladás a böngésző helyi tárolójában (localStorage) mentődik, ezért mindig ugyanabban a böngészőben kell játszani.

A tanári PIN-t az első belépéskor kell beállítani. Ha elfelejtődik, a böngésző oldaladatainak törlésével nullázható (a haladás is törlődik).

## Tartalom bővítése

Az olvasási napok az `index.html` elején, az `R(...)` hívásokban vannak; egy új hívás egy új napot ad hozzá. A matek témák a `G` objektumban, a napi témakészletek a `POOLS`-ban vannak. A szövegek szereplői kitaláltak.

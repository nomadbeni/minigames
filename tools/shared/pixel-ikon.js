/* Saját pixelikonok a leggyakoribb emojik helyett, hogy minden eszközön egyformán nézzenek ki.
   A felület szövegében (nem a canvasra rajzolt képen) az ismert emojit egy kis, élesen nagyított képre cseréli.
   Ha a gombnak vagy elemnek nincs más szövege és aria-label-je, a kép kap egy rövid magyar nevet. */
(function(){
  var ICONS={
    spk:['Hang',['............','.....k......','....kk...w..','kkkkgk.w..w.','kggggk..w.w.','kggggk..w.w.','kggggk..w.w.','kkkkgk.w..w.','....kk...w..','.....k......','............','............'],{k:'#8a93a3',g:'#d8dde6',w:'#7fdcff'}],
    mute:['Némítva',['............','.....k......','....kk......','kkkkgk.r...r','kggggk..r.r.','kggggk...r..','kggggk..r.r.','kkkkgk.r...r','....kk......','.....k......','............','............'],{k:'#8a93a3',g:'#d8dde6',r:'#ff4d5a'}],
    gear:['Beállítások',['....gggg....','..g.gGGg.g..','.gggGGGGggg.','..gGGggGGg..','ggGGg..gGGgg','gGGg....gGGg','gGGg....gGGg','ggGGg..gGGgg','..gGGggGGg..','.gggGGGGggg.','..g.gGGg.g..','....gggg....'],{g:'#8a93a3',G:'#cfd6de'}],
    coin:['Érme',['....yyyy....','..yyYYYYyy..','.yYYyyyyYYy.','.yYyYYYYyYy.','yYyYYyyYYyYy','yYyYyYYyYyYy','yYyYyYYyYyYy','yYyYYyyYYyYy','.yYyYYYYyYy.','.yYYyyyyYYy.','..yyYYYYyy..','....yyyy....'],{y:'#c9931e',Y:'#ffd23f'}],
    trophy:['Kupa',['.YYYYYYYYYY.','YyYYYYYYYYyY','Y.YYYYYYYY.Y','Y.YYYwYYYY.Y','.YYYYwYYYYY.','..YYYYYYYY..','...YYYYYY...','.....YY.....','.....YY.....','....yyyy....','...kkkkkk...','...kkkkkk...'],{Y:'#ffd23f',y:'#c9931e',w:'#fff6c0',k:'#8a5a2a'}],
    heart:['Szív',['............','..rr....rr..','.rRRr..rrrr.','.rRrrrrrrrr.','.rrrrrrrrrr.','.rrrrrrrrrr.','..rrrrrrrr..','...rrrrrr...','....rrrr....','.....rr.....','............','............'],{r:'#ff3b5c',R:'#ffb3c0'}],
    star:['Csillag',['.....yy.....','.....yy.....','....yyyy....','yyyyyYYyyyyy','.yyyYYYYyyy.','..yyYYYYyy..','...yyyyyy...','...yyyyyy...','..yyy..yyy..','..yy....yy..','.yy......yy.','............'],{y:'#ffc83d',Y:'#fff0a0'}],
    lock:['Zárva',['....kkkk....','...k....k...','...k....k...','...k....k...','..yyyyyyyy..','..yYYYYYYy..','..yYYhhYYy..','..yYYhhYYy..','..yYYYhYYy..','..yYYYYYYy..','..yyyyyyyy..','............'],{k:'#a8b0bc',y:'#c9931e',Y:'#ffd23f',h:'#4a3a10'}],
    bolt:['Villám',['.......yyy..','......yyy...','.....yyy....','....yyy.....','...yyyyyyy..','......yyy...','.....yyy....','....yyy.....','...yyy......','..yy........','.y..........','............'],{y:'#ffd23f'}],
    box:['Láda',['............','..bbbbbbbb..','.bBBBBBBBBb.','bbbbbbbbbbbb','bBBBBttBBBBb','bBBBBttBBBBb','bBBBBBBBBBBb','bBBBBBBBBBBb','bBBBBBBBBBBb','bbbbbbbbbbbb','............','............'],{b:'#8a5a2a',B:'#c58e4c',t:'#e8c48a'}],
    pick:['Csákány',['..ssssss....','.s......s...','s...bb...s..','....bb......','.....bb.....','.....bb.....','......bb....','......bb....','.......bb...','.......bb...','........bb..','............'],{s:'#cfd6de',b:'#a8743a'}],
    sun:['Nap',['.....yy.....','.y...yy...y.','..y......y..','....yyyy....','...yYYYYy...','yy.yYYYYy.yy','yy.yYYYYy.yy','...yYYYYy...','....yyyy....','..y......y..','.y...yy...y.','.....yy.....'],{y:'#ffb020',Y:'#ffe066'}],
    wrench:['Szerszám',['........ss..','.......s..s.','........s.s.','.......sss..','......ss....','.....ss.....','....ss......','...ss.......','..ss........','.ss.........','.s..........','............'],{s:'#cfd6de'}],
    bag:['Táska',['....bbbb....','...b....b...','..gggggggg..','.gGGGGGGGGg.','.gGGGGGGGGg.','.gggggggggg.','.gGGGyyGGGg.','.gGGGGGGGGg.','.gGGGGGGGGg.','.gggggggggg.','............','............'],{b:'#a8743a',g:'#2f6a3a',G:'#4a9a5a',y:'#ffd23f'}],
    compass:['Iránytű',['....cccc....','..cc....cc..','.c...r....c.','.c..rr....c.','c...rr.....c','c...wWw....c','c....ww....c','c....ww....c','.c...w....c.','.c........c.','..cc....cc..','....cccc....'],{c:'#c9931e',r:'#ff3b5c',w:'#e8e8f0',W:'#ffffff'}],
    shield:['Pajzs',['.bbbbbbbbbb.','.bBBBBbbbbb.','.bBBBBbbbbb.','.bBBBBbbbbb.','.bbbbbbbbbb.','.bbbbbBBBBb.','.bbbbbBBBBb.','..bbbbBBBb..','...bbbbbb...','....bbbb....','.....bb.....','............'],{b:'#2f6bff',B:'#9fc0ff'}],
    gem:['Gyémánt',['............','...cccccc...','..cWWcccCc..','.cWcccccccC.','cCCCCCCCCCCc','.cccccccccc.','..cccccccc..','...cccccc...','....cccc....','.....cc.....','............','............'],{c:'#3fd2bb',C:'#1f9a8a',W:'#e8fffb'}],
    key:['Kulcs',['............','............','..yyy.......','.y...y......','.y...yyyyyyy','.y...y..y.y.','..yyy...y.y.','............','............','............','............','............'],{y:'#ffd23f'}],
    fire:['Tűz',['.....r......','....rr......','....rrr..r..','...rrorr.r..','..rrooorrr..','..rooyyorr..','.rroyyyyorr.','.rooyyyyoor.','.rooyyyyoor.','..rooyyoor..','...roooor...','....rrrr....'],{r:'#e5301a',o:'#ff7a1a',y:'#ffe04a'}],
    bomb:['Bomba',['.........y..','........y.y.','.......k....','......k.....','...kkkk.....','..kkkkkk....','.kkwkkkkk...','.kwkkkkkk...','.kkkkkkkk...','.kkkkkkkk...','..kkkkkk....','...kkkk.....'],{k:'#3a3a48',w:'#9aa3b0',y:'#ffd23f'}],
    trash:['Törlés',['....kkkk....','.kkkkkkkkkk.','............','..gggggggg..','..gGgGgGgg..','..gGgGgGgg..','..gGgGgGgg..','..gGgGgGgg..','..gGgGgGgg..','..gggggggg..','............','............'],{k:'#8a93a3',g:'#5a6270',G:'#a8b0bc'}],
    robot:['Robot',["....rr......", "....gg......", "..gggggggg..", "..gwwggwwg..", "..gwkggwkg..", "..gggggggg..", "..gggrrggg..", "..gggggggg..", "...gg..gg...", "..gggggggg..", "..g.g..g.g..", "............"],{'r':'#ff4d5a','g':'#9aa3ad','w':'#ffffff','k':'#1a1a1a'}],
    swirl:['Vihar',["...pppppp...", "..p......p..", ".p..pppp..p.", ".p.p....p.p.", ".p.p.pp.p.p.", ".p.p.p..p.p.", ".p.p..pp..p.", ".p..p.....p.", "..p..pppp.p.", "...p......p.", "....pppppp..", "............"],{'p':'#b46bff'}],
    shoe:['Cipő',["............", "............", "....bbb.....", "...bbbb.....", "...bwbbb....", "...bbbbbb...", "..bbbwwbbbb.", "..bbbbbbbbbb", "..kkkkkkkkkk", "............", "............", "............"],{'b':'#3a7ae8','w':'#ffffff','k':'#1a1a1a'}],
    rocket:['Rakéta',[".....rr.....", "....rwwr....", "....wwww....", "....wbbw....", "....wbbw....", "....wwww....", "...rwwwwr...", "..rrwwwwrr..", "....oyyo....", ".....oo.....", ".....y......", "............"],{'r':'#e53935','w':'#e8e8f0','b':'#4aa3e8','o':'#ff7a1a','y':'#ffe04a'}],
    magnet:['Mágnes',["ww......ww..", "ww......ww..", "rr......rr..", "rr......rr..", "rr......rr..", "rr......rr..", "rrr....rrr..", ".rrrrrrrr...", "..rrrrrr....", "............", "............", "............"],{'r':'#e53935','w':'#e8e8f0'}],
    pad:['Kontroller',["............", "............", "..kkkkkkkk..", ".kggggggggk.", "kggwggggrggk", "kgwwwgggggbk", "kggwggyggggk", "kggggggggggk", ".kggk..kggk.", "..kk....kk..", "............", "............"],{'k':'#2a2a35','g':'#8a8a9a','w':'#e8e8f0','r':'#ff4d5a','b':'#4aa3e8','y':'#ffd23f'}],
    target:['Cél',["....rrrr....", "..rrwwwwrr..", ".rwwrrrrwwr.", ".rwrrwwrrwr.", "rwrrwrrwrrwr", "rwrwrrrrwrwr", "rwrwrrrrwrwr", "rwrrwrrwrrwr", ".rwrrwwrrwr.", ".rwwrrrrwwr.", "..rrwwwwrr..", "....rrrr...."],{'r':'#e53935','w':'#ffffff'}],
    flag:['Célzászló',["k...........", "kwwkkwwkkww.", "kwwkkwwkkww.", "kkkwwkkwwkk.", "kkkwwkkwwkk.", "kwwkkwwkkww.", "kwwkkwwkkww.", "k...........", "k...........", "k...........", "k...........", "............"],{'k':'#1a1a1a','w':'#ffffff'}],
    mud:['Sár',["............", ".bbbbbbbbbb.", ".bBbbbbbBbb.", ".bbbbBbbbbb.", ".bbbbbbbbbb.", ".bbBbbbbbBb.", ".bbbbbbBbbb.", ".bBbbbbbbbb.", ".bbbbbBbbbb.", ".bbbbbbbbbb.", "............", "............"],{'b':'#7a5230','B':'#5a3a20'}],
    crash:['Ütközés',[".....y......", "..y..yy..y..", "...yyooyy...", "y..yorroy..y", ".yyorrrroyy.", "..yorrrroy..", "..yorrrroy..", ".yyorrrroyy.", "y..yorroy..y", "...yyooyy...", "..y..yy..y..", ".....y......"],{'y':'#ffe04a','o':'#ff7a1a','r':'#e53935'}],
    sign:['Tábla',["............", "bbbbbbbbbbbb", "bwwwwwwwwwwb", "bwkkwkkkwwwb", "bwwwwwwwwwwb", "bwkkkwkkwwwb", "bwwwwwwwwwwb", "bbbbbbbbbbbb", ".....bb.....", ".....bb.....", ".....bb.....", "............"],{'b':'#8a5a2a','w':'#f4e6c4','k':'#5a4a3a'}],
    calendar:['Nap',["..k....k....", ".rrrrrrrrrr.", ".rrrrrrrrrr.", ".wwwwwwwwww.", ".wkwkwkwkww.", ".wwwwwwwwww.", ".wkwkwrrkww.", ".wwwwwrrwww.", ".wkwkwkwkww.", ".wwwwwwwwww.", "............", "............"],{'k':'#5a6270','r':'#e53935','w':'#f2f2f2'}],
    cart:['Bolt',["k...........", ".k..........", ".kkkkkkkkkk.", ".k.g.g.g.gk.", ".kkkkkkkkk..", ".k.g.g.g.k..", ".kkkkkkkk...", ".k..........", ".kkkkkkkk...", "..o....o....", "............", "............"],{'k':'#cfd6de','g':'#7a8494','o':'#8a93a3'}],
    house:['Műhely',[".....rr.....", "....rrrr....", "...rrrrrr...", "..rrrrrrrr..", ".rrrrrrrrrr.", "..wwwwwwww..", "..wbbwwbbw..", "..wbbwwbbw..", "..wwwkkwww..", "..wwwkkwww..", "..wwwkkwww..", "............"],{'r':'#c62828','w':'#f4e6c4','b':'#4aa3e8','k':'#8a5a2a'}],
    bike:['Bringa',["............", "......kk....", ".......k....", "...rrrrr....", "..r.r..r....", "kkk.r..rkkk.", "k..kr..k..k.", "k.k.rrk...k.", "k..k...k..k.", "kkk.....kkk.", "............", "............"],{'k':'#cfd6de','r':'#e84a5f'}],
    wheel:['Gumi',["....kkkk....", "..kkkkkkkk..", ".kkkgggkkkk.", ".kkg...gkkk.", "kkg.....gkkk", "kkg..s..gkkk", "kkg.....gkkk", ".kkg...gkkk.", ".kkkgggkkkk.", "..kkkkkkkk..", "....kkkk....", "............"],{'k':'#3a3a48','g':'#8a8a9a','s':'#cfd6de'}],
    warn:['Figyelem',[".....yy.....", "....yyyy....", "....yyyy....", "...yykkyy...", "...yykkyy...", "..yyykkyyy..", "..yyykkyyy..", ".yyyyyyyyyy.", ".yyyykkyyyy.", "yyyyyyyyyyyy", "yyyyyyyyyyyy", "............"],{'y':'#ffc83d','k':'#1a1a1a'}],
    speech:['Beszéd',["............", ".wwwwwwwwww.", "wwwwwwwwwwww", "wwkwwkwwkwww", "wwwwwwwwwwww", ".wwwwwwwwww.", "..www.......", "..ww........", "..w.........", "............", "............", "............"],{'w':'#e8f6ff','k':'#4a5a6a'}],
    point:['Koppints',[".....s......", "....sSs.....", "....sSs.....", "....sSs.....", "....sSsss...", "....sSsSss..", "..s.sSsSsSs.", "..sssSSSSSs.", "..sSSSSSSSs.", "...sSSSSSs..", "....sSSSs...", "............"],{'s':'#c98a5a','S':'#f0c39a'}],
    corn:['Kukorica',[".....yy.....", "....yYyy....", "....yyYy....", "....yYyy....", "..g.yyYy.g..", "..gg.yYy.gg.", "...gg.yy.g..", "...ggg.ggg..", "....gggg....", ".....gg.....", ".....gg.....", "............"],{'y':'#ffd23f','Y':'#ffb020','g':'#3a9a3a'}],
    bulb:['Ötlet',["....yyyy....", "...yYYYYy...", "..yYYwYYYy..", "..yYwYYYYy..", "..yYYYYYYy..", "...yYYYYy...", "....yYYy....", "....ssss....", "....ssss....", ".....ss.....", "............", "............"],{'y':'#ffb020','Y':'#ffe066','w':'#ffffff','s':'#9aa3ad'}],
    cycle:['Újra',["....bbbb....", "..bb....bbb.", ".b.......bb.", "b.......bbb.", "b...........", "b..........b", "b..........b", "...........b", ".bbb.......b", ".bb.......b.", ".bbb....bb..", "....bbbb...."],{'b':'#4aa3e8'}],
    chart:['Statisztika',["............", "..........k.", "........r.k.", "........r.k.", "....g...r.k.", "....g...r.k.", "..b.g.y.r.k.", "..b.g.y.r.k.", "..b.g.y.r.k.", "kkkkkkkkkkk.", "............", "............"],{'k':'#8a93a3','b':'#4aa3e8','g':'#3ddc84','y':'#ffd23f','r':'#ff4d5a'}],
    skull:['Halál',["...wwwwww...", "..wwwwwwww..", ".wwwwwwwwww.", ".wkkwwwwkkw.", ".wkkwwwwkkw.", ".wwwwkkwwww.", "..wwwwwwww..", "...wkwkwk...", "...wwwwww...", "............", "............", "............"],{'w':'#e8e8f0','k':'#1a1a1a'}],
    helmet:['Katona',["............", "....gggg....", "..ggGGgggg..", ".gGGgggggggg", ".ggggggggggg", "gggggggggggg", "kkkkkkkkkkkk", "............", "............", "............", "............", "............"],{'g':'#4a6a3a','G':'#7a9a5a','k':'#2a3a20'}],
    wave:['Hullám',["............", "......bbb...", "....bbwwbb..", "...bbw..wb..", "..bbw....b..", "..bw...bb...", ".bbb.bbbb...", "bbbbbbbbbbbb", "bBbbbBbbbBbb", "bbbbbbbbbbbb", "bBbbbBbbbBbb", "............"],{'b':'#2f7ad0','B':'#5ab0ff','w':'#e8f6ff'}],
    door:['Ajtó',["..bbbbbbbb..", "..bBBBBBBb..", "..bBbbbbBb..", "..bBbbbbBb..", "..bBBBBBBb..", "..bBbbbbBb..", "..bBbbbyBb..", "..bBbbbbBb..", "..bBbbbbBb..", "..bBBBBBBb..", "..bbbbbbbb..", "............"],{'b':'#8a5a2a','B':'#b07a40','y':'#ffd23f'}],
    zombie:['Zombi',["...gggggg...", "..gggggggg..", "..gkkggkkg..", "..gggggggg..", "..ggkkkkgg..", "...gggggg...", "gg.bbbbbb.gg", ".gbbbbbbbbg.", "...bbbbbb...", "...bb..bb...", "...gg..gg...", "............"],{'g':'#7ab85a','k':'#2a3a20','b':'#5a4a7a'}],
    potion:['Ital',[".....kk.....", ".....ww.....", ".....ww.....", "....wwww....", "...wggggw...", "..wggGgggw..", "..wgggggggw.", "..wggggGggw.", "..wggggggw..", "...wwwwww...", "............", "............"],{'k':'#8a5a2a','w':'#cfe8ff','g':'#3ddc84','G':'#c6ffd9'}],
    scroll:['Küldetés',["..pppppppp..", ".pPPPPPPPPp.", "..pkkkkkkp..", "..pPPPPPPp..", "..pkkkkkPp..", "..pPPPPPPp..", "..pkkkkkkp..", "..pPPPPPPp..", ".pPPPPPPPPp.", "..pppppppp..", "............", "............"],{'p':'#c9a36a','P':'#f4e6c4','k':'#8a6a3a'}],
    swords:['Harc',["s..........s", ".s........s.", "..s......s..", "...s....s...", "....s..s....", ".....ss.....", ".....ss.....", "....b..b....", "...b....b...", "..y......y..", ".y........y.", "............"],{'s':'#e8e8f0','b':'#a8743a','y':'#ffd23f'}],
    run:['Futás',["......kk....", "......kk....", "....bbb.....", "...bbbbbb...", "..b.bbb..b..", "....bbb.....", "....b..bb...", "...b.....b..", "..b......b..", ".k.......k..", "............", "............"],{'k':'#f0c39a','b':'#3ddc84'}],
    excl:['Feladat',[".....rr.....", "....rrrr....", "....rrrr....", "....rrrr....", ".....rr.....", ".....rr.....", ".....rr.....", "............", ".....rr.....", "....rrrr....", ".....rr.....", "............"],{'r':'#ff4d5a'}],
    quest:['Kérdés',["...rrrrr....", "..rr...rr...", "..rr...rr...", ".......rr...", "......rr....", ".....rr.....", ".....rr.....", "............", ".....rr.....", ".....rr.....", "............", "............"],{'r':'#ff4d5a'}],
    picture:['Kép',["bbbbbbbbbbbb", "bsssssssssyb", "bssssssssssb", "bssssssssssb", "bsssggsssssb", "bssggggssssb", "bsggggggsggb", "bggggggggggb", "bggggggggggb", "bbbbbbbbbbbb", "............", "............"],{'b':'#8a5a2a','s':'#9fd0ff','y':'#ffd23f','g':'#3a9a3a'}],
    shovel:['Ásó',[".........bb.", "........bb..", ".......bb...", "......bb....", ".....bb.....", "....bb......", "..sss.......", ".sssss......", ".sssss......", "..sss.......", "...s........", "............"],{'b':'#a8743a','s':'#cfd6de'}],
    card:['Kártya',["..wwwwwwww..", "..wrwwwwww..", "..wwwwwwww..", "..wwwrrwww..", "..wwrrrrww..", "..wwwrrwww..", "..wwwwwwww..", "..wwwwwwrw..", "..wwwwwwww..", "............", "............", "............"],{'w':'#f4f4f8','r':'#e53935'}],
    sunflower:['Napraforgó',["...y.yy.y...", "..yyyyyyyy..", ".yyybbbbyyy.", "yyybbbbbbyyy", ".yybbbbbbyy.", "yyybbbbbbyyy", ".yyybbbbyyy.", "..yyyyyyyy..", "...y.gg.y...", "....ggg.....", ".....gg.....", "............"],{'y':'#ffc83d','b':'#7a4a1a','g':'#3a9a3a'}],
    abc:['Szótagok',["bbbbbbbbbbbb", "bwwwwwwwwwwb", "bwkwwkkwwkwb", "bkwkwkwkwkwb", "bkkkwkkwwkwb", "bkwkwkwkwkwb", "bkwkwkkwwkwb", "bwwwwwwwwwwb", "bbbbbbbbbbbb", "............", "............", "............"],{'b':'#4aa3e8','w':'#e8f6ff','k':'#1a3a5a'}],
    factory:['Farm',["kk..........", "kk..........", "kk..........", "kk.r..r.....", "kkrrrrrrrrr.", "krrrrrrrrrr.", "rrwwrrwwrrr.", "rrwwrrwwrrr.", "rrrrrrrrrrr.", "rrrrrkkrrrr.", "rrrrrkkrrrr.", "............"],{'k':'#8a93a3','r':'#a8432a','w':'#ffe066'}],
    bricks:['Új föld',["rrrrrkrrrrrk", "rrrrrkrrrrrk", "kkkkkkkkkkkk", "rrkrrrrrkrrr", "rrkrrrrrkrrr", "kkkkkkkkkkkk", "rrrrrkrrrrrk", "rrrrrkrrrrrk", "kkkkkkkkkkkk", "rrkrrrrrkrrr", "rrkrrrrrkrrr", "............"],{'r':'#c0573a','k':'#7a3a28'}],
    sprout:['Mag',["............", "..gg....gg..", ".gGGg..gGGg.", ".gGGGggGGGg.", "..gggggggg..", ".....gg.....", ".....gg.....", ".....gg.....", "...bbbbbb...", "..bbbbbbbb..", "............", "............"],{'g':'#2f8a3a','G':'#5ad06a','b':'#7a5230'}],
    clip:['Szerződés',["....kkkk....", "..bbkkkkbb..", "..bwwwwwwb..", "..bwkkkkwb..", "..bwwwwwwb..", "..bwkkkwwb..", "..bwwwwwwb..", "..bwkkkkwb..", "..bwwwwwwb..", "..bbbbbbbb..", "............", "............"],{'k':'#8a93a3','b':'#a8743a','w':'#f4f4f8'}],
    drop:['Öntözés',[".....bb.....", ".....bb.....", "....bbbb....", "....bbbb....", "...bbbbbb...", "..bbwbbbbb..", "..bwbbbbbb..", "..bwbbbbbb..", "..bbbbbbbb..", "...bbbbbb...", "....bbbb....", "............"],{'b':'#3a8ae8','w':'#cfe8ff'}],
    face:['Élet',["...yyyyyy...", "..yyyyyyyy..", ".yyyyyyyyyy.", ".yykyyyykyy.", ".yykyyyykyy.", ".yyyyyyyyyy.", ".ykyyyyyykyy", ".yykyyyykyy.", ".yyykkkkyyy.", "..yyyyyyyy..", "...yyyyyy...", "............"],{'y':'#ffd23f','k':'#5a3a10'}],
    meat:['Pont',["............", "......rrrr..", ".....rRRrrr.", "....rRrrrrrr", "....rrrrrrrr", "...rrrrrrrr.", "..wbrrrrrr..", ".wwbbrrr....", "ww.b........", "w...........", "............", "............"],{'r':'#c0573a','R':'#e8906a','w':'#f4f4f8','b':'#d9c8bd'}],
    pause:['Szünet',["............", "............", "...ww..ww...", "...ww..ww...", "...ww..ww...", "...ww..ww...", "...ww..ww...", "...ww..ww...", "...ww..ww...", "...ww..ww...", "............", "............"],{'w':'#e8e8f0'}],
    timer:['Idő',["....kkkk....", ".....kk.....", "...wwwwww...", "..wwwwwwww..", ".wwwwkwwwww.", ".wwwwkwwwww.", ".wwwwkkkwww.", ".wwwwwwwwww.", ".wwwwwwwwww.", "..wwwwwwww..", "...wwwwww...", "............"],{'k':'#ff4d5a','w':'#e8e8f0'}],
    left:['Vissza',["............", "....w.......", "...ww.......", "..www.......", ".wwwwwwwwww.", "wwwwwwwwwww.", ".wwwwwwwwww.", "..www.......", "...ww.......", "....w.......", "............", "............"],{'w':'#e8e8f0'}],
    cross:['Nem',["............", ".rr......rr.", ".rrr....rrr.", "..rrr..rrr..", "...rrrrrr...", "....rrrr....", "....rrrr....", "...rrrrrr...", "..rrr..rrr..", ".rrr....rrr.", ".rr......rr.", "............"],{'r':'#ff4d5a'}],
    scissors:['Rövidítés',["s.........s.", "ss.......ss.", ".ss.....ss..", "..ss...ss...", "...ss.ss....", "....sss.....", "....rrr.....", "...r...r....", "..r.....r...", ".r.......r..", "..r.....r...", "............"],{'s':'#cfd6de','r':'#ff4d5a'}],
    book:['Olvasás',["............", ".bbbbb.bbbbb", "bwwwwwbwwwwb", "bwkkkwbwkkwb", "bwwwwwbwwwwb", "bwkkkwbwkkkb", "bwwwwwbwwwwb", "bwkkwwbwkkwb", "bwwwwwbwwwwb", ".bbbbbbbbbb.", "............", "............"],{'b':'#c0573a','w':'#f4f4f8','k':'#8a93a3'}],
    numbers:['Matek',["bbbbbbbbbbbb", "bwwwwwwwwwwb", "bwwkwkkwkkwb", "bwkkwwkwwkwb", "bwwkwkwwwkwb", "bwwkwkwwkwwb", "bwwkwkkwkkwb", "bwwwwwwwwwwb", "bbbbbbbbbbbb", "............", "............", "............"],{'b':'#4aa3e8','w':'#e8f6ff','k':'#1a3a5a'}],
    hello:['Szia',["..s.s.......", ".sSsSs.s....", ".sSsSsSs....", ".sSsSsSs.s..", ".sSSSSSSsSs.", ".sSSSSSSSSs.", ".sSSSSSSSs..", "..sSSSSSSs..", "...sSSSSs...", "....ssss....", "............", "............"],{'s':'#c98a5a','S':'#f0c39a'}]
  };
  var MAP={'\u{1F50A}':'spk','\u{1F508}':'spk','\u{1F509}':'spk','\u{1F507}':'mute','⚙':'gear','\u{1FA99}':'coin','\u{1F3C6}':'trophy',
    '❤':'heart','⭐':'star','\u{1F512}':'lock','⚡':'bolt','\u{1F4E6}':'box','⛏':'pick','☀':'sun','\u{1F527}':'wrench',
    '\u{1F392}':'bag','\u{1F9ED}':'compass','\u{1F6E1}':'shield','\u{1F48E}':'gem','\u{1F511}':'key','\u{1F525}':'fire','\u{1F4A3}':'bomb','\u{1F5D1}':'trash',
    '\u{1F916}':'robot','\u{1F300}':'swirl','\u{1F45F}':'shoe','\u{1F680}':'rocket','\u{1F9F2}':'magnet','\u{1F579}':'pad','\u{1F3AE}':'pad','\u{1F3AF}':'target','\u{1F3C1}':'flag','\u{1F7EB}':'mud','\u{1F4A5}':'crash','\u{1FAA7}':'sign','\u{1F4C5}':'calendar','\u{1F6D2}':'cart','\u{1F3E0}':'house','\u{1F6B2}':'bike','\u{1F6DE}':'wheel','\u{26A0}':'warn','\u{1F4AC}':'speech','\u{1F446}':'point','\u{1F33D}':'corn','\u{1F4A1}':'bulb','\u{1F504}':'cycle','\u{1F4CA}':'chart','\u{1F480}':'skull','\u{1FA96}':'helmet','\u{1F30A}':'wave','\u{1F6AA}':'door','\u{1F9DF}':'zombie','\u{1F9EA}':'potion','\u{1F4DC}':'scroll','\u{2694}':'swords','\u{1F3C3}':'run','\u{2757}':'excl','\u{2753}':'quest','\u{1F5BC}':'picture','\u{1FA8F}':'shovel','\u{1F0CF}':'card','\u{1F33B}':'sunflower','\u{1F524}':'abc','\u{1F3ED}':'factory','\u{1F9F1}':'bricks','\u{1F331}':'sprout','\u{1F4CB}':'clip','\u{1F4A7}':'drop','\u{1F642}':'face','\u{1F356}':'meat',
    '\u{23F8}':'pause','\u{23F1}':'timer','\u{23F0}':'timer','\u{2B05}':'left','\u{274C}':'cross',
    '\u{2702}':'scissors',
    '\u{1F4D6}':'book','\u{1F522}':'numbers','\u{1F44B}':'hello'};
  var RE=new RegExp('('+Object.keys(MAP).join('|')+')\\uFE0F?','u'),REG=new RegExp(RE.source,'gu');
  var urls={};
  function url(n){
    if(urls[n])return urls[n];
    var d=ICONS[n],c=document.createElement('canvas');c.width=12;c.height=12;var g=c.getContext('2d');
    d[1].forEach(function(row,y){for(var x=0;x<row.length;x++){var ch=row[x];if(ch!=='.'){g.fillStyle=d[2][ch];g.fillRect(x,y,1,1)}}});
    return urls[n]=c.toDataURL();
  }
  var SKIP={SCRIPT:1,STYLE:1,TEXTAREA:1,INPUT:1,OPTION:1,SELECT:1,CANVAS:1,TITLE:1,svg:1};
  function fix(node){
    var t=node.nodeValue;if(!t||!RE.test(t))return;
    var p=node.parentNode;if(!p||SKIP[p.nodeName]||(p.closest&&p.closest('[data-no-pxi]')))return;
    var host=p.closest?p.closest('button,a,[role=button]')||p:p;
    var labelled=host.getAttribute&&host.getAttribute('aria-label');
    var bare=!t.replace(REG,'').trim()&&!(host.textContent||'').replace(REG,'').trim();
    var f=document.createDocumentFragment(),last=0;REG.lastIndex=0;var m;
    while((m=REG.exec(t))){
      if(m.index>last)f.appendChild(document.createTextNode(t.slice(last,m.index)));
      var n=MAP[m[1]],im=document.createElement('img');
      im.className='pxi';im.src=url(n);im.alt=(bare&&!labelled)?ICONS[n][0]:'';if(!im.alt)im.setAttribute('aria-hidden','true');
      f.appendChild(im);last=REG.lastIndex;
    }
    if(last<t.length)f.appendChild(document.createTextNode(t.slice(last)));
    p.replaceChild(f,node);
  }
  function walk(root){
    if(root.nodeType===3){fix(root);return}
    if(root.nodeType!==1||SKIP[root.nodeName])return;
    var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),list=[],n;
    while((n=w.nextNode()))if(RE.test(n.nodeValue))list.push(n);
    list.forEach(fix);
  }
  var st=document.createElement('style');
  st.textContent='img.pxi{display:inline-block;width:1.15em;height:1.15em;vertical-align:-.2em;image-rendering:pixelated;image-rendering:crisp-edges}';
  document.head.appendChild(st);
  walk(document.body);
  try{new MutationObserver(function(ms){ms.forEach(function(m){
    if(m.type==='characterData')fix(m.target);else m.addedNodes.forEach(walk);
  })}).observe(document.body,{childList:true,subtree:true,characterData:true})}catch(e){}
})();

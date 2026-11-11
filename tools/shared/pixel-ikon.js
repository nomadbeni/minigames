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
    trash:['Törlés',['....kkkk....','.kkkkkkkkkk.','............','..gggggggg..','..gGgGgGgg..','..gGgGgGgg..','..gGgGgGgg..','..gGgGgGgg..','..gGgGgGgg..','..gggggggg..','............','............'],{k:'#8a93a3',g:'#5a6270',G:'#a8b0bc'}]
  };
  var MAP={'\u{1F50A}':'spk','\u{1F508}':'spk','\u{1F509}':'spk','\u{1F507}':'mute','⚙':'gear','\u{1FA99}':'coin','\u{1F3C6}':'trophy',
    '❤':'heart','⭐':'star','\u{1F512}':'lock','⚡':'bolt','\u{1F4E6}':'box','⛏':'pick','☀':'sun','\u{1F527}':'wrench',
    '\u{1F392}':'bag','\u{1F9ED}':'compass','\u{1F6E1}':'shield','\u{1F48E}':'gem','\u{1F511}':'key','\u{1F525}':'fire','\u{1F4A3}':'bomb','\u{1F5D1}':'trash'};
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

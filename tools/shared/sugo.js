/* Egységes „Hogyan kell?” súgó. A felső sávba (.top-bar) egy „?” gombot tesz; az ablakban a játék saját
   vezérlése látszik három fülön: Érintés, Billentyű, Kontroller. Az a fül nyílik meg, amivel épp játszanak.
   A játék a blokk ELŐTT megadja a tartalmat, soronként [jel, rövid szöveg]:
     window.SUGO={
       erinto:[['👆','Húzd az ujjad: mozgás']],
       gep:[['← →','mozgás'],['Szóköz','ugrás']],
       kontroller:[['Kar','mozgás'],['A','ugrás'],['Start','szünet']]
     };
   Megnyitáskor a játék a saját szünet-logikájával megáll (ugyanaz fut le, mint amikor a lap háttérbe kerül).
   Billentyűvel a ? nyitja, az Esc zárja; kontrollerrel a Start zárja. A szöveg textContent-tel kerül ki. */
(function(){
  var d=document,S=window.SUGO;
  if(!S||typeof S!=='object')return;
  var TABS=[['erinto','👆','Érintés'],['gep','⌨️','Billentyű'],['kontroller','🎮','Kontroller']];
  function rows(k){var r=S[k];return Array.isArray(r)?r.filter(function(x){return Array.isArray(x)&&x.length===2&&String(x[0])&&String(x[1])}):[]}
  var tabs=TABS.filter(function(t){return rows(t[0]).length});
  if(!tabs.length)return;
  var st=d.createElement('style');
  st.textContent='.sugo-btn{all:unset;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;'+
    'min-height:44px;min-width:44px;padding:6px 10px;border-radius:999px;border:1px solid currentColor;color:inherit;opacity:.75;'+
    'cursor:pointer;font:800 20px/1 system-ui,sans-serif}.sugo-btn:focus-visible{outline:3px solid #ffd23f;outline-offset:2px}'+
    'dialog.sugo{box-sizing:border-box;width:min(400px,calc(100vw - 16px));max-width:none;max-height:calc(100dvh - 16px);margin:auto;'+
    'padding:16px;border:2px solid #3b4660;border-radius:16px;background:#10141f;color:#fff;overflow:auto;'+
    'font:400 18px/1.35 Lexend,system-ui,sans-serif;z-index:4000}dialog.sugo::backdrop{background:rgba(0,0,0,.7)}'+
    'dialog.sugo h2{margin:0 0 12px;font-size:22px;font-weight:700}'+
    'dialog.sugo .sugo-tabs{display:flex;gap:6px;margin-bottom:12px}'+
    'dialog.sugo .sugo-tabs button{all:unset;box-sizing:border-box;flex:1;min-height:48px;padding:4px 6px;border-radius:10px;'+
    'border:2px solid #3b4660;text-align:center;cursor:pointer;font:600 15px/1.15 Lexend,system-ui,sans-serif;color:#cfd6e6}'+
    'dialog.sugo .sugo-tabs button span{display:block;font-size:20px}'+
    'dialog.sugo .sugo-tabs button[aria-selected="true"]{background:#2a6df4;border-color:#2a6df4;color:#fff}'+
    'dialog.sugo button:focus-visible{outline:3px solid #ffd23f;outline-offset:2px}'+
    'dialog.sugo dl{display:grid;grid-template-columns:auto 1fr;gap:10px 12px;align-items:center;margin:0 0 16px}'+
    'dialog.sugo dt{justify-self:start;min-width:44px;padding:4px 8px;border-radius:8px;background:#26304a;border:1px solid #4a5878;'+
    'text-align:center;font-weight:700;white-space:nowrap}dialog.sugo dd{margin:0}'+
    'dialog.sugo .sugo-ok{all:unset;box-sizing:border-box;display:block;width:100%;min-height:48px;padding:10px;border-radius:12px;'+
    'background:#ffd23f;color:#1a1a1a;text-align:center;cursor:pointer;font:700 18px/1.2 Lexend,system-ui,sans-serif}';
  d.head.appendChild(st);
  var dlg=d.createElement('dialog');dlg.className='sugo';dlg.setAttribute('aria-labelledby','sugo-cim');
  var h=d.createElement('h2');h.id='sugo-cim';h.textContent='❓ Hogyan kell?';dlg.appendChild(h);
  var bar=d.createElement('div');bar.className='sugo-tabs';bar.setAttribute('role','tablist');
  var list=d.createElement('dl');list.setAttribute('role','tabpanel');
  var ok=d.createElement('button');ok.type='button';ok.className='sugo-ok hot';ok.textContent='Értem';
  var cur=null,btns={};
  function show(k){
    cur=k;
    tabs.forEach(function(t){btns[t[0]].setAttribute('aria-selected',t[0]===k?'true':'false')});
    list.textContent='';
    rows(k).forEach(function(r){
      var dt=d.createElement('dt'),dd=d.createElement('dd');dt.textContent=String(r[0]);dd.textContent=String(r[1]);
      list.appendChild(dt);list.appendChild(dd);
    });
  }
  tabs.forEach(function(t){
    var b=d.createElement('button');b.type='button';b.setAttribute('role','tab');
    var i=d.createElement('span');i.setAttribute('aria-hidden','true');i.textContent=t[1];b.appendChild(i);
    b.appendChild(d.createTextNode(t[2]));
    b.addEventListener('click',function(){show(t[0])});btns[t[0]]=b;bar.appendChild(b);
  });
  if(tabs.length>1)dlg.appendChild(bar);
  dlg.appendChild(list);dlg.appendChild(ok);
  function has(k){return tabs.some(function(t){return t[0]===k})}
  function pad(){try{var p=navigator.getGamepads?navigator.getGamepads():[];for(var i=0;i<p.length;i++)if(p[i]&&p[i].connected)return true}catch(e){}return false}
  function touch(){try{return matchMedia('(pointer:coarse)').matches}catch(e){return false}}
  var lastKey=false;
  function best(){
    if(pad()&&has('kontroller'))return 'kontroller';
    if(lastKey&&has('gep'))return 'gep';
    if(touch()&&has('erinto'))return 'erinto';
    if(has('gep'))return 'gep';
    return tabs[0][0];
  }
  function pauseGame(){
    try{
      Object.defineProperty(d,'hidden',{configurable:true,get:function(){return true}});
      d.dispatchEvent(new Event('visibilitychange'));
    }catch(e){}
    try{delete d.hidden}catch(e){}
  }
  function isOpen(){return dlg.open}
  function open(){
    if(isOpen())return;
    show(best());pauseGame();
    try{dlg.showModal()}catch(e){dlg.setAttribute('open','')}
    ok.focus();
  }
  function close(){
    if(!isOpen())return;
    try{dlg.close()}catch(e){dlg.removeAttribute('open')}
    var a=d.activeElement;if(a&&a.blur)a.blur();   /* a szóköz utána ne nyissa újra a gombot */
  }
  ok.addEventListener('click',close);
  dlg.addEventListener('cancel',function(e){e.preventDefault();close()});
  dlg.addEventListener('click',function(e){if(e.target===dlg)close()});   /* a sötét háttérre koppintás is bezár */
  /* amíg nyitva van, a játék ne kapja meg az érintést és a billentyűt */
  ['pointerdown','pointerup','pointermove','touchstart','touchmove','touchend','mousedown','mouseup','click','wheel'].forEach(function(t){
    dlg.addEventListener(t,function(e){e.stopPropagation()});
  });
  addEventListener('keydown',function(e){
    if(isOpen()){
      if(e.key==='Escape'){e.preventDefault();close()}
      else if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
        var a=d.activeElement;
        if(a&&a.parentNode===bar){e.preventDefault();var i=tabs.map(function(t){return btns[t[0]]}).indexOf(a),n=tabs.length;
          var b=btns[tabs[(i+(e.key==='ArrowLeft'?n-1:1))%n][0]];b.focus();b.click()}
      }
      e.stopImmediatePropagation();return;
    }
    lastKey=e.isTrusted&&e.key!=='Tab';
    if(e.key==='?'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){
      var t=e.target;if(t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable))return;
      e.preventDefault();e.stopImmediatePropagation();open();
    }
  },true);
  addEventListener('keyup',function(e){if(isOpen())e.stopImmediatePropagation()},true);
  addEventListener('pointerdown',function(e){if(e.pointerType==='touch'||e.pointerType==='pen')lastKey=false},true);
  function init(){
    d.body.appendChild(dlg);
    var top=d.querySelector('.top-bar');if(!top)return;
    var b=d.createElement('button');b.type='button';b.className='sugo-btn';b.textContent='?';
    b.setAttribute('aria-label','Hogyan kell?');b.title='Hogyan kell? (?)';
    ['pointerdown','touchstart','mousedown'].forEach(function(t){b.addEventListener(t,function(e){e.stopPropagation()})});
    b.addEventListener('click',function(e){e.stopPropagation();open()});
    top.appendChild(b);
    /* ha nem fér ki egy sorba, a teljes képernyő gomb csak ikont mutat (ugyanaz a jelzés, amit a gomb szkriptje is ismer) */
    function fit(){
      var fs=d.querySelector('.fs-btn'),first=top.firstElementChild;
      if(fs&&first&&b.offsetTop>first.offsetTop+4){fs.dataset.compact='1';fs.textContent='⛶'}
    }
    fit();addEventListener('gamepadconnected',function(){setTimeout(fit,50)});
  }
  if(d.readyState==='loading')d.addEventListener('DOMContentLoaded',init);else init();
  window.Sugo={open:open,close:close};
})();

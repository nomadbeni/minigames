/* Modern böngészőképességek egy helyen. Mind opcionális: ha a böngésző nem tudja, vagy hibát ad, csendben nem
   történik semmi, a játék ugyanúgy játszható. Hálózatot nem használ, és a játék soha nem vár rá.
   A játék fő szkriptje ELŐTT kell betölteni, mert a játék a window.Kepesseg függvényeit hívja.
     Kepesseg.haptic(minta)   rövid rezgés telefonon (navigator.vibrate) és kontrolleren (vibrationActuator).
                              minta: 'tap' | 'hit' | 'hurt' | 'boom' | 'reward' | 'over', vagy ms, vagy ms-tömb.
                              Csak koppintás/gombnyomás után rezeg, van rá időkorlát, és ki lehet kapcsolni.
     Kepesseg.hapticsOn() / Kepesseg.setHaptics(be)   a közös rezgés-beállítás (localStorage: kepesseg:rezges).
       Ha az oldalon van .hap-btn gomb, az kapcsolja; csak ott látszik, ahol van mit rezegtetni.
     Kepesseg.wakeLock(be)    true: amíg tart a játék, a kijelző ne aludjon el; false: elengedi. Háttérbe tett
                              lap után magától újrakéri; 2 perc tétlenség után elengedi, a következő érintésre újra.
     Kepesseg.transition(fn)  fn a képernyőváltás DOM-módosítása; View Transitionnel fut, ha lehet, és nincs
                              csökkentett mozgás. Különben (vagy hibánál) azonnal fut. Az átmenet alatt (0,15 mp)
                              a böngésző nem ad át érintést, ezért csak ablak MEGJELENÉSÉRE használd; a játékba
                              visszavezető bezárás legyen azonnali, és hívja a Kepesseg.endTransition()-t.
     Kepesseg.quality(most)   képkockánként hívva a díszítő grafika szintje: 2 teljes, 1 kevesebb, 0 legkevesebb.
                              Csak látványra használd (részecske, háttér), játéklogikára soha.
     Tájolás: ha a <head>-ben <meta name="games:orientation" content="portrait"> (vagy landscape) áll, és a
       készülék már így áll, teljes képernyőn ebben rögzíti (nem fordul el véletlenül), kilépéskor felold.
       Ha másképp áll, nem zárol és nem forgat; ilyenkor a CSS-es elrendezés és a fekvo-jelzes segít. */
(function(){
  if(window.Kepesseg)return;
  var d=document,nav=navigator,noop=function(){};
  function now(){return (window.performance&&performance.now)?performance.now():Date.now()}
  function mq(q){try{return matchMedia(q).matches}catch(e){return false}}
  function calm(){return mq('(prefers-reduced-motion: reduce)')}
  function quiet(p){try{if(p&&typeof p.then==='function')p.then(noop,noop)}catch(e){}return p}

  /* ---------- rezgés ---------- */
  var KEY='kepesseg:rezges',PAT={tap:[10],hit:[20],hurt:[45],boom:[70],reward:[25,50,25],over:[40,60,40]};
  var POW={tap:.25,hit:.45,hurt:.8,boom:1,reward:.5,over:.7},RANK={tap:0,hit:1,reward:2,hurt:3,boom:3,over:4};
  var on=true,last=-1e9,busy=0,busyRank=-1;
  try{on=localStorage.getItem(KEY)!=='0'}catch(e){}
  function pattern(m){
    var p=typeof m==='string'?PAT[m]:typeof m==='number'?[m]:Array.isArray(m)?m:null,out=[],sum=0;
    if(!p)return null;
    for(var i=0;i<p.length&&i<7;i++){var v=+p[i];if(!(v>=0))return null;v=Math.min(200,Math.round(v));
      if(i%2===0){if(sum+v>400)v=400-sum;sum+=v}out.push(v)}
    return sum>0?out:null;
  }
  function pads(){
    var r=[];try{var g=nav.getGamepads?nav.getGamepads():[];for(var i=0;i<g.length;i++)
      if(g[i]&&g[i].connected!==false&&(g[i].vibrationActuator||(g[i].hapticActuators&&g[i].hapticActuators[0])))r.push(g[i])}catch(e){}
    return r;
  }
  function phone(){return typeof nav.vibrate==='function'&&mq('(pointer: coarse)')}
  function rumble(gp,ms,pow){
    try{
      var a=gp.vibrationActuator;
      if(a&&typeof a.playEffect==='function'){
        var t=(a.effects&&a.effects.indexOf&&a.effects.indexOf('dual-rumble')<0&&a.effects.indexOf('trigger-rumble')<0)?a.effects[0]:'dual-rumble';
        quiet(a.playEffect(t||'dual-rumble',{startDelay:0,duration:ms,strongMagnitude:pow,weakMagnitude:Math.min(1,pow+.2)}));
      }else if(gp.hapticActuators&&gp.hapticActuators[0]&&gp.hapticActuators[0].pulse){
        quiet(gp.hapticActuators[0].pulse(pow,ms));
      }
    }catch(e){}
  }
  function haptic(m){
    if(!on)return false;
    try{var ua=nav.userActivation;if(ua&&!ua.hasBeenActive)return false}catch(e){}
    var p=pattern(m);if(!p)return false;
    var t=now(),rk=typeof m==='string'?RANK[m]:1,total=0;
    if(t-last<70)return false;                       /* sűrű eseményeknél nem rezeg minden alkalommal */
    if(t<busy&&rk<=busyRank)return false;            /* gyengébb jelzés nem szakítja meg az erősebbet */
    for(var i=0;i<p.length;i++)total+=p[i];
    last=t;busy=t+total;busyRank=rk;
    var did=false,gs=pads(),pow=typeof m==='string'?POW[m]:.5;
    if(gs.length){
      var off=0;did=true;
      for(var j=0;j<p.length;j+=2){(function(ms,at){
        if(at===0)gs.forEach(function(g){rumble(g,ms,pow)});
        else setTimeout(function(){if(on)pads().forEach(function(g){rumble(g,ms,pow)})},at);
      })(p[j],off);off+=p[j]+(p[j+1]||0)}
    }
    if(phone()){try{did=nav.vibrate(p.length===1?p[0]:p)!==false||did}catch(e){}}
    return did;
  }
  function stop(){busy=0;try{if(typeof nav.vibrate==='function')nav.vibrate(0)}catch(e){}
    pads().forEach(function(g){try{var a=g.vibrationActuator;if(a&&a.reset)quiet(a.reset())}catch(e){}})}
  function setHaptics(v){on=!!v;try{localStorage.setItem(KEY,on?'1':'0')}catch(e){}if(!on)stop();label()}
  var btn=null;
  function label(){
    if(!btn)return;
    btn.textContent=on?'📳':'📴';btn.setAttribute('aria-pressed',on?'true':'false');
    btn.setAttribute('aria-label',on?'Rezgés: be':'Rezgés: ki');btn.title=on?'Rezgés: be':'Rezgés: ki';
    btn.style.opacity=on?'.75':'.45';
  }
  function showBtn(){
    if(!btn)return;
    btn.style.display=(phone()||pads().length)?'inline-flex':'none';
    /* ha nem fér ki egy sorba, a teljes képernyő gomb csak ikont mutat (ugyanaz a data-compact jelzés, amit a gomb szkriptje is ismer) */
    var fs=d.querySelector('.fs-btn'),first=btn.parentNode&&btn.parentNode.firstElementChild;
    if(fs&&first&&btn.style.display!=='none'&&btn.offsetTop>first.offsetTop+4){fs.dataset.compact='1';fs.textContent='⛶'}
  }
  function initBtn(){
    btn=d.querySelector('.hap-btn');if(!btn)return;
    btn.addEventListener('click',function(){setHaptics(!on);if(on)haptic('hit');btn.blur()});
    label();showBtn();
  }
  addEventListener('gamepadconnected',showBtn);addEventListener('gamepaddisconnected',showBtn);

  /* ---------- ébren tartás (Screen Wake Lock) ---------- */
  var IDLE=120000,want=false,lock=null,pending=false,lastUse=0,timer=0;
  function wlRequest(){
    if(!want||lock||pending||d.visibilityState!=='visible')return;
    var w=nav.wakeLock;if(!w||typeof w.request!=='function')return;
    pending=true;
    try{
      w.request('screen').then(function(s){
        pending=false;
        if(!want||!s){try{s&&quiet(s.release())}catch(e){}return}
        lock=s;try{s.addEventListener('release',function(){if(lock===s)lock=null})}catch(e){}
      },function(){pending=false});
    }catch(e){pending=false}
  }
  function wlRelease(){var s=lock;lock=null;if(s)try{quiet(s.release())}catch(e){}}
  function used(){lastUse=now();if(want&&!lock)wlRequest()}
  function tick(){if(lock&&now()-lastUse>IDLE)wlRelease()}
  function wakeLock(v){
    want=!!v;lastUse=now();
    if(want){wlRequest();if(!timer)timer=setInterval(tick,15000)}
    else{wlRelease();if(timer){clearInterval(timer);timer=0}}
  }
  d.addEventListener('visibilitychange',function(){if(d.visibilityState==='visible'){lastUse=now();wlRequest()}});
  ['pointerdown','keydown','touchstart'].forEach(function(ev){addEventListener(ev,used,{capture:true,passive:true})});
  addEventListener('pagehide',function(){wlRelease();oriUnlock()});

  /* ---------- képernyőváltás (View Transitions) ---------- */
  var vt=null,vtCss=false;
  function transition(fn){
    var done=false,run=function(){if(done)return;done=true;
      try{fn()}catch(e){setTimeout(function(){throw e},0)}};   /* a játék hibája ne vesszen el */
    /* betöltés közben (első képernyő) nincs mit átúsztatni */
    if(typeof d.startViewTransition!=='function'||calm()||d.visibilityState!=='visible'||d.readyState!=='complete'){run();return}
    if(!vtCss){vtCss=true;try{var st=d.createElement('style');
      st.textContent='::view-transition-old(root),::view-transition-new(root){animation-duration:.15s}';d.head.appendChild(st)}catch(e){}}
    try{
      var t=d.startViewTransition(run);vt=t;
      var clear=function(){if(vt===t)vt=null};
      quiet(t.ready);quiet(t.updateCallbackDone);
      if(t.finished&&t.finished.then)t.finished.then(clear,clear);
    }catch(e){run()}
    if(!done)setTimeout(run,250);                     /* ha a böngésző nem futtatná le, akkor is megtörténik */
  }
  /* a futó átmenet azonnali vége: bezáráskor és bármilyen érintésre, gombnyomásra, hogy a játék ne várjon rá */
  function endTransition(){var t=vt;vt=null;if(t)try{t.skipTransition()}catch(e){}}
  ['pointerdown','keydown'].forEach(function(ev){addEventListener(ev,function(){if(vt)endTransition()},{capture:true,passive:true})});

  /* ---------- tájolás (Screen Orientation) ---------- */
  var ori=null,oriLocked=false;
  function oriPref(){var m=d.querySelector('meta[name="games:orientation"]'),v=m&&m.getAttribute('content');
    return v==='portrait'||v==='landscape'?v:null}
  function oriLock(){
    var o=window.screen&&screen.orientation,p=ori||(ori=oriPref());
    if(!p||!o||typeof o.lock!=='function')return;
    if(String(o.type||'').split('-')[0]!==p)return;   /* csak a már meglévő tájolást rögzíti: soha nem forgatja el a képet */
    try{var r=o.lock(p);oriLocked=true;if(r&&r.then)r.then(noop,function(){oriLocked=false})}catch(e){oriLocked=false}
  }
  function oriUnlock(){
    if(!oriLocked)return;oriLocked=false;
    try{var o=window.screen&&screen.orientation;if(o&&typeof o.unlock==='function')o.unlock()}catch(e){}
  }
  function fsChange(){if(d.fullscreenElement||d.webkitFullscreenElement)oriLock();else oriUnlock()}
  d.addEventListener('fullscreenchange',fsChange);d.addEventListener('webkitfullscreenchange',fsChange);

  /* ---------- adaptív grafikai minőség ---------- */
  var Q={lvl:2,t:0,acc:0,n:0,bad:0,good:0,changed:-1e9,ups:0,hot:false,watch:false,forced:null};
  function watchPressure(){
    Q.watch=true;
    try{if(typeof window.PressureObserver==='function'){
      var po=new window.PressureObserver(function(rs){var s=rs&&rs.length&&rs[rs.length-1].state;Q.hot=s==='serious'||s==='critical'});
      quiet(po.observe('cpu'));
    }}catch(e){}
  }
  function level(){var l=Q.forced!=null?Q.forced:Q.lvl;return calm()?Math.min(l,1):l}
  function quality(t){
    if(typeof t!=='number'||!isFinite(t))return level();
    if(!Q.watch)watchPressure();
    var dt=t-Q.t;Q.t=t;
    if(!(dt>0)||dt>250)return level();               /* szünet, háttér: nem mérjük */
    Q.acc+=dt;Q.n++;
    if(Q.acc>=1000){
      var avg=Q.acc/Q.n;Q.acc=0;Q.n=0;
      Q.bad=(avg>24||Q.hot)?Q.bad+1:0;Q.good=(avg<18&&!Q.hot)?Q.good+1:0;
      if(t-Q.changed>4000){
        if(Q.bad>=3&&Q.lvl>0){Q.lvl--;Q.changed=t;Q.bad=Q.good=0}   /* 3 lassú másodperc egymás után: egy rövid akadás nem számít */
        else if(Q.good>=15&&Q.lvl<2&&Q.ups<2){Q.lvl++;Q.ups++;Q.changed=t;Q.good=0}   /* ritkán, és csak kétszer lép vissza */
      }
    }
    return level();
  }
  function setQuality(l){Q.forced=(l===0||l===1||l===2)?l:null}

  window.Kepesseg={haptic:haptic,hapticsOn:function(){return on},setHaptics:setHaptics,wakeLock:wakeLock,
    wakeLockHeld:function(){return !!lock},transition:transition,endTransition:endTransition,quality:quality,setQuality:setQuality};
  if(d.readyState==='loading')d.addEventListener('DOMContentLoaded',initBtn);else initBtn();
})();

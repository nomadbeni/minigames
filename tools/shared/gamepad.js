/* Kontroller (gamepad) a böngésző Gamepad API-jával. A játék kódjához nem nyúl: a kontrollert billentyűkké
   fordítja, amelyeket a játék már ismer. Ha egy ablak (menü, szünet, vége) látszik, a kar a gombok között lép,
   az A gomb megnyomja a kijelöltet. Kiosztás (szabványos kontroller):
     bal kar / d-pad → nyilak, A → szóköz, X → J, Y → K, B → L, RB → L, Start → Escape (szünet), Select → Enter.
   iPhone-on a böngésző nem támogatja, ott ez a rész nem csinál semmit. */
(function(){
  if(!navigator.getGamepads)return;
  var DIRS=[['ArrowUp',12],['ArrowDown',13],['ArrowLeft',14],['ArrowRight',15]];
  var BTN=[[0,' ','Space'],[2,'j','KeyJ'],[3,'k','KeyK'],[1,'l','KeyL'],[5,'l','KeyL'],[9,'Escape','Escape'],[8,'Enter','Enter']];
  var held={},raf=0,shown=false,lastNav=0;
  function key(type,k,code){
    var e=new KeyboardEvent(type,{key:k,code:code,bubbles:true,cancelable:true});
    (document.activeElement&&document.activeElement!==document.body?document.activeElement:document).dispatchEvent(e);
  }
  function set(name,on,k,code){if(!!held[name]===on)return;held[name]=on;key(on?'keydown':'keyup',k,code||k)}
  function visible(el){if(!el||el.hidden)return false;var r=el.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(el).visibility!=='hidden'}
  function dialog(){
    var c=document.querySelectorAll('#ov,#over,#pick,#overlay,.modal,dialog[open],.rotate-hint');
    for(var i=0;i<c.length;i++)if(visible(c[i])&&!c[i].classList.contains('rotate-hint'))return c[i];
    return null;
  }
  function buttons(d){return Array.prototype.filter.call(d.querySelectorAll('button:not(:disabled),a[href]'),visible)}
  function nav(d,dir){
    var b=buttons(d);if(!b.length)return;
    var i=b.indexOf(document.activeElement);
    if(i<0){var hot=d.querySelector('.hot:not(:disabled)');(hot&&visible(hot)?hot:b[0]).focus();return}
    var cur=b[i].getBoundingClientRect(),best=null,bd=1e9;
    b.forEach(function(x){if(x===b[i])return;var r=x.getBoundingClientRect(),dx=r.left+r.width/2-(cur.left+cur.width/2),dy=r.top+r.height/2-(cur.top+cur.height/2);
      var ok=dir==='ArrowUp'?dy<-4:dir==='ArrowDown'?dy>4:dir==='ArrowLeft'?dx<-4:dx>4;if(!ok)return;
      var dist=Math.abs(dx)+Math.abs(dy)*(dir==='ArrowLeft'||dir==='ArrowRight'?3:1)+Math.abs(dx)*(dir==='ArrowUp'||dir==='ArrowDown'?2:0);if(dist<bd){bd=dist;best=x}});
    (best||b[(i+(dir==='ArrowUp'||dir==='ArrowLeft'?b.length-1:1))%b.length]).focus();
  }
  function note(){
    if(shown)return;shown=true;
    var t=document.createElement('div');t.setAttribute('role','status');
    t.style.cssText='position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:3500;background:#0b0c10;color:#fff;border:1px solid #444;border-radius:10px;padding:10px 16px;font:700 15px system-ui,sans-serif;pointer-events:none';
    t.textContent='Kontroller csatlakoztatva';document.body.appendChild(t);setTimeout(function(){t.remove()},2500);
  }
  function poll(){
    raf=setTimeout(poll,16); /* időzítő, nem képkocka: álló képnél is figyeli a kontrollert */
    var pads=navigator.getGamepads?navigator.getGamepads():[],gp=null;
    for(var i=0;i<pads.length;i++)if(pads[i]&&pads[i].connected){gp=pads[i];break}
    if(!gp){for(var n in held)if(held[n])held[n]=false;return}
    note();
    var pr=function(i){var b=gp.buttons[i];return !!b&&(b.pressed||b.value>.5)};
    var ax=gp.axes[0]||0,ay=gp.axes[1]||0,dz=.25;
    var dirOn={ArrowUp:ay<-dz,ArrowDown:ay>dz,ArrowLeft:ax<-dz,ArrowRight:ax>dz};
    DIRS.forEach(function(d){if(pr(d[1]))dirOn[d[0]]=true});
    var d=dialog();
    if(d){
      DIRS.forEach(function(x){if(held[x[0]])set(x[0],false,x[0])});
      BTN.forEach(function(b){if(held['b'+b[0]])set('b'+b[0],false,b[1],b[2])});
      var now=performance.now(),any=null;DIRS.forEach(function(x){if(dirOn[x[0]])any=x[0]});
      if(any&&now-lastNav>220){lastNav=now;nav(d,any)}else if(!any)lastNav=0;
      var a=pr(0);if(a&&!held.navA){var f=document.activeElement;if(f&&d.contains(f)&&f.click)f.click();else{var b=buttons(d),hot=d.querySelector('.hot:not(:disabled)');(hot&&visible(hot)?hot:b[0])&&(hot&&visible(hot)?hot:b[0]).click()}}
      held.navA=a;
      if(pr(9)&&!held.Escape)set('Escape',true,'Escape');else if(!pr(9))set('Escape',false,'Escape');
      return;
    }
    held.navA=pr(0);
    DIRS.forEach(function(x){set(x[0],dirOn[x[0]],x[0])});
    BTN.forEach(function(b){set('b'+b[0],pr(b[0]),b[1],b[2])});
  }
  addEventListener('gamepadconnected',function(){if(!raf)poll()});
  addEventListener('gamepaddisconnected',function(){var p=navigator.getGamepads(),any=false;for(var i=0;i<p.length;i++)if(p[i])any=true;if(!any){clearTimeout(raf);raf=0;for(var n in held)if(held[n]&&n.indexOf('Arrow')===0)set(n,false,n)}});
  try{var p0=navigator.getGamepads();for(var i=0;i<p0.length;i++)if(p0[i]){poll();break}}catch(e){}
})();

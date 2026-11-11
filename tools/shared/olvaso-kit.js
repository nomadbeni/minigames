const K=(()=>{
  /* storage: a saved value must have the same shape as the default, or the default is used.
     For objects, each default key with a wrong type is put back to its default. */
  const kind=v=>Array.isArray(v)?'array':v===null?'null':typeof v==='number'?(Number.isFinite(v)?'number':'bad'):typeof v;
  const store={
    get(k,d){
      let v;try{const raw=localStorage.getItem(k);if(raw==null)return d;v=JSON.parse(raw)}catch(e){return d}
      if(d===undefined||d===null)return v;
      if(kind(v)!==kind(d))return d;
      if(kind(d)==='object'){for(const key of Object.keys(d))if(key in v?kind(v[key])!==kind(d[key])&&d[key]!==null:true)v[key]=d[key]}
      return v;
    },
    set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
  };
  const clampInt=(v,lo,hi)=>Number.isFinite(v)?Math.max(lo,Math.min(hi,Math.floor(v))):lo;
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const plain=w=>String(w).replace(/\|/g,'');
  /* speech */
  let voice=null;
  const hasTTS='speechSynthesis' in window&&'SpeechSynthesisUtterance' in window;
  function pick(){try{const vs=speechSynthesis.getVoices();voice=vs.find(v=>/^hu/i.test(v.lang))||null}catch(e){}}
  if(hasTTS){pick();try{speechSynthesis.addEventListener('voiceschanged',pick)}catch(e){}}
  function say(t){
    if(!hasTTS)return false;
    try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(plain(t));u.lang='hu-HU';if(voice)u.voice=voice;u.rate=.85;speechSynthesis.speak(u);return true}catch(e){return false}
  }
  /* mastery: how many times a word was read right, shared by all reading games */
  const MK='olvaso:mastery';
  /* only word -> non-negative count pairs survive; nothing can reach the object prototype */
  const mastery=Object.create(null);
  {const raw=store.get(MK,{});for(const k of Object.keys(raw).slice(0,5000))if(k.length<=60&&Number.isFinite(raw[k])&&raw[k]>0)mastery[k]=clampInt(raw[k],0,1e6)}
  const settings=store.get('olvaso:settings',{split:'auto'});
  if(settings.split!=='auto'&&settings.split!=='mindig')settings.split='auto';
  function seen(w){const k=plain(w).toLowerCase();mastery[k]=Math.min(1e6,(mastery[k]||0)+1);store.set(MK,mastery);if(api.addXP)api.addXP(2)}
  function level(w){
    if(settings.split==='mindig')return 2;
    const n=mastery[plain(w).toLowerCase()]||0;
    return n<4?2:n<8?1:0;
  }
  /* word: "fék|betét" -> coloured parts; level 2 also shows a dot between parts */
  function word(w,lv){
    const toks=String(w).split(/(\|| )/);
    if(lv==null)lv=level(w);
    if(toks.length<2||lv===0)return `<span class="w">${esc(plain(w))}</span>`;
    let i=0,h='';
    for(const t of toks){if(t==='|')h+=lv===2?'<i class="dot">·</i>':'';else if(t===' ')h+=' ';else h+=`<span class="p${(i++)%2}">${esc(t)}</span>`}
    return `<span class="w">${h}</span>`;
  }
  function sentence(s,lv){return String(s).split(' ').map(t=>t.includes('|')?word(t,lv):esc(t)).join(' ')}
  function setSplit(v){settings.split=v==='mindig'?'mindig':'auto';store.set('olvaso:settings',settings)}
  /* speaker buttons: <button class="say" data-say="text">; a game may set K.onSay(text) -> false to refuse */
  const api={store,esc,plain,say,hasTTS,word,sentence,seen,level,settings,setSplit,onSay:null,
    sayBtn:(t,label)=>hasTTS?`<button type="button" class="say" data-say="${esc(t)}" aria-label="${esc(label||'Felolvasás')}">🔊</button>`:''};
  document.addEventListener('click',e=>{
    const b=e.target.closest&&e.target.closest('[data-say]');if(!b||b.disabled)return;
    e.stopPropagation();
    const t=b.dataset.say;
    if(api.onSay&&api.onSay(t,b)===false)return;
    if(say(t)){b.classList.add('talking');setTimeout(()=>b.classList.remove('talking'),1200)}
  },true);
  /* sounds */
  let ac=null;api.sound=store.get('olvaso:sound',true)!==false;
  api.toggleSound=()=>{api.sound=!api.sound;store.set('olvaso:sound',api.sound);return api.sound};
  api.beep=(f=440,d=.08,type='square',vol=.06,slide=0)=>{
    if(!api.sound)return;
    try{ac=ac||new (window.AudioContext||window.webkitAudioContext)();
      const o=ac.createOscillator(),g=ac.createGain(),t=ac.currentTime;
      o.type=type;o.frequency.setValueAtTime(f,t);if(slide)o.frequency.exponentialRampToValueAtTime(Math.max(30,f+slide),t+d);
      g.gain.setValueAtTime(vol,t);g.gain.exponentialRampToValueAtTime(.0001,t+d);
      o.connect(g).connect(ac.destination);o.start(t);o.stop(t+d+.02)}catch(e){}
  };
  api.good=()=>{api.beep(660,.08,'square');setTimeout(()=>api.beep(990,.12,'square'),80)};
  api.bad=()=>api.beep(160,.18,'sawtooth',.05,-60);
  api.coin=()=>{api.beep(1200,.05,'square',.04);setTimeout(()=>api.beep(1600,.08,'square',.04),50)};

  /* pixel sprites: {r:[rows], p:{char:color}}; '.' is transparent */
  const sprCache=new Map();
  api.spr=def=>{
    const key=JSON.stringify(def);let c=sprCache.get(key);if(c)return c;
    const w=Math.max(...def.r.map(r=>r.length)),h=def.r.length;
    c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');
    def.r.forEach((row,y)=>{for(let i=0;i<row.length;i++){const col=def.p[row[i]];if(col){x.fillStyle=col;x.fillRect(i,y,1,1)}}});
    c._url=null;sprCache.set(key,c);return c;
  };
  api.img=(def,size,alt)=>{const c=api.spr(def);if(!c._url)c._url=c.toDataURL();return `<img class="px" src="${c._url}" alt="${esc(alt||'')}" style="width:${size}px;height:${Math.round(size*c.height/c.width)}px">`};
  api.draw=(ctx,def,cx,cy,w)=>{const c=api.spr(def),h=w*c.height/c.width;ctx.imageSmoothingEnabled=false;ctx.drawImage(c,Math.round(cx-w/2),Math.round(cy-h/2),Math.round(w),Math.round(h))};
  /* a small pixel person, used for riders, customers and villagers */
  api.human=(o={})=>{
    const r=["...hhhh...","..hhhhhh..","..hssssh..","..sesses..","..ssssss..",o.beard?"..sbbbbs..":"...smms...","..tttttt..",".tttttttt.",".sttttttss",".s.tttt.s.","...pppp...","...p..p...","...p..p...","..kk..kk.."];
    if(o.hat){r[0]="..HHHHHH..";r[1]=".HHHHHHHH."}
    if(o.cap){r[0]="..HHHHHH..";r[1]="..HHHHHHHH"}
    if(o.apron){r[7]=".twwwwwwt.";r[8]=".swwwwwwss";r[9]=".s.wwww.s."}
    return {r,p:{h:o.hair||'#3a2a1a',s:o.skin||'#e8b48a',e:'#141414',m:o.mouth||'#b0705a',b:o.hair||'#3a2a1a',t:o.shirt||'#3a6ee8',p:o.pants||'#2a3550',k:'#1f1a16',H:o.hatC||'#555',w:'#f2f2f2'}};
  };
  const HAIR=['#2a1d14','#4a3020','#8a5a2a','#d9b25a','#1a1a1a','#a83a2a'],SKIN=['#f0c7a0','#e0a878','#c98a5a','#8a5a3a'],SHIRT=['#e8494a','#ff7a1a','#2fa86a','#3a6ee8','#8a4ae8','#222831','#f2f2f2','#e8c13a'];
  api.randomHuman=()=>api.human({hair:api.pick(HAIR),skin:api.pick(SKIN),shirt:api.pick(SHIRT),pants:api.pick(['#2a3550','#1f1f24','#4a4a52','#3a5a2a']),cap:Math.random()<.35,hatC:api.pick(SHIRT),beard:Math.random()<.2});
  /* shared XP and rank across all the reading games */
  const RANKS=[[0,'Bronz','#c98a5a'],[120,'Ezüst','#c9d1dc'],[350,'Arany','#ffd166'],[800,'Platina','#6fe3d4'],[1600,'Gyémánt','#7fb6ff'],[3000,'Mester','#c38bff'],[5000,'Legenda','#ff5e6c']];
  api.xp=clampInt(store.get('olvaso:xp',0),0,1e7);
  const rankOf=x=>{let i=0;while(i+1<RANKS.length&&x>=RANKS[i+1][0])i++;return i};
  api.rank=()=>{const i=rankOf(api.xp),cur=RANKS[i],nx=RANKS[i+1];return {i,name:cur[1],color:cur[2],pct:nx?(api.xp-cur[0])/(nx[0]-cur[0]):1,next:nx?nx[1]:null}};
  api.rankChip=()=>{const r=api.rank();return `<span class="rankchip" style="--rc:${r.color}" title="Rang: ${r.name}, ${api.xp} XP"><b>◆ ${r.name}</b><i><u style="width:${Math.round(r.pct*100)}%"></u></i></span>`};
  const paint=()=>document.querySelectorAll('[data-rank]').forEach(el=>el.innerHTML=api.rankChip());
  api.addXP=n=>{const before=rankOf(api.xp);api.xp=clampInt(api.xp+Math.max(0,Math.round(Number(n)||0)),0,1e7);store.set('olvaso:xp',api.xp);paint();
    const after=rankOf(api.xp);if(after>before)api.toast(`Új rang: <b style="color:${RANKS[after][2]}">◆ ${RANKS[after][1]}</b>`)};
  api.clampInt=clampInt;
  api.toast=h=>{let t=document.getElementById('ktoast');if(!t){t=document.createElement('div');t.id='ktoast';document.body.appendChild(t)}
    t.innerHTML=h;t.className='show';clearTimeout(t._t);t._t=setTimeout(()=>t.className='',2200)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',paint);else setTimeout(paint);
  api.shuffle=a=>{a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a};
  api.pick=a=>a[Math.random()*a.length|0];
  return api;
})();

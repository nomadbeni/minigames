/* Fekvő telefonon „Fordítsd el a telefont” jelzés. A játék álló képernyőre készült, ezért amíg a telefon
   fekszik, a jelzés eltakarja, és a játék a saját szünet-logikájával megáll (ugyanaz fut le, mint amikor
   a lap háttérbe kerül). Gépen, széles ablakban nem jelenik meg (csak érintőképernyőn, alacsony ablakban). */
(function(){
  var mq;
  try{ mq=matchMedia('(orientation: landscape) and (max-height: 500px) and (pointer: coarse)'); }catch(e){ return; }
  var st=document.createElement('style');
  st.textContent='.rotate-hint{position:fixed;inset:0;z-index:3000;display:grid;place-items:center;padding:16px;'+
    'background:rgba(5,8,14,.95);color:#fff;font:700 20px/1.3 system-ui,sans-serif;text-align:center}'+
    '.rotate-hint[hidden]{display:none!important}.rotate-hint p{margin:8px 0}'+
    '.rotate-hint .sub{font-weight:400;font-size:16px;opacity:.85}.rotate-hint svg{width:56px;height:56px}';
  var el=document.createElement('div');
  el.className='rotate-hint';el.setAttribute('role','alert');el.hidden=true;
  el.innerHTML='<div><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="2" width="10" height="20" rx="2" '+
    'fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="18.5" r="1" fill="currentColor"/></svg>'+
    '<p>Fordítsd el a telefont!</p><p class="sub">Ez a játék álló képernyőre készült. Addig szünetel.</p></div>';
  function pauseGame(){
    try{
      Object.defineProperty(document,'hidden',{configurable:true,get:function(){return true;}});
      document.dispatchEvent(new Event('visibilitychange'));
    }catch(e){}
    try{ delete document.hidden; }catch(e){}
  }
  function update(e){
    if(mq.matches){ if(el.hidden){ el.hidden=false; if(e) pauseGame(); } }
    else el.hidden=true;
  }
  document.head.appendChild(st);
  document.body.appendChild(el);
  if(mq.addEventListener) mq.addEventListener('change',update); else if(mq.addListener) mq.addListener(update);
  update();
})();

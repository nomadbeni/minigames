const ORDER=Object.keys(TYPES);
const VOX=[];let minX=1e9,maxX=-1e9,minZ=1e9,maxZ=-1e9,YMAX=0;
for(const [kk,t] of V){
  const [x,y,z]=kk.split(',').map(Number);
  if(!TYPES[t])throw new Error('Unknown type '+t);
  VOX.push([x,y,z,t]);
  minX=Math.min(minX,x);maxX=Math.max(maxX,x);minZ=Math.min(minZ,z);maxZ=Math.max(maxZ,z);YMAX=Math.max(YMAX,y);
}
const NX=maxX-minX+1,NZ=maxZ-minZ+1;
const layerCounts=Array.from({length:YMAX+1},()=>({}));
const total={};
for(const [x,y,z,t] of VOX){layerCounts[y][t]=(layerCounts[y][t]||0)+1;total[t]=(total[t]||0)+1;}
const noteFor=y=>NOTES.find(n=>y>=n[0]&&y<=n[1]);

let cur=0,rot=0,hover=null;
const $=id=>document.getElementById(id);
const fmt=n=>n.toLocaleString('hu-HU');
const solidCount=VOX.filter(v=>!TYPES[v[3]].liquid&&!TYPES[v[3]].dig).length;
$('chips').innerHTML=[`${NX} × ${NZ} terület`,`${YMAX+1} szint (Y 0–${YMAX})`,`${fmt(solidCount)} blokk`,...CHIPS].map(s=>`<span class="chip">${s}</span>`).join('');
$('ymax').textContent='/ '+YMAX;$('layer').max=YMAX;

function css(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
function rgb(h){h=h.replace('#','');return [0,2,4].map(i=>parseInt(h.substr(i,2),16));}
function shade(h,f,a=1){const [r,g,b]=rgb(h);return `rgba(${Math.min(255,r*f)|0},${Math.min(255,g*f)|0},${Math.min(255,b*f)|0},${a})`;}
/* Anyagminta: a blokk színe, rajta a blokk rajzolata (tégla, deszka, rönk, kő, üveg, víz), az angol név alapján. */
const SW_LINE='rgba(0,0,0,.30)',SW_HI='rgba(255,255,255,.35)';
function swPattern(e){
  e=e||'';
  if(/Brick|Tile/.test(e))return `linear-gradient(${SW_LINE} 1px,transparent 1px) 0 0/100% 6px,linear-gradient(90deg,${SW_LINE} 1px,transparent 1px) 0 0/9px 6px`;
  if(/Planks|Slab|Stairs|Door|Barrel|Bookshelf|Table|Chest/.test(e))return `linear-gradient(${SW_LINE} 1px,transparent 1px) 0 0/100% 4.5px`;
  if(/Log|Fence|Ladder/.test(e))return `linear-gradient(90deg,${SW_LINE} 1px,transparent 1px) 0 0/4.5px 100%`;
  if(/Glass|Ice/.test(e))return `linear-gradient(135deg,transparent 35%,${SW_HI} 35%,${SW_HI} 50%,transparent 50%)`;
  if(/Water|Lava/.test(e))return `linear-gradient(${SW_HI} 1px,transparent 1px) 0 2px/100% 6px`;
  if(/Stone|Cobble|Andesite|Diorite|Deepslate|Calcite|Tuff|Basalt|Dirt|Gravel|Sand/.test(e))
    return `radial-gradient(${SW_LINE} 1px,transparent 1.5px) 0 0/6px 6px,radial-gradient(${SW_HI} 1px,transparent 1.5px) 3px 3px/6px 6px`;
  return '';
}
const swStyle=T=>{const pat=swPattern(T.e);return `background:${pat?pat+',':''}${T.c}`;};
const sw=T=>`<span class="sw" style="${swStyle(T)}"></span>`;

function renderMats(){
  const c=layerCounts[cur];
  $('lmats').innerHTML=ORDER.filter(t=>c[t]).map(t=>{
    const T=TYPES[t],n=c[t];
    const lab=T.dig?`${fmt(n)} blokknyi`:T.door?`${fmt(n)} blokk (${fmt(n/2)} ajtó)`:T.liquid?'vödrökkel':fmt(n)+' db';
    return `<li>${sw(T)}<span class="mname">${T.n}<small>${T.e}</small></span><span class="num">${lab}</span></li>`;
  }).join('')||'<li><span></span><span class="mname">Ezen a szinten nincs blokk.</span><span></span></li>';
  const nw=Object.entries(c).filter(([t])=>!TYPES[t].liquid&&!TYPES[t].dig).reduce((s,[,n])=>s+n,0);
  $('ncount').textContent=fmt(nw)+' blokk ezen a szinten';
}
function renderTotals(){
  $('totals').innerHTML=ORDER.filter(t=>total[t]).map(t=>{
    const T=TYPES[t],n=total[t];
    const nm=`<td><span class="sw inl" style="${swStyle(T)}"></span>${T.n}</td><td>${T.e}</td>`;
    if(T.dig)return `<tr>${nm}<td class="num">${fmt(n)} blokknyi</td><td class="num">nem kell blokk</td></tr>`;
    if(T.liquid)return `<tr>${nm}<td class="num">${fmt(n)} felület</td><td class="num">2 vödör (végtelen forrás)</td></tr>`;
    if(T.door)return `<tr>${nm}<td class="num">${fmt(n/2)} ajtó</td><td class="num">–</td></tr>`;
    const st=Math.floor(n/64),r=n%64;
    return `<tr>${nm}<td class="num">${fmt(n)}</td><td class="num">${st?st+' + '+r:r}</td></tr>`;
  }).join('');
}

const topcv=$('topcv');let cell=10;
function drawTop(){
  const w=topcv.clientWidth,dpr=window.devicePixelRatio||1;
  cell=w/NX;const h=cell*NZ;
  topcv.width=Math.round(w*dpr);topcv.height=Math.round(h*dpr);topcv.style.height=h+'px';
  const g=topcv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);
  g.fillStyle=css('--gridbg');g.fillRect(0,0,w,h);
  for(let gx=0;gx<NX;gx++)for(let gz=0;gz<NZ;gz++){
    const x=gx+minX,z=gz+minZ,t=get(x,cur,z),px=gx*cell,pz=gz*cell;
    if(t){
      const T=TYPES[t];
      if(T.dig){g.fillStyle=shade(T.c,1,.28);g.fillRect(px,pz,cell,cell);g.strokeStyle=shade(T.c,.8,.7);g.lineWidth=1;g.beginPath();g.moveTo(px,pz+cell);g.lineTo(px+cell,pz);g.stroke();}
      else if(T.thin){g.fillStyle=shade(T.c,1);const s=cell*Math.max(.35,T.thin+.1);g.fillRect(px+(cell-s)/2,pz+(cell-s)/2,s,s);}
      else{g.fillStyle=shade(T.c,1,T.alpha||1);g.fillRect(px,pz,cell,cell);}
      if(T.door){g.strokeStyle='rgba(0,0,0,.5)';g.lineWidth=1;g.strokeRect(px+cell*.25,pz+cell*.15,cell*.5,cell*.7);}
    }else if(cur>0){
      const b=get(x,cur-1,z);
      if(b&&!TYPES[b].dig){g.fillStyle=shade(TYPES[b].c,1,.2);g.fillRect(px,pz,cell,cell);}
    }
  }
  const mod5=v=>((v%5)+5)%5===0;
  for(let i=0;i<=NX;i++){const m=mod5(i+minX);g.strokeStyle=css(m?'--gl2':'--gl1');g.lineWidth=m?1.2:.6;g.beginPath();g.moveTo(i*cell,0);g.lineTo(i*cell,h);g.stroke();}
  for(let i=0;i<=NZ;i++){const m=mod5(i+minZ);g.strokeStyle=css(m?'--gl2':'--gl1');g.lineWidth=m?1.2:.6;g.beginPath();g.moveTo(0,i*cell);g.lineTo(w,i*cell);g.stroke();}
  if(hover){g.strokeStyle=css('--accent');g.lineWidth=2;g.strokeRect(hover[0]*cell+1,hover[1]*cell+1,cell-2,cell-2);}
}
function pick(e){
  const r=topcv.getBoundingClientRect();
  const gx=Math.floor((e.clientX-r.left)/cell),gz=Math.floor((e.clientY-r.top)/cell);
  if(gx<0||gz<0||gx>=NX||gz>=NZ)return;
  hover=[gx,gz];
  const x=gx+minX,z=gz+minZ,t=get(x,cur,z);
  $('info').textContent=`x ${x}, z ${z}, y ${cur} · `+(t?TYPES[t].n+' ('+TYPES[t].e+')':'üres');
  drawTop();
}
topcv.addEventListener('pointermove',e=>{if(e.pointerType==='mouse')pick(e);});
topcv.addEventListener('pointerdown',pick);
topcv.addEventListener('pointerleave',()=>{hover=null;drawTop();});

const isocv=$('isocv');
const CX=(minX+maxX)/2,CZ=(minZ+maxZ)/2;
function rotXZ(x,z,r){for(let i=0;i<r;i++){const nx=CX-(z-CZ),nz=CZ+(x-CX);x=nx;z=nz;}return [x,z];}
function drawIso(){
  const w=isocv.clientWidth,dpr=window.devicePixelRatio||1,ghost=$('ghost').checked;
  const list=[];let dmin=1e9,dmax=-1e9,smin=1e9,smax=-1e9;
  for(const v of VOX){
    const [rx,rz]=rotXZ(v[0],v[2],rot);
    const d=rx-rz,s=rx+rz;dmin=Math.min(dmin,d);dmax=Math.max(dmax,d);smin=Math.min(smin,s);smax=Math.max(smax,s);
    if(TYPES[v[3]].dig||(v[1]>cur&&!ghost))continue;
    list.push([rx,v[1],rz,v[3]]);
  }
  const du=dmax-dmin+4, su=(smax-smin+4)/2, yu=(YMAX+1)*1.2;
  const maxH=Math.max(340,window.innerHeight*.78);
  const a=Math.min(w/du,maxH/(su+yu)), hh=a*1.2, H=Math.round(a*(su+yu));
  isocv.width=Math.round(w*dpr);isocv.height=Math.round(H*dpr);isocv.style.height=H+'px';
  const g=isocv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,H);
  const ox=w/2-((dmin+dmax)/2)*a, oy=a+(YMAX+1)*hh-smin*a/2;
  const P=(x,z,y)=>[ox+(x-z)*a,oy+(x+z)*a/2-y*hh];
  list.sort((p,q)=>(p[0]+p[2]+p[1])-(q[0]+q[2]+q[1])||p[1]-q[1]);
  const poly=(pts,fill)=>{g.beginPath();g.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<4;i++)g.lineTo(pts[i][0],pts[i][1]);g.closePath();g.fillStyle=fill;g.fill();g.stroke();};
  g.lineWidth=.5;g.lineJoin='round';
  for(const [x,y,z,t] of list){
    const T=TYPES[t];let al=T.alpha||1;
    const above=y>cur;if(above)al*=.13;
    const cl=y===cur?1.12:1;
    let x0=x,x1=x+1,z0=z,z1=z+1;
    if(T.thin){const m=(1-T.thin)/2;x0+=m;x1-=m;z0+=m;z1-=m;}
    const top=T.liquid?y+.85:y+1;
    g.strokeStyle=above?'rgba(0,0,0,0)':'rgba(0,0,0,.22)';
    poly([P(x1,z0,top),P(x1,z1,top),P(x1,z1,y),P(x1,z0,y)],shade(T.c,.72*cl,al));
    poly([P(x0,z1,top),P(x1,z1,top),P(x1,z1,y),P(x0,z1,y)],shade(T.c,.86*cl,al));
    poly([P(x0,z0,top),P(x1,z0,top),P(x1,z1,top),P(x0,z1,top)],shade(T.c,1.08*cl,al));
  }
}

function render(){
  $('ynum').textContent=cur;$('layer').value=cur;
  const n=noteFor(cur);
  $('ntitle').textContent=n[2];$('ntext').textContent=n[3];
  $('nrange').textContent=n[0]===n[1]?'':`Y ${n[0]}–${n[1]}`;
  $('prev').disabled=cur===0;$('next').disabled=cur===YMAX;
  renderMats();drawTop();drawIso();
}
function go(n){cur=Math.max(0,Math.min(YMAX,n));render();}
$('prev').onclick=()=>go(cur-1);
$('next').onclick=()=>go(cur+1);
$('layer').oninput=e=>go(+e.target.value);
$('rot').onclick=()=>{rot=(rot+1)%4;drawIso();};
$('ghost').onchange=drawIso;
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT'&&e.target.type==='range')return;
  if(e.key==='ArrowRight'||e.key==='ArrowUp'){go(cur+1);e.preventDefault();}
  if(e.key==='ArrowLeft'||e.key==='ArrowDown'){go(cur-1);e.preventDefault();}
});
new ResizeObserver(()=>{drawTop();drawIso();}).observe(document.querySelector('.stage'));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawTop();drawIso();});
new MutationObserver(()=>{drawTop();drawIso();}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
renderTotals();render();

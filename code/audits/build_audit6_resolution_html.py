"""Build Audit6-resolution.html from Audit6-disagreements.csv (no source column: the page does not reveal the key)."""
import csv, json, html
rows=[dict(pair=r['pair'],slot=r['slot'],dna=r['DNA'],ee=r['EE'],eenote=r['EE note for the pair'],s=r['sentence']) for r in csv.DictReader(open('Audit6-disagreements.csv',encoding='utf-8-sig'))]
dn={r['pair']:r['note'].strip() for r in csv.DictReader(open('Audit6-answers-DNA.csv',encoding='utf-8-sig'))}
for r in rows: r['dnanote']=dn.get(r['pair'],'')
DEF=open('build_audit6_html.py',encoding='utf-8').read()
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit 6 resolution</title><style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1d1b;--mut:#6b6a66;--line:#dedcd5;--acc:#1f5f8b;--yes:#2e7d4f;--no:#a23b3b;--na:#8a6d1a}
@media(prefers-color-scheme:dark){:root{--bg:#191918;--card:#232322;--ink:#ecebe6;--mut:#a3a29c;--line:#3a3936;--acc:#7fb6dc;--yes:#6fc493;--no:#e08a8a;--na:#d9b95a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:20px 16px 120px}h1{font-size:1.35rem;margin:0 0 4px}p.lead{color:var(--mut);margin:0 0 14px}
.top{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap;z-index:2}
.top .count{font-weight:600;margin-right:auto}button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:7px 12px;cursor:pointer}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}.card.done{border-left:5px solid var(--acc)}
.head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;color:var(--mut);font-size:.9rem}.head b{color:var(--ink);font-size:1rem}
.sent{font-size:1.05rem;margin:10px 0 12px;overflow-wrap:anywhere}.who{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
@media(max-width:560px){.who{grid-template-columns:1fr}}.who div{border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:.92rem}
.who .lab{color:var(--mut);font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}.claim{color:var(--yes);font-weight:600}.not{color:var(--no);font-weight:600}.n{color:var(--mut);display:block;margin-top:4px}
.opts{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.opts label{border:1px solid var(--line);border-radius:8px;padding:7px 12px;cursor:pointer;user-select:none}
.opts input{position:absolute;opacity:0}.opts label:has(input:checked){color:#fff;border-color:transparent}.opts label.c:has(input:checked){background:var(--yes)}.opts label.x:has(input:checked){background:var(--no)}.opts label.u:has(input:checked){background:var(--na)}
.opts label:has(input:focus-visible){outline:2px solid var(--acc)}textarea{width:100%;min-height:64px;font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px}
details{margin:12px 0;border:1px solid var(--line);border-radius:8px;padding:8px 12px;background:var(--card)}summary{cursor:pointer;font-weight:600}
.gen textarea{min-height:90px}#msg{color:var(--mut);font-size:.9rem}
</style></head><body><main>
<h1>Audit 6: resolving the 20 differing judgements</h1>
<p class="lead">DNA and EE, together. Each card is one sentence that one of you judged a claim and the other did not. The page does not show where a sentence came from. Change a judgement only if the definition persuades you; "Not agreed" is an acceptable outcome.</p>
<details class="gen" open><summary>Rule agreed for recurring types (fill this in first)</summary>
<p style="color:var(--mut);margin:6px 0">Most differences are of three types: awards and rankings; statements of intent or acknowledgement; descriptions of an activity or reporting process.</p>
<textarea id="general" placeholder="What we agreed on these types, and anything else from the meeting"></textarea></details>
<div class="top"><span class="count" id="count"></span><span id="msg"></span><button id="dl" class="primary">Download CSV</button></div>
<div id="cards"></div></main><script>
const ROWS=__ROWS__;const KEY='audit6-resolution-v1';let st={};try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(st));msg.textContent='saved in this browser '+new Date().toLocaleTimeString()}catch(e){msg.textContent='not saved in browser: use Download CSV'}upd()};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cls=v=>v==='claim'?'claim':'not';const cards=document.getElementById('cards'),msg=document.getElementById('msg');
ROWS.forEach((r,i)=>{const id=r.pair+r.slot,v=st[id]||{};const d=document.createElement('section');d.className='card';d.id='c'+id;
d.innerHTML=`<div class="head"><b>${i+1} of ${ROWS.length}</b><span>pair ${esc(r.pair)}, sentence ${esc(r.slot)}</span></div><div class="sent">${esc(r.s)}</div>
<div class="who"><div><span class="lab">DNA</span><br><span class="${cls(r.dna)}">${esc(r.dna)}</span>${r.dnanote?`<span class="n">Note on the pair: ${esc(r.dnanote)}</span>`:''}</div>
<div><span class="lab">EE</span><br><span class="${cls(r.ee)}">${esc(r.ee)}</span>${r.eenote?`<span class="n">Note on the pair: ${esc(r.eenote)}</span>`:''}</div></div>
<div class="opts">${[['claim','Claim','c'],['not claim','Not a claim','x'],['not agreed','Not agreed','u']].map(o=>`<label class="${o[2]}"><input type="radio" name="r${id}" value="${o[0]}" ${v.res===o[0]?'checked':''}>${o[1]}</label>`).join('')}</div>
<textarea placeholder="Reason / note from the discussion">${esc(v.note||'')}</textarea>`;
d.querySelectorAll('input').forEach(x=>x.onchange=()=>{st[id]={...(st[id]||{}),res:x.value};save()});
d.querySelector('textarea').oninput=e=>{st[id]={...(st[id]||{}),note:e.target.value};save()};cards.appendChild(d)});
const g=document.getElementById('general');g.value=st._general||'';g.oninput=()=>{st._general=g.value;save()};
function upd(){let n=0;ROWS.forEach(r=>{const id=r.pair+r.slot,ok=!!(st[id]&&st[id].res);n+=ok;document.getElementById('c'+id).classList.toggle('done',ok)});document.getElementById('count').textContent=n+' of '+ROWS.length+' decided'}upd();
const q=s=>'"'+String(s||'').replace(/"/g,'""')+'"';
document.getElementById('dl').onclick=()=>{const t=new Date().toISOString();let L=['pair,slot,DNA,EE,resolved,note,saved_at'];
ROWS.forEach(r=>{const v=st[r.pair+r.slot]||{};L.push([r.pair,r.slot,q(r.dna),q(r.ee),q(v.res),q(v.note),q(t)].join(','))});L.push(['general','',q(''),q(''),q(''),q(st._general),q(t)].join(','));
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\\ufeff'+L.join('\\n')],{type:'text/csv'}));a.download='Audit6-resolution-DNA-EE.csv';a.click()};
</script></body></html>'''
open('Audit6-resolution.html','w',encoding='utf-8').write(page.replace('__ROWS__',json.dumps(rows,ensure_ascii=False).replace('</','<\\/')))
print(len(rows))

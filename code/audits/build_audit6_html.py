"""Interactive HTML version of the Audit 6 form (same 45 pairs as the workbook; built from the workbook, not from the key)."""
import openpyxl, json, html
ws = openpyxl.load_workbook('revision/audits/Audit6-Claim-or-not-pairs-DNA.xlsx')['Pairs']
P = [dict(n=r[0], ca=r[1], a=r[2], cb=r[3], b=r[4]) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
T = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claim or not — Audit 6</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1f2933;--muted:#5b6673;--line:#d9dee5;--accent:#174f86;--accent-soft:#e6eef7;--ok:#1e7a4c;--warn:#9a5b00}
@media (prefers-color-scheme:dark){:root{--bg:#14181d;--card:#1d232b;--ink:#e8ecf1;--muted:#9aa6b3;--line:#323b46;--accent:#7fb2e5;--accent-soft:#22303f;--ok:#63c796;--warn:#e0b060}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 2px}.sub{color:var(--muted);font-size:14px;margin:0 0 12px}
.bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.bar input{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);width:150px}
.prog{flex:1;min-width:160px;height:8px;background:var(--line);border-radius:4px;overflow:hidden}.prog i{display:block;height:100%;background:var(--accent);width:0}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:14.5px}
summary{cursor:pointer;font-weight:600}details ul{margin:6px 0 8px 18px;padding:0}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media (max-width:760px){.pair{grid-template-columns:1fr}}
.s{background:var(--card);border:2px solid var(--line);border-radius:10px;padding:14px 16px;min-height:150px}
.s.on{border-color:var(--accent);background:var(--accent-soft)}
.s .tag{font-weight:700;color:var(--accent);font-size:13px;letter-spacing:.04em}.s .co{color:var(--muted);font-size:13px;margin-left:8px}
.s p{margin:8px 0 0;font-size:17px}
.ans{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}@media (max-width:560px){.ans{grid-template-columns:1fr 1fr}}
button{font:inherit;cursor:pointer;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:10px 12px}
button:hover{border-color:var(--accent)}.ans button{font-weight:600;padding:14px 8px}.ans button.sel{background:var(--accent);border-color:var(--accent);color:#fff}
@media (prefers-color-scheme:dark){.ans button.sel{color:#0e1318}}
.ans small{display:block;font-weight:400;color:inherit;opacity:.75;font-size:12px}
textarea{width:100%;font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);min-height:44px}
.nav{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}.nav .sp{flex:1}
.dots{display:flex;flex-wrap:wrap;gap:4px;margin:16px 0}.dots b{width:26px;height:26px;border-radius:5px;border:1px solid var(--line);font-size:11px;font-weight:500;display:grid;place-items:center;cursor:pointer;background:var(--card);color:var(--muted)}
.dots b.done{background:var(--accent-soft);color:var(--ink);border-color:var(--accent)}.dots b.cur{outline:2px solid var(--accent)}
.primary{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600}@media (prefers-color-scheme:dark){.primary{color:#0e1318}}
.msg{font-size:14px;color:var(--muted)}.msg.ok{color:var(--ok)}.msg.warn{color:var(--warn)}
.count{font-variant-numeric:tabular-nums;color:var(--muted);font-size:14px}
</style></head><body><div class="wrap">
<h1>Is it a claim?</h1><p class="sub">Audit 6 · 45 pairs, 90 sentences · work alone, and do not open the key</p>
<div class="bar"><label>Auditor <input id="who" placeholder="DNA or EE" maxlength="12"></label><div class="prog"><i id="pg"></i></div><span class="count" id="cnt"></span></div>
<details open><summary>Definition of a claim (the instruction given to the extraction model, word for word)</summary>
<p>A “claim” is any statement where the company asserts:</p><ul><li>A contribution to a sustainability goal or target</li><li>An achievement, metric, or outcome related to ESG performance</li><li>A commitment, target, or plan for sustainability improvement</li><li>An alignment with SDGs, GRI standards, or other sustainability frameworks</li></ul>
<p>Not a claim:</p><ul><li>Generic background text about global sustainability challenges</li><li>Descriptions of the SDG framework itself</li><li>Boilerplate language (copyright notices, disclaimers, table of contents)</li><li>Procedural descriptions of the reporting process</li></ul>
<p>Judge each sentence on its own, as written. A pair may hold two claims, one or none. If you cannot decide, skip the pair and say why in the note.</p></details>
<div class="count" id="ttl"></div>
<div class="pair"><div class="s" id="sa"><span class="tag">A</span><span class="co" id="ca"></span><p id="ta"></p></div><div class="s" id="sb"><span class="tag">B</span><span class="co" id="cb"></span><p id="tb"></p></div></div>
<div class="ans" id="ans"><button data-v="A">A is a claim<small>key: A</small></button><button data-v="B">B is a claim<small>key: B</small></button><button data-v="Both">Both<small>key: 2</small></button><button data-v="Neither">Neither<small>key: N</small></button></div>
<textarea id="note" placeholder="Note (optional): why you hesitated or skipped"></textarea>
<div class="nav"><button id="prev">← Previous</button><button id="next">Next →</button><button id="clr">Clear this answer</button><span class="sp"></span><button id="load">Load saved answers…</button><input type="file" id="file" accept=".csv" hidden><button class="primary" id="save">Download answers (CSV)</button></div>
<p class="msg" id="msg"></p><div class="dots" id="dots"></div>
<p class="msg">Your answers are kept in this browser tab as you go. Use “Download answers” when you finish, or at any time to keep a copy, and save the file in <code>revision/audits/</code>. To continue later, open this page again and use “Load saved answers”.</p>
</div><script>
const P=__DATA__;const A={},N={};let i=0;const $=id=>document.getElementById(id);const KEY="audit6-answers-v1";
function store(){try{localStorage.setItem(KEY,JSON.stringify({A,N,who:$("who").value,i}))}catch(e){}}
function restore(){try{const s=JSON.parse(localStorage.getItem(KEY)||"null");if(s){Object.assign(A,s.A||{});Object.assign(N,s.N||{});$("who").value=s.who||"";i=Math.min(P.length-1,s.i||0)}}catch(e){}}
function show(){const p=P[i];$("ttl").textContent="Pair "+p.n+" of "+P.length;$("ca").textContent=p.ca;$("cb").textContent=p.cb;$("ta").textContent=p.a;$("tb").textContent=p.b;
 const v=A[p.n]||"";document.querySelectorAll("#ans button").forEach(b=>b.classList.toggle("sel",b.dataset.v===v));
 $("sa").classList.toggle("on",v==="A"||v==="Both");$("sb").classList.toggle("on",v==="B"||v==="Both");$("note").value=N[p.n]||"";
 const d=Object.keys(A).filter(k=>A[k]).length;$("pg").style.width=(100*d/P.length)+"%";$("cnt").textContent=d+" of "+P.length+" answered";
 $("dots").innerHTML=P.map((q,k)=>'<b class="'+(A[q.n]?"done ":"")+(k===i?"cur":"")+'" data-k="'+k+'" title="Pair '+q.n+(A[q.n]?": "+A[q.n]:"")+'">'+q.n+"</b>").join("");
 $("prev").disabled=i===0;$("next").disabled=i===P.length-1;store()}
function set(v){A[P[i].n]=v;document.querySelector("details").open=false;if(i<P.length-1){show();setTimeout(()=>{i++;show()},180)}else show()}
document.querySelectorAll("#ans button").forEach(b=>b.onclick=()=>set(b.dataset.v));
$("prev").onclick=()=>{if(i>0){i--;show()}};$("next").onclick=()=>{if(i<P.length-1){i++;show()}};$("clr").onclick=()=>{delete A[P[i].n];show()};
$("note").oninput=e=>{N[P[i].n]=e.target.value;store()};$("who").oninput=store;
$("dots").onclick=e=>{const k=e.target.dataset.k;if(k!==undefined){i=+k;show()}};
document.addEventListener("keydown",e=>{if(["TEXTAREA","INPUT"].includes(e.target.tagName))return;const k=e.key.toLowerCase();
 if(k==="a")set("A");else if(k==="b")set("B");else if(k==="2")set("Both");else if(k==="n")set("Neither");else if(e.key==="ArrowLeft")$("prev").click();else if(e.key==="ArrowRight")$("next").click()});
const q=s=>'"'+String(s==null?"":s).replace(/"/g,'""')+'"';
$("save").onclick=()=>{const who=($("who").value||"").trim().toUpperCase();if(!who){$("msg").className="msg warn";$("msg").textContent="Please type the auditor's initials first (DNA or EE).";$("who").focus();return}
 const rows=[["pair","answer","note","auditor","saved_at"].join(",")].concat(P.map(p=>[p.n,q(A[p.n]||""),q(N[p.n]||""),q(who),q(new Date().toISOString())].join(",")));
 const blob=new Blob(["﻿"+rows.join("\r\n")],{type:"text/csv"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="Audit6-answers-"+who+".csv";document.body.appendChild(a);a.click();a.remove();
 const d=Object.keys(A).filter(k=>A[k]).length;$("msg").className="msg ok";$("msg").textContent="Downloaded Audit6-answers-"+who+".csv with "+d+" of "+P.length+" pairs answered. Save it in revision/audits/."};
$("load").onclick=()=>$("file").click();
$("file").onchange=e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();r.onload=()=>{let n=0;String(r.result).replace(/^﻿/,"").split(/\r?\n/).slice(1).forEach(line=>{const m=line.match(/^(\d+),"((?:[^"]|"")*)","((?:[^"]|"")*)","((?:[^"]|"")*)"/);if(m){const k=+m[1];if(m[2]){A[k]=m[2];n++}else delete A[k];if(m[3])N[k]=m[3].replace(/""/g,'"');if(m[4])$("who").value=m[4]}});
 $("msg").className="msg ok";$("msg").textContent="Loaded "+n+" answers from "+f.name+".";show()};r.readAsText(f)};
restore();if(Object.keys(A).length)document.querySelector("details").open=false;show();
</script></body></html>'''
open('revision/audits/Audit6-Claim-or-not.html', 'w', encoding='utf8').write(T.replace('__DATA__', json.dumps(P, ensure_ascii=False).replace('</', '<\\/')))
print('pairs', len(P))

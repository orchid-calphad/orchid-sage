#!/usr/bin/env python3
"""Render a standalone ORCHID assessment dashboard (one HTML file, no network) from an assessment-results document.

  python3 tools/build_dashboard.py DASHBOARD_DATA.json OUT.html [--snapshot] [--no-fonts]

System-agnostic: everything shown comes from the document (schema/assessment-results.schema.json); a `pending`
object is shown as "Pending" with its reason, never as a number. Colours, fonts and logo come from tools/palette.json
and tools/assets/ (ORCHID brand: site tokens, IBM Plex embedded, evidence-class colours never reused, status by shape
and line style as well as colour). Figures listed in `figures` are embedded as data URIs. The dashboard always renders in the ORCHID style (PI 6 Nov 2026: our tools
produce it); light and dark follow the viewer's system setting only, with no theme switch. Generalised from the Cu-Zr
campaign renderer (cuzr-protocol-20261104 dashboard_views.render), read only.
Also prints a WCAG contrast report of the data colours against the card colour in both themes.
"""
import base64
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402
import frozen  # noqa: E402

T = Path(__file__).resolve().parent
PAL = json.loads((T / "palette.json").read_text())


def lum(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_report():
    out = []
    for theme in ("light", "dark"):
        card = PAL["ui"][theme]["card"]
        for grp in ("data", "status", "topology_class"):
            for k, v in PAL[grp].items():
                if isinstance(v, dict) and theme in v:
                    out.append((theme, f"{grp}.{k}", v[theme], round(contrast(v[theme], card), 2)))
        for k in ("fg", "muted", "accent", "ok"):
            out.append((theme, f"ui.{k}", PAL["ui"][theme][k], round(contrast(PAL["ui"][theme][k], card), 2)))
    return out


def css_vars():
    def block(theme):
        u = PAL["ui"][theme]
        v = [f"--{k}:{c}" for k, c in u.items()]
        v += [f"--c-{k}:{c[theme]}" for k, c in PAL["data"].items() if isinstance(c, dict)]
        v += [f"--s-{k}:{c[theme]}" for k, c in PAL["status"].items() if isinstance(c, dict)]
        v += [f"--t-{k}:{c[theme]}" for k, c in PAL["topology_class"].items() if isinstance(c, dict)]
        v += [f"--n-{k}:{c[theme]}" for k, c in PAL["neutral"].items()]
        v += [f"--step{i}:{c}" for i, c in enumerate(PAL["steps"][theme])]
        return ";".join(v)
    return (f":root{{{block('light')};color-scheme:light}}"
            f"@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{{block('dark')};color-scheme:dark}}}}"
            f":root[data-theme=dark]{{{block('dark')};color-scheme:dark}}")


def fonts_css():
    out = []
    for fam, f, w, st in (("IBM Plex Sans", "IBMPlexSans-Regular.ttf", 400, "normal"), ("IBM Plex Sans", "IBMPlexSans-SemiBold.ttf", 600, "normal"),
                          ("IBM Plex Serif", "IBMPlexSerif-Italic.ttf", 400, "italic")):
        b = base64.b64encode((T / "assets" / f).read_bytes()).decode()
        out.append(f"@font-face{{font-family:'{fam}';src:url(data:font/ttf;base64,{b}) format('truetype');font-weight:{w};font-style:{st};font-display:swap}}")
    return "".join(out)


def data_uri(p):
    p = op.expand(p)
    mt = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg"}.get(p.suffix, "application/octet-stream")
    return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()


CSS = r"""
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 'IBM Plex Sans',system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--accent)}code,.mono{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12px;overflow-wrap:anywhere}
header{background:var(--card);border-bottom:1px solid var(--line);padding:18px 16px}
.hin{max-width:1240px;margin:auto;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.icon{height:26px;width:26px;display:block}.brand{font-weight:600;font-size:18px;letter-spacing:.02em}.ht{flex:1 1 280px;min-width:0}.status{color:var(--muted);font-size:12.5px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
h1{font-weight:600;font-size:26px;line-height:1.2;margin:2px 0}h2{font-weight:600;font-size:18px;margin:0 0 10px}h3{font-weight:600;font-size:15px;margin:14px 0 6px}
.kicker{font-family:'IBM Plex Serif',Georgia,serif;font-style:italic;color:var(--muted);font-size:14px}
.sub{color:var(--muted);font-size:13px}main{max-width:1240px;margin:auto;padding:16px}
.notice{background:var(--accent2);border-left:4px solid var(--accent);padding:12px 16px;border-radius:6px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:16px;min-width:0}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:14px}
.metric{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.metric b{display:block;font-weight:600;font-size:22px;overflow-wrap:anywhere}
small,.small{font-size:12px;color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:12.5px}.tw table{min-width:640px}th,td{text-align:left;padding:6px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;background:var(--accent2);color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:.04em}.scroll{max-height:420px;overflow:auto}.tw{overflow-x:auto}
svg.chart{width:100%;height:auto;display:block}svg text{fill:var(--fg);font-family:inherit}svg .mut{fill:var(--muted)}
.pending{color:var(--muted);font-style:italic}.pending:before{content:"Pending: ";font-style:normal;font-weight:600;color:var(--fg)}
.chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.chip{border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:12.5px;background:var(--card)}
.chip.lin{border-color:var(--accent)}.chip.pick{background:var(--accent);color:var(--card);border-color:var(--accent)}.chip.fail{border-style:dashed}
.arrow{color:var(--muted)}select,button{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
button{cursor:pointer;border-color:var(--accent)}figure{margin:0}figure img{width:100%;height:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
figcaption{font-size:12px;color:var(--muted);margin-top:4px}.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);margin-top:6px}
.legend span{display:inline-flex;align-items:center;gap:5px}.ok{color:var(--ok);font-weight:600}.no{font-weight:600}
details summary{cursor:pointer;color:var(--accent);margin:8px 0}footer{color:var(--muted);font-size:12px;padding:24px 0}
.ctl{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:8px;font-size:13px}
@media(max-width:820px){.grid{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}h1{font-size:21px}}
@media(max-width:420px){main{padding:12px}.panel{padding:12px}}
"""

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent),PAL=JSON.parse(document.getElementById('pal').textContent),SNAP=__SNAP__;
const $=id=>document.getElementById(id),esc=x=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const isP=x=>x&&typeof x==='object'&&x.status==='pending';const pend=x=>`<p class="pending">${esc(x.reason)}</p>`;
const num=(x,d=3)=>typeof x==='number'?x.toLocaleString('en-US',{maximumFractionDigits:d}):(x==null?'—':esc(x));
const cv=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const table=(h,rows)=>'<div class="tw"><table><thead><tr>'+h.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
// --- ORCHID badge hook: replaced by the "ORCHID Brand" design-system badge when it is specified (mark + "ORCHID vYYYY.MM").
function orchidBadge(release){return `<span class="chip" style="background:var(--accent2);color:var(--accent);border-color:var(--accent2)">${esc(release||'release pending')}</span>`}
function mark(kind,x,y,r,col,fill){r=r||4;const f=fill?col:'none',s=`stroke="${col}" stroke-width="1.4" fill="${f}"`;
 if(kind==='circle'||kind==='ring')return `<circle cx="${x}" cy="${y}" r="${r}" ${s}/>`;
 if(kind==='square')return `<rect x="${x-r}" y="${y-r}" width="${2*r}" height="${2*r}" ${s}/>`;
 if(kind==='triangle')return `<path d="M${x},${y-r*1.2}L${x+r*1.1},${y+r*.8}L${x-r*1.1},${y+r*.8}Z" ${s}/>`;
 if(kind==='diamond')return `<path d="M${x},${y-r*1.3}L${x+r},${y}L${x},${y+r*1.3}L${x-r},${y}Z" ${s}/>`;
 if(kind==='cross')return `<path d="M${x-r},${y-r}L${x+r},${y+r}M${x-r},${y+r}L${x+r},${y-r}" stroke="${col}" stroke-width="1.8"/>`;
 if(kind==='star')return `<path d="M${x},${y-r*1.5}L${x+r*.45},${y-r*.45}L${x+r*1.5},${y-r*.4}L${x+r*.7},${y+r*.35}L${x+r*.95},${y+r*1.45}L${x},${y+r*.8}L${x-r*.95},${y+r*1.45}L${x-r*.7},${y+r*.35}L${x-r*1.5},${y-r*.4}L${x-r*.45},${y-r*.45}Z" ${s}/>`;
 return `<circle cx="${x}" cy="${y}" r="${r}" ${s}/>`}
const TC=c=>({ok:['circle',cv('--t-ok'),true],wrong:['triangle',cv('--t-wrong'),false]}[c]||['square',cv('--t-unknown'),false]);
function axes(W,H,m,xl,yl,xt,yt){let o='';o+=`<path d="M${m.l},${m.t}V${H-m.b}H${W-m.r}" fill="none" stroke="${cv('--n-ink2')}" stroke-width="1"/>`;
 for(const [v,p] of xt)o+=`<path d="M${p},${H-m.b}v4" stroke="${cv('--n-ink2')}"/><text x="${p}" y="${H-m.b+16}" font-size="11" text-anchor="middle">${v}</text>`;
 for(const [v,p] of yt)o+=`<path d="M${m.l},${p}h-4" stroke="${cv('--n-ink2')}"/><text x="${m.l-6}" y="${p+4}" font-size="11" text-anchor="end">${v}</text>`;
 o+=`<text x="${(m.l+W-m.r)/2}" y="${H-4}" font-size="12" text-anchor="middle">${esc(xl)}</text><text x="12" y="${(m.t+H-m.b)/2}" font-size="12" text-anchor="middle" transform="rotate(-90 12 ${(m.t+H-m.b)/2})">${esc(yl)}</text>`;return o}
function ticks(a,b,n){if(a===b){a-=1;b+=1}const s=Math.pow(10,Math.floor(Math.log10((b-a)/n))),e=[1,2,5,10].map(k=>k*s).find(k=>(b-a)/k<=n)||s*10;const t=[];for(let v=Math.ceil(a/e)*e;v<=b+1e-12;v+=e)t.push(+v.toPrecision(12));return t}
function fmtT(v){return Math.abs(v)>=1e4||(Math.abs(v)<1e-2&&v!==0)?v.toExponential(1):String(+v.toPrecision(4))}

// ---------- header, metrics
function head(){$('title').textContent=D.title||D.id;$('meta').innerHTML=`${orchidBadge(D.orchid_release)} <code>${esc(D.specific_protocol)}</code> · instantiates <code>${esc(D.general_protocol)}</code> · pick ${esc(D.pick.step)} ${esc(D.pick.start)}`;
 $('fresh').textContent=(SNAP||D.snapshot.frozen?'FROZEN SNAPSHOT':'LIVE')+' · generated '+D.generated_utc+(D.snapshot.underlying_data_utc?' · data '+D.snapshot.underlying_data_utc:'');
 $('banner').innerHTML='<b>'+esc(D.snapshot.note)+'</b>'+(D.status_banner?'<br>'+esc(D.status_banner):'');
 const lin=D.steps.filter(s=>s.role==='lineage').length,starts=D.steps.reduce((a,s)=>a+(s.starts||0),0);
 const inv=Array.isArray(D.invariants)?D.invariants:[],ip=inv.filter(i=>i.pass).length;
 $('metrics').innerHTML=[['Pick',D.pick.label],[D.pick.objective_name.split('(')[0],num(D.pick.objective,2)],['Invariants within window',inv.length?ip+'/'+inv.length:'Pending'],['Steps (lineage) · starts',lin+' · '+starts]].map(([a,b])=>`<div class="metric"><small>${esc(a)}</small><b>${b}</b></div>`).join('')}
// ---------- figures
function figs(){const F=D.figures||[];$('figs').innerHTML=F.length?F.map(f=>`<figure><img alt="${esc(f.caption)}" src="${(window.FIG||{})[f.panel]||''}"><figcaption>${esc(f.caption)} · <code>${esc(f.file.path.split('/').pop())}</code> sha256 ${esc(f.file.sha256.slice(0,12))}…</figcaption></figure>`).join('<br>'):'<p class="pending">no computed figure on disk</p>'}
// ---------- steps
function steps(){const S=D.steps;$('chips').innerHTML=S.filter(s=>s.role==='lineage').map(s=>`<span class="chip lin${s.step===D.pick.step?' pick':''}">${esc(s.step)}${s.pick?' · '+esc(s.pick):''}</span>`).join('<span class="arrow">→</span>')+
 (S.some(s=>s.role!=='lineage')?'<span class="small" style="margin-left:8px">side / failed: </span>'+S.filter(s=>s.role!=='lineage').map(s=>`<span class="chip fail">${esc(s.step)} (${esc(s.role)})</span>`).join(' '):'');
 $('steptab').innerHTML=table(['Step','Role','Data added','Free','Starts','Pick','Objective','Right topology','Key results','Notes'],S.map(s=>[`<b>${esc(s.step)}</b><br><small>${esc(s.general_step)}</small>`,esc(s.role),esc(s.data_added),num(s.free_parameters),num(s.starts),esc(s.pick),num(s.objective,2),
 s.topology_ok==null?'—':(s.topology_ok?'<span class="ok">● yes</span>':'<span class="no">▲ no</span>')+(s.n_topology_ok!=null&&s.starts?` <small>(${s.n_topology_ok}/${s.starts} starts)</small>`:''),esc(s.key_results),'<small>'+esc(s.notes)+'</small>']))}
// ---------- states
function states(){const S0=D.states_evaluated;if(isP(S0)){$('states').innerHTML=pend(S0);return}const S=S0.filter(r=>r.x!=null&&r.match!=null);const Q=D.states_summary||{};
 const W=520,H=320,m={l:52,r:12,t:12,b:40},xs=S.map(r=>r.x),ts=S.map(r=>r.T_K),t0=Math.min(...ts),t1=Math.max(...ts);const X=x=>m.l+(W-m.l-m.r)*x,Y=t=>H-m.b-(H-m.t-m.b)*(t-t0)/(t1-t0||1);
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,'mole fraction','T (K)',[0,.25,.5,.75,1].map(v=>[v,X(v)]),ticks(t0,t1,5).map(v=>[v,Y(v)]));
 for(const r of S){o+=r.match?mark('circle',X(r.x),Y(r.T_K),2.6,cv('--s-match'),true):mark('cross',X(r.x),Y(r.T_K),3.4,cv('--s-mismatch'))}
 const fit=S.filter(r=>r.collection==='fit'),cov=S.filter(r=>r.collection==='coverage');const pc=(A,f)=>A.length?`${A.filter(f).length}/${A.length}`:'—';
 $('states').innerHTML=o+'</svg>'+`<p class="small">Exact assemblage match: fit ${pc(fit,r=>r.match)}, coverage ${pc(cov,r=>r.match)}; expected phases present: fit ${pc(fit,r=>r.contains_expected)}, coverage ${pc(cov,r=>r.contains_expected)}. Certainty tiers: ${esc(JSON.stringify(Q.tiers||{}))}. Partial tie lines are evaluated at the known vertex, so "present" is the fair test for them.</p>`+
 `<p class="small">ORCHID links: ${esc(JSON.stringify(Q.link_coverage||{}))} (bundle ${esc(Q.evidence_bundle_version||'')}).</p>`+
 '<details><summary>Mismatched states ('+S.filter(r=>!r.match).length+')</summary><div class="scroll">'+table(['T (K)','x','Expected','Calculated','Kind','Tier','ORCHID record / state'],S.filter(r=>!r.match).map(r=>[num(r.T_K,1),num(r.x,4),esc(r.expected.join(' + ')),esc((r.predicted||[]).join(' + ')),esc(r.kind),tier(r),lnk(r)]))+'</div></details>'+
 '<details><summary>All evaluated states ('+S.length+') with their ORCHID links</summary><div class="scroll">'+table(['T (K)','x','Expected','Calculated','Match','Tier','ORCHID record / state'],S.map(r=>[num(r.T_K,1),num(r.x,4),esc(r.expected.join(' + ')),esc((r.predicted||[]).join(' + ')),r.match?'<span class="ok">● yes</span>':'<span class="no">✕ no</span>',tier(r),lnk(r)]))+'</div></details>'}
function tier(r){const z=r.zpf_certainty;let o=z?esc(z.certainty_tier)+' <small>('+esc(z.energy_scale_J_per_mol_atom)+')</small>':'';if(r.exclusions&&r.exclusions.length)o+=(o?'<br>':'')+'<small>excl. '+r.exclusions.map(e=>esc(e.phase)+' '+esc(e.energy_scale_J_per_mol_atom)).join(', ')+'</small>';return o||'—'}
function lnk(r){if(r.orchid_link==='present'){return (r.orchid_links||[]).slice(0,3).map(l=>{const d=(l.paper_id||'').startsWith('doi:')?'https://doi.org/'+l.paper_id.slice(4):null;const t=esc((l.pid||'')+(l.state_id?' | '+l.state_id:''));
  return (d?`<a href="${esc(d)}" title="${t}" target="_blank" rel="noopener"><code>${esc(l.id)}</code></a>`:`<code title="${t}">${esc(l.id)}</code>`)+(l.state_id?` <code>${esc(l.state_id)}</code>`:'')+(l.in_release?' <small>v2026.10</small>':' <small>unreleased</small>')}).join('<br>')+((r.orchid_links||[]).length>3?` <small>+${r.orchid_links.length-3}</small>`:'')}
 return '<small class="no">missing: '+esc(r.missing_reason||'')+'</small><br><small><code>'+esc(r.intake_ref||'')+'</code></small>'+((r.orchid_ids||[]).length?'<br><code>'+esc(r.orchid_ids.slice(0,2).join(' '))+'</code>':'')}
// ---------- invariants
function invariants(){const I=D.invariants;if(isP(I)){$('inv').innerHTML=pend(I);return}
 $('inv').innerHTML=table(['Reaction','ORCHID ids','Observed (K)','Calculated (K)','ΔT (K)','Within window','Basis / note'],I.map(i=>[esc(i.reaction),((i.orchid_ids||[]).length>2?`<details><summary>${i.orchid_ids.length} ORC ids</summary>`+i.orchid_ids.map(x=>'<code style="white-space:nowrap">'+esc(x)+'</code>').join(' ')+'</details>':(i.orchid_ids||[]).map(x=>'<code style="white-space:nowrap">'+esc(x)+'</code>').join(' ')),num(i.observed_K,1)+(i.sigma_K?` ± ${i.sigma_K}`:''),num(i.calculated_K,1),num(i.dT_K,1),i.pass==null?'—':(i.pass?'<span class="ok">● yes</span>':'<span class="no">✕ no</span>'),'<small>'+esc(i.observed_basis)+(i.note?'; '+esc(i.note):'')+'</small>']));
 const W=520,H=40+22*I.length,m={l:200,r:16,t:10,b:34};const all=I.flatMap(i=>[i.observed_K,i.calculated_K]).filter(v=>v!=null),a=Math.min(...all)-20,b=Math.max(...all)+20,X=v=>m.l+(W-m.l-m.r)*(v-a)/(b-a);
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,'T (K)','',ticks(a,b,5).map(v=>[v,X(v)]),[]);
 I.forEach((i,k)=>{const y=m.t+10+22*k;o+=`<text x="${m.l-6}" y="${y+4}" font-size="10.5" text-anchor="end">${esc(i.reaction.slice(0,30))}</text>`;
  if(i.observed_K!=null&&i.calculated_K!=null)o+=`<path d="M${X(i.observed_K)},${y}H${X(i.calculated_K)}" stroke="${cv('--n-grey_m')}" stroke-width="2"/>`;
  if(i.observed_K!=null)o+=mark('square',X(i.observed_K),y,4,cv('--c-experimental'),true);if(i.calculated_K!=null)o+=mark('circle',X(i.calculated_K),y,4,cv('--c-orchid'),true)});
 $('invplot').innerHTML=o+'</svg><div class="legend"><span>'+`<svg width="12" height="12">${mark('square',6,6,4,cv('--c-experimental'),true)}</svg>`+' observed (experimental class)</span><span>'+`<svg width="12" height="12">${mark('circle',6,6,4,cv('--c-orchid'),true)}</svg>`+' calculated from the pick (ORCHID fit)</span></div>'}
// ---------- objective components
function comps(){const O=D.objective_components,E=Object.entries(O.components||{});const mx=Math.max(...E.map(([k,v])=>Math.abs(v)),1);
 $('comps').innerHTML='<p class="small">'+esc(O.name)+' · total '+num(O.total,2)+'</p>'+table(['Component','Value','Share of |total|'],E.map(([k,v])=>[esc(k),num(v,2),`<svg width="120" height="10"><rect width="${120*Math.abs(v)/mx}" height="10" fill="${cv('--c-orchid')}"/></svg>`]))+'<p class="small">'+esc(O.note)+'</p>'}
// ---------- per-dataset residuals
function residuals(){const R=D.per_dataset_residuals;if(isP(R)){$('resid').innerHTML=pend(R);return}
 const rows=[...R].sort((a,b)=>(b.rms_z||0)-(a.rms_z||0));$('resid').innerHTML='<div class="scroll">'+table(['Dataset','Group','Type','n','rms z','max |z|'],rows.map(r=>[`<code>${esc(r.dataset)}</code>`,esc(r.group),esc((r.type||'').replace('Residual','')),num(r.n),`<svg width="90" height="9"><rect width="${Math.min(90,90*Math.log10(1+(r.rms_z||0))/Math.log10(1+Math.max(...rows.map(q=>q.rms_z||0))))}" height="9" fill="${cv('--n-ink2')}"/></svg> `+num(r.rms_z,2),num(r.max_abs_z,2)]))+'</div><p class="small">'+esc(rows[0]?.unit)+'. Bars on a log(1 + z) scale.</p>'}
// ---------- one-shot shifts
function shifts(){const S=D.oneshot_shifts;if(isP(S)){$('shifts').innerHTML=pend(S);return}
 const steps=[...new Set(S.map(s=>s.step))],ids=[...new Set(S.map(s=>s.id))];const W=560,H=60+16*ids.length,m={l:170,r:16,t:10,b:34};
 const v=S.map(s=>s.shift_sigma).filter(x=>x!=null),a=Math.min(-2.5,...v),b=Math.max(2.5,...v),X=x=>m.l+(W-m.l-m.r)*(x-a)/(b-a);
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,'shift from the one-shot value (σ)','',ticks(a,b,6).map(x=>[x,X(x)]),[]);
 o+=`<rect x="${X(-1)}" y="${m.t}" width="${X(1)-X(-1)}" height="${H-m.t-m.b}" fill="${cv('--accent2')}"/><path d="M${X(0)},${m.t}V${H-m.b}" stroke="${cv('--n-grey_m')}"/>`;
 const MK=PAL.starts.markers;ids.forEach((id,k)=>{const y=m.t+10+16*k;o+=`<text x="${m.l-6}" y="${y+4}" font-size="10" text-anchor="end">${esc(id)}</text>`;
  steps.forEach((st,j)=>{const s=S.find(q=>q.id===id&&q.step===st);if(!s||s.shift_sigma==null)return;const last=j===steps.length-1;o+=mark(MK[j%MK.length],X(s.shift_sigma),y,3.4,last?cv('--c-orchid'):cv('--n-ink2'),last)})});
 $('shifts').innerHTML=o+'</svg><div class="legend">'+steps.map((s,j)=>`<span><svg width="12" height="12">${mark(MK[j%MK.length],6,6,3.4,j===steps.length-1?cv('--c-orchid'):cv('--n-ink2'),j===steps.length-1)}</svg>${esc(s)}</span>`).join('')+'<span>shaded: ±1σ</span></div>'}
// ---------- checks
function kv(o){if(isP(o))return pend(o);return '<div class="tw"><table><tbody>'+Object.entries(o).map(([k,v])=>`<tr><th>${esc(k)}</th><td>${typeof v==='object'&&v!==null?(isP(v)?pend(v):'<code>'+esc(JSON.stringify(v))+'</code>'):esc(v)}</td></tr>`).join('')+'</tbody></table></div>'}
function checks(){const C=D.checks;$('checks').innerHTML=Object.entries(C).map(([k,v])=>`<h3>${esc(k.replaceAll('_',' '))}</h3>`+kv(v)).join('')}
// ---------- trajectory timeline
const R=D.trajectory.runs;
function order(){const st=[...new Set(R.map(r=>r.step))];return st}
function timeline(){const comp=$('comp').value,logy=$('logy').checked;const st=order();let off=0;const seg=[];
 for(const s of st){const rs=R.filter(r=>r.step===s);const n=Math.max(1,...rs.map(r=>r.points[r.points.length-1].eval));seg.push({s,off,n,role:rs[0].role});off+=n+Math.max(5,n*.04)}
 const val=p=>comp==='objective'?p.objective:(p.components||{})[comp];const pts=[];for(const r of R){const g=seg.find(q=>q.s===r.step);for(const p of r.points){const v=val(p);if(v!=null)pts.push([g.off+p.eval,v])}}
 const W=900,H=350,m={l:64,r:12,t:32,b:42};if(!pts.length){$('timeline').innerHTML='<p class="pending">no values for this component</p>';return}
 const tr=v=>logy?Math.log10(Math.max(1e-6,-v)):v;const ys=pts.map(p=>tr(p[1])),y0=Math.min(...ys),y1=Math.max(...ys),X=x=>m.l+(W-m.l-m.r)*x/off,Y=v=>logy?m.t+(H-m.t-m.b)*(tr(v)-y0)/(y1-y0||1):H-m.b-(H-m.t-m.b)*(v-y0)/(y1-y0||1);
 const yt=logy?ticks(y0,y1,5).map(e=>[fmtT(-Math.pow(10,e)),m.t+(H-m.t-m.b)*(e-y0)/(y1-y0||1)]):ticks(y0,y1,5).map(v=>[fmtT(v),Y(v)]);
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,'evaluation (cumulative across steps)',(comp==='objective'?D.trajectory.objective_name:comp)+(logy?' (log of −value)':''),[],yt);
 seg.forEach((g,i)=>{o+=`<path d="M${X(g.off)},${m.t}V${H-m.b}" stroke="${cv('--line')}" stroke-dasharray="3 3"/><text x="${X(g.off)+3}" y="${m.t-6+(i%2)*11}" font-size="10" class="mut">${esc(g.s.replace('step','').slice(0,16))}</text>`});
 for(const r of R){const g=seg.find(q=>q.s===r.step);const P=r.points.filter(p=>val(p)!=null);if(!P.length)continue;const col=r.is_pick?cv('--c-orchid'):cv('--n-ink2');
  const d=P.map((p,i)=>(i?'L':'M')+X(g.off+p.eval).toFixed(1)+','+Y(val(p)).toFixed(1)).join('');o+=`<path d="${d}" fill="none" stroke="${col}" stroke-width="${r.is_pick?2:1}" opacity="${r.is_pick?1:.55}" ${r.recorded?'':'stroke-dasharray="2 3"'}><title>${esc(r.step+' '+r.start)}</title></path>`;
  const e=P[P.length-1];const [mk,c,f]=TC(r.final_topology_class);o+=r.is_pick?mark('star',X(g.off+e.eval),Y(val(e)),6.5,cv('--c-orchid'),true):mark(mk,X(g.off+e.eval),Y(val(e)),3.5,c,f)}
 $('timeline').innerHTML=o+'</svg>';$('tlnote').textContent=(R.some(r=>!r.recorded)?'Dashed: trajectory not recorded (start and end only, never interpolated). ':'')+D.trajectory.component_note}
function compSel(){const ks=new Set();R.forEach(r=>r.points.forEach(p=>Object.keys(p.components||{}).forEach(k=>ks.add(k))));$('comp').innerHTML=['objective',...ks].map(k=>`<option>${esc(k)}</option>`).join('')}
// ---------- parameter traces
function ptrace(){const T=D.trajectory,P=D.projection,k=+$('param').value;const sc=isP(P)?1:P.scale[k],t1=T.oneshot_theta[k];const st=order();let off=0;const seg=[];
 for(const s of st){const rs=R.filter(r=>r.step===s);const n=Math.max(1,...rs.map(r=>r.points[r.points.length-1].eval));seg.push({s,off});off+=n+Math.max(5,n*.04)}
 const pts=[];R.forEach(r=>{const g=seg.find(q=>q.s===r.step);r.points.forEach(p=>{if(p.theta)pts.push((p.theta[k]-t1)/sc)})});const a=Math.min(-1,...pts),b=Math.max(1,...pts);
 const W=900,H=260,m={l:64,r:12,t:12,b:42},X=x=>m.l+(W-m.l-m.r)*x/off,Y=v=>H-m.b-(H-m.t-m.b)*(v-a)/(b-a);
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,'evaluation (cumulative across steps)','(θ − θ one-shot) / scale',[],ticks(a,b,6).map(v=>[fmtT(v),Y(v)]));
 o+=`<rect x="${m.l}" y="${Y(1)}" width="${W-m.l-m.r}" height="${Y(-1)-Y(1)}" fill="${cv('--accent2')}"/>`;seg.forEach(g=>o+=`<path d="M${X(g.off)},${m.t}V${H-m.b}" stroke="${cv('--line')}" stroke-dasharray="3 3"/>`);
 R.forEach(r=>{const g=seg.find(q=>q.s===r.step);const Q=r.points.filter(p=>p.theta);if(!Q.length)return;const col=r.is_pick?cv('--c-orchid'):cv('--n-ink2');
  o+=`<path d="${Q.map((p,i)=>(i?'L':'M')+X(g.off+p.eval).toFixed(1)+','+Y((p.theta[k]-t1)/sc).toFixed(1)).join('')}" fill="none" stroke="${col}" stroke-width="${r.is_pick?2:1}" opacity="${r.is_pick?1:.5}" ${r.recorded?'':'stroke-dasharray="2 3"'}/>`});
 $('ptrace').innerHTML=o+'</svg>';$('pnote').textContent=`${T.parameter_labels[k]} (${T.parameter_names[k]}, ${T.parameter_units[k]}); scale ${num(sc,4)}; shaded ±1 scale. Scale basis: `+(isP(P)?'—':P.scale_basis)}
// ---------- projection
function proj(){const P=D.projection;if(isP(P)){$('proj').innerHTML=pend(P);return}
 const pr=th=>{let u=0,v=0;for(let i=0;i<th.length;i++){const z=th[i]/P.scale[i]-P.center[i]/P.scale[i];u+=z*P.basis[i][0];v+=z*P.basis[i][1]}return [u,v]};
 const all=[];R.forEach(r=>r.points.forEach(p=>{if(p.theta)all.push(pr(p.theta))}));(P.uq_points||[]).forEach(q=>all.push(q.xy));
 const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]),x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys),pad=.05;
 const W=560,H=440,m={l:52,r:12,t:12,b:42},X=x=>m.l+(W-m.l-m.r)*((x-x0)/(x1-x0||1)*(1-2*pad)+pad),Y=y=>H-m.b-(H-m.t-m.b)*((y-y0)/(y1-y0||1)*(1-2*pad)+pad);
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,`PC1 (${(100*P.explained_variance_ratio[0]).toFixed(1)} %)`,`PC2 (${(100*P.explained_variance_ratio[1]).toFixed(1)} %)`,[],[]);
 if($('uq').checked)(P.uq_points||[]).forEach(q=>{o+=q.kind==='draw'?`<circle cx="${X(q.xy[0])}" cy="${Y(q.xy[1])}" r="1.3" fill="${cv('--n-grey_m')}"/>`:mark('diamond',X(q.xy[0]),Y(q.xy[1]),4.5,cv('--n-ink'),false)});
 R.forEach(r=>{const Q=r.points.filter(p=>p.theta).map(p=>pr(p.theta));if(Q.length<1)return;const col=r.is_pick?cv('--c-orchid'):cv('--n-ink2');
  if(Q.length>1)o+=`<path d="${Q.map((q,i)=>(i?'L':'M')+X(q[0]).toFixed(1)+','+Y(q[1]).toFixed(1)).join('')}" fill="none" stroke="${col}" stroke-width="${r.is_pick?1.8:.8}" opacity="${r.is_pick?1:.45}" ${r.recorded?'':'stroke-dasharray="2 3"'}><title>${esc(r.step+' '+r.start)}</title></path>`;
  const e=Q[Q.length-1];const [mk,c,f]=TC(r.final_topology_class);o+=r.is_pick?mark('star',X(e[0]),Y(e[1]),7,cv('--c-orchid'),true):mark(mk,X(e[0]),Y(e[1]),3.2,c,f)});
 const s1=pr(D.trajectory.oneshot_theta);o+=mark('star',X(s1[0]),Y(s1[1]),6,cv('--c-dft'),true);
 $('proj').innerHTML=o+'</svg><div class="legend"><span><svg width="14" height="14">'+mark('star',7,7,5,cv('--c-dft'),true)+'</svg>one-shot (MLIP/DFT class)</span><span><svg width="14" height="14">'+mark('circle',7,7,4,cv('--t-ok'),true)+'</svg>right topology</span><span><svg width="14" height="14">'+mark('triangle',7,7,4,cv('--t-wrong'),false)+'</svg>wrong topology</span><span><svg width="14" height="14">'+mark('square',7,7,4,cv('--t-unknown'),false)+'</svg>not evaluated</span><span style="color:var(--c-orchid)">★ — pick and its path</span>'+((P.uq_points||[]).length?'<span>· grey dots: Laplace draws; ◇ modes</span>':'')+'</div>';
 $('projnote').textContent=P.method+'. Scale: '+P.scale_basis+'. '+(P.note||'')}
// ---------- distance from one-shot by phase
function dist(){const T=D.trajectory,P=D.projection;if(isP(P)){$('dist').innerHTML=pend(P);return}const phs=[...new Set(T.phase_of_parameter)];
 const ends=R.filter(r=>r.points.length&&r.points[r.points.length-1].theta&&r.step!==R[0].step);
 const dd=(th,ph)=>Math.sqrt(T.phase_of_parameter.reduce((a,p,i)=>p===ph?a+Math.pow((th[i]-T.oneshot_theta[i])/P.scale[i],2):a,0));
 const W=560,H=50+26*phs.length,m={l:110,r:16,t:10,b:36};const vals=ends.flatMap(r=>phs.map(ph=>dd(r.points[r.points.length-1].theta,ph)));const b=Math.max(1,...vals),X=v=>m.l+(W-m.l-m.r)*v/b;
 let o=`<svg class="chart" viewBox="0 0 ${W} ${H}">`+axes(W,H,m,'distance from the one-shot (scale units, per phase)','',ticks(0,b,5).map(v=>[v,X(v)]),[]);
 phs.forEach((ph,k)=>{const y=m.t+14+26*k;o+=`<text x="${m.l-6}" y="${y+4}" font-size="11" text-anchor="end">${esc(ph)}</text>`;ends.forEach(r=>{const v=dd(r.points[r.points.length-1].theta,ph);const [mk,c,f]=TC(r.final_topology_class);o+=mark(r.is_pick?'star':mk,X(v),y+(r.is_pick?0:((r.start.charCodeAt(r.start.length-1)%5)-2)*2),r.is_pick?5:2.8,r.is_pick?cv('--c-orchid'):c,r.is_pick||f)})});
 $('dist').innerHTML=o+'</svg><p class="small">End point of every start of every fit step; the pick is the accent star. Distance = sqrt of the sum over that phase\'s parameters of ((θ − θ one-shot)/scale)². Small vertical offsets separate starts.</p>'}
// ---------- UQ, decisions, next, provenance
function uq(){const U=D.uq;if(isP(U)){$('uqp').innerHTML=pend(U);return}$('uqp').innerHTML='<p>'+esc(U.method)+'</p>'+kv(U.summary)+(U.modes?'<h3>Modes</h3>'+table(Object.keys(U.modes[0]),U.modes.map(m=>Object.values(m).map(v=>typeof v==='number'?num(v,3):esc(v)))):'')+'<p class="small">'+esc(U.note||'')+'</p>'}
function rest(){$('dec').innerHTML='<div class="scroll">'+table(['Date','Who','Decision','Why','Source'],D.decisions.map(x=>[esc(x.date),esc(x.who),esc(x.decision)+(x.quote?`<br><small>“${esc(x.quote)}”</small>`:''),esc(x.why),'<small>'+esc(x.source)+'</small>']))+'</div>';
 $('next').innerHTML='<ol>'+(D.next_actions||[]).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol><h3>ORCHID intake</h3>'+kv(D.orchid_intake);
 $('comp_t').innerHTML=table(['Host','What','Processes','Status'],(D.computation||[]).map(c=>[esc(c.host),esc(c.what),esc(c.pids||''),esc(c.status)]))+'<p class="small">Frozen snapshot: process states are as recorded in the campaign files, not checked live.</p>';
 const A=[...D.artifacts,...D.provenance.inputs];$('prov').innerHTML='<p>Extractor <code>'+esc(D.provenance.extractor.path)+'</code> sha256 <code>'+esc(D.provenance.extractor.sha256)+'</code></p><div class="scroll">'+table(['Role','Path','sha256','Storage'],A.map(a=>[esc(a.role||''),'<code>'+esc(a.path)+'</code>','<code>'+esc(a.sha256)+'</code>',esc(a.storage_class)]))+'</div>'}
function all(){head();figs();steps();states();invariants();comps();residuals();shifts();checks();compSel();timeline();
 $('param').innerHTML=D.trajectory.parameter_labels.map((l,i)=>`<option value="${i}">${esc(l)}</option>`).join('');ptrace();proj();dist();uq();rest()}
$('comp').onchange=timeline;$('logy').onchange=timeline;$('param').onchange=ptrace;$('uq').onchange=proj;
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',all);
$('dl').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,1)],{type:'application/json'}));a.download=D.id+'.json';a.click()};
all();
"""

BODY = """<header><div class="hin"><img class="icon" alt="" src="__ICON__" width="26" height="26"><span class="brand">ORCHID</span>
<div class="ht"><h1 id="title"></h1><div class="status" id="meta"></div><div class="status" id="fresh"></div></div>
<div style="margin-left:auto" class="chips"><button id="dl" type="button">Download data</button></div></div></header>
<main><div class="notice" id="banner"></div><div id="metrics" class="metrics"></div>
<div class="grid"><section class="panel"><h2>Phase diagram of the pick</h2><div id="figs"></div></section>
<section class="panel"><h2>Assemblage agreement at observed states</h2><div id="states"></div><div class="legend"><span>● match</span><span>✕ mismatch</span><span>coordinates are observation locations; no boundaries implied</span></div></section></div>
<section class="panel"><h2>Step sequence</h2><div class="chips" id="chips"></div><h3>Per-step table</h3><div id="steptab"></div></section>
<section class="panel"><h2>Invariant scorecard</h2><div id="invplot"></div><div id="inv"></div></section>
<div class="grid"><section class="panel"><h2>Objective components (pick)</h2><div id="comps"></div></section><section class="panel"><h2>Residuals by dataset (pick)</h2><div id="resid"></div></section></div>
<section class="panel"><h2>One-shot energies moved, in units of their σ</h2><div id="shifts"></div></section>
<section class="panel"><h2>Trajectory of the fit</h2><div class="ctl"><label>Quantity <select id="comp"></select></label><label><input type="checkbox" id="logy" checked> log scale of −value</label></div><div id="timeline"></div><p class="small" id="tlnote"></p>
<div class="legend"><span><svg width="12" height="12"><circle cx="6" cy="6" r="4" fill="var(--t-ok)"/></svg>end: right topology</span><span><svg width="12" height="12"><path d="M6,1L11,10H1Z" fill="none" stroke="var(--t-wrong)"/></svg>end: wrong topology</span><span style="color:var(--c-orchid)">★ — pick</span><span>dashed vertical lines: step boundaries</span></div></section>
<section class="panel"><h2>Evolution in model space</h2><h3>(a) Parameter traces, normalised</h3><div class="ctl"><label>Parameter <select id="param"></select></label></div><div id="ptrace"></div><p class="small" id="pnote"></p>
<div class="grid"><div><h3>(b) 2-D projection (fixed PCA basis)</h3><div class="ctl"><label><input type="checkbox" id="uq" checked> show UQ draws</label></div><div id="proj"></div><p class="small" id="projnote"></p></div><div><h3>(c) Distance from the one-shot by phase</h3><div id="dist"></div></div></div></section>
<div class="grid"><section class="panel"><h2>Physics and plausibility checks</h2><div id="checks"></div></section><section class="panel"><h2>Uncertainty</h2><div id="uqp"></div></section></div>
<section class="panel"><h2>Decisions log</h2><div id="dec"></div></section>
<div class="grid"><section class="panel"><h2>Next actions and ORCHID intake</h2><div id="next"></div></section><section class="panel"><h2>Computation</h2><div id="comp_t"></div></section></div>
<section class="panel"><h2>Provenance and artifacts</h2><div id="prov"></div></section>
<footer>__FOOT__</footer></main>"""


def render(doc, snapshot=True, embed_fonts=True):
    icon = data_uri(T / "assets/orchid-icon.svg")
    figs = {f["panel"]: data_uri(f["file"]["path"]) for f in doc.get("figures", [])}
    payload = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    pal = json.dumps(PAL, separators=(",", ":")).replace("</", "<\\/")
    foot = ("Frozen review snapshot: no background update; regenerate with tools/build_dashboard.py from the dashboard data. " if snapshot else "") + \
        "Standalone file, no network. ORCHID colours and IBM Plex (SIL OFL 1.1); evidence-class colours as in the ORCHID paper figures. Schema orchid-assessment-schema 1.0.0-draft."
    title = html.escape(f"{doc.get('system', '')} assessment")
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{title}</title><link rel=\"icon\" href=\"{icon}\"><style>{fonts_css() if embed_fonts else ''}{css_vars()}{CSS}</style></head><body>"
            + BODY.replace("__ICON__", icon).replace("__FOOT__", html.escape(foot))
            + f"<script id=\"data\" type=\"application/json\">{payload}</script><script id=\"pal\" type=\"application/json\">{pal}</script>"
            + f"<script>window.FIG={json.dumps(figs)};</script><script>{JS.replace('__SNAP__', 'true' if snapshot else 'false')}</script></body></html>")


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    doc = json.loads(Path(src).read_text())
    errs = op.SchemaValidator().validate(doc, "assessment-results.schema.json")
    if errs:
        print("dashboard data does not validate:", *errs[:10], sep="\n  "); sys.exit(1)
    frozen.write(out, render(doc, "--snapshot" in sys.argv, "--no-fonts" not in sys.argv))   # refuses a frozen file
    print(out, round(Path(out).stat().st_size / 1e6, 2) if Path(out).exists() else "(not written)", "MB")
    low = [r for r in contrast_report() if r[3] < 3.0]
    print("contrast vs card (WCAG, >= 3:1 for graphics):", "all pass" if not low else "; ".join(f"{t} {k} {c} {v}" for t, k, c, v in low))

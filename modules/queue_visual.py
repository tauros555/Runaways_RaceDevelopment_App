import html
import pandas as pd

def _esc(x): return html.escape(str(x))
def _badge(g): return g if g in ("◎","○","△","×") else ""

def _card(r, rank):
    try: num=int(r["馬番"])
    except Exception: num="-"
    lift_txt=""
    try:
        lift=float(r.get("JockeyLift4",0))
        if lift>0.015: lift_txt=" 騎手＋"
        elif lift<-0.015: lift_txt=" 騎手−"
    except Exception: pass
    return (f'<div class="horse-card"><div class="horse-num">{num}</div>'
            f'<div class="horse-main"><div class="horse-name">{_esc(r.get("馬名",""))} '
            f'<span class="grade">{_badge(r.get("展開評価",""))}</span></div>'
            f'<div class="horse-meta">{_esc(r.get("今回想定脚質",""))} / {_esc(r.get("騎手",""))}{lift_txt}</div></div>'
            f'<div class="rank-chip">{rank}</div></div>')

def _packs(df, rank_col, max_per=4):
    d=df.sort_values(rank_col)
    rows=[]; bucket=[]; last=None
    for _,r in d.iterrows():
        try: rank=int(r[rank_col])
        except Exception: rank=999
        if bucket and (len(bucket)>=max_per or (last is not None and rank-last>=3)):
            rows.append(bucket); bucket=[]
        bucket.append((rank,r)); last=rank
    if bucket: rows.append(bucket)
    return rows

def _stage(df,title,rank_col=None):
    if rank_col is None:
        body="".join(_card(r,int(r["馬番"]) if pd.notna(r["馬番"]) else "-") for _,r in df.sort_values("馬番").iterrows())
        return f'<div class="stage-wrap"><div class="stage-title">{title}</div><div class="start-grid">{body}</div></div>'
    out=[]
    for i,pack in enumerate(_packs(df,rank_col),1):
        horses="".join(_card(r,rank) for rank,r in pack)
        out.append(f'<div class="pack-row"><div class="pack-label">PACK {i}</div><div class="pack-horses">{horses}</div></div>')
    return f'<div class="stage-wrap"><div class="stage-title">{title}</div>{"".join(out)}</div>'

def render_flow(df,active_scenario,raceinfo):
    css="""
    <style>
    .flow-root{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .flow-head{display:flex;justify-content:space-between;align-items:center;margin:4px 0 12px}
    .scenario-pill{padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.25);font-weight:700}
    .stage-wrap{padding:12px 0 16px;border-bottom:1px solid rgba(255,255,255,.12)}
    .stage-title{font-size:18px;font-weight:800;margin-bottom:8px}
    .start-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}
    .pack-row{display:flex;align-items:flex-start;gap:8px;margin:8px 0}
    .pack-label{width:70px;font-size:12px;opacity:.65;padding-top:8px}
    .pack-horses{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;flex:1}
    .horse-card{display:flex;align-items:center;gap:8px;padding:7px 9px;border:1px solid rgba(255,255,255,.18);border-radius:10px;background:rgba(255,255,255,.04);min-width:0}
    .horse-num{width:27px;height:27px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;border:1px solid rgba(255,255,255,.28);flex:0 0 auto}
    .horse-main{min-width:0;flex:1}
    .horse-name{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .horse-meta{font-size:11px;opacity:.70;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .rank-chip{font-size:12px;opacity:.75}
    .grade{font-weight:900}
    @media(max-width:900px){.start-grid,.pack-horses{grid-template-columns:repeat(2,minmax(0,1fr))}}
    </style>
    """
    head=(f'<div class="flow-head"><div><b>隊列フロー</b></div>'
          f'<div class="scenario-pill">{_esc(active_scenario)} / 先行圧力 {_esc(raceinfo.get("先行圧力",""))}</div></div>')
    return ('<div class="flow-root">'+css+head+_stage(df,"スタート")+_stage(df,"初角","PredFirstRank")+_stage(df,"3角","Pred3Rank")+_stage(df,"4角（シナリオ反映）","Pred4ScenarioRank")+'</div>')

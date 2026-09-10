from __future__ import annotations
import html
import math
import pandas as pd

GROUPS = ["先頭","先行集団","中団前","中団後","後方"]

def _esc(v): return html.escape(str(v))

def _group_for_rank(rank:int, n:int) -> str:
    # Stable five-block race shape. More space is deliberately reserved between blocks.
    if n <= 5:
        cuts = [1,2,3,4]
    else:
        cuts = [
            max(1, round(n*0.12)),
            max(2, round(n*0.34)),
            max(3, round(n*0.56)),
            max(4, round(n*0.78)),
        ]
    if rank <= cuts[0]: return "先頭"
    if rank <= cuts[1]: return "先行集団"
    if rank <= cuts[2]: return "中団前"
    if rank <= cuts[3]: return "中団後"
    return "後方"

def add_pack_groups(df:pd.DataFrame, rank_col:str) -> pd.DataFrame:
    x=df.copy()
    n=max(len(x),1)
    ranks=pd.to_numeric(x[rank_col],errors="coerce")
    x["_pack_group"]=[_group_for_rank(int(r) if pd.notna(r) else n,n) for r in ranks]
    return x

def _horse_card(r, rank_col):
    try: num=int(r["馬番"])
    except Exception: num="-"
    try: rank=int(r[rank_col])
    except Exception: rank="-"
    grade=str(r.get("展開評価",""))
    return (
        "<div class='q2-card'>"
        f"<div class='q2-num'>{num}</div>"
        "<div class='q2-main'>"
        f"<b>{_esc(r.get('馬名',''))} <span>{_esc(grade)}</span></b>"
        f"<small>{_esc(r.get('今回想定脚質',''))} / {_esc(r.get('騎手',''))}</small>"
        "</div>"
        f"<div class='q2-rank'>{rank}</div>"
        "</div>"
    )

def _stage(df,title,rank_col):
    x=add_pack_groups(df,rank_col)
    parts=[]
    for gi,g in enumerate(GROUPS):
        z=x[x["_pack_group"]==g].sort_values(rank_col)
        cards="".join(_horse_card(r,rank_col) for _,r in z.iterrows())
        if not cards:
            cards="<div class='q2-empty'>—</div>"
        spacer=" q2-big-gap" if gi in (0,1,2,3) else ""
        parts.append(
            f"<div class='q2-pack{spacer}'>"
            f"<div class='q2-label'>{g}</div>"
            f"<div class='q2-horses'>{cards}</div>"
            "</div>"
        )
    return f"<div class='q2-stage'><div class='q2-title'>{title}</div>{''.join(parts)}</div>"

def render_grouped_flow(df:pd.DataFrame, active_scenario:str, raceinfo:dict) -> str:
    css="""
    <style>
    .q2-root{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .q2-head{display:flex;gap:10px;align-items:center;margin:2px 0 10px;flex-wrap:wrap}
    .q2-pill{border:1px solid rgba(128,128,128,.28);border-radius:999px;padding:5px 10px;font-size:12px;font-weight:800}
    .q2-stage{border:1px solid rgba(128,128,128,.24);border-radius:15px;padding:13px 14px;margin:12px 0}
    .q2-title{font-size:18px;font-weight:900;margin-bottom:6px}
    .q2-pack{display:grid;grid-template-columns:82px 1fr;gap:10px;align-items:start;padding:5px 0}
    .q2-big-gap{margin-bottom:10px;padding-bottom:10px;border-bottom:1px dashed rgba(128,128,128,.18)}
    .q2-label{font-size:12px;font-weight:800;opacity:.78;padding-top:9px}
    .q2-horses{display:flex;gap:8px;flex-wrap:wrap;min-height:42px}
    .q2-card{display:grid;grid-template-columns:27px minmax(120px,1fr) 25px;gap:7px;align-items:center;min-width:205px;max-width:260px;border:1px solid rgba(128,128,128,.24);border-radius:10px;padding:7px 8px}
    .q2-num{width:25px;height:25px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:1px solid rgba(128,128,128,.35);font-weight:900}
    .q2-main{min-width:0}.q2-main b{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}.q2-main small{font-size:10px;opacity:.65;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .q2-rank{text-align:center;font-weight:900;font-size:12px}
    .q2-empty{opacity:.35;padding:8px}
    @media(max-width:900px){.q2-pack{grid-template-columns:70px 1fr}.q2-card{min-width:170px;max-width:100%}}
    </style>
    """
    head=(
        "<div class='q2-head'>"
        f"<span class='q2-pill'>Scenario {html.escape(str(active_scenario))}</span>"
        f"<span class='q2-pill'>先行圧力 {html.escape(str(raceinfo.get('先行圧力','-')))}</span>"
        f"<span class='q2-pill'>LCI {float(raceinfo.get('LeadCompetitionIndex_v2',0)):.3f}</span>"
        "</div>"
    )
    return (
        css+"<div class='q2-root'>"+head
        +_stage(df,"初角","PredFirstRank")
        +_stage(df,"3角","Pred3Rank")
        +_stage(df,"4角","Pred4ScenarioRank")
        +"</div>"
    )

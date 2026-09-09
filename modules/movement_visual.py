from __future__ import annotations
import pandas as pd
import numpy as np

def add_movement_columns(df: pd.DataFrame) -> pd.DataFrame:
    x=df.copy()
    for c in ["PredFirstRank","Pred3Rank","Pred4ScenarioRank"]:
        if c not in x.columns:
            x[c]=np.nan
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x["Move_First_to_3"]=x["PredFirstRank"]-x["Pred3Rank"]
    x["Move_3_to_4"]=x["Pred3Rank"]-x["Pred4ScenarioRank"]
    x["Move_First_to_4"]=x["PredFirstRank"]-x["Pred4ScenarioRank"]

    def pat(r):
        a,b=r["Move_First_to_3"],r["Move_3_to_4"]
        if pd.isna(a) or pd.isna(b): return "不明"
        if a>=3 and b>=1: return "早仕掛け→継続進出"
        if a>=3: return "向正面〜3角で進出"
        if b>=3: return "3角→4角で急進"
        if a<=-3 and b>=2: return "一旦後退→4角再進出"
        if a<=-2 or b<=-2: return "位置取り後退"
        if abs(a)<=1 and abs(b)<=1: return "位置キープ"
        if a>0 or b>0: return "じわっと進出"
        return "やや後退"
    x["MovePattern"]=x.apply(pat,axis=1)
    return x

def _arrow(v):
    try: v=int(v)
    except Exception: return "-"
    if v>0: return f"↑{v}"
    if v<0: return f"↓{abs(v)}"
    return "→0"

def render_movement_table(df: pd.DataFrame) -> pd.DataFrame:
    x=add_movement_columns(df)
    cols=[c for c in ["馬番","馬名","今回想定脚質","PredFirstRank","Pred3Rank","Pred4ScenarioRank",
                     "Move_First_to_3","Move_3_to_4","Move_First_to_4","MovePattern","展開評価"] if c in x.columns]
    out=x[cols].copy().rename(columns={
        "PredFirstRank":"初角","Pred3Rank":"3角","Pred4ScenarioRank":"4角",
        "Move_First_to_3":"初角→3角","Move_3_to_4":"3角→4角",
        "Move_First_to_4":"初角→4角","MovePattern":"動き予測"
    })
    for c in ["初角→3角","3角→4角","初角→4角"]:
        if c in out.columns: out[c]=out[c].map(_arrow)
    if "4角" in out.columns: out=out.sort_values("4角")
    return out

def render_movement_flow(df: pd.DataFrame) -> str:
    x=add_movement_columns(df).sort_values("Pred4ScenarioRank")
    rows=[]
    for _,r in x.iterrows():
        num=int(r["馬番"]) if pd.notna(r.get("馬番")) else "-"
        name=str(r.get("馬名",""))
        style=str(r.get("今回想定脚質",""))
        grade=str(r.get("展開評価",""))
        f=int(r["PredFirstRank"]) if pd.notna(r["PredFirstRank"]) else "-"
        c3=int(r["Pred3Rank"]) if pd.notna(r["Pred3Rank"]) else "-"
        c4=int(r["Pred4ScenarioRank"]) if pd.notna(r["Pred4ScenarioRank"]) else "-"
        a=_arrow(r["Move_First_to_3"]); b=_arrow(r["Move_3_to_4"])
        pattern=str(r["MovePattern"])
        rows.append(
            f"<div style='display:grid;grid-template-columns:180px 55px 65px 55px 65px 55px 1fr;gap:6px;align-items:center;padding:7px 4px;border-bottom:1px solid rgba(128,128,128,.25)'>"
            f"<div><b>{num} {name}</b> {grade}<br><span style='font-size:11px;opacity:.7'>{style}</span></div>"
            f"<div style='text-align:center'>初角<br><b>{f}</b></div>"
            f"<div style='text-align:center'><b>→</b><br>{a}</div>"
            f"<div style='text-align:center'>3角<br><b>{c3}</b></div>"
            f"<div style='text-align:center'><b>→</b><br>{b}</div>"
            f"<div style='text-align:center'>4角<br><b>{c4}</b></div>"
            f"<div style='font-size:12px'><b>{pattern}</b></div>"
            f"</div>"
        )
    return "<div><div style='font-size:12px;opacity:.75;margin-bottom:6px'>↑=前へ進出 / ↓=後退（1位が最前）</div>"+''.join(rows)+"</div>"

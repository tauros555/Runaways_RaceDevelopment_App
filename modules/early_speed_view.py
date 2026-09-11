from __future__ import annotations
import html
import numpy as np
import pandas as pd

def add_ten_metrics(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    for c, default in [
        ("StartDashScore", 50.0),
        ("EarlyTrackingScore", 50.0),
        ("LeadProb_Jockey", 0.08),
    ]:
        if c not in x.columns:
            x[c] = default
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(default)

    # Race Development display index.
    # This is NOT SmartRC's proprietary "テン" formula.
    x["RDテン性能指数"] = (
        0.45*x["StartDashScore"]
        + 0.35*x["EarlyTrackingScore"]
        + 0.20*(x["LeadProb_Jockey"].clip(0,1)*100)
    ).clip(0,100)

    if "統合テン指数" in x.columns:
        x["テン性能指数"] = pd.to_numeric(x["統合テン指数"],errors="coerce").fillna(x["RDテン性能指数"])
    else:
        x["テン性能指数"] = x["RDテン性能指数"]

    x["ハナ獲得目安"] = (x["LeadProb_Jockey"].clip(0,1)*100)
    if "統合テン順位" in x.columns:
        x["テン順位"] = pd.to_numeric(x["統合テン順位"],errors="coerce").fillna(
            x["テン性能指数"].rank(method="first", ascending=False)
        ).astype(int)
    else:
        x["テン順位"] = x["テン性能指数"].rank(method="first", ascending=False).astype(int)
    return x

def _esc(v): return html.escape(str(v))

def render_ten_battle(df: pd.DataFrame, top_n: int = 6) -> str:
    x = add_ten_metrics(df).sort_values(["テン性能指数","LeadProb_Jockey"], ascending=False).head(top_n)
    if x.empty:
        return "<div>テン争いデータなし</div>"

    top_score = float(x["テン性能指数"].iloc[0])
    second = float(x["テン性能指数"].iloc[1]) if len(x)>1 else top_score
    gap = top_score - second
    if gap >= 8:
        summary = "単騎先頭の可能性が比較的高い"
    elif gap >= 4:
        summary = "上位1頭がやや優勢"
    else:
        summary = "ハナ争いは接戦"

    rows=[]
    for _,r in x.iterrows():
        num = int(r["馬番"]) if pd.notna(r.get("馬番")) else "-"
        score = float(r["テン性能指数"])
        lead = float(r["ハナ獲得目安"])
        sd = float(r["StartDashScore"])
        et = float(r["EarlyTrackingScore"])
        rows.append(
            f"<div class='ten-row'>"
            f"<div class='ten-rank'>{int(r['テン順位'])}</div>"
            f"<div class='ten-horse'><b>{num} {_esc(r.get('馬名',''))}</b><br>"
            f"<span>{_esc(r.get('今回想定脚質',''))} / {_esc(r.get('騎手',''))}</span></div>"
            f"<div class='ten-score'><b>{score:.1f}</b><small>テン性能</small></div>"
            f"<div class='ten-mini'>StartDash<br><b>{sd:.1f}</b></div>"
            f"<div class='ten-mini'>EarlyTrack<br><b>{et:.1f}</b></div>"
            f"<div class='ten-mini'>ハナ目安<br><b>{lead:.1f}%</b></div>"
            f"</div>"
        )

    css = """
    <style>
    .ten-wrap{border:1px solid rgba(128,128,128,.24);border-radius:14px;padding:12px 14px;margin:6px 0 14px}
    .ten-summary{font-weight:800;margin-bottom:8px}
    .ten-note{font-size:11px;opacity:.68;margin-bottom:10px}
    .ten-row{display:grid;grid-template-columns:34px minmax(160px,1.4fr) 84px 82px 82px 82px;gap:8px;align-items:center;padding:8px 4px;border-top:1px solid rgba(128,128,128,.16)}
    .ten-rank{font-size:19px;font-weight:900;text-align:center}
    .ten-horse span{font-size:11px;opacity:.68}
    .ten-score,.ten-mini{text-align:center}
    .ten-score b{font-size:20px}.ten-score small{display:block;font-size:10px;opacity:.65}
    .ten-mini{font-size:10px;opacity:.76}.ten-mini b{font-size:13px;opacity:1}
    @media(max-width:900px){.ten-row{grid-template-columns:30px 1fr 70px 70px}.ten-row .ten-mini:nth-last-child(-n+2){display:none}}
    </style>
    """
    return (
        css
        + "<div class='ten-wrap'>"
        + f"<div class='ten-summary'>序盤評価：{summary}</div>"
        + "<div class='ten-note'>テン性能指数はRDテンを基礎に、SmartRC ten_has取得時はレース内標準化してSmartRC 30% / RD 70%で統合。SmartRC欠損馬はRD 100%へ自動フォールバックします。</div>"
        + "".join(rows)
        + "</div>"
    )

from __future__ import annotations
import pandas as pd
import numpy as np

HONMEI_COL = "本命候補判定"
JIRAI_COL = "地雷ラップ判定"
PREV_HILL_COL = '前日坂路時計'
PREV_HILL_THRESHOLD = 66.99

def _is_circle(v) -> bool:
    s = str(v).strip()
    return s in {"〇", "○", "◯", "◎"}

def add_attention_flags(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()

    x["注目_本命候補"] = x[HONMEI_COL].map(_is_circle) if HONMEI_COL in x.columns else False
    x["注目_地雷ラップ"] = x[JIRAI_COL].map(_is_circle) if JIRAI_COL in x.columns else False

    if PREV_HILL_COL and PREV_HILL_COL in x.columns:
        t = pd.to_numeric(x[PREV_HILL_COL], errors="coerce")
        x["注目_前日坂路66秒台以下"] = t.notna() & (t <= PREV_HILL_THRESHOLD)
        x["前日坂路時計_表示"] = t
    else:
        x["注目_前日坂路66秒台以下"] = False
        x["前日坂路時計_表示"] = np.nan

    def badges(r):
        out = []
        if bool(r.get("注目_本命候補", False)):
            out.append("本命候補〇")
        if bool(r.get("注目_地雷ラップ", False)):
            out.append("地雷ラップ〇")
        if bool(r.get("注目_前日坂路66秒台以下", False)):
            v = r.get("前日坂路時計_表示")
            if pd.notna(v):
                out.append(f"前日坂路{float(v):.1f}秒")
            else:
                out.append("前日坂路66秒台以下")
        return " / ".join(out) if out else ""

    x["注目フラグ"] = x.apply(badges, axis=1)
    x["注目数"] = (
        x[["注目_本命候補","注目_地雷ラップ","注目_前日坂路66秒台以下"]]
        .astype(int).sum(axis=1)
    )
    return x

def attention_summary(df: pd.DataFrame) -> pd.DataFrame:
    x = add_attention_flags(df)
    cols = [c for c in [
        "馬番","馬名","注目フラグ",
        HONMEI_COL,JIRAI_COL,PREV_HILL_COL,
        "注目数"
    ] if c and c in x.columns]
    out = x[x["注目数"] > 0][cols].copy()
    if "注目数" in out.columns:
        out = out.sort_values(["注目数","馬番"], ascending=[False,True])
    return out

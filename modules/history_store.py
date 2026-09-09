from pathlib import Path
import pandas as pd, numpy as np
CANON=["race_key","date","year","場所","レース番号","芝・ダ","トラックコード","距離","頭数","馬番","枠番","馬名","性別","騎手","騎手コード","斤量","確定着順","人気","単勝オッズ","走破タイム(秒)","通過順位1角","通過順位2角","通過順位3角","通過順位4角","脚質","上がり3Fタイム","PCI","RPCI","馬場状態","血統登録番号","父馬名"]
def read_csv_auto(f):
    for enc in ("cp932","utf-8-sig","utf-8"):
        try:
            if hasattr(f,"seek"): f.seek(0)
            return pd.read_csv(f,encoding=enc,low_memory=False)
        except Exception: pass
    raise ValueError("CSVを読み込めません。")
def canonicalize(df):
    x=df.rename(columns={"R":"レース番号","父":"父馬名"}).copy()
    if "race_key" not in x.columns:
        if "レースID(新)" not in x.columns: raise ValueError("レースID(新) が必要です。")
        x["race_key"]=x["レースID(新)"].astype(str).str.replace(r"\.0$","",regex=True).str[:16]
    if "血統登録番号" not in x.columns: raise ValueError("血統登録番号 が必要です。")
    x["血統登録番号"]=x["血統登録番号"].astype(str).str.replace(r"\.0$","",regex=True)
    if "year" not in x.columns and "年" in x.columns:
        y=pd.to_numeric(x["年"],errors="coerce"); x["year"]=np.where(y<100,y+2000,y)
    if "date" not in x.columns and all(c in x.columns for c in ["年","月","日"]):
        y=pd.to_numeric(x["年"],errors="coerce"); y=np.where(y<100,y+2000,y)
        x["date"]=y*10000+pd.to_numeric(x["月"],errors="coerce")*100+pd.to_numeric(x["日"],errors="coerce")
    if "異常コード" in x.columns: x=x[pd.to_numeric(x["異常コード"],errors="coerce").fillna(0).eq(0)]
    if "トラックコード" in x.columns: x=x[~pd.to_numeric(x["トラックコード"],errors="coerce").isin([2,3])]
    for c in CANON:
        if c not in x.columns: x[c]=np.nan
    return x[CANON].drop_duplicates(["race_key","血統登録番号"],keep="last")
def load_history(history_path,seed_path):
    p=Path(history_path); s=Path(seed_path); src=p if p.exists() else s
    return pd.read_csv(src,encoding="cp932",compression="infer",low_memory=False) if src.exists() else pd.DataFrame(columns=CANON)
def upsert_annual(history,annual_raw):
    a=canonicalize(annual_raw); h=history[CANON].drop_duplicates(["race_key","血統登録番号"],keep="last")
    key=["race_key","血統登録番号"]; hi=h.set_index(key); ai=a.set_index(key)
    new=ai.index.difference(hi.index); common=ai.index.intersection(hi.index)
    ch=(hi.loc[common].astype("string").fillna("").ne(ai.loc[common].astype("string").fillna(""))).any(axis=1)
    upd=ch[ch].index; skip=int((~ch).sum())
    kept=hi[~hi.index.isin(upd)]
    add=ai.loc[new.union(upd)] if len(new)+len(upd) else ai.iloc[0:0]
    out=pd.concat([kept,add]).reset_index().sort_values(["date","場所","レース番号","馬番"],kind="stable")
    return out,{"既存件数":len(h),"年度入力件数":len(a),"INSERT":len(new),"UPDATE":len(upd),"SKIP":skip,"更新後件数":len(out)}
def save_history(df,path):
    Path(path).parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False,encoding="cp932",compression="gzip")

import pandas as pd
PRIORITY=["アプリ連携","メイン判定","出馬表"]
ALIASES={"レース番号":"R","父":"父馬名","芝ダ":"芝・ダ","芝・ダート":"芝・ダ"}
REQ=["場所","R","馬番","馬名","芝・ダ","距離"]
def norm(df):
    x=df.copy(); x.columns=[str(c).strip() for c in x.columns]; x=x.rename(columns={k:v for k,v in ALIASES.items() if k in x.columns})
    for c in ["R","馬番","枠番","距離","年月日","年","月","日"]:
        if c in x.columns: x[c]=pd.to_numeric(x[c],errors="coerce")
    if "血統登録番号" in x.columns: x["血統登録番号"]=x["血統登録番号"].astype(str).str.replace(r"\.0$","",regex=True)
    if "年月日" not in x.columns and all(c in x.columns for c in ["年","月","日"]):
        y=x["年"].where(x["年"]>=100,x["年"]+2000); x["年月日"]=y*10000+x["月"]*100+x["日"]
    miss=[c for c in REQ if c not in x.columns]
    if miss: raise ValueError("必要列不足: "+",".join(miss))
    return x
def read_runaway_file(f):
    name=getattr(f,"name","").lower()
    if name.endswith(".csv"):
        for enc in ("cp932","utf-8-sig","utf-8"):
            try: f.seek(0); return norm(pd.read_csv(f,encoding=enc,low_memory=False)),"CSV"
            except Exception: pass
        raise ValueError("CSV読込失敗")
    f.seek(0); xls=pd.ExcelFile(f,engine="openpyxl")
    for s in PRIORITY+xls.sheet_names:
        if s not in xls.sheet_names: continue
        try: return norm(pd.read_excel(xls,sheet_name=s,engine="openpyxl")),s
        except Exception: pass
    raise ValueError("出馬表列を検出できません。")

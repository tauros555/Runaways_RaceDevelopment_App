from __future__ import annotations
from pathlib import Path
import pandas as pd

REQUIRED_RACECARD_COLUMNS = [
    "年月日", "場所", "R", "馬番", "レース名", "芝・ダ", "距離",
    "馬名", "騎手", "枠", "レースID", "血統登録番号"
]

OPTIONAL_RACECARD_COLUMNS = [
    "性別", "調教師", "所属", "父", "コースID", "ZI", "脚質",
    "本命候補判定", "相手候補判定", "地雷ラップ判定", "前日坂路時計"
]

def _read_csv_any(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    last_err = None
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"調教判定表CSVを読み込めません: {last_err}")

def _valid_yyyymmdd(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    n = pd.to_numeric(s, errors="coerce").astype("Int64")
    txt = n.astype("string")
    eight = txt.str.fullmatch(r"\d{8}", na=False)
    parsed = pd.to_datetime(txt.where(eight), format="%Y%m%d", errors="coerce")
    valid = eight & parsed.notna()
    return n.where(valid), parsed

def normalize_training_judgment_table(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x.columns = [str(c).strip() for c in x.columns]
    missing = [c for c in REQUIRED_RACECARD_COLUMNS if c not in x.columns]
    if missing:
        raise ValueError("調教判定表に必要列がありません: " + ", ".join(missing))

    x["年月日"], parsed = _valid_yyyymmdd(x["年月日"])
    x["_date_parsed"] = parsed
    x["_date_valid"] = x["年月日"].notna()
    x["日付表示"] = parsed.dt.strftime("%Y/%m/%d")

    for c in ["R","馬番","枠","距離"]:
        x[c] = pd.to_numeric(x[c], errors="coerce").astype("Int64")

    # 調教判定表では血統登録番号が8桁短縮形（例: 23106616）で入ることがある。
    # history_seed / TARGET履歴は10桁形（例: 2023106616）なので、内部キーを10桁へ統一する。
    reg = (
        pd.to_numeric(x["血統登録番号"], errors="coerce")
        .astype("Int64")
        .astype("string")
    )
    reg = reg.str.replace(r"\.0$", "", regex=True)
    short8 = reg.str.fullmatch(r"\d{8}", na=False)
    reg = reg.where(~short8, "20" + reg)
    x["血統登録番号"] = reg

    x["current_race_key"] = (
        x["年月日"].astype("string")
        + "_"
        + x["場所"].astype("string").str.strip()
        + "_R"
        + x["R"].astype("string").str.zfill(2)
    )
    return x

def load_training_judgment_racecard(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"出馬表元データが見つかりません: {path}\n"
            "data/調教判定表.csv を配置してください。"
        )
    return normalize_training_judgment_table(_read_csv_any(path))

def available_races(df: pd.DataFrame) -> pd.DataFrame:
    # Invalid values such as 20, 202609, NaN are never exposed to the UI.
    x = df[df["_date_valid"]].copy()
    cols = ["年月日","日付表示","場所","R","レース名","芝・ダ","距離","current_race_key"]
    out = x[cols].dropna(subset=["年月日","場所","R"]).drop_duplicates().copy()
    return out.sort_values(["年月日","場所","R"], ascending=[False,True,True])

def select_race(df: pd.DataFrame, current_race_key: str) -> pd.DataFrame:
    out = df[df["current_race_key"] == current_race_key].copy()
    return out.sort_values("馬番")

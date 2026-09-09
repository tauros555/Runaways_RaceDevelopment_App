from __future__ import annotations

from pathlib import Path
import pandas as pd


REQUIRED_RACECARD_COLUMNS = [
    "年月日", "場所", "R", "馬番", "レース名", "芝・ダ", "距離",
    "馬名", "騎手", "枠", "レースID", "血統登録番号"
]

OPTIONAL_RACECARD_COLUMNS = [
    "性別", "調教師", "所属", "父", "コースID", "ZI", "脚質",
    "本命候補判定", "相手候補判定", "地雷ラップ判定"
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


def normalize_training_judgment_table(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x.columns = [str(c).strip() for c in x.columns]

    missing = [c for c in REQUIRED_RACECARD_COLUMNS if c not in x.columns]
    if missing:
        raise ValueError("調教判定表に必要列がありません: " + ", ".join(missing))

    # Normalize types used by Race Development.
    x["年月日"] = pd.to_numeric(x["年月日"], errors="coerce").astype("Int64")
    x["R"] = pd.to_numeric(x["R"], errors="coerce").astype("Int64")
    x["馬番"] = pd.to_numeric(x["馬番"], errors="coerce").astype("Int64")
    x["枠"] = pd.to_numeric(x["枠"], errors="coerce").astype("Int64")
    x["距離"] = pd.to_numeric(x["距離"], errors="coerce").astype("Int64")

    # IMPORTANT: race id / pedigree registration number are identifiers, not floats.
    # Prefer 血統登録番号 as the horse key. Avoid trusting scientific-notation race IDs
    # when Excel/CSV has already coerced them to floating point.
    x["血統登録番号"] = (
        pd.to_numeric(x["血統登録番号"], errors="coerce")
        .astype("Int64")
        .astype("string")
    )

    # Build a stable current-race key from date/place/R rather than the potentially
    # float-coerced レースID column.
    x["current_race_key"] = (
        x["年月日"].astype("string").str.zfill(8)
        + "_"
        + x["場所"].astype("string").str.strip()
        + "_R"
        + x["R"].astype("string").str.zfill(2)
    )

    # Race Development uses this file only as current race-card data.
    # Runaway/training judgment columns remain available for final UI reference,
    # but are not to be injected into Simulator predictive features.
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
    cols = ["年月日", "場所", "R", "レース名", "芝・ダ", "距離", "current_race_key"]
    out = df[cols].drop_duplicates().copy()
    return out.sort_values(["年月日", "場所", "R"], ascending=[False, True, True])


def select_race(df: pd.DataFrame, current_race_key: str) -> pd.DataFrame:
    out = df[df["current_race_key"] == current_race_key].copy()
    return out.sort_values("馬番")

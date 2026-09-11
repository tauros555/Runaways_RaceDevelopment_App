# v6.8.3 History Base Fix

正式な役割分担:

- `data/調教判定表.csv`
  - 今回の出走馬を選ぶ出馬表
  - 本命候補/地雷/前日坂路などの参考表示
  - 過去履歴データとしては使用しない

- `data/history_seed_2020_2026.csv.gz`
  - Race Developmentの過去分析の基礎データ
  - 常に読み込む

- `data/history_master.csv.gz`
  - Data Builder等で追加された更新履歴
  - seedへ `race_key × 血統登録番号` で上書き結合
  - seedを置き換えるのではなく、更新分として扱う

予測時:
`build_features(current_racecard, historical_history, course)`
の形を維持する。

# Race Development runtime masters

このフォルダはアプリが直接参照する本番データです。

- `history_seed_2020_2026.csv.gz`
  - 初期履歴マスタ。平地・正常走行の約30.8万走。
  - `history_master.csv.gz` が未作成の場合の初期データ。
- `history_master.csv.gz`
  - TARGET年度CSV更新後に生成される運用履歴マスタ（初回起動時は未存在で正常）。
- `course_structure.csv`
  - 全105コースのコース構造・初角・直線・圧力関連マスタ。
- `horse_startdash_tracking.csv`
  - 馬単位のStartDash / EarlyTracking特性マスタ。
- `scenario_thresholds.csv`
  - 芝/ダート別、Past-Onlyの展開評価◎○△×閾値。
- `scenario_queue_transform.csv`
  - シナリオ別隊列変換の研究・運用参照マスタ。
- `pair_reference.csv`
  - 位置関係・脚質ペアの共存しやすさ参考マスタ。

## 毎週更新するもの
ユーザーがアップロードするTARGET年度CSVから `history_master.csv.gz` を差分更新します。
固定マスタを毎週手作業で差し替える必要はありません。

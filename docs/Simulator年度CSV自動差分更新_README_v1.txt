Simulator 年度CSV自動差分更新モジュール v1

目的:
TARGETから年度データを毎週丸ごと出力しても、
Simulator側で新規・変更・重複を自動判定して履歴マスタを更新する。

更新キー:
race_key × 血統登録番号
race_key = TARGET馬単位「レースID(新)」先頭16桁

処理:
INSERT  新規キーを追加
SKIP    同一キー・同一内容は無視
UPDATE  同一キーで内容変更があればTARGET最新版で置換

CLI例:
python simulator_incremental_update.py ^
  --master SimulatorHistoryMaster.csv ^
  --annual TARGET_2026.csv ^
  --output SimulatorHistoryMaster_updated.csv ^
  --audit update_audit.csv

Streamlitへ組み込む場合:
incremental_update(master_csv, annual_csv, output_csv, audit_csv)
を呼び出すだけでよい。

注意:
このv1は「履歴の安全な差分更新」まで。
更新後に Horse recent5 / Jockey recent50 / Scenario特徴量 / OOF学習用派生列などを
再構築する処理は別レイヤーにする。

# Runaway's Race Development

Race Development本番パッケージ v6.1

## 同梱済み
- Streamlitアプリ本体
- ヘッダー画像
- 2020-2026初期履歴
- コース構造マスタ
- StartDash / EarlyTrackingマスタ
- シナリオ関連マスタ
- 展開評価閾値
- 位置関係参考マスタ
- 学習済みLead/隊列モデル
- 学習済み5分類Scenarioモデル
- FullWinProbモデル
- Monte Carlo Simulation
- TARGET年度CSV自動差分更新

## 最短起動（Windows）
1. `install_windows.bat`
2. `start_windows.bat`

## フォルダ
- `assets/` 画面素材
- `data/` 本番マスタ
- `models/` 学習済みモデル
- `modules/` Race Developmentロジック
- `input/` 手動入力保存用
- `output/` 将来の結果保存用
- `backups/` 履歴バックアップ用
- `docs/` 仕様・運用手順・マスタ一覧

詳細は `docs/運用手順.md` を参照。


## Google Drive persistent storage
- 起動時に最新historyを自動取得
- TARGET更新前にDriveへバックアップ
- 更新後historyをDriveへ保存
- update_log.csvへ監査ログ追記
- 接続状態を画面表示

設定は `docs/GOOGLE_DRIVE_SETUP.md`。


## v6.5 Google Drive OAuth版
- 自分のGoogleアカウントでDrive認証
- 起動時に最新履歴取得
- TARGET更新前バックアップ
- 更新後history_master保存
- update_log.csv追記
- 設定: `docs/GOOGLE_DRIVE_OAUTH_SETUP.md`


## v6.5 出馬表参照方式変更
現在レースの出馬表はアップロード方式を廃止。
`data/調教判定表.csv` を直接参照する。

このファイルはRunaway's本体が読み込む調教判定表と同じ形式。
Race Developmentは出馬表列だけをSimulator入力に使用する。


## v6.5 調教判定表 注目フラグ
- 本命候補判定〇
- 地雷ラップ判定〇
- 前日坂路時計 <= 66.99秒
を該当馬ごとに表示。

# Race Development v6.7 UI Rework

## 変更点
- レース日付はYYYYMMDDの8桁かつ実在日だけ採用。
- UI表示はYYYY/MM/DD。
- `20`、`202609`、NaNなどはレース選択肢から除外。
- 予測は「Race Development予測を実行」を押した時だけ実行。
- Monte Carloも別ボタン。
- 馬群表示を5ブロック化:
  - 先頭
  - 先行集団
  - 中団前
  - 中団後
  - 後方
- 各ブロック間に意図的な空間を作り、従来の密集表示を廃止。
- 「テン争い」を独立表示。
  - StartDashScore
  - EarlyTrackingScore
  - LeadProb_Jockey
  を使うRace Development独自の表示指数。
- SmartRCの proprietary formula は複製しない。
- TARGET年度CSVアップロード/更新画面はRace Development本体から除外。
  将来のTARGET Data Builderへ分離する。

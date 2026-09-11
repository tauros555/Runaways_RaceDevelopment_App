# v6.10 SmartRCテン自動連携

## 自動読込
`data/smartrc_ten_latest.csv`

## レース照合
SmartRC `rcode` から
- 日付
- JRA場コード
- R
を復元し、今回選択レースへ照合。
その後 `馬番` で各出走馬へ結合。

## テン統合
RDテン:
`StartDash 45% + EarlyTracking 35% + LeadProb 20%`

SmartRC:
`ten_has`（小さいほど速い）

両方を同一レース内で標準化し、
`統合テンZ = RD 70% + SmartRC 30%`

SmartRC欠損馬:
`RD 100%`

## 重要
SmartRCテンはテン争い評価へ統合する。
現段階では FullWinProb / Runaway's Ver7 score へ直接加点しない。
勝率への直接二重計上を避けるため。

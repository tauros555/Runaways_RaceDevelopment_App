# v6.8.4 Racecard Reload Fix

原因:
`racecard_master()` が引数なしの `st.cache_data` だったため、
`data/調教判定表.csv` を差し替えても同一プロセス内では古いキャッシュを返す可能性があった。

修正:
- `調教判定表.csv` の `mtime_ns` と `size` をキャッシュキーに使用
- ファイル差し替え時に自動で再読込
- サイドバーへ `🔄 出馬表を再読込` ボタン追加
- 手動再読込時は予測/MCのセッション結果もクリア

役割:
- 調教判定表.csv = 今回の出馬表
- history_seed/history_master = 過去分析履歴

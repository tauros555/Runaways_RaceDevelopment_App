# Google Drive連携セットアップ

1. Google Driveに `Runaways_RaceDevelopment` フォルダを作成。
2. URLの `/folders/XXXX` の `XXXX` を folder_id として使う。
3. Google Cloudでプロジェクト作成 → Google Drive APIを有効化。
4. サービスアカウントを作成し、JSON鍵を発行。
5. サービスアカウントの client_email をDriveフォルダへ「編集者」で共有。
6. Streamlit Cloudの Secrets に `.streamlit/secrets.toml.example` と同形式で登録。

起動時: Driveの最新 `history_master.csv.gz` を自動取得。無ければ同梱seed。
更新時: 更新前を `backup/` に保存 → 最新履歴をDriveへ上書き → `update_log.csv`追記。

サービスアカウントJSONや `secrets.toml` はGitHubへ置かない。

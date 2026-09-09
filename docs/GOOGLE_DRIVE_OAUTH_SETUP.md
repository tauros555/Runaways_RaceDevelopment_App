# Google Drive OAuth setup — Race Development v6.3

1. Google Driveに `Runaways_RaceDevelopment` フォルダを作成し、URL末尾のfolder_idを控える。
2. Google CloudでDrive APIを有効化。
3. OAuth同意画面を設定し、自分をテストユーザーに追加。
4. OAuth 2.0 Client ID → Web application を作成。
5. Authorized redirect URI にStreamlit CloudのURLを完全一致で登録。
6. Client ID / Client Secret / folder_id / redirect_uri をStreamlit Secretsへ登録。
7. アプリの「Google Driveに接続」から自分のGoogleアカウントで許可。
8. 接続後は起動時に最新履歴を取得し、TARGET更新時にbackup作成→history_master上書き→update_log追記。

## セキュリティ
- 実credentialsはGitHubに置かない。
- `.streamlit/secrets.toml` はコミットしない。
- client_secretやrefresh_tokenを公開しない。

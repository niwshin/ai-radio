# AI Radio

ローカルPCで24時間ループ再生するAIラジオMVPです。

## MVPの構成

- `app`: FastAPIアプリ。Web検索ジョブ作成、SQLite保存、VOICEVOX合成、ローカルWeb UIを担当。
- `searxng`: Web話題収集用のメタ検索。
- `voicevox`: ローカルTTS。
- `codex_worker`: ホスト側で `codex exec` を呼び、ChatGPTログイン済みCodex枠で原稿JSONを生成。

DockerコンテナにCodex認証情報を入れないため、Codex実行だけホスト側workerで行います。

## 起動

```bash
docker compose up --build
```

別ターミナルで、ホスト側からCodex workerを起動します。

```bash
python3 -m pip install -e .
python3 -m ai_radio.codex_worker --data-dir ./data --loop
```

ブラウザで開きます。

```text
http://localhost:8000
```

## 画面の使い方（これだけ）

1. `Queue` に番組が出るまで待つ。
2. `Start` を押す。
3. あとは放置する。番組が自動で繰り返し流れる。

画面の見方:

- `pending jobs`: 作成待ちの番組数。`0` でも問題ありません。
- `last error`: `none` なら正常です。
- `Queue`: 再生する番組の一覧です。

`番組生成待ちです` と表示される間は、まだ番組を作っています。しばらく待ってください。音が出ないときは、もう一度 `Start` を押してください。

## 主な環境変数

- `AI_RADIO_DB_PATH`: SQLite DB path。既定値 `/data/ai_radio.sqlite3`
- `AI_RADIO_DATA_DIR`: データ保存先。既定値 `/data`
- `AI_RADIO_GENERATION_INTERVAL_SECONDS`: 話題収集/原稿生成間隔。既定値 `3600`
- `AI_RADIO_PROGRAM_TARGET_MINUTES`: 原稿の目標尺。既定値 `30`
- `AI_RADIO_THEME`: 初期テーマ。既定値 `tech gadgets trending`
- `AI_RADIO_SEARXNG_URL`: SearXNG URL。既定値 `http://searxng:8080`
- `AI_RADIO_VOICEVOX_URL`: VOICEVOX URL。既定値 `http://voicevox:50021`
- `AI_RADIO_VOICEVOX_SPEAKER`: VOICEVOX speaker ID。既定値 `2`
- `AI_RADIO_RETENTION_DAYS`: 音声/ログ保持日数。既定値 `7`

ホスト側workerにも `requirements.txt` のPython依存関係が必要です。

## 現状の制約

- Codex workerは `codex login status` が成功するホストで動かしてください。
- Web UIの自動再生はブラウザ制約により、最初にStartボタン操作が必要です。
- Spotify/BGM連携はMVP外です。

# Docker Compose起動時のappエラー

## 対象環境

- Windowsホスト
- WSL2上のUbuntu
- Docker DesktopのWSL Integration
- `docker compose up --build` で `app`、SearXNG、VOICEVOXを起動

## 症状と原因

### SearXNG検索が403になる

`app-1` に次のエラーが繰り返し出た。

```text
httpx.HTTPStatusError: Client error '403 Forbidden' for url 'http://searxng:8080/search?...&format=json...'
```

SearXNGは、`settings.yml` の `search.formats` で許可されていない出力形式を403で拒否する。既定設定ではHTMLだけが有効で、アプリが要求するJSONが無効だった。

`config/searxng/settings.yml` を追加し、`html` と `json` を許可した。ローカル専用インスタンスなのでlimiterを無効化し、既定値ではない開発用`secret_key`も設定した。

### SearXNGが終了コード1で停止する

独自の `settings.yml` をマウントした直後、次のエラーでworkerが終了した。

```text
server.secret_key is not changed. Please use something else instead of ultrasecretkey.
```

原因はSearXNGの既定secretをそのまま使用したこと。設定ファイルへローカル開発用の非既定値を明示した。

### VOICEVOXが終了コード2で停止する

```text
/entrypoint.sh: line 7: exec: --: invalid option
```

Composeの `command: ["--host", "0.0.0.0"]` がイメージ既定CMDを置き換え、実行ファイルなしでオプションだけをentrypointへ渡していた。`command` を削除し、VOICEVOXイメージの既定CMDを使用した。

### app起動直後に接続エラーが出る

```text
httpx.ConnectError: All connection attempts failed
```

短縮形式の `depends_on` はコンテナの起動順しか保証せず、SearXNGがHTTP応答可能になる前にschedulerが検索を開始していた。SearXNGとVOICEVOXへHTTP healthcheckを追加し、`app` の依存条件を `service_healthy` に変更した。

### 検索が400になる

```text
httpx.HTTPStatusError: Client error '400 Bad Request' ... language=ja-JP%2Cen-US
```

SearXNGの `language` は単一値であり、カンマ区切りの複数ロケールは無効だった。日本語・英語を限定せず扱えるよう `language=all` に変更した。

### X-Forwarded-For警告

```text
X-Forwarded-For nor X-Real-IP header is set!
```

これは403の直接原因ではないが、SearXNGのbot detectionがクライアントIPを判断できない警告だった。内部通信用検索リクエストへ `X-Real-IP: 127.0.0.1` を付与した。

## 確認方法

```bash
source .venv/bin/activate
docker compose down
docker compose up --build
```

別ターミナルで確認する。

```bash
source .venv/bin/activate
docker compose ps
curl -fsS http://localhost:8000/api/status
curl -fsS http://localhost:50021/version
curl -fsS --get http://localhost:8080/search --data-urlencode q=test --data format=json
python -m pytest
```

正常時はSearXNGとVOICEVOXが `healthy`、`app` が `running` となり、`/api/status` の `last_error` が `null` になる。

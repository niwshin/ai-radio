# Ubuntu on WSLのターミナルで実行する

この手順では、リポジトリ、Python、Codex workerをUbuntu on WSL側に置き、WSLのターミナルから実行します。FastAPIアプリ、VOICEVOX、SearXNGはWindows側のDocker Desktop上で動作します。

リポジトリは `/home/<user>/repos/ai-radio` のようにWSLのLinuxファイルシステム上へ置くことを推奨します。Windows側のPowerShellだけで実行する場合は、[Windowsターミナルで実行する](run-in-windows.md)を使用してください。

## 前提ソフトウェア

- WSL2とUbuntu
- Windows側のDocker Desktop
- Ubuntu側のPython 3.12以上と `venv`
- Ubuntu側のCodex CLI
- ChatGPTのCodex利用可能なアカウント

Docker Desktopは[公式のWindowsインストール手順](https://docs.docker.com/desktop/setup/install/windows-install/)に従って導入します。Docker Desktopの `Settings > Resources > WSL Integration` で対象のUbuntuを有効にしてください。詳細は[DockerのWSL手順](https://docs.docker.com/desktop/features/wsl/use-wsl/)を参照してください。

Codex CLIについては[OpenAI公式CLI手順](https://developers.openai.com/codex/cli)を参照してください。

## 1. 前提を確認する

Ubuntuターミナルを開き、リポジトリへ移動します。

```bash
cd ~/repos/ai-radio

python3 --version
docker version
docker compose version
codex --version
codex login status
```

このリポジトリの現在の配置場所を使う場合は次のパスです。

```bash
cd /home/niwshin/repos/ai-radio
```

`docker version` でServer情報が出ない場合は、Windows側でDocker Desktopを起動し、対象UbuntuのWSL Integrationを有効にします。設定変更後も認識しない場合は、PowerShellから `wsl --shutdown` を実行し、Ubuntuを開き直します。

Codexにログインしていない場合は、次を実行して画面の案内に従います。

```bash
codex
```

ログイン後はCodexを終了し、再度 `codex login status` を確認します。このプロジェクトはOpenAI APIキーではなく、ホスト側でログイン済みのCodex CLIを原稿生成に利用します。

## 2. Python仮想環境を作る

`venv` が未導入の場合は、対話可能なUbuntuターミナルで実行します。

```bash
sudo apt update
sudo apt install -y python3-venv
```

初回だけ仮想環境を作ります。

```bash
cd /home/niwshin/repos/ai-radio
python3 -m venv .venv
```

以後、PythonやDockerを操作する前に仮想環境を有効化し、実体を確認します。

```bash
cd /home/niwshin/repos/ai-radio
source .venv/bin/activate

printf 'VIRTUAL_ENV=%s\n' "$VIRTUAL_ENV"
python -c 'import sys; print(sys.executable); print(sys.version)'
```

Pythonのパスが `/home/niwshin/repos/ai-radio/.venv/bin/python` であることを確認してから依存関係を入れます。

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m pytest
```

## 3. AIラジオを起動する

Docker ComposeとCodex workerは、同じリポジトリの `data/` を共有する必要があります。以下の2つのUbuntuターミナルを、必ず同じリポジトリから起動してください。

### Ubuntuターミナル1: コンテナを起動する

```bash
cd /home/niwshin/repos/ai-radio
source .venv/bin/activate

printf 'VIRTUAL_ENV=%s\n' "$VIRTUAL_ENV"
docker compose up --build
```

このターミナルではFastAPIアプリ、VOICEVOX、SearXNGのログが表示されます。初回はコンテナイメージの取得とビルドに時間がかかります。

### Ubuntuターミナル2: Codex workerを起動する

別のUbuntuターミナルを開きます。

```bash
cd /home/niwshin/repos/ai-radio
source .venv/bin/activate

printf 'VIRTUAL_ENV=%s\n' "$VIRTUAL_ENV"
codex login status
python -m ai_radio.codex_worker --data-dir ./data --loop
```

モデルを明示したい場合は、`AI_RADIO_CODEX_MODEL` を指定します。

```bash
AI_RADIO_CODEX_MODEL=o3 python -m ai_radio.codex_worker --data-dir ./data --loop
```

workerは、アプリが `data/codex_jobs/pending` に作成したジョブをCodex CLIへ渡します。このターミナルを閉じると新しい原稿は生成されません。

## 4. 動作を確認する

WindowsまたはWSL側のブラウザで次を開きます。

```text
http://localhost:8000
```

ブラウザの自動再生制限があるため、最初に画面の `Start` を押します。起動直後は番組がまだ存在せず、検索、原稿生成、音声合成が完了してから再生可能になります。

別のUbuntuターミナルから状態を確認する場合も、先に仮想環境を有効化します。

```bash
cd /home/niwshin/repos/ai-radio
source .venv/bin/activate

curl -s http://localhost:8000/api/status
curl -s http://localhost:8000/api/programs
docker compose ps
```

生成したDB、ジョブ、音声は `data/` に保存されます。

## 5. 停止・再開する

Codex workerのターミナルで `Ctrl+C` を押し、Composeのターミナルでも `Ctrl+C` を押します。その後、コンテナを停止します。

```bash
cd /home/niwshin/repos/ai-radio
source .venv/bin/activate

printf 'VIRTUAL_ENV=%s\n' "$VIRTUAL_ENV"
docker compose down
```

再開時は「3. AIラジオを起動する」の2つのプロセスを再度起動します。`docker compose down` では `data/` の内容は削除されません。

24時間動作させる場合は、Docker Desktop、Compose、Codex worker、再生中のブラウザを起動したままにします。Windowsのスリープも無効化してください。

## トラブルシューティング

### `sudo: a terminal is required` と表示される

`sudo` は対話可能なUbuntuターミナルから実行し、Ubuntuユーザーのパスワードを入力します。非対話のツールや別プロセス経由ではパスワード入力ができません。

### `docker: command not found` またはDocker Serverへ接続できない

Windows側でDocker Desktopを起動し、`Settings > Resources > WSL Integration` で対象Ubuntuを有効化します。必要ならPowerShellで次を実行してからUbuntuを開き直します。

```powershell
wsl --shutdown
```

### `No module named pytest` または `No module named ai_radio`

仮想環境を有効化し、依存関係を再導入します。

```bash
source .venv/bin/activate
python -m pip install -e '.[test]'
```

### 原稿が生成されない

次を順に確認します。

```bash
source .venv/bin/activate
codex login status
docker compose ps
find data/codex_jobs -maxdepth 2 -type f -print
```

`failed/` にエラーファイルがある場合は、その内容とCodex worker側の出力を確認します。

### `data/` に書き込めない

コンテナ実行後に所有者が変わった場合だけ、所有者を現在のWSLユーザーへ戻します。

```bash
sudo chown -R "$USER":"$USER" data
```

### ポートが使用中になる

この構成は `8000`、`8080`、`50021` を使用します。既存のCompose環境を停止してから再起動してください。

```bash
source .venv/bin/activate
docker compose down
ss -ltnp | grep -E ':(8000|8080|50021)\\b'
```

# Windows ターミナルで実行する

この手順では、リポジトリ、Python、Codex workerをWindows側に置き、PowerShellから実行します。FastAPIアプリ、VOICEVOX、SearXNGはDocker Desktop上で動作します。

WSL上のリポジトリを使う場合は、[Ubuntu on WSLで実行する](run-in-ubuntu-on-wsl.md)を使用してください。Windows版では、リポジトリを `C:\src\ai-radio` などWindowsファイルシステム上に置くことを推奨します。

## 前提ソフトウェア

- Windows 11またはWindows 10
- Docker Desktop（WSL 2 backendを有効化）
- Python 3.12以上
- Codex CLI
- ChatGPTのCodex利用可能なアカウント

Docker Desktopは[公式のWindowsインストール手順](https://docs.docker.com/desktop/setup/install/windows-install/)に従って導入し、起動しておきます。Codex CLIは[公式CLI手順](https://developers.openai.com/codex/cli)と[Windows向け手順](https://developers.openai.com/codex/windows)を参照してください。

## 1. 前提を確認する

PowerShellを開き、リポジトリへ移動します。

```powershell
Set-Location C:\src\ai-radio

py -3.12 --version
docker version
docker compose version
codex --version
codex login status
```

`docker version` でServer情報が出ない場合は、Docker Desktopを起動してから再実行します。

Codexにログインしていない場合は、次を実行して画面の案内に従います。

```powershell
codex
```

ログイン後はCodexを終了し、再度 `codex login status` を確認します。このプロジェクトはOpenAI APIキーではなく、ホスト側でログイン済みのCodex CLIを原稿生成に利用します。

## 2. Python仮想環境を作る

初回だけ実行します。

```powershell
Set-Location C:\src\ai-radio
py -3.12 -m venv .venv
```

仮想環境を有効化します。

```powershell
.\.venv\Scripts\Activate.ps1
```

スクリプト実行が禁止されている場合は、現在のPowerShellプロセスだけ許可してから有効化します。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

仮想環境とPython実体を確認します。

```powershell
$env:VIRTUAL_ENV
python -c "import sys; print(sys.executable); print(sys.version)"
```

出力されたPythonのパスが `.venv\Scripts\python.exe` であることを確認してから依存関係を入れます。

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest
```

## 3. AIラジオを起動する

Docker ComposeとCodex workerは、同じリポジトリの `data` ディレクトリを共有する必要があります。以下の2つのPowerShellを、必ず同じリポジトリから起動してください。

### PowerShell 1: コンテナを起動する

```powershell
Set-Location C:\src\ai-radio
.\.venv\Scripts\Activate.ps1

$env:VIRTUAL_ENV
docker compose up --build
```

このターミナルではFastAPIアプリ、VOICEVOX、SearXNGのログが表示されます。初回はコンテナイメージの取得とビルドに時間がかかります。

### PowerShell 2: Codex workerを起動する

別のPowerShellを開きます。

```powershell
Set-Location C:\src\ai-radio
.\.venv\Scripts\Activate.ps1

$env:VIRTUAL_ENV
codex login status
python -m ai_radio.codex_worker --data-dir .\data --loop
```

workerは、アプリが `data\codex_jobs\pending` に作成したジョブをCodex CLIへ渡します。このPowerShellを閉じると新しい原稿は生成されません。

## 4. 動作を確認する

ブラウザで次を開きます。

```text
http://localhost:8000
```

ブラウザの自動再生制限があるため、最初に画面の `Start` を押します。起動直後は番組がまだ存在せず、検索、原稿生成、音声合成が完了してから再生可能になります。

PowerShellから状態を確認する場合は次を使います。

```powershell
Invoke-RestMethod http://localhost:8000/api/status | ConvertTo-Json -Depth 5
Invoke-RestMethod http://localhost:8000/api/programs | ConvertTo-Json -Depth 5
docker compose ps
```

生成したDB、ジョブ、音声は `data` に保存されます。

## 5. 停止・再開する

Codex workerのPowerShellで `Ctrl+C` を押し、ComposeのPowerShellでも `Ctrl+C` を押します。その後、コンテナを停止します。

```powershell
Set-Location C:\src\ai-radio
.\.venv\Scripts\Activate.ps1
docker compose down
```

再開時は「3. AIラジオを起動する」の2つのプロセスを再度起動します。`docker compose down` では `data` の内容は削除されません。

24時間動作させる場合は、Docker Desktop、Compose、Codex worker、再生中のブラウザを起動したままにします。Windowsのスリープも無効化してください。

## トラブルシューティング

### `docker` が見つからない、またはServerへ接続できない

Docker Desktopを起動し、WSL 2 backendが有効になっていることを確認します。その後、新しいPowerShellで `docker version` を再実行します。

### `No module named pytest` または `No module named ai_radio`

仮想環境を有効化し、依存関係を再導入します。

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

### 原稿が生成されない

次を順に確認します。

```powershell
codex login status
docker compose ps
Get-ChildItem .\data\codex_jobs -Recurse
```

`failed` にエラーファイルがある場合は、その内容とCodex worker側の出力を確認します。

### ポートが使用中になる

この構成は `8000`、`8080`、`50021` を使用します。使用中のプロセスまたは既存コンテナを停止してから再起動してください。

```powershell
docker compose down
Get-NetTCPConnection -LocalPort 8000,8080,50021 -ErrorAction SilentlyContinue
```

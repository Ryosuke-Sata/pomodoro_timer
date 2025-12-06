# Modern Pomodoro Timer for Windows 11

Windows 11のデザイン言語に調和するように設計された、軽量かつ高機能なポモドーロタイマーアプリケーションです。
PythonとCustomTkinterを用いて開発されており、タスク名記録、CSVエクスポート、ミニモード、Windowsネイティブ通知などの機能を備えています。

## ✨ 主な機能

* **モダンなUI**: Windows 11ライクな角丸デザインとダークモード対応。
* **プリセットタイマー**: Focus (25分/50分) と Break (5分/15分) をワンクリックで切り替え。
* **タスク記録**: 作業内容（タスク名）を入力してログに残すことが可能。
* **作業履歴**: 日ごとの作業時間を自動集計し、アプリ内で閲覧可能。
* **CSVエクスポート**: 蓄積されたログをExcel等で分析可能なCSV形式で出力。
* **ミニモード**: 作業の邪魔にならないコンパクトなウィンドウサイズ（オーバーレイ表示）に切り替え可能。
* **通知機能**: タイマー終了時にWindows標準のトースト通知とアラーム音でお知らせ。
* **常時最前面**: スイッチ一つでウィンドウを最前面に固定。

## 🛠 動作環境・使用技術

* **OS**: Windows 10 / 11 (※通知機能に `winotify` を使用しているためWindows専用です)
* **言語**: Python 3.x
* **ライブラリ**:
    * `customtkinter` (GUI)
    * `winotify` (トースト通知)
    * `winsound` (標準ライブラリ: 音声)
    * `sqlite3` (標準ライブラリ: データベース)

## 📦 インストール方法

### 1. リポジトリのクローン（またはファイルのダウンロード）
ソースコード（`pomodoro_full.py`）を任意のディレクトリに配置してください。

### 2. 仮想環境の作成 (推奨)
```bash
python -m venv .venv
# 仮想環境のアクティベート
.venv\Scripts\activate
```

### 3. 依存ライブラリのインストール
以下のコマンドで必要なライブラリを一括インストールします。
```bash
pip install customtkinter winotify
```
※ Exe化する場合は `pip install pyinstaller` も追加してください。

## 🚀 使い方（ソースコードから実行する場合）

### コマンドでの実行
仮想環境に入った状態で以下を実行します。
```bash
python pomodoro_full.py
```

### ショートカットやバッチファイルでの実行に関する注意
仮想環境（venv）を使用している場合、通常のショートカットではライブラリが見つからずエラーになることがあります。以下のいずれかの方法を推奨します。

#### A. 起動用バッチファイル (`start.bat`) を作成する `pomodoro_full.py` と同じフォルダに以下の内容で作成し、これをダブルクリックします。
```batch
@echo off
cd /d %~dp0
call .venv\Scripts\activate
start pythonw pomodoro_full.py
```

#### B. ショートカットのリンク先を編集する ショートカットのプロパティを開き、リンク先を「venv内のpythonw.exe」経由で指定します。
```text
"C:\Path\To\.venv\Scripts\pythonw.exe" "C:\Path\To\pomodoro_full.py"
```

## 🔧 アプリケーション化（Exe化）の手順
Python環境がないPCでも実行できるように、単一の実行ファイル（.exe）に変換する方法です。

1. PyInstallerのインストール
```bash
pip install pyinstaller
```

2. Exeファイルの作成
```bash
pyinstaller --noconsole --onefile pomodoro_full.py
```

3. 実行 `dist` フォルダ内に生成された `pomodoro_full.exe` を使用してください。

## 📂 データと履歴の保存場所について
本アプリは、実行ファイル（またはスクリプト）と同じディレクトリに `work_log.db` というデータベースファイルを自動生成して履歴を保存します。

- 注意点: `pomodoro_full.exe` を別の場所（別のフォルダやPC）に移動する場合、履歴を引き継ぐには `work_log.db` も一緒に移動させてください。

- exeファイル単体だけを移動すると、移動先で新しい（空の）データベースが作成され、履歴がリセットされたようになります。
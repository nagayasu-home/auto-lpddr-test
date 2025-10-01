# LPDDR Test Automation Terminal Guide

## 概要

`lpddr_terminal.py` は、GUIアプリケーションの代わりにコマンドラインインターフェースを提供するターミナル版のLPDDRテスト自動化ツールです。

## なぜターミナル版が推奨されるのか？

### 🔧 リソース競合の回避
- **シリアルポートの排他制御**: GUIアプリと同時実行時のポート競合を回避
- **メモリ使用量の削減**: GUIフレームワーク（Tkinter）を使用しないため軽量
- **CPU使用率の最適化**: グラフィカル要素の描画処理が不要

### 🚀 運用上の利点
- **サーバー環境での実行**: ヘッドレス環境でも動作
- **自動化スクリプトとの統合**: シェルスクリプトから呼び出し可能
- **リモート実行**: SSH経由でのリモートテスト実行
- **ログ出力の最適化**: 標準出力への直接出力

### 🛠️ 開発・デバッグの利点
- **リアルタイムフィードバック**: コマンド実行結果の即座な確認
- **詳細なログ表示**: エラーメッセージの詳細確認
- **設定の柔軟性**: コマンドラインでの動的設定変更

## 起動方法

```bash
# 基本的な起動
python3 lpddr_terminal.py

# または実行権限を付与して起動
chmod +x lpddr_terminal.py
./lpddr_terminal.py
```

## コマンド一覧

### 📋 基本コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `help` | ヘルプメッセージを表示 | `help` |
| `status` | 現在のステータスを表示 | `status` |
| `clear` | 画面をクリア | `clear` |
| `exit` | アプリケーションを終了 | `exit` |

### ⚙️ 設定コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `config show` | 現在の設定を表示 | `config show` |
| `config port <port>` | シリアルポートを設定 | `config port /dev/ttyUSB0` |
| `config baudrate <rate>` | ボーレートを設定 | `config baudrate 115200` |
| `config timeout <seconds>` | タイムアウトを設定 | `config timeout 30` |
| `config frequencies <freqs>` | テスト周波数を設定 | `config frequencies 800,666` |
| `config patterns <patterns>` | テストパターンを設定 | `config patterns 1,15` |
| `config 2d <on\|off>` | 2Dトレーニングの有効/無効 | `config 2d on` |
| `config eye <on\|off>` | アイパターンテストの有効/無効 | `config eye on` |
| `config power <on\|off>` | 電源制御の有効/無効 | `config power off` |
| `config save <filename>` | 設定をファイルに保存 | `config save my_config.yaml` |
| `config load <filename>` | 設定をファイルから読み込み | `config load my_config.yaml` |

### 🔌 接続コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `connect` | ターゲットボードに接続 | `connect` |
| `disconnect` | ターゲットボードから切断 | `disconnect` |

### 🧪 テストコマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `test` | フルテストシーケンスを実行 | `test` |
| `test freq <frequency>` | 単一周波数テストを実行 | `test freq 800` |
| `test diag` | 診断テストのみを実行 | `test diag` |
| `test eye <type> [lane] [bit]` | アイパターンテストを実行 | `test eye tx 0 0` |
| `stop` | 実行中のテストを停止 | `stop` |

### 📊 情報コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `log [lines]` | ログを表示（デフォルト20行） | `log 50` |
| `log clear` | ログファイルをクリア | `log clear` |
| `history` | コマンド履歴を表示 | `history` |

## 使用例

### 基本的なテストフロー

```bash
# 1. アプリケーション起動
python3 lpddr_terminal.py

# 2. 設定の確認・変更
config show
config port /dev/ttyUSB0
config baudrate 115200
config frequencies 800,666
config patterns 1,15

# 3. ターゲットボードに接続
connect

# 4. テスト実行
test

# 5. 結果確認
log 30
status

# 6. 切断・終了
disconnect
exit
```

### 設定ファイルの使用

```bash
# 設定を保存
config save production_config.yaml

# 別の設定を読み込み
config load test_config.yaml

# 設定を確認
config show
```

### 単一テストの実行

```bash
# 特定の周波数でのテスト
test freq 800

# 診断テストのみ
test diag

# アイパターンテスト
test eye tx 0 0
```

## 設定ファイルの例

### production_config.yaml
```yaml
serial:
  port: "/dev/ttyUSB0"
  baudrate: 115200
  timeout: 30.0

test:
  patterns: [1, 15]
  enable_2d_training: false
  enable_eye_pattern: true

power_control:
  enabled: false
  port: "COM4"
```

### test_config.yaml
```yaml
serial:
  port: "/dev/ttyUSB1"
  baudrate: 115200
  timeout: 60.0

test:
  patterns: [1, 15]
  enable_2d_training: true
  enable_eye_pattern: true

power_control:
  enabled: true
  port: "COM4"
```

## 自動化スクリプトとの統合

### シェルスクリプト例

```bash
#!/bin/bash
# auto_test.sh

echo "Starting LPDDR test automation..."

# ターミナル版を起動してコマンドを実行
python3 lpddr_terminal.py << EOF
config load production_config.yaml
connect
test
log 50
disconnect
exit
EOF

echo "Test completed. Check logs for results."
```

### Pythonスクリプト例

```python
#!/usr/bin/env python3
import subprocess
import sys

def run_lpddr_test():
    commands = [
        "config load production_config.yaml",
        "connect",
        "test",
        "log 50",
        "disconnect",
        "exit"
    ]
    
    # ターミナル版を起動
    process = subprocess.Popen(
        [sys.executable, "lpddr_terminal.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # コマンドを送信
    input_data = "\n".join(commands)
    stdout, stderr = process.communicate(input=input_data)
    
    print("STDOUT:", stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return process.returncode

if __name__ == "__main__":
    exit_code = run_lpddr_test()
    sys.exit(exit_code)
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. 接続エラー
```bash
# ポートの確認
ls /dev/ttyUSB*

# 権限の確認
ls -l /dev/ttyUSB0

# 権限の設定（必要に応じて）
sudo chmod 666 /dev/ttyUSB0
```

#### 2. 設定エラー
```bash
# 設定の確認
config show

# デフォルト設定に戻す
config port /dev/ttyUSB0
config baudrate 115200
config timeout 30
```

#### 3. テスト実行エラー
```bash
# 接続状態の確認
status

# ログの確認
log 50

# テストの停止
stop
```

## ログファイル

### ログファイルの場所
- メインログ: `logs/lpddr_test.log`
- エラーログ: `logs/lpddr_error.log`

### ログの確認方法
```bash
# ターミナル内で確認
log 100

# 直接ファイルを確認
tail -f logs/lpddr_test.log
cat logs/lpddr_error.log
```

## パフォーマンス比較

| 項目 | GUI版 | ターミナル版 |
|------|-------|-------------|
| メモリ使用量 | ~50MB | ~20MB |
| CPU使用率 | 中 | 低 |
| 起動時間 | 3-5秒 | 1-2秒 |
| シリアルポート競合 | あり | なし |
| リモート実行 | 困難 | 容易 |
| 自動化 | 困難 | 容易 |

## まとめ

ターミナル版は以下の場合に特に推奨されます：

✅ **本番環境での運用**  
✅ **自動化スクリプトとの統合**  
✅ **リモート環境での実行**  
✅ **リソース制約のある環境**  
✅ **バッチ処理での大量テスト**  

GUI版は以下の場合に適しています：

✅ **対話的なテスト実行**  
✅ **リアルタイムでの結果確認**  
✅ **視覚的な設定変更**  
✅ **開発・デバッグ作業**  

用途に応じて適切なバージョンを選択することで、効率的なLPDDRテスト自動化が可能になります。

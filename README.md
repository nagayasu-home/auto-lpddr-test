# LPDDR Test Automation Software

AI-CAMKITメインボードのLPDDR4インタフェース検証を自動化するソフトウェアです。

## 機能

- シリアルポート経由でのターゲットボードとの通信
- 自動テスト実行（周波数選択、トレーニング、メモリテスト、診断テスト）
- 結果判定と次ステップ決定
- GUI インターフェース（オプション）
- 設定ファイルによる柔軟な設定
- **高度な可視化機能**（Eye Patternヒートマップ、統合ダッシュボード、テストタイムライン）

## インストール

### 前提条件

- Python 3.8以上
- Windows 10/11 または Linux
- シリアルポート（COMポート）へのアクセス権限

### Windows環境でのセットアップ

#### 1. Pythonのインストール確認
```cmd
python --version
# または
python3 --version
```

#### 2. 仮想環境の作成と有効化
```cmd
# プロジェクトディレクトリに移動
cd C:\path\to\auto-lpddr-test

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
venv\Scripts\activate

# 仮想環境が有効化されていることを確認（プロンプトに(venv)が表示される）
(venv) C:\path\to\auto-lpddr-test>
```

#### 3. 依存関係のインストール
```cmd
# pipを最新版にアップグレード
python -m pip install --upgrade pip

# 依存関係をインストール
pip install -r requirements.txt
```

#### 4. シリアルポートの設定
```cmd
# デバイスマネージャーでCOMポート番号を確認
# 通常はCOM3, COM7など

# config.yamlでポート番号を設定
# serial:
#   port: "COM7"  # 実際のポート番号に変更
```

### Linux環境でのセットアップ

#### 1. 仮想環境の作成と有効化
```bash
# プロジェクトディレクトリに移動
cd /path/to/auto-lpddr-test

# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 仮想環境が有効化されていることを確認
(venv) user@host:~/auto-lpddr-test$
```

#### 2. 依存関係のインストール
```bash
# pipを最新版にアップグレード
python -m pip install --upgrade pip

# 依存関係をインストール
pip install -r requirements.txt
```

#### 3. シリアルポートの権限設定
```bash
# ユーザーをdialoutグループに追加
sudo usermod -a -G dialout $USER

# 変更を反映するためにログアウト・ログインするか、以下を実行
newgrp dialout

# シリアルポートの権限を確認
ls -l /dev/ttyUSB* /dev/ttyACM*
```

### 仮想環境の管理

#### 仮想環境の有効化
```cmd
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### 仮想環境の無効化
```cmd
# Windows/Linux/Mac共通
deactivate
```

#### 仮想環境の削除
```cmd
# Windows
rmdir /s venv

# Linux/Mac
rm -rf venv
```

### トラブルシューティング

#### Windows環境でのよくある問題

**Q: 'python' コマンドが見つからない**
```cmd
# Pythonがインストールされているか確認
where python
# または
where python3

# PATHに追加されていない場合は、フルパスで実行
C:\Python39\python.exe -m venv venv
```

**Q: 仮想環境の有効化でエラーが発生する**
```cmd
# 実行ポリシーの問題の場合
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# または、PowerShellではなくコマンドプロンプトを使用
cmd
venv\Scripts\activate.bat
```

**Q: シリアルポートにアクセスできない**
```cmd
# デバイスマネージャーでCOMポートを確認
# 他のアプリケーション（TeraTerm等）がポートを使用していないか確認
# 管理者権限で実行してみる
```

#### Linux環境でのよくある問題

**Q: シリアルポートの権限エラー**
```bash
# 権限を確認
ls -l /dev/ttyUSB0

# 一時的に権限を変更（推奨しない）
sudo chmod 666 /dev/ttyUSB0

# 正しい方法：ユーザーをdialoutグループに追加
sudo usermod -a -G dialout $USER
```

**Q: 仮想環境でpipが見つからない**
```bash
# 仮想環境を再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
```

## 使用方法

### 仮想環境の有効化

実行前に必ず仮想環境を有効化してください：

```cmd
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### コマンドライン版

```cmd
# Windows
python lpddr_test_automation.py

# Linux/Mac
python3 lpddr_test_automation.py
```

### GUI版

```cmd
# Windows
python lpddr_gui.py

# Linux/Mac
python3 lpddr_gui.py
```

### ターミナル版（推奨）

```cmd
# Windows
python lpddr_terminal.py

# Linux/Mac
python3 lpddr_terminal.py
```

### Windows環境での実行例

```cmd
# 1. 仮想環境を有効化
C:\temp\auto-lpddr-test> venv\Scripts\activate

# 2. 仮想環境が有効化されていることを確認
(venv) C:\temp\auto-lpddr-test>

# 3. GUI版を実行
(venv) C:\temp\auto-lpddr-test> python lpddr_gui.py

# 4. 実行後、仮想環境を無効化（オプション）
(venv) C:\temp\auto-lpddr-test> deactivate
C:\temp\auto-lpddr-test>
```

**ターミナル版の利点:**
- リソース競合の回避（シリアルポートの排他制御）
- 軽量で高速な起動
- 自動化スクリプトとの統合が容易
- リモート環境での実行が可能
- サーバー環境での運用に適している

## 設定

`config.yaml` ファイルで設定を変更できます。このファイルは、LPDDRテスト自動化ソフトウェアの動作を制御する重要な設定ファイルです。

### 設定ファイルの場所
- プロジェクトルートディレクトリの `config.yaml`
- ファイルが存在しない場合は、デフォルト設定が使用されます

### 設定項目の詳細

#### 1. シリアル通信設定 (`serial`)
```yaml
serial:
  port: "COM7"        # シリアルポート（Windows: COM7, Linux: /dev/ttyUSB0）
  baudrate: 115200    # ボーレート
  timeout: 30.0       # タイムアウト（秒）
  parity: "N"         # パリティ（N: なし, E: 偶数, O: 奇数）
  stopbits: 1         # ストップビット
  bytesize: 8         # データビット
```

**設定例：**
- **Windows**: `port: "COM7"`
- **Linux**: `port: "/dev/ttyUSB0"`

#### 2. テスト設定 (`test`)

##### 周波数設定
```yaml
test:
  frequencies: [800, 666]  # テストする周波数（MHz）
```

##### テストパターン設定
```yaml
test:
  patterns:
    - id: 1
      name: "test_lpddrA"
      description: "increment by byte"
    - id: 15
      name: "test_lpddr_bitwalk"
      description: "bit walk test"
```

**利用可能なパターン：**
- `1`: test_lpddrA（バイト単位インクリメント）
- `15`: test_lpddr_bitwalk（ビットウォークテスト）

##### 診断テスト設定
```yaml
test:
  diagnostics:
    addr_low: "0000"    # 開始アドレス（16進数）
    addr_high: "03ff"   # 終了アドレス（16進数）
    loop_count: "00"    # ループ回数
```

##### テストバイト数
```yaml
test:
  test_bytes: 2147483648  # テストするバイト数（全範囲テスト）
```

##### 2Dトレーニング設定
```yaml
test:
  enable_2d_training: false  # 2Dトレーニングの有効/無効
```

##### アイパターンテスト設定
```yaml
test:
  enable_eye_pattern: true   # アイパターンテストの有効/無効
  eye_pattern:
    lanes: 4                 # テストするレーン数
    bits: 8                  # テストするビット数
    timeout: 30.0            # テストタイムアウト（秒）
```

#### 3. 電源制御設定 (`power_control`)
```yaml
power_control:
  enabled: false           # 電源制御の有効/無効
  port: "COM4"            # 電源制御用ポート
  baudrate: 9600          # 電源制御のボーレート
  power_off_delay: 2.0    # 電源OFF待機時間（秒）
  power_on_delay: 3.0     # 電源ON待機時間（秒）
```

#### 4. ログ設定 (`logging`)
```yaml
logging:
  level: "INFO"                                    # ログレベル
  file: "lpddr_test.log"                          # ログファイル名
  format: "%(asctime)s - %(levelname)s - %(message)s"  # ログフォーマット
```

**ログレベル：**
- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 一般的な情報
- `WARNING`: 警告メッセージ
- `ERROR`: エラーメッセージ

#### 5. 結果判定設定 (`judgment`)
```yaml
judgment:
  messages:
    freq_800_pattern_01_pass: "メモリは動作しているが不安定な可能性があります"
    freq_800_pattern_15_pass: "信号線は接続されているが、メモリアクセスが不安定です"
    freq_666_pattern_01_pass: "800MHzでは動作しないが666MHzでは動作します"
    freq_666_pattern_15_pass: "666MHzで信号線接続が確認されました"
    memory_fail_diag_pass: "メモリは動作しているが不安定な可能性があります"
    all_fail: "メモリが動作していません"
  
  require_diagnostics: false  # 診断テストが必要な条件
```

### 設定変更の手順

#### 1. シリアルポートの変更
```yaml
# Windows環境の場合
serial:
  port: "COM7"  # デバイスマネージャーで確認したポート番号に変更

# Linux環境の場合
serial:
  port: "/dev/ttyUSB0"  # 実際のデバイスファイルに変更
```

#### 2. テストパターンの変更
```yaml
# 特定のパターンのみテストする場合
test:
  patterns:
    - id: 1
      name: "test_lpddrA"
      description: "increment by byte"
    # パターン15をコメントアウトして無効化
    # - id: 15
    #   name: "test_lpddr_bitwalk"
    #   description: "bit walk test"
```

#### 3. ログレベルの変更
```yaml
# デバッグ情報を表示したい場合
logging:
  level: "DEBUG"  # INFOからDEBUGに変更
```

### 設定ファイルの検証

設定ファイルの構文を確認するには：
```cmd
# YAML構文チェック（Pythonで）
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### よくある設定ミス

1. **ポート番号の間違い**: デバイスマネージャーで正しいCOMポート番号を確認
2. **YAML構文エラー**: インデント（スペース）に注意
3. **存在しないパターンID**: 利用可能なパターンID（1, 15）のみ使用
4. **権限の問題**: シリアルポートへのアクセス権限を確認

### 設定のリセット

デフォルト設定に戻したい場合：
```cmd
# バックアップを作成
copy config.yaml config.yaml.backup

# デフォルト設定を再生成（アプリケーション起動時に自動生成される）
```

## テストフロー

1. シリアル接続確立
2. 周波数選択（800MHz → 666MHz）
3. 1Dトレーニング実行
4. メモリテスト実行（パターン01, 15）
5. 診断テスト実行
6. 結果判定とレポート生成

## ファイル構成

- `lpddr_test_automation.py` - メインの自動化スクリプト
- `lpddr_gui.py` - GUI インターフェース
- `lpddr_terminal.py` - ターミナル インターフェース（推奨）
- `visualization.py` - ビジュアライゼーション機能
- `config.yaml` - 設定ファイル
- `requirements.txt` - 依存関係
- `README.md` - このファイル
- `TERMINAL_GUIDE.md` - ターミナル版の詳細ガイド
- `API_DOCUMENTATION.md` - API仕様書

## 実装した機能：

### 1. 完全自動化されたテストシーケンス
- シリアル通信による双方向データ交換
- プロンプト待機と自動応答
- テスト結果の自動解析
- **NEW**: 2Dトレーニング機能
- **NEW**: 電源リセット機能
- **NEW**: 強化されたエラーハンドリング

### 2. インテリジェントな判定ロジック
- PDFの判定基準を完全実装
- 次ステップの自動決定
- 総合的な結果判定
- **NEW**: TX/RXアイパターンテストによる詳細分析
- **NEW**: 構造化ログによる詳細な分析

### 3. 柔軟な設定システム
- YAML設定ファイル
- 周波数・パターンのカスタマイズ
- ログレベル調整
- **NEW**: アイパターンテスト設定
- **NEW**: 電源制御設定
- **NEW**: 設定バリデーション機能

### 4. ユーザーフレンドリーなインターフェース
- GUI版とコマンドライン版
- リアルタイムログ表示
- 結果レポート生成
- **NEW**: アイパターン結果の詳細表示
- **NEW**: プログレスバーとステータス表示
- **NEW**: 結果エクスポート機能
- **NEW**: 高度なビジュアライゼーション機能

### 5. 新機能詳細

#### TX/RXアイパターンテスト
- 信号品質の詳細分析
- レーン別・ビット別の個別テスト
- 包括的なアイパターン分析

#### 2Dトレーニング
- 高度なメモリ調整機能
- 設定による有効/無効切り替え
- トレーニング結果の自動検証

#### 電源リセット機能
- テスト失敗時の自動復旧
- 電源制御ポート経由の自動制御
- 手動電源リセットのサポート

#### 高度なビジュアライゼーション機能
- アイパターン結果のヒートマップ表示
- テスト実行タイムラインの可視化
- インタラクティブダッシュボード
- 包括的なサマリーレポート生成
- 複数形式でのエクスポート（PNG, HTML, TXT）

### 6. 品質向上機能

#### 単体テスト
- 包括的なテストカバレッジ
- モックを使用したテスト
- エラーケースのテスト

#### エラーハンドリング
- カスタム例外クラス
- 詳細なエラーメッセージ
- 適切な例外の伝播

#### 構造化ログ
- JSON形式のログ出力
- ログローテーション
- パフォーマンス監視

#### 設定バリデーション
- 入力値の検証
- 型安全性の確保
- エラーメッセージの改善

## ビジュアライゼーション機能

### 利用可能な可視化

1. **アイパターンヒートマップ**
   - TX/RX信号品質の4レーン×8ビットマトリックス表示
   - パス/フェイル結果の色分け表示
   - 統計情報とパス率の表示

2. **テストタイムライン**
   - テスト実行の時系列表示
   - ステップ別の結果分布
   - パス/フェイル率の統計

3. **インタラクティブダッシュボード**
   - 複数の可視化を統合したHTMLダッシュボード
   - ブラウザで表示可能
   - ズーム・パン機能付き

4. **サマリーレポート**
   - テスト結果の詳細分析
   - 推奨事項の自動生成
   - テキスト形式でのエクスポート

### 使用方法

#### GUI版での可視化操作

##### 基本的な操作手順
1. **テスト実行**: まずLPDDRテストを実行してください
2. **結果可視化ボタン**: テスト完了後、「結果可視化」ボタンをクリック
3. **可視化表示**: 以下の可視化が自動的に生成・表示されます：
   - Eye Patternヒートマップ
   - テストタイムライン
   - 統合ダッシュボード
   - サマリーレポート

##### 詳細な操作説明

**ステップ1: テスト実行**
```
1. 接続設定を確認（COMポート、ボーレート等）
2. テスト設定を確認（周波数、パターン、2D Training、Eye Pattern等）
3. 「テスト開始」ボタンをクリック
4. テストログで進行状況を確認
```

**ステップ2: 可視化の実行**
```
1. テスト完了後、「結果可視化」ボタンが有効になります
2. ボタンをクリックすると以下の処理が実行されます：
   - テスト結果の解析
   - 可視化データの生成
   - グラフ・チャートの作成
   - ファイルの保存
```

**ステップ3: 結果の確認**
```
1. 生成された可視化ファイルの場所：
   - visualization_output/eye_pattern_results_YYYYMMDD_HHMMSS.png
   - visualization_output/dashboard_unified_YYYYMMDD_HHMMSS.html
   - visualization_output/summary_report_unified_YYYYMMDD_HHMMSS.txt
   - visualization_output/test_timeline_unified_YYYYMMDD_HHMMSS.png

2. ファイルの開き方：
   - PNGファイル: 画像ビューアーで開く
   - HTMLファイル: ウェブブラウザで開く
   - TXTファイル: テキストエディタで開く
```

#### コマンドライン版での可視化操作

##### 自動可視化
```bash
# テスト実行時に自動的に可視化が生成されます
python lpddr_terminal.py

# 生成されるファイル
ls visualization_output/
# eye_pattern_results_20241009_143022.png
# dashboard_unified_20241009_143022.html
# summary_report_unified_20241009_143022.txt
```

##### 手動可視化
```python
# Pythonスクリプトで手動実行
from visualization import LPDDRVisualizer

# 可視化インスタンスの作成
visualizer = LPDDRVisualizer()

# テスト結果の可視化
visualizer.plot_test_results(test_results, save_plot=True, show_plot=False)
```

#### 可視化ファイルの操作

##### ファイルの種類と用途
1. **Eye Patternヒートマップ** (PNG)
   - 用途: 信号品質の詳細分析
   - 開き方: 画像ビューアー、画像編集ソフト
   - 活用: レポート作成、プレゼンテーション

2. **統合ダッシュボード** (HTML)
   - 用途: 包括的な結果表示
   - 開き方: ウェブブラウザ（Chrome、Firefox、Edge等）
   - 活用: インタラクティブな分析、共有

3. **サマリーレポート** (TXT)
   - 用途: テキスト形式での結果確認
   - 開き方: テキストエディタ、メモ帳
   - 活用: ログ分析、自動処理

4. **テストタイムライン** (PNG)
   - 用途: 時系列での結果分析
   - 開き方: 画像ビューアー
   - 活用: テスト効率の分析

##### ファイルの管理
```bash
# 可視化ファイルの一覧表示
ls -la visualization_output/

# 古いファイルの削除（30日以上前）
find visualization_output/ -name "*.png" -mtime +30 -delete
find visualization_output/ -name "*.html" -mtime +30 -delete
find visualization_output/ -name "*.txt" -mtime +30 -delete

# ファイルのバックアップ
cp -r visualization_output/ backup_visualization_$(date +%Y%m%d)/
```

#### 可視化のトラブルシューティング

##### よくある問題と解決方法

**問題1: 「可視化する結果がありません」エラー**
```
原因: テストが実行されていない、または結果データが存在しない
解決方法:
1. まずLPDDRテストを実行してください
2. テストが正常に完了していることを確認
3. テストログでエラーがないことを確認
```

**問題2: 可視化ファイルが生成されない**
```
原因: 必要なライブラリがインストールされていない
解決方法:
pip install matplotlib seaborn plotly pandas numpy
```

**問題3: HTMLダッシュボードが正しく表示されない**
```
原因: ブラウザの互換性問題
解決方法:
1. 最新のブラウザを使用（Chrome、Firefox、Edge）
2. JavaScriptが有効になっていることを確認
3. ローカルファイルの制限を解除
```

**問題4: Eye Patternヒートマップが空白**
```
原因: Eye Patternテストが実行されていない
解決方法:
1. config.yamlでenable_eye_pattern: trueを設定
2. 2D Trainingも有効にする（enable_2d_training: true）
3. テストを再実行
```

##### デバッグ方法

**ログの確認**
```bash
# 詳細ログを有効にしてテスト実行
python lpddr_gui.py --debug

# 可視化のデバッグ情報を確認
python -c "
from visualization import LPDDRVisualizer
import logging
logging.basicConfig(level=logging.DEBUG)
visualizer = LPDDRVisualizer()
"
```

**手動での可視化テスト**
```python
# テストデータでの可視化確認
from visualization import LPDDRVisualizer

# サンプルデータの作成
test_data = {
    'eye_pattern_test_1': '#### Finish Diagnostics test (Tx Eye Pattern)\nEye Pattern Test completed successfully.\nQuality: 0.95',
    'eye_pattern_test_2': '#### Finish Diagnostics test (Rx Eye Pattern)\nEye Pattern Test completed successfully.\nQuality: 0.92'
}

# 可視化の実行
visualizer = LPDDRVisualizer()
result = visualizer.visualize_eye_pattern_results(test_data, save_plot=True)
print(f"可視化ファイル: {result}")
```

#### 高度な可視化操作

##### カスタム可視化の作成

**特定の周波数での結果のみ可視化**
```python
from visualization import LPDDRVisualizer
from lpddr_test_automation import TestResultData, TestStep, TestResult

# 特定の周波数の結果のみフィルタリング
filtered_results = [r for r in test_results if r.frequency == 800]

# 可視化の実行
visualizer = LPDDRVisualizer()
visualizer.plot_test_results(filtered_results, save_plot=True)
```

**複数のテスト結果の比較**
```python
# 複数のテスト結果を比較
visualizer = LPDDRVisualizer()

# 結果1の可視化
result1 = visualizer.plot_test_results(test_results_1, save_plot=True, show_plot=False)

# 結果2の可視化
result2 = visualizer.plot_test_results(test_results_2, save_plot=True, show_plot=False)

print(f"比較用ファイル1: {result1}")
print(f"比較用ファイル2: {result2}")
```

##### バッチ処理での可視化

**複数のテスト結果を一括可視化**
```python
import os
import glob
from visualization import LPDDRVisualizer

def batch_visualize_results(results_directory):
    """複数のテスト結果を一括可視化"""
    visualizer = LPDDRVisualizer()
    
    # 結果ファイルの検索
    result_files = glob.glob(os.path.join(results_directory, "*.json"))
    
    for result_file in result_files:
        # 結果の読み込み
        with open(result_file, 'r') as f:
            test_results = json.load(f)
        
        # 可視化の実行
        output_file = visualizer.plot_test_results(test_results, save_plot=True)
        print(f"可視化完了: {output_file}")

# 使用例
batch_visualize_results("test_results/")
```

##### 可視化結果の自動分析

**結果の自動判定**
```python
from visualization import LPDDRVisualizer

def analyze_visualization_results(visualizer, test_results):
    """可視化結果の自動分析"""
    unified_data = visualizer.convert_to_unified_data(test_results)
    
    # パス率の計算
    pass_rate = unified_data.summary_stats['pass_rate']
    
    # 自動判定
    if pass_rate >= 90:
        status = "EXCELLENT"
        recommendation = "すべてのテストが正常に完了しています"
    elif pass_rate >= 70:
        status = "GOOD"
        recommendation = "一部のテストで問題がありますが、基本的な動作は確認できています"
    elif pass_rate >= 50:
        status = "WARNING"
        recommendation = "複数のテストで問題が発生しています。詳細な調査が必要です"
    else:
        status = "CRITICAL"
        recommendation = "重大な問題が発生しています。ハードウェアの確認が必要です"
    
    return {
        'status': status,
        'pass_rate': pass_rate,
        'recommendation': recommendation
    }

# 使用例
visualizer = LPDDRVisualizer()
analysis = analyze_visualization_results(visualizer, test_results)
print(f"判定結果: {analysis['status']}")
print(f"推奨事項: {analysis['recommendation']}")
```

#### 可視化結果の活用方法

##### レポート作成での活用

**Eye Patternヒートマップの活用**
- 信号品質の問題箇所の特定
- ハードウェア設計の改善点の提案
- テスト結果の視覚的な説明

**統合ダッシュボードの活用**
- ステークホルダーへの結果報告
- インタラクティブな結果確認
- 複数のテスト結果の比較

**サマリーレポートの活用**
- 自動化された結果分析
- ログファイルとの照合
- 継続的な品質監視

##### 品質管理での活用

**トレンド分析**
```python
# 複数のテスト結果からトレンドを分析
def analyze_trends(test_results_history):
    """テスト結果のトレンド分析"""
    pass_rates = []
    dates = []
    
    for result in test_results_history:
        pass_rates.append(result['pass_rate'])
        dates.append(result['date'])
    
    # トレンドの計算
    if len(pass_rates) > 1:
        trend = "改善" if pass_rates[-1] > pass_rates[0] else "悪化"
    else:
        trend = "データ不足"
    
    return {
        'trend': trend,
        'current_pass_rate': pass_rates[-1] if pass_rates else 0,
        'historical_data': list(zip(dates, pass_rates))
    }
```

**品質ゲートの設定**
```python
def quality_gate_check(pass_rate, eye_pattern_quality):
    """品質ゲートのチェック"""
    if pass_rate >= 95 and eye_pattern_quality >= 0.9:
        return "PASS - 製品リリース可能"
    elif pass_rate >= 80 and eye_pattern_quality >= 0.7:
        return "CONDITIONAL PASS - 条件付きリリース"
    else:
        return "FAIL - リリース不可、改善が必要"
```

## 注意事項

### 共通の注意事項
- ターゲットボードが正しく接続されていることを確認してください
- テスト実行中は他のアプリケーションでシリアルポートを使用しないでください
- ビジュアライゼーション機能には追加のPythonライブラリが必要です（matplotlib, seaborn, plotly等）

### Windows環境での注意事項
- **シリアルポートの競合**: TeraTermやPuTTYなどの他のシリアル通信ソフトウェアを閉じてから実行してください
- **管理者権限**: シリアルポートにアクセスできない場合は、管理者権限でコマンドプロンプトを実行してください
- **COMポート番号**: デバイスマネージャーで正しいCOMポート番号を確認し、`config.yaml`で設定してください
- **仮想環境**: 必ず仮想環境を有効化してから実行してください
- **実行ポリシー**: PowerShellで仮想環境の有効化に失敗する場合は、コマンドプロンプトを使用してください

### Linux環境での注意事項
- **シリアルポートの権限**: ユーザーをdialoutグループに追加してください（`sudo usermod -a -G dialout $USER`）
- **デバイスファイル**: シリアルデバイスが`/dev/ttyUSB0`や`/dev/ttyACM0`として認識されていることを確認してください
- **権限確認**: `ls -l /dev/ttyUSB*`で権限を確認してください

### トラブルシューティング

#### 接続エラーの対処法
1. **ポートが使用中**: 他のアプリケーション（TeraTerm等）を閉じる
2. **権限エラー**: 管理者権限で実行する（Windows）またはユーザーをdialoutグループに追加（Linux）
3. **ポート番号が間違っている**: デバイスマネージャー（Windows）または`ls /dev/tty*`（Linux）で確認
4. **ケーブル接続**: USBケーブルが正しく接続されているか確認

#### 仮想環境の問題
1. **仮想環境が有効化されない**: コマンドプロンプトを使用（PowerShellではなく）
2. **パッケージが見つからない**: 仮想環境を有効化してから`pip install -r requirements.txt`を実行
3. **Pythonコマンドが見つからない**: フルパスで実行するか、PATHを設定

## ビジュアライゼーション機能の詳細

### 機能概要

LPDDR Test Automation Softwareには、テスト結果を直感的に理解できる高度なビジュアライゼーション機能が搭載されています。これらの機能により、信号品質の問題を迅速に特定し、適切な対策を講じることができます。

### 1. アイパターンヒートマップ

#### 機能
- **TX/RX信号品質の可視化**: 4レーン×8ビットのマトリックス表示
- **色分け表示**: 緑色（PASS）、赤色（FAIL）で結果を視覚化
- **統計情報**: 各レーン・ビットのパス率を数値で表示
- **高解像度出力**: 300DPIでのPNG形式保存

#### 読み方
```
TX Eye Pattern Results          RX Eye Pattern Results
  0 1 2 3 4 5 6 7               0 1 2 3 4 5 6 7
0 1 1 1 1 1 1 1 1             0 1 1 1 1 1 1 1 1
1 1 1 1 1 1 1 1 1             1 1 1 1 1 1 1 1 1
2 1 1 1 1 1 1 1 1             2 1 1 1 1 1 1 1 1
3 1 1 1 1 1 1 1 1             3 1 1 1 1 1 1 1 1
```
- **1**: テストパス（緑色表示）
- **0**: テストフェイル（赤色表示）

#### 活用方法
- 特定のレーン・ビットで問題が発生している場合の特定
- 信号品質の傾向分析
- ハードウェア設計の改善点の特定

### 2. テストタイムライン

#### 機能
- **時系列表示**: テスト実行の時間軸での結果表示
- **ステップ別分析**: 各テストステップの分布を棒グラフで表示
- **詳細アノテーション**: 各ポイントに周波数、パターン、結果を表示
- **統計サマリー**: 全体のパス/フェイル率を表示

#### 読み方
```
Test Execution Timeline
PASS (1.0) ●─────────────────●
           │                 │
UNKNOWN(0.5)                 │
           │                 │
FAIL (0.0) ●─────────────────●
           │                 │
          時間軸（実行順序）
```

#### 活用方法
- テスト実行の流れの把握
- 問題が発生したタイミングの特定
- テスト効率の分析

### 3. インタラクティブダッシュボード

#### 機能
- **統合表示**: 複数の可視化を1つのHTMLファイルに統合
- **ブラウザ表示**: 標準的なWebブラウザで表示可能
- **インタラクティブ操作**: ズーム、パン、ホバー情報表示
- **4つのサブプロット**:
  1. テスト結果タイムライン
  2. アイパターン結果ヒートマップ
  3. テストステップ分布
  4. パス/フェイルサマリー

#### 使用方法
1. 生成されたHTMLファイルをブラウザで開く
2. 各グラフをクリック・ドラッグで操作
3. ホバーで詳細情報を確認

### 4. サマリーレポート

#### 機能
- **包括的分析**: 全テスト結果の詳細統計
- **推奨事項**: 問題に応じた具体的な対策提案
- **テキスト形式**: 読みやすい形式での出力
- **自動生成**: テスト結果に基づく自動分析

#### レポート内容
```
=== LPDDR Test Report ===
Generated: 2024-01-15 14:30:25

TEST RESULTS SUMMARY:
------------------------------
Total Tests: 12
PASS: 8 (66.7%)
FAIL: 3 (25.0%)
UNKNOWN: 1 (8.3%)

STEP-BY-STEP SUMMARY:
------------------------------
memory_test: 6/8 (75.0%)
eye_pattern: 2/4 (50.0%)

EYE PATTERN TEST SUMMARY:
------------------------------
TX Eye Pattern Tests: 15/16 (93.8%)
RX Eye Pattern Tests: 12/16 (75.0%)

RECOMMENDATIONS:
------------------------------
⚠ Good test results with some issues. Consider signal optimization.
• Consider adjusting signal timing and voltage parameters
• Check for electromagnetic interference (EMI) issues
• Verify PCB routing and impedance matching
```

### 5. エクスポート機能

#### 対応形式
- **PNG**: 高解像度画像（300DPI）
- **HTML**: インタラクティブダッシュボード
- **TXT**: サマリーレポート

#### ファイル命名規則
```
eye_pattern_results_20240115_143025.png
test_timeline_20240115_143025.png
dashboard_20240115_143025.html
summary_report_20240115_143025.txt
```

### 6. 高度な分析機能

#### 信号品質分析
- **レーン別分析**: 各レーンの信号品質を個別評価
- **ビット別分析**: 各ビットの信号品質を個別評価
- **TX/RX比較**: 送信・受信信号の品質比較
- **統計的評価**: パス率による定量的評価

#### 問題診断
- **信号劣化の特定**: 特定のレーン・ビットでの問題特定
- **タイミング問題**: 信号タイミングの問題検出
- **電圧問題**: 信号電圧の問題検出
- **EMI問題**: 電磁干渉の影響評価

### 7. カスタマイズ機能

#### 設定可能項目
- **出力ディレクトリ**: ビジュアライゼーション結果の保存先
- **表示/非表示**: 各可視化の表示制御
- **色設定**: パス/フェイルの色分け設定
- **解像度**: 出力画像の解像度設定

#### プログラムでの使用例
```python
from visualization import LPDDRVisualizer

# ビジュアライザーの初期化
visualizer = LPDDRVisualizer(output_dir="my_results")

# アイパターン結果の可視化
visualizer.visualize_eye_pattern_results(
    eye_pattern_results, 
    save_plot=True, 
    show_plot=True
)

# 全ビジュアライゼーションのエクスポート
exported_files = visualizer.export_all_visualizations(
    test_results, 
    eye_pattern_results
)
```

### 8. トラブルシューティング

#### よくある問題と解決方法

**Q: ビジュアライゼーションが表示されない**
A: 以下のライブラリがインストールされているか確認してください：
```bash
pip install matplotlib seaborn plotly pandas numpy
```

**Q: 日本語が正しく表示されない**
A: システムに日本語フォントがインストールされているか確認してください。

**Q: HTMLダッシュボードが開けない**
A: ブラウザのJavaScriptが有効になっているか確認してください。

**Q: 画像の解像度が低い**
A: デフォルトは300DPIですが、必要に応じてコード内で調整可能です。

### 9. パフォーマンス最適化

#### 推奨設定
- **大量データ**: アイパターンテストの結果が多い場合は、表示を制限
- **メモリ使用量**: 大きなデータセットの場合は、バッチ処理を推奨
- **出力サイズ**: 高解像度画像はファイルサイズが大きくなるため注意

#### 最適化のヒント
```python
# 大量データの場合の最適化例
if len(eye_pattern_results) > 100:
    # サンプリングして表示
    sampled_results = dict(list(eye_pattern_results.items())[:50])
    visualizer.visualize_eye_pattern_results(sampled_results)
```

### 10. 今後の拡張予定

#### 予定されている機能
- **3D可視化**: 信号品質の3次元表示
- **リアルタイム監視**: テスト実行中のリアルタイム可視化
- **比較機能**: 複数テスト結果の比較表示
- **自動レポート**: より詳細な自動分析レポート
- **カスタムテーマ**: ユーザー定義の表示テーマ

これらのビジュアライゼーション機能により、LPDDR4インターフェースの信号品質をより深く理解し、効率的な問題解決が可能になります。

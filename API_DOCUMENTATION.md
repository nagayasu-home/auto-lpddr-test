# LPDDR Test Automation API Documentation

## 概要

このドキュメントは、LPDDR Test Automation SoftwareのAPI仕様と使用方法について説明します。

## モジュール構成

### 1. lpddr_test_automation.py
メインの自動化ロジックを提供するモジュール

### 2. lpddr_gui.py
GUI インターフェースを提供するモジュール

### 3. constants.py
定数定義モジュール

### 4. exceptions.py
カスタム例外クラス定義

### 5. validators.py
設定バリデーション機能

### 6. logger_config.py
ログ設定と構造化ログ機能

### 7. visualization.py
ビジュアライゼーション機能

## 主要クラス

### TestConfig

テスト設定を管理するデータクラス

```python
@dataclass
class TestConfig:
    port: str = "COM3"  # シリアルポート
    baudrate: int = 115200  # ボーレート
    timeout: float = 30.0  # タイムアウト（秒）
    test_patterns: List[int] = None  # テストパターン
    enable_2d_training: bool = False  # 2Dトレーニング有効化
    enable_eye_pattern: bool = True  # アイパターンテスト有効化
    power_control_enabled: bool = False  # 電源制御有効化
    power_control_port: str = None  # 電源制御ポート
```

#### メソッド

- `_validate_config()`: 設定のバリデーションを実行

### LPDDRAutomation

LPDDRテスト自動化のメインクラス

#### コンストラクタ

```python
def __init__(self, config: TestConfig):
    """
    LPDDRAutomationインスタンスを初期化
    
    Args:
        config (TestConfig): テスト設定
    """
```

#### 主要メソッド

##### connect() -> bool
```python
def connect(self) -> bool:
    """
    シリアル接続を確立
    
    Returns:
        bool: 接続成功時True、失敗時False
        
    Raises:
        SerialConnectionError: シリアル接続エラー
        ConnectionError: 一般的な接続エラー
    """
```

##### disconnect()
```python
def disconnect(self):
    """
    シリアル接続を切断
    """
```

##### send_command(command: str) -> bool
```python
def send_command(self, command: str) -> bool:
    """
    コマンドを送信
    
    Args:
        command (str): 送信するコマンド
        
    Returns:
        bool: 送信成功時True、失敗時False
        
    Raises:
        CommandError: コマンド送信エラー
    """
```

##### read_response(timeout: float = None) -> str
```python
def read_response(self, timeout: float = None) -> str:
    """
    レスポンスを読み取り
    
    Args:
        timeout (float, optional): タイムアウト時間（秒）
        
    Returns:
        str: 受信したレスポンス
        
    Raises:
        CommandError: レスポンス読み取りエラー
    """
```

##### wait_for_prompt(prompt_pattern: str, timeout: float = 30.0) -> bool
```python
def wait_for_prompt(self, prompt_pattern: str, timeout: float = 30.0) -> bool:
    """
    プロンプトを待機
    
    Args:
        prompt_pattern (str): 待機するプロンプトパターン
        timeout (float): タイムアウト時間（秒）
        
    Returns:
        bool: プロンプト受信時True
        
    Raises:
        TimeoutError: タイムアウトエラー
    """
```

##### run_frequency_test(frequency: int) -> Dict[str, TestResult]
```python
def run_frequency_test(self, frequency: int) -> Dict[str, TestResult]:
    """
    周波数テストを実行
    
    Args:
        frequency (int): テスト周波数（MHz）
        
    Returns:
        Dict[str, TestResult]: パターン別テスト結果
        
    Raises:
        TestExecutionError: テスト実行エラー
    """
```

##### run_diagnostics_test() -> TestResult
```python
def run_diagnostics_test(self) -> TestResult:
    """
    診断テストを実行
    
    Returns:
        TestResult: 診断テスト結果
        
    Raises:
        TestExecutionError: テスト実行エラー
    """
```

##### run_eye_pattern_test(pattern_type: EyePatternType, lane: int = 0, bit: int = 0) -> TestResult
```python
def run_eye_pattern_test(self, pattern_type: EyePatternType, lane: int = 0, bit: int = 0) -> TestResult:
    """
    アイパターンテストを実行
    
    Args:
        pattern_type (EyePatternType): アイパターンタイプ
        lane (int): レーン番号（0-3）
        bit (int): ビット番号（0-7）
        
    Returns:
        TestResult: アイパターンテスト結果
        
    Raises:
        TestExecutionError: テスト実行エラー
    """
```

##### run_full_test_sequence() -> bool
```python
def run_full_test_sequence(self) -> bool:
    """
    完全なテストシーケンスを実行
    
    Returns:
        bool: テスト成功時True、失敗時False
    """
```

### LPDDRTestGUI

GUI インターフェースクラス

#### コンストラクタ

```python
def __init__(self, root):
    """
    GUIインスタンスを初期化
    
    Args:
        root: Tkinterルートウィンドウ
    """
```

#### 主要メソッド

##### start_test()
```python
def start_test(self):
    """
    テストを開始
    
    設定の検証を行い、テストを別スレッドで実行
    """
```

##### stop_test()
```python
def stop_test(self):
    """
    テストを停止
    """
```

##### validate_settings() -> bool
```python
def validate_settings(self) -> bool:
    """
    設定の妥当性をチェック
    
    Returns:
        bool: 設定が有効な場合True
    """
```

##### save_config()
```python
def save_config(self):
    """
    設定をYAMLファイルに保存
    """
```

##### load_config()
```python
def load_config(self):
    """
    YAMLファイルから設定を読み込み
    """
```

##### export_results()
```python
def export_results(self):
    """
    テスト結果をテキストファイルにエクスポート
    """
```

## 列挙型

### TestResult
```python
class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
```

### TestStep
```python
class TestStep(Enum):
    FREQUENCY_SELECT = "frequency_select"
    TRAINING = "training"
    MEMORY_TEST = "memory_test"
    DIAGNOSTICS = "diagnostics"
    EYE_PATTERN = "eye_pattern"
    POWER_CYCLE = "power_cycle"
    COMPLETE = "complete"
```

### EyePatternType
```python
class EyePatternType(Enum):
    TX = "tx"
    RX = "rx"
    SIMPLE_WRITE_READ = "simple_write_read"
```

## 例外クラス

### LPDDRAutomationError
基底例外クラス

### ConnectionError
接続関連のエラー

### SerialConnectionError
シリアル接続エラー

### ConfigurationError
設定関連のエラー

### ValidationError
設定バリデーションエラー

### TestExecutionError
テスト実行エラー

### TimeoutError
タイムアウトエラー

### CommandError
コマンド関連のエラー

## バリデーター

### ConfigValidator
設定値のバリデーション機能を提供

#### 主要メソッド

- `validate_baudrate(baudrate: int)`: ボーレート検証
- `validate_timeout(timeout: float)`: タイムアウト検証
- `validate_port(port: str)`: ポート検証
- `validate_frequency(frequency: int)`: 周波数検証
- `validate_patterns(patterns: List[int])`: パターン検証

### FileValidator
ファイル関連のバリデーション機能

### StringValidator
文字列関連のバリデーション機能

### RangeValidator
範囲関連のバリデーション機能

## ログ機能

### LPDDRLogger
構造化ログ機能を提供

### TestLogger
テスト専用ログ機能

#### 主要メソッド

- `log_test_start(frequency: int, pattern: int = None)`: テスト開始ログ
- `log_test_result(frequency: int, pattern: int, result: str, message: str = "")`: テスト結果ログ
- `log_connection(port: str, baudrate: int, success: bool)`: 接続ログ
- `log_command(command: str, response: str = None)`: コマンドログ
- `log_error(error: Exception, context: Dict[str, Any] = None)`: エラーログ

## 使用例

### 基本的な使用方法

```python
from lpddr_test_automation import LPDDRAutomation, TestConfig

# 設定を作成
config = TestConfig(
    port="/dev/ttyUSB0",
    baudrate=115200,
    timeout=30.0
)

# 自動化インスタンスを作成
automation = LPDDRAutomation(config)

# テストを実行
try:
    success = automation.run_full_test_sequence()
    if success:
        print("テストが正常に完了しました")
    else:
        print("テストが失敗しました")
except Exception as e:
    print(f"エラーが発生しました: {e}")
finally:
    automation.disconnect()
```

### GUIの使用方法

```python
import tkinter as tk
from lpddr_gui import LPDDRTestGUI

# GUIを起動
root = tk.Tk()
app = LPDDRTestGUI(root)
app.check_log_queue()  # ログキュー監視を開始
root.mainloop()
```

### 設定ファイルの例

```yaml
# config.yaml
serial:
  port: "/dev/ttyUSB0"
  baudrate: 115200
  timeout: 30.0

test:
  frequencies: [800, 666]
  patterns: [1, 15]
  enable_2d_training: false
  enable_eye_pattern: true

power_control:
  enabled: false
  port: "COM4"
  baudrate: 9600

logging:
  level: "INFO"
  file: "lpddr_test.log"
```

## エラーハンドリング

### 推奨されるエラーハンドリングパターン

```python
from lpddr_test_automation import LPDDRAutomation, TestConfig
from exceptions import (
    ConnectionError, SerialConnectionError, 
    ConfigurationError, TestExecutionError
)

try:
    config = TestConfig(port="/dev/ttyUSB0")
    automation = LPDDRAutomation(config)
    
    if not automation.connect():
        print("接続に失敗しました")
        return
    
    # テスト実行
    results = automation.run_frequency_test(800)
    
except SerialConnectionError as e:
    print(f"シリアル接続エラー: {e}")
except ConfigurationError as e:
    print(f"設定エラー: {e}")
except TestExecutionError as e:
    print(f"テスト実行エラー: {e}")
except Exception as e:
    print(f"予期しないエラー: {e}")
finally:
    if 'automation' in locals():
        automation.disconnect()
```

## 設定バリデーション

### 設定値の検証例

```python
from validators import ConfigValidator
from exceptions import ValidationError

try:
    # ボーレート検証
    ConfigValidator.validate_baudrate(115200)
    
    # 周波数検証
    ConfigValidator.validate_frequency(800)
    
    # パターン検証
    ConfigValidator.validate_patterns([1, 15])
    
    print("設定は有効です")
    
except ValidationError as e:
    print(f"設定エラー: {e}")
```

## ログ機能の使用

### 構造化ログの使用例

```python
from logger_config import setup_logging, get_test_logger

# ログ設定
logger = setup_logging(log_level="INFO")

# テストロガーの使用
test_logger = get_test_logger("test_001")
test_logger.log_test_start(frequency=800, pattern=1)
test_logger.log_test_result(frequency=800, pattern=1, result="PASS")
test_logger.log_connection(port="/dev/ttyUSB0", baudrate=115200, success=True)
```

## ビジュアライゼーション機能

### LPDDRVisualizer

テスト結果のビジュアライゼーション機能を提供するクラス

#### コンストラクタ

```python
def __init__(self, output_dir: str = "visualization_output"):
    """
    ビジュアライザーを初期化
    
    Args:
        output_dir (str): 出力ディレクトリ
    """
```

#### 主要メソッド

##### visualize_eye_pattern_results(eye_pattern_results, save_plot=True, show_plot=False) -> str
```python
def visualize_eye_pattern_results(self, eye_pattern_results: Dict[str, str], 
                                save_plot: bool = True, show_plot: bool = False) -> str:
    """
    アイパターン結果をヒートマップで可視化
    
    Args:
        eye_pattern_results (Dict[str, str]): アイパターン結果辞書
        save_plot (bool): プロットを保存するか
        show_plot (bool): プロットを表示するか
        
    Returns:
        str: 保存されたファイルパス
    """
```

##### visualize_test_timeline(test_results, save_plot=True, show_plot=False) -> str
```python
def visualize_test_timeline(self, test_results: List[TestResult], 
                          save_plot: bool = True, show_plot: bool = False) -> str:
    """
    テスト実行タイムラインを可視化
    
    Args:
        test_results (List[TestResult]): テスト結果リスト
        save_plot (bool): プロットを保存するか
        show_plot (bool): プロットを表示するか
        
    Returns:
        str: 保存されたファイルパス
    """
```

##### create_interactive_dashboard(test_results, eye_pattern_results, save_html=True) -> str
```python
def create_interactive_dashboard(self, test_results: List[TestResult], 
                               eye_pattern_results: Dict[str, str],
                               save_html: bool = True) -> str:
    """
    インタラクティブなダッシュボードを作成
    
    Args:
        test_results (List[TestResult]): テスト結果リスト
        eye_pattern_results (Dict[str, str]): アイパターン結果辞書
        save_html (bool): HTMLファイルを保存するか
        
    Returns:
        str: 保存されたファイルパス
    """
```

##### export_all_visualizations(test_results, eye_pattern_results) -> Dict[str, str]
```python
def export_all_visualizations(self, test_results: List[TestResult], 
                            eye_pattern_results: Dict[str, str]) -> Dict[str, str]:
    """
    すべてのビジュアライゼーションをエクスポート
    
    Args:
        test_results (List[TestResult]): テスト結果リスト
        eye_pattern_results (Dict[str, str]): アイパターン結果辞書
        
    Returns:
        Dict[str, str]: エクスポートされたファイルのパス辞書
    """
```

## 注意事項

1. **シリアルポートの権限**: Linux環境では、シリアルポートへのアクセス権限が必要です
2. **接続の確認**: テスト実行前にターゲットボードの接続を確認してください
3. **エラーハンドリング**: 適切な例外処理を実装してください
4. **リソース管理**: テスト完了後は必ず接続を切断してください
5. **設定の検証**: テスト実行前に設定値の妥当性を確認してください
6. **ビジュアライゼーション依存関係**: matplotlib, seaborn, plotly等のライブラリが必要です

## トラブルシューティング

### よくある問題と解決方法

1. **接続エラー**
   - シリアルポートの権限を確認
   - ポート名とボーレートを確認
   - 他のアプリケーションがポートを使用していないか確認

2. **設定エラー**
   - 設定値の範囲を確認
   - YAMLファイルの構文を確認

3. **テスト実行エラー**
   - ターゲットボードの状態を確認
   - ログファイルで詳細なエラー情報を確認

4. **GUI関連の問題**
   - 設定の妥当性を確認
   - ログウィンドウでエラーメッセージを確認

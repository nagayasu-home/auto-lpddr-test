#!/usr/bin/env python3
"""
LPDDR Test Automation Constants
"""

from enum import Enum
from typing import Dict, List


class FrequencyMapping(Enum):
    """周波数マッピング定数"""
    FREQ_400 = 0
    FREQ_666 = 1
    FREQ_700 = 2
    FREQ_725 = 3
    FREQ_800 = 4
    
    # 周波数値からキーへのマッピング
    FREQUENCY_TO_KEY: Dict[int, int] = {
        400: 0,
        666: 1,
        700: 2,
        725: 3,
        800: 4
    }
    
    # サポートされている周波数リスト
    SUPPORTED_FREQUENCIES: List[int] = [400, 666, 700, 725, 800]


class TestPatterns(Enum):
    """テストパターン定数"""
    TEST_LPDDR_A = 1  # increment by byte
    TEST_LPDDR_BITWALK = 15  # bit walk test
    
    # デフォルトテストパターン
    DEFAULT_PATTERNS: List[int] = [1, 15]
    
    # パターン名マッピング
    PATTERN_NAMES: Dict[int, str] = {
        1: "test_lpddrA",
        15: "test_lpddr_bitwalk"
    }


class SerialSettings(Enum):
    """シリアル通信設定定数"""
    # サポートされているボーレート
    SUPPORTED_BAUDRATES: List[int] = [9600, 19200, 38400, 57600, 115200]
    
    # デフォルト設定
    DEFAULT_BAUDRATE: int = 115200
    DEFAULT_TIMEOUT: float = 30.0
    DEFAULT_PARITY: str = "N"
    DEFAULT_STOPBITS: int = 1
    DEFAULT_BYTESIZE: int = 8
    
    # 電源制御用設定
    POWER_CONTROL_BAUDRATE: int = 9600
    POWER_CONTROL_TIMEOUT: float = 5.0


class TestLimits(Enum):
    """テスト制限定数"""
    # タイムアウト設定
    CONNECTION_TIMEOUT: float = 30.0
    COMMAND_TIMEOUT: float = 120.0  # 2分（test_lpddrAの実行時間に合わせて）
    EYE_PATTERN_TIMEOUT: float = 30.0
    DIAGNOSTICS_TIMEOUT: float = 10.0
    
    # テスト範囲
    MAX_TEST_BYTES: int = 2147483648  # 全範囲テスト
    MAX_LOOP_COUNT: str = "00"
    
    # アイパターンテスト設定
    MAX_LANES: int = 4
    MAX_BITS: int = 8


class PowerControl(Enum):
    """電源制御定数"""
    # 電源制御コマンド
    POWER_OFF_CMD: bytes = b"POWER_OFF\n"
    POWER_ON_CMD: bytes = b"POWER_ON\n"
    
    # 待機時間
    POWER_OFF_DELAY: float = 2.0
    POWER_ON_DELAY: float = 3.0
    RECONNECT_DELAY: float = 1.0


class PromptPatterns(Enum):
    """プロンプトパターン定数"""
    FREQUENCY_SELECT = r"Please Hit number key"
    TRAINING_COMPLETE = r"Training Complete 7"
    TRAINING_2D_COMPLETE = r"2D Training Complete"
    SELECT_2D_TRAINING = r"select 2D training mode"
    SELECT_TEST_MODE = r"select test mode"
    INPUT_OUT_VALUE = r"input out_value"
    REPEAT_MEMORY_TESTS = r"Repeat memory tests"
    MODE_SELECT = r"ModeSelect"
    SET_DIAG_ADDR_LOW = r"Set DiagAddrLow"
    SET_DIAG_ADDR_HIGH = r"Set DiagAddrHigh"
    SET_LOOP_COUNT = r"Set the loop count"
    REPEAT_DIAGNOSTICS = r"Repeat diagnostics"
    SELECT_LANE = r"Selectlane"
    SELECT_BIT = r"Selectbit"


class TestCommands(Enum):
    """テストコマンド定数"""
    # テストモード選択
    MEMORY_ACCESS_TEST = "1"
    DIAGNOSTICS_TEST = "0"
    
    # 2Dトレーニング
    ENABLE_2D_TRAINING = "1"
    DISABLE_2D_TRAINING = "0"
    
    # アイパターンテスト
    TX_EYE_PATTERN = "1"
    RX_EYE_PATTERN = "2"
    SIMPLE_WRITE_READ = "0"
    
    # リピート選択
    END_TEST = "0"
    REPEAT_TEST = "1"


class DiagnosticSettings(Enum):
    """診断設定定数"""
    # デフォルト診断設定
    DEFAULT_ADDR_LOW: str = "0000"
    DEFAULT_ADDR_HIGH: str = "03ff"
    DEFAULT_LOOP_COUNT: str = "00"


class ErrorMessages(Enum):
    """エラーメッセージ定数"""
    CONNECTION_FAILED = "接続に失敗しました"
    CONNECTION_TEST_FAILED = "接続テストに失敗しました"
    INVALID_BAUDRATE = "無効なボーレートです"
    INVALID_TIMEOUT = "タイムアウト値は正の数である必要があります"
    INVALID_FREQUENCY = "サポートされていない周波数です"
    INVALID_PATTERN = "無効なテストパターンです"
    COMMAND_SEND_FAILED = "コマンドの送信に失敗しました"
    RESPONSE_READ_FAILED = "レスポンスの読み取りに失敗しました"
    PROMPT_TIMEOUT = "プロンプトの待機がタイムアウトしました"
    POWER_CYCLE_FAILED = "電源リセットに失敗しました"
    TEST_EXECUTION_FAILED = "テスト実行中にエラーが発生しました"


class SuccessMessages(Enum):
    """成功メッセージ定数"""
    CONNECTION_ESTABLISHED = "接続が確立されました"
    COMMAND_SENT = "コマンドを送信しました"
    RESPONSE_RECEIVED = "レスポンスを受信しました"
    TEST_COMPLETED = "テストが完了しました"
    POWER_CYCLE_SUCCESS = "電源リセットが完了しました"


class JudgmentMessages(Enum):
    """判定メッセージ定数"""
    FREQ_800_PATTERN_01_PASS = "メモリは動作しているが不安定な可能性があります"
    FREQ_800_PATTERN_15_PASS = "信号線は接続されているが、メモリアクセスが不安定です"
    FREQ_666_PATTERN_01_PASS = "800MHzでは動作しないが666MHzでは動作します"
    FREQ_666_PATTERN_15_PASS = "666MHzで信号線接続が確認されました"
    MEMORY_FUNC_DIAG_PASS = "メモリは動作しているが不安定な可能性があります"
    ALL_FAIL = "メモリが動作していません"
    MEMORY_FUNCTIONAL = "メモリは正常に動作しています"
    MEMORY_UNSTABLE = "メモリは動作している可能性がありますが不安定です"
    MEMORY_NOT_FUNCTIONAL = "メモリが動作していません"


class LogLevels(Enum):
    """ログレベル定数"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FileExtensions(Enum):
    """ファイル拡張子定数"""
    YAML = ".yaml"
    YML = ".yml"
    LOG = ".log"
    TXT = ".txt"
    CSV = ".csv"
    JSON = ".json"


class GUIElements(Enum):
    """GUI要素定数"""
    # ウィンドウサイズ
    WINDOW_WIDTH: int = 800
    WINDOW_HEIGHT: int = 600
    
    # ログ表示
    LOG_HEIGHT: int = 20
    LOG_WIDTH: int = 80
    
    # 結果表示
    RESULT_HEIGHT: int = 8
    RESULT_WIDTH: int = 80
    
    # プログレスバー
    PROGRESS_MAX: int = 100
    PROGRESS_UPDATE_INTERVAL: int = 100  # ms
    
    # キュー監視間隔
    QUEUE_CHECK_INTERVAL: int = 100  # ms

#!/usr/bin/env python3
"""
LPDDR Test Automation Software
AI-CAMKIT Main Board LPDDR4 Interface Test Automation
"""

import serial
import time
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

# カスタムモジュールのインポート
from constants import (
    FrequencyMapping, TestPatterns, SerialSettings, TestLimits,
    PowerControl, PromptPatterns, TestCommands, DiagnosticSettings,
    ErrorMessages, SuccessMessages, JudgmentMessages
)
from exceptions import (
    LPDDRAutomationError, ConnectionError, SerialConnectionError,
    PowerControlError, ConfigurationError, ValidationError,
    TestExecutionError, TimeoutError, CommandError, TestResultError
)
from validators import ConfigValidator
try:
    from visualization import LPDDRVisualizer
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GUIコールバック用のログ関数
def log_to_gui(message: str, level: str = "INFO", gui_callback=None):
    """GUIのログウィンドウにメッセージを出力"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"
    print(formatted_message)  # コンソールにも出力
    
    # GUIコールバックが利用可能な場合は使用
    if gui_callback:
        gui_callback(formatted_message, level)

def check_test_result(response: str) -> str:
    """レスポンスからテスト結果を検出"""
    response_upper = response.upper()
    logger.info(f"check_test_result - input: '{response.strip()}'")
    logger.info(f"check_test_result - upper: '{response_upper.strip()}'")
    
    # PASSパターン
    pass_patterns = ["MEMORY ACCESS TEST PASS", "TEST PASS", "PASS"]
    for pattern in pass_patterns:
        if pattern in response_upper:
            logger.info(f"check_test_result - PASS pattern found: '{pattern}'")
            return "PASS"
    
    # FAILパターン
    fail_patterns = ["MEMORY ACCESS TEST FAIL", "TEST FAIL", "FAIL"]
    for pattern in fail_patterns:
        if pattern in response_upper:
            logger.info(f"check_test_result - FAIL pattern found: '{pattern}'")
            return "FAIL"
    
    logger.info("check_test_result - no result pattern found")
    return None

class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"

class TestStep(Enum):
    FREQUENCY_SELECT = "frequency_select"
    TRAINING = "training"
    MEMORY_TEST = "memory_test"
    DIAGNOSTICS = "diagnostics"
    EYE_PATTERN = "eye_pattern"
    POWER_CYCLE = "power_cycle"
    COMPLETE = "complete"

class EyePatternType(Enum):
    TX = "tx"
    RX = "rx"
    SIMPLE_WRITE_READ = "simple_write_read"

@dataclass
class TestConfig:
    """テスト設定"""
    port: str = "COM3"  # Windows: COM3, Linux: /dev/ttyUSB0
    baudrate: int = 115200
    timeout: float = 30.0
    test_patterns: List[int] = None
    enable_2d_training: bool = False
    enable_eye_pattern: bool = True
    power_control_enabled: bool = False
    power_control_port: str = None  # 電源制御用の別ポート
    
    def __post_init__(self):
        if self.test_patterns is None:
            self.test_patterns = TestPatterns.DEFAULT_PATTERNS.value
        self._validate_config()
    
    def _validate_config(self):
        """設定のバリデーション"""
        try:
            ConfigValidator.validate_port(self.port)
            ConfigValidator.validate_baudrate(self.baudrate)
            ConfigValidator.validate_timeout(self.timeout)
            ConfigValidator.validate_patterns(self.test_patterns)
            ConfigValidator.validate_boolean(self.enable_2d_training, "enable_2d_training")
            ConfigValidator.validate_boolean(self.enable_eye_pattern, "enable_eye_pattern")
            ConfigValidator.validate_boolean(self.power_control_enabled, "power_control_enabled")
            
            if self.power_control_enabled and self.power_control_port:
                ConfigValidator.validate_port(self.power_control_port)
        except ValidationError as e:
            raise ConfigurationError(f"設定エラー: {e}", field=e.field, value=e.value)

@dataclass
class TestResultData:
    """テスト結果データ"""
    step: TestStep
    frequency: int
    pattern: int
    result: TestResult
    message: str
    timestamp: float

class LPDDRAutomation:
    """LPDDRテスト自動化クラス"""
    
    def __init__(self, config: TestConfig, gui_callback=None, gui_status_callback=None):
        self.config = config
        self.serial_conn: Optional[serial.Serial] = None
        self.power_conn: Optional[serial.Serial] = None  # 電源制御用
        self.test_results: List[TestResultData] = []
        self.current_step = TestStep.FREQUENCY_SELECT
        self.eye_pattern_results: Dict[str, str] = {}
        self.visualizer = LPDDRVisualizer()
        self.gui_callback = gui_callback  # GUIへのコールバック関数
        self.gui_status_callback = gui_status_callback  # GUIのテスト状況更新用コールバック
        
    def connect(self) -> bool:
        """シリアル接続を確立"""
        try:
            logger.info(f"Attempting to connect to {self.config.port} at {self.config.baudrate} baud")
            
            # 既存の接続がある場合は、それをテストして再利用
            if self.serial_conn and self.serial_conn.is_open:
                logger.info(f"Existing connection found to {self.config.port}, testing...")
                if self._test_connection():
                    logger.info("Existing connection is valid, reusing...")
                    return True
                else:
                    logger.info("Existing connection is invalid, reconnecting...")
                    self.disconnect()
            
            # 新しい接続を作成
            logger.info(f"Creating new serial connection to {self.config.port}")
            self.serial_conn = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout
            )
            logger.info(f"✓ Serial connection established to {self.config.port} at {self.config.baudrate} baud")
            
            # 接続テスト
            if not self._test_connection():
                raise SerialConnectionError(
                    ErrorMessages.CONNECTION_TEST_FAILED.value,
                    port=self.config.port,
                    baudrate=self.config.baudrate
                )
            
            # 電源制御ポートの接続
            if self.config.power_control_enabled and self.config.power_control_port:
                self.power_conn = serial.Serial(
                    port=self.config.power_control_port,
                    baudrate=SerialSettings.POWER_CONTROL_BAUDRATE.value,
                    timeout=SerialSettings.POWER_CONTROL_TIMEOUT.value
                )
                logger.info(f"Connected to power control port {self.config.power_control_port}")
            
            return True
        except serial.SerialException as e:
            logger.error(f"Serial connection failed: {e}")
            raise SerialConnectionError(
                f"シリアル接続に失敗しました: {e}",
                port=self.config.port,
                baudrate=self.config.baudrate
            )
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            raise ConnectionError(f"予期しない接続エラー: {e}")
    
    def _test_connection(self) -> bool:
        """接続テストを実行（ハンドシェイク方式）"""
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                logger.error("Serial connection is not open")
                return False
            
            logger.info("Starting connection test with target device...")
            logger.info(f"Serial port: {self.serial_conn.port}")
            logger.info(f"Baudrate: {self.serial_conn.baudrate}")
            logger.info(f"Timeout: {self.serial_conn.timeout}")
            
            # バッファをクリア
            logger.info("Clearing input/output buffers...")
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            
            # Enterキーを送信してハンドシェイク
            logger.info("Sending handshake command (Enter key)...")
            self.serial_conn.write(b'\r\n')
            logger.info("Enter key sent, waiting for response...")
            time.sleep(1.0)  # レスポンス待機
            
            # レスポンスを読み取り（1分タイムアウト）
            response = ""
            start_time = time.time()
            timeout_seconds = 60.0  # 1分タイムアウト
            
            logger.info("Waiting for target device response...")
            while time.time() - start_time < timeout_seconds:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    decoded_data = data.decode('utf-8', errors='ignore')
                    response += decoded_data
                    logger.info(f"Received data: '{decoded_data.strip()}'")
                    logger.info(f"Total response so far: '{response.strip()}'")
                    
                    # 周波数選択プロンプトを確認
                    if "Please Hit number key:" in response:
                        logger.info("✓ Connection test PASSED - Frequency selection prompt received from target device")
                        logger.info("Target device is ready for LPDDR testing")
                        return True
                else:
                    # データが来ていない場合のログ（5秒ごと）
                    elapsed = time.time() - start_time
                    if int(elapsed) % 5 == 0 and elapsed > 0:
                        logger.info(f"No data received yet, elapsed time: {elapsed:.1f}s")
                time.sleep(0.1)
            
            # タイムアウト時のログ出力
            logger.error("✗ Connection test FAILED - Timeout after 60 seconds")
            logger.error(f"Expected 'Please Hit number key:' prompt, but received: {response[:200]}")
            logger.error("Please check:")
            logger.error("  1. Target device is powered on")
            logger.error("  2. Serial cable is properly connected")
            logger.error("  3. Correct COM port is selected")
            logger.error("  4. Target device firmware is running")
            return False
            
        except Exception as e:
            logger.error(f"✗ Connection test FAILED - Exception occurred: {e}")
            return False
    
    def disconnect(self):
        """シリアル接続を切断"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected")
        
        if self.power_conn and self.power_conn.is_open:
            self.power_conn.close()
            logger.info("Power control disconnected")
    
    def send_command(self, command: str, add_newline: bool = False) -> bool:
        """コマンドを送信"""
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                raise CommandError(
                    "シリアル接続が確立されていません",
                    command=command
                )
            
            # 数値入力の場合は改行文字を追加しない
            if add_newline:
                self.serial_conn.write(f"{command}\n".encode())
                # 送信コマンドをテスト結果Windowに出力
                if hasattr(self, 'gui_callback') and self.gui_callback:
                    self.gui_callback(f"Please Hit number key:{command}", "SERIAL")
            else:
                self.serial_conn.write(command.encode())
                # 送信コマンドをテスト結果Windowに出力
                if hasattr(self, 'gui_callback') and self.gui_callback:
                    self.gui_callback(f"Please Hit number key:{command}", "SERIAL")
            
            return True
        except serial.SerialException as e:
            logger.error(f"Serial error while sending command: {e}")
            raise CommandError(
                f"コマンド送信でシリアルエラー: {e}",
                command=command
            )
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            raise CommandError(
                f"コマンド送信に失敗: {e}",
                command=command
            )
    
    def read_response(self, timeout: float = None) -> str:
        """レスポンスを読み取り"""
        if not self.serial_conn or not self.serial_conn.is_open:
            raise CommandError("シリアル接続が確立されていません")
        
        try:
            original_timeout = self.serial_conn.timeout
            if timeout:
                self.serial_conn.timeout = timeout
            
            response = self.serial_conn.read_until(b'\n').decode('utf-8', errors='ignore').strip()
            
            # シリアルログをテスト結果Windowに出力
            if hasattr(self, 'gui_callback') and self.gui_callback and response:
                self.gui_callback(response, "SERIAL")
            
            return response
        except serial.SerialException as e:
            logger.error(f"Serial error while reading response: {e}")
            raise CommandError(
                f"レスポンス読み取りでシリアルエラー: {e}",
                response=""
            )
        except Exception as e:
            logger.error(f"Failed to read response: {e}")
            raise CommandError(
                f"レスポンス読み取りに失敗: {e}",
                response=""
            )
        finally:
            # タイムアウトを元に戻す
            if timeout:
                self.serial_conn.timeout = original_timeout
    
    def wait_for_prompt(self, prompt_pattern: str, timeout: float = 30.0) -> bool:
        """プロンプトを待機"""
        logger.info(f"Waiting for prompt: '{prompt_pattern}' (timeout: {timeout}s)")
        start_time = time.time()
        response_buffer = ""
        
        while time.time() - start_time < timeout:
            try:
                response = self.read_response(1.0)
                if response and response.strip():  # 空でないレスポンスのみ処理
                    response_buffer += response + "\n"
                    logger.info(f"Received response: '{response}'")
                    
                if re.search(prompt_pattern, response, re.IGNORECASE):
                    logger.info(f"Prompt found: '{prompt_pattern}'")
                    return True
                elif response:  # 空のレスポンスはログに記録しない
                    logger.debug(f"Received empty response")
            except CommandError:
                # レスポンス読み取りエラーは無視して続行
                continue
        
        # タイムアウト
        logger.error(f"Timeout waiting for prompt: '{prompt_pattern}'")
        logger.error(f"Received responses: {response_buffer}")
        raise TimeoutError(
            f"{ErrorMessages.PROMPT_TIMEOUT.value}: {prompt_pattern}",
            timeout=timeout,
            operation="wait_for_prompt"
        )
    
    def parse_test_result(self, response: str) -> TestResult:
        """テスト結果を解析"""
        if not response:
            raise TestResultError(
                "空のレスポンスからテスト結果を解析できません",
                raw_response=response
            )
        
        response_upper = response.upper()
        if "PASS" in response_upper:
            return TestResult.PASS
        elif "FAIL" in response_upper:
            return TestResult.FAIL
        else:
            return TestResult.UNKNOWN
    
    def power_cycle(self) -> bool:
        """電源リセットを実行"""
        if not self.config.power_control_enabled:
            logger.warning("Power control not enabled - manual power cycle required")
            return False
        
        try:
            if self.power_conn and self.power_conn.is_open:
                # 電源OFF
                self.power_conn.write(PowerControl.POWER_OFF_CMD.value)
                logger.info("Power OFF command sent")
                time.sleep(PowerControl.POWER_OFF_DELAY.value)
                
                # 電源ON
                self.power_conn.write(PowerControl.POWER_ON_CMD.value)
                logger.info("Power ON command sent")
                time.sleep(PowerControl.POWER_ON_DELAY.value)
                
                # シリアル接続を再確立
                self.disconnect()
                time.sleep(PowerControl.RECONNECT_DELAY.value)
                return self.connect()
            else:
                raise PowerControlError("電源制御ポートが利用できません")
        except serial.SerialException as e:
            logger.error(f"Power control serial error: {e}")
            raise PowerControlError(f"電源制御でシリアルエラー: {e}")
        except Exception as e:
            logger.error(f"Power cycle failed: {e}")
            raise PowerControlError(f"電源リセットに失敗: {e}")
    
    def run_frequency_test(self, frequency: int) -> Dict[str, TestResultData]:
        """周波数テストを実行"""
        logger.info(f"Starting frequency test at {frequency}MHz")
        results = {}
        
        # 周波数選択プロンプトを待機（666MHzテストの場合）
        if frequency == 666:
            logger.info("Waiting for frequency selection prompt for 666MHz test...")
            try:
                self.wait_for_prompt("set frequency for LPDDR")
                logger.info("Frequency selection prompt received")
            except TimeoutError:
                logger.warning("Frequency selection prompt not found, continuing...")
        
        # 周波数選択
        logger.info("Sending frequency selection command")
        freq_key = FrequencyMapping.FREQUENCY_TO_KEY.value.get(frequency, FrequencyMapping.FREQ_666.value)
        freq_str = str(freq_key)
        for i, char in enumerate(freq_str):
            self.serial_conn.write(char.encode('utf-8'))
            time.sleep(0.1)
        
        # 送信完了後にコマンドをログ出力
        if hasattr(self, 'gui_callback') and self.gui_callback:
            self.gui_callback(f"Please Hit number key:{freq_str}", "SERIAL")
        
        # 周波数選択後のレスポンス待機
        self.wait_for_prompt("PLL LOCK")
        
        # 周波数選択後、すぐに次のプロンプト（2Dトレーニング選択）が表示される
        # トレーニングはバックグラウンドで実行されるため、完了待機は不要
        
        # 2Dトレーニング設定
        try:
            if self.wait_for_prompt(PromptPatterns.SELECT_2D_TRAINING.value):
                if self.config.enable_2d_training:
                    training_cmd = TestCommands.ENABLE_2D_TRAINING.value
                    for i, char in enumerate(training_cmd):
                        self.serial_conn.write(char.encode('utf-8'))
                        time.sleep(0.1)
                    logger.info("2D training enabled")
                    # 送信完了後にコマンドをログ出力
                    if hasattr(self, 'gui_callback') and self.gui_callback:
                        self.gui_callback(f"Please Hit number key:{training_cmd}", "SERIAL")
                    # 2Dトレーニング完了待機
                    self.wait_for_prompt(PromptPatterns.TRAINING_2D_COMPLETE.value)
                else:
                    training_cmd = TestCommands.DISABLE_2D_TRAINING.value
                    for i, char in enumerate(training_cmd):
                        self.serial_conn.write(char.encode('utf-8'))
                        time.sleep(0.1)
                    logger.info("2D training disabled")
                    # 送信完了後にコマンドをログ出力
                    if hasattr(self, 'gui_callback') and self.gui_callback:
                        self.gui_callback(f"Please Hit number key:{training_cmd}", "SERIAL")
                
                # 2Dトレーニング選択後のレスポンス待機
                self.wait_for_prompt("input out_value : dec:0")
        except TimeoutError:
            logger.warning("2D training prompt not found or timeout")
        
        # メモリテスト選択
        self.wait_for_prompt(PromptPatterns.SELECT_TEST_MODE.value)
        memory_cmd = TestCommands.MEMORY_ACCESS_TEST.value
        for i, char in enumerate(memory_cmd):
            self.serial_conn.write(char.encode('utf-8'))
            time.sleep(0.1)
        
        # 送信完了後にコマンドをログ出力
        if hasattr(self, 'gui_callback') and self.gui_callback:
            self.gui_callback(f"Please Hit number key:{memory_cmd}", "SERIAL")
        
        # メモリアクセステスト選択後のレスポンス待機
        self.wait_for_prompt("input out_value : dec:1")
        
        # テストバイト数設定（メモリアクセステスト選択後のプロンプト待機）
        # テストバイト数選択のプロンプトを待機（select test_numの後）
        self.wait_for_prompt("select test_num")
        self.wait_for_prompt("Please Hit number key:")
        # プロンプト表示後の待機時間を追加（ターゲットの準備を待つ）
        time.sleep(1.0)
        
        # シリアルバッファをクリア
        self.serial_conn.reset_input_buffer()
        self.serial_conn.reset_output_buffer()
        
        # 1文字ずつ送信
        test_bytes_str = str(TestLimits.MAX_TEST_BYTES.value)
        for i, char in enumerate(test_bytes_str):
            self.serial_conn.write(char.encode('utf-8'))
            time.sleep(0.1)  # 各文字の間に短い待機
        
        # 送信完了後にコマンドをログ出力
        if hasattr(self, 'gui_callback') and self.gui_callback:
            self.gui_callback(f"Please Hit number key:{test_bytes_str}", "SERIAL")
        
        # テストバイト数送信後のレスポンス待機
        # 複数行のレスポンスを読み取り（15秒タイムアウト）
        response_buffer = ""
        start_time = time.time()
        timeout_seconds = 15.0
        
        while time.time() - start_time < timeout_seconds:
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.read(self.serial_conn.in_waiting)
                decoded_data = data.decode('utf-8', errors='ignore')
                response_buffer += decoded_data
                
                # シリアルログをテスト結果Windowに出力
                if hasattr(self, 'gui_callback') and self.gui_callback and decoded_data:
                    # 改行で分割して各行を出力
                    lines = decoded_data.split('\n')
                    for line in lines:
                        if line.strip():
                            self.gui_callback(line.strip(), "SERIAL")
                
                # 期待されるレスポンスを確認
                if "input out_value : dec:2147483648" in response_buffer:
                    break
                elif "Start Memory Access test" in response_buffer:
                    break
            time.sleep(0.1)
        
        # タイムアウトチェック
        if time.time() - start_time >= timeout_seconds:
            logger.warning("Timeout waiting for test bytes input confirmation")
        
        # テストバイト数送信後のプロンプト待機
        
        # 各テストパターンを実行
        for pattern in self.config.test_patterns:
            try:
                # テストパターン開始ログ
                log_to_gui(f"周波数 {frequency}MHz テストパターン {pattern:02d} 開始", "INFO", self.gui_callback)
                
                # GUIのテスト状況表示を更新
                if self.gui_status_callback:
                    self.gui_status_callback(f"周波数 {frequency}MHz テストパターン {pattern:02d} 開始")
                
                # テストパターン選択（最初のパターンは既にプロンプト待機済み）
                # 2番目以降のパターンは、リピート選択後に既にプロンプト待機済み
                if pattern == self.config.test_patterns[0]:
                    logger.info(f"First pattern {pattern:02d}, prompt already waited")
                else:
                    logger.info(f"Subsequent pattern {pattern:02d}, prompt already waited after Repeat selection")
                
                logger.info(f"About to send test pattern {pattern:02d}")
                
                # テストパターンを1文字ずつ送信（テストバイト数と同じ方法）
                pattern_str = f"{pattern:02d}"
                logger.info(f"Sending test pattern: {pattern_str} (pattern number: {pattern})")
                
                # 1文字ずつ送信（デバッグログ付き）
                for i, char in enumerate(pattern_str):
                    self.serial_conn.write(char.encode('utf-8'))
                    logger.info(f"Sending character {i+1}/{len(pattern_str)}: '{char}'")
                    time.sleep(0.1)  # 各文字の間に短い待機
                
                # 送信完了後にコマンドをログ出力
                if hasattr(self, 'gui_callback') and self.gui_callback:
                    self.gui_callback(f"Please Hit number key:{pattern_str}", "SERIAL")
                
                logger.info(f"Test pattern {pattern:02d} sent successfully, starting response waiting")
                
                # テストパターン送信後のレスポンス待機
                response_buffer = ""
                start_time = time.time()
                timeout_seconds = 10.0
                
                logger.info(f"Waiting for test pattern {pattern:02d} input confirmation")
                while time.time() - start_time < timeout_seconds:
                    if self.serial_conn.in_waiting > 0:
                        data = self.serial_conn.read(self.serial_conn.in_waiting)
                        decoded_data = data.decode('utf-8', errors='ignore')
                        response_buffer += decoded_data
                        
                        # シリアルログをテスト結果Windowに出力
                        if hasattr(self, 'gui_callback') and self.gui_callback and decoded_data:
                            # 改行で分割して各行を出力
                            lines = decoded_data.split('\n')
                            for line in lines:
                                if line.strip():
                                    self.gui_callback(line.strip(), "SERIAL")
                        
                        # 期待されるレスポンスを確認
                        expected_response = f"input out_value : dec:{pattern}"
                        logger.info(f"Looking for: '{expected_response}' in response buffer")
                        logger.info(f"Current response buffer: '{response_buffer}'")
                        if expected_response in response_buffer:
                            logger.info(f"Found expected response: '{expected_response}'")
                            break
                    time.sleep(0.1)
                
                # タイムアウトチェック
                if time.time() - start_time >= timeout_seconds:
                    logger.warning(f"Timeout waiting for test pattern {pattern:02d} input confirmation")
                    logger.info(f"Final response buffer: '{response_buffer}'")
                
                # テスト結果待機（複数のレスポンスを読み取り）
                test_result = None
                test_result_logged = False  # テスト結果ログ出力済みフラグ
                # response_bufferは既存のバッファを保持
                start_time = time.time()
                timeout_seconds = TestLimits.COMMAND_TIMEOUT.value
                
                logger.info(f"Starting test result reading loop for pattern {pattern:02d}")
                logger.info(f"Timeout: {timeout_seconds} seconds")
                
                # 既存のレスポンスバッファをチェック
                logger.info(f"Checking existing response buffer for pattern {pattern:02d}")
                logger.info(f"Existing buffer content: '{response_buffer.strip()}'")
                detected_result = check_test_result(response_buffer)
                if detected_result and not test_result_logged:
                    test_result = detected_result
                    test_result_logged = True
                    logger.info(f"Test result detected from existing buffer: {test_result}")
                    # テスト完了メッセージを表示
                    log_to_gui(f"周波数 {frequency}MHz テストパターン {pattern:02d} 完了: {test_result}", "SUCCESS" if test_result == "PASS" else "ERROR", self.gui_callback)
                    # 既存バッファから検知した場合、Repeat選択ロジックを実行するためループをスキップ
                    logger.info("Skipping response reading loop, proceeding to repeat selection logic")
                else:
                    # 既存バッファにテスト結果がない場合のみ、レスポンス待機ループを実行
                    while time.time() - start_time < timeout_seconds:
                        response = self.read_response(1.0)  # 1秒ずつ読み取り
                        if response:
                            response_buffer += response + "\n"
                            logger.info(f"Test result reading - received: '{response.strip()}'")
                            logger.info(f"Test result reading - buffer length: {len(response_buffer)}")
                            logger.info(f"Test result reading - buffer content: '{response_buffer.strip()}'")
                        else:
                            logger.info(f"No response received, elapsed time: {time.time() - start_time:.1f}s")
                        
                            # テスト結果を検出（重複ログを防ぐ）
                            detected_result = check_test_result(response_buffer)
                            if detected_result and not test_result_logged:
                                test_result = detected_result
                                logger.info(f"Test result detected: {test_result}")
                                log_to_gui(f"周波数 {frequency}MHz テストパターン {pattern:02d} 完了: {test_result}", "SUCCESS" if test_result == "PASS" else "ERROR", self.gui_callback)
                                test_result_logged = True  # ログ出力済みフラグを設定
                            
                            # テスト完了の合図を検出（テスト結果検知後も「Repeat memory tests?」を待機）
                            if "Repeat memory tests?" in response_buffer:
                                logger.info("Repeat memory tests prompt detected - test completed")
                                # テスト結果が検知されていない場合は、レスポンスバッファから再検索
                                if not test_result_logged:
                                    logger.warning("Test result not detected yet, searching in response buffer")
                                    detected_result = check_test_result(response_buffer)
                                    if detected_result:
                                        test_result = detected_result
                                        logger.info(f"Test result found in buffer: {test_result}")
                                        log_to_gui(f"周波数 {frequency}MHz テストパターン {pattern:02d} 完了: {test_result}", "SUCCESS" if test_result == "PASS" else "ERROR", self.gui_callback)
                                        test_result_logged = True
                                break
                            elif "Finish Memory Access test" in response_buffer:
                                logger.info("Finish Memory Access test signal detected")
                                break
                
                # タイムアウトチェック
                if time.time() - start_time >= timeout_seconds:
                    logger.warning(f"Timeout waiting for test result for pattern {pattern:02d}")
                    logger.info(f"Final response buffer: '{response_buffer.strip()}'")
                    # タイムアウト時でもレスポンスバッファからテスト結果を検索
                    if not test_result_logged:
                        detected_result = check_test_result(response_buffer)
                        if detected_result:
                            test_result = detected_result
                            logger.info(f"Test result found in buffer after timeout: {test_result}")
                            log_to_gui(f"周波数 {frequency}MHz テストパターン {pattern:02d} 完了: {test_result}", "SUCCESS" if test_result == "PASS" else "ERROR", self.gui_callback)
                            test_result_logged = True
                
                result = self.parse_test_result(response_buffer)
                
                results[f"pattern_{pattern}"] = result
                self.test_results.append(TestResultData(
                    step=TestStep.MEMORY_TEST,
                    frequency=frequency,
                    pattern=pattern,
                    result=result,
                    message=response,
                    timestamp=time.time()
                ))
                
                # テスト結果検知後、「Repeat memory tests?」プロンプトは既に上記のループで待機済み
                logger.info("Repeat memory tests prompt already received in test result loop")
                logger.info(f"Starting repeat selection logic for pattern {pattern:02d}")
                
                # リピート選択（同じ周波数内に他のパターンがあるかどうかで判断）
                # 同じ周波数内に他のパターンがあるかチェック
                remaining_patterns = [p for p in self.config.test_patterns if p > pattern]
                logger.info(f"Current pattern: {pattern:02d}, All patterns: {self.config.test_patterns}, Remaining patterns: {remaining_patterns}")
                
                if remaining_patterns:
                    # 他のパターンがある場合は「1 : Repeat」を選択
                    repeat_cmd = "1"
                    logger.info(f"More patterns remaining, selecting Repeat (1) for pattern {pattern:02d}")
                else:
                    # 最後のパターンの場合は「0 : Finish」を選択
                    repeat_cmd = "0"
                    logger.info(f"Last pattern, selecting Finish (0) for pattern {pattern:02d}")
                
                # リピート/フィニッシュコマンドを送信
                logger.info(f"Sending repeat/finish command: '{repeat_cmd}'")
                for i, char in enumerate(repeat_cmd):
                    self.serial_conn.write(char.encode('utf-8'))
                    logger.info(f"Sending character {i+1}/{len(repeat_cmd)}: '{char}'")
                    time.sleep(0.1)
                
                # 送信完了後にコマンドをログ出力
                if hasattr(self, 'gui_callback') and self.gui_callback:
                    self.gui_callback(f"Please Hit number key:{repeat_cmd}", "SERIAL")
                logger.info(f"Repeat/finish command '{repeat_cmd}' sent successfully")
                
                # リピート/フィニッシュ選択後の処理
                if remaining_patterns:
                    # 他のパターンがある場合は次のパターン選択のプロンプトを待機
                    logger.info("Waiting for next pattern selection prompt after Repeat selection")
                    try:
                        # リピート選択後、即座に次のテスト選択メニューが表示される
                        # 短い待機時間を設けて、レスポンスを確認
                        time.sleep(0.5)  # 短い待機
                        
                        # 現在のレスポンスを確認
                        current_response = self.read_response(2.0)
                        logger.info(f"Response after repeat selection: '{current_response}'")
                        
                        # "Please Hit number key:"プロンプトが既に表示されているかチェック
                        if "Please Hit number key:" in current_response:
                            logger.info("Next pattern selection prompt already available")
                        else:
                            # プロンプトを待機
                            logger.info("Waiting for 'Please Hit number key:' prompt...")
                            self.wait_for_prompt("Please Hit number key:")
                            logger.info("Next pattern selection prompt received")
                            
                    except TimeoutError as e:
                        logger.warning(f"Next pattern selection prompt not found after Repeat selection: {e}")
                else:
                    # 最後のパターンの場合、Finish選択後の処理
                    logger.info("Waiting for Finish Memory Access test prompt after Finish selection")
                    try:
                        # Finish選択後、メモリアクセステスト終了メッセージを待機
                        time.sleep(0.5)  # 短い待機
                        
                        # 現在のレスポンスを確認
                        current_response = self.read_response(2.0)
                        logger.info(f"Response after finish selection: '{current_response}'")
                        
                        # "#### Please Turn-OFF SW1-1, and Hit Enter Key:"プロンプトを待機
                        if "#### Please Turn-OFF SW1-1, and Hit Enter Key:" in current_response:
                            logger.info("Turn-OFF SW1-1 prompt detected, sending Enter key")
                            # Enterキーを送信
                            self.serial_conn.write(b'\r\n')
                            logger.info("Enter key sent for frequency change")
                        else:
                            # プロンプトを待機
                            logger.info("Waiting for '#### Please Turn-OFF SW1-1, and Hit Enter Key:' prompt...")
                            self.wait_for_prompt("#### Please Turn-OFF SW1-1, and Hit Enter Key:")
                            logger.info("Turn-OFF SW1-1 prompt received, sending Enter key")
                            # Enterキーを送信
                            self.serial_conn.write(b'\r\n')
                            logger.info("Enter key sent for frequency change")
                            
                    except TimeoutError as e:
                        logger.warning(f"Turn-OFF SW1-1 prompt not found after Finish selection: {e}")
                        # タイムアウトした場合、現在のレスポンスを確認
                        try:
                            current_response = self.read_response(1.0)
                            logger.info(f"Current response after timeout: '{current_response}'")
                        except:
                            logger.info("No response available after timeout")
                    
            except (TimeoutError, CommandError, TestResultError) as e:
                logger.error(f"Pattern {pattern} test failed: {e}")
                results[f"pattern_{pattern}"] = TestResult.UNKNOWN
                continue
        
        # 周波数テスト完了
        logger.info(f"Frequency {frequency}MHz test completed")
        
        return results
    
    def run_diagnostics_test(self) -> TestResultData:
        """診断テストを実行"""
        logger.info("Starting diagnostics test")
        
        # 診断テスト選択
        self.wait_for_prompt(PromptPatterns.SELECT_TEST_MODE.value)
        self.send_command(TestCommands.DIAGNOSTICS_TEST.value)
        
        # Simple Write Read選択
        self.wait_for_prompt(PromptPatterns.MODE_SELECT.value)
        self.send_command(TestCommands.SIMPLE_WRITE_READ.value)
        
        # アドレス設定
        self.wait_for_prompt(PromptPatterns.SET_DIAG_ADDR_LOW.value)
        self.send_command(DiagnosticSettings.DEFAULT_ADDR_LOW.value)
        
        self.wait_for_prompt(PromptPatterns.SET_DIAG_ADDR_HIGH.value)
        self.send_command(DiagnosticSettings.DEFAULT_ADDR_HIGH.value)
        
        self.wait_for_prompt(PromptPatterns.SET_LOOP_COUNT.value)
        self.send_command(DiagnosticSettings.DEFAULT_LOOP_COUNT.value)
        
        # テスト結果待機
        response = self.read_response(TestLimits.DIAGNOSTICS_TIMEOUT.value)
        result = self.parse_test_result(response)
        
        test_result = TestResultData(
            step=TestStep.DIAGNOSTICS,
            frequency=0,
            pattern=0,
            result=result,
            message=response,
            timestamp=time.time()
        )
        
        self.test_results.append(test_result)
        
        # リピート選択
        try:
            self.wait_for_prompt(PromptPatterns.REPEAT_DIAGNOSTICS.value)
            self.send_command(TestCommands.END_TEST.value)
        except TimeoutError:
            logger.warning("Repeat diagnostics prompt not found")
        
        return test_result
    
    def run_eye_pattern_test(self, pattern_type: EyePatternType, lane: int = 0, bit: int = 0) -> TestResultData:
        """アイパターンテストを実行"""
        logger.info(f"Starting {pattern_type.value} eye pattern test (Lane: {lane}, Bit: {bit})")
        
        # 診断テスト選択
        self.wait_for_prompt(PromptPatterns.SELECT_TEST_MODE.value)
        self.send_command(TestCommands.DIAGNOSTICS_TEST.value)
        
        # アイパターンテスト選択
        self.wait_for_prompt(PromptPatterns.MODE_SELECT.value)
        if pattern_type == EyePatternType.TX:
            self.send_command(TestCommands.TX_EYE_PATTERN.value)
        elif pattern_type == EyePatternType.RX:
            self.send_command(TestCommands.RX_EYE_PATTERN.value)
        else:
            self.send_command(TestCommands.SIMPLE_WRITE_READ.value)
            return self.run_diagnostics_test()
        
        # レーン選択
        self.wait_for_prompt(PromptPatterns.SELECT_LANE.value)
        self.send_command(f"{lane:02d}")
        
        # ビット選択
        self.wait_for_prompt(PromptPatterns.SELECT_BIT.value)
        self.send_command(f"{bit:02d}")
        
        # テスト実行と結果取得
        response = self.read_response(TestLimits.EYE_PATTERN_TIMEOUT.value)
        result = self.parse_test_result(response)
        
        # アイパターン結果を保存
        key = f"{pattern_type.value}_lane_{lane}_bit_{bit}"
        self.eye_pattern_results[key] = response
        
        test_result = TestResultData(
            step=TestStep.EYE_PATTERN,
            frequency=0,
            pattern=0,
            result=result,
            message=response,
            timestamp=time.time()
        )
        
        self.test_results.append(test_result)
        logger.info(f"Eye pattern test result: {result.value}")
        
        return test_result
    
    def run_comprehensive_eye_pattern_test(self) -> Dict[str, TestResultData]:
        """包括的なアイパターンテストを実行"""
        logger.info("Starting comprehensive eye pattern test")
        results = {}
        
        if not self.config.enable_eye_pattern:
            logger.info("Eye pattern test disabled in configuration")
            return results
        
        # TX/RXアイパターンテストを実行
        for pattern_type in [EyePatternType.TX, EyePatternType.RX]:
            for lane in range(4):  # 通常4レーン
                for bit in range(8):  # 8ビット
                    try:
                        result = self.run_eye_pattern_test(pattern_type, lane, bit)
                        key = f"{pattern_type.value}_lane_{lane}_bit_{bit}"
                        results[key] = result
                        
                        # リピート選択
                        try:
                            self.wait_for_prompt(PromptPatterns.REPEAT_DIAGNOSTICS.value)
                            self.send_command(TestCommands.END_TEST.value)
                        except TimeoutError:
                            logger.warning("Repeat diagnostics prompt not found")
                            
                    except Exception as e:
                        logger.error(f"Eye pattern test failed for {pattern_type.value} lane {lane} bit {bit}: {e}")
                        continue
        
        return results
    
    def determine_next_step(self) -> TestStep:
        """次のステップを決定"""
        if not self.test_results:
            return TestStep.FREQUENCY_SELECT
        
        # 最新の結果を取得
        latest_results = [r for r in self.test_results if r.step == TestStep.MEMORY_TEST]
        
        if not latest_results:
            return TestStep.DIAGNOSTICS
        
        # 判定ロジック（PDFの判定基準に基づく）
        for result in latest_results:
            if result.frequency == 800 and result.pattern == 1 and result.result == TestResult.PASS:
                logger.info(f"800MHz pattern 01 PASS - {JudgmentMessages.FREQ_800_PATTERN_01_PASS.value}")
                return TestStep.EYE_PATTERN  # アイパターンテストで原因分析
            elif result.frequency == 800 and result.pattern == 15 and result.result == TestResult.PASS:
                logger.info(f"800MHz pattern 15 PASS - {JudgmentMessages.FREQ_800_PATTERN_15_PASS.value}")
                return TestStep.EYE_PATTERN  # アイパターンテストで原因分析
            elif result.frequency == 666 and result.pattern == 1 and result.result == TestResult.PASS:
                logger.info(f"666MHz pattern 01 PASS - {JudgmentMessages.FREQ_666_PATTERN_01_PASS.value}")
                return TestStep.EYE_PATTERN  # アイパターンテストで原因分析
            elif result.frequency == 666 and result.pattern == 15 and result.result == TestResult.PASS:
                logger.info(f"666MHz pattern 15 PASS - {JudgmentMessages.FREQ_666_PATTERN_15_PASS.value}")
                return TestStep.EYE_PATTERN  # アイパターンテストで原因分析
        
        # 全て失敗した場合
        logger.warning(f"All memory tests failed - {JudgmentMessages.ALL_FAIL.value}")
        return TestStep.DIAGNOSTICS
    
    def run_full_test_sequence(self) -> bool:
        """完全なテストシーケンスを実行"""
        if not self.connect():
            return False
        
        try:
            # テスト順序: 800MHz → 666MHz
            frequencies = [800, 666]
            
            for i, frequency in enumerate(frequencies):
                logger.info(f"Testing frequency: {frequency}MHz")
                results = self.run_frequency_test(frequency)
                
                # 結果をログ出力
                for pattern, result in results.items():
                    logger.info(f"{frequency}MHz {pattern}: {result.value}")
                
                # 800MHzテスト完了後、666MHzテストの準備
                if frequency == 800 and i < len(frequencies) - 1:
                    logger.info("800MHz test completed, preparing for 666MHz test...")
                    # 周波数選択プロンプトは666MHzテスト開始時に処理される
            
            # 診断テスト実行
            diag_result = self.run_diagnostics_test()
            logger.info(f"Diagnostics test: {diag_result.result.value}")
            
            # 次のステップを決定
            next_step = self.determine_next_step()
            
            if next_step == TestStep.EYE_PATTERN:
                logger.info("Running eye pattern tests for detailed analysis")
                eye_results = self.run_comprehensive_eye_pattern_test()
                logger.info(f"Eye pattern tests completed: {len(eye_results)} tests")
            
            elif next_step == TestStep.POWER_CYCLE:
                logger.info("Power cycle required - restarting test sequence")
                if self.power_cycle():
                    # 電源リセット後、テストを再実行
                    return self.run_full_test_sequence()
                else:
                    logger.error("Power cycle failed")
            
            # 最終判定
            self.generate_final_report()
            
            return True
            
        except Exception as e:
            logger.error(f"Test sequence failed: {e}")
            return False
        finally:
            self.disconnect()
    
    def generate_final_report(self):
        """最終レポートを生成"""
        logger.info("=== LPDDR Test Report ===")
        
        for result in self.test_results:
            logger.info(f"Step: {result.step.value}, "
                       f"Freq: {result.frequency}MHz, "
                       f"Pattern: {result.pattern}, "
                       f"Result: {result.result.value}")
        
        # 総合判定
        memory_tests = [r for r in self.test_results if r.step == TestStep.MEMORY_TEST]
        diag_tests = [r for r in self.test_results if r.step == TestStep.DIAGNOSTICS]
        eye_tests = [r for r in self.test_results if r.step == TestStep.EYE_PATTERN]
        
        logger.info("=== アイパターンテスト結果 ===")
        for key, result in self.eye_pattern_results.items():
            logger.info(f"{key}: {result[:100]}...")  # 最初の100文字のみ表示
        
        if any(r.result == TestResult.PASS for r in memory_tests):
            logger.info(f"OVERALL RESULT: {JudgmentMessages.MEMORY_FUNCTIONAL.value}")
            if eye_tests:
                logger.info("Eye pattern analysis completed for detailed signal quality assessment")
        elif any(r.result == TestResult.PASS for r in diag_tests):
            logger.info(f"OVERALL RESULT: {JudgmentMessages.MEMORY_UNSTABLE.value}")
            if eye_tests:
                logger.info("Eye pattern analysis completed - check signal integrity")
        else:
            logger.info(f"OVERALL RESULT: {JudgmentMessages.MEMORY_NOT_FUNCTIONAL.value}")
            if eye_tests:
                logger.info("Eye pattern analysis completed - signal quality issues detected")
        
        # ビジュアライゼーションを生成
        try:
            logger.info("Generating visualizations...")
            exported_files = self.visualizer.export_all_visualizations(
                self.test_results, 
                self.eye_pattern_results
            )
            logger.info(f"Visualizations exported: {list(exported_files.keys())}")
        except Exception as e:
            logger.warning(f"Failed to generate visualizations: {e}")

def main():
    """メイン関数"""
    config = TestConfig(
        port="/dev/ttyUSB0",  # Linux環境
        baudrate=115200,
        timeout=30.0
    )
    
    automation = LPDDRAutomation(config)
    success = automation.run_full_test_sequence()
    
    if success:
        logger.info("Test automation completed successfully")
    else:
        logger.error("Test automation failed")

if __name__ == "__main__":
    main()

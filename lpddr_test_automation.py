#!/usr/bin/env python3
"""
LPDDR Test Automation Software
AI-CAMKIT Main Board LPDDR4 Interface Test Automation
"""

import serial
import time
import re
import logging
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
from visualization import LPDDRVisualizer

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
class TestResult:
    """テスト結果"""
    step: TestStep
    frequency: int
    pattern: int
    result: TestResult
    message: str
    timestamp: float

class LPDDRAutomation:
    """LPDDRテスト自動化クラス"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.serial_conn: Optional[serial.Serial] = None
        self.power_conn: Optional[serial.Serial] = None  # 電源制御用
        self.test_results: List[TestResult] = []
        self.current_step = TestStep.FREQUENCY_SELECT
        self.eye_pattern_results: Dict[str, str] = {}
        self.visualizer = LPDDRVisualizer()
        
    def connect(self) -> bool:
        """シリアル接続を確立"""
        try:
            self.serial_conn = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout
            )
            logger.info(f"Connected to {self.config.port} at {self.config.baudrate} baud")
            
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
        """接続テストを実行"""
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                return False
            
            # 簡単な接続テスト（必要に応じて実装）
            # ここでは接続が開いているかどうかのみチェック
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def disconnect(self):
        """シリアル接続を切断"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected")
        
        if self.power_conn and self.power_conn.is_open:
            self.power_conn.close()
            logger.info("Power control disconnected")
    
    def send_command(self, command: str) -> bool:
        """コマンドを送信"""
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                raise CommandError(
                    "シリアル接続が確立されていません",
                    command=command
                )
            
            self.serial_conn.write(f"{command}\n".encode())
            logger.info(f"Sent command: {command}")
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
            logger.info(f"Received: {response}")
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
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.read_response(1.0)
                if re.search(prompt_pattern, response, re.IGNORECASE):
                    return True
            except CommandError:
                # レスポンス読み取りエラーは無視して続行
                continue
        
        # タイムアウト
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
    
    def run_frequency_test(self, frequency: int) -> Dict[str, TestResult]:
        """周波数テストを実行"""
        logger.info(f"Starting frequency test at {frequency}MHz")
        results = {}
        
        # 周波数選択
        if not self.wait_for_prompt("Please Hit number key"):
            logger.error("Frequency selection prompt not found")
            return results
        
        freq_key = FrequencyMapping.FREQUENCY_TO_KEY.value.get(frequency, FrequencyMapping.FREQ_666.value)
        self.send_command(str(freq_key))
        
        # トレーニング完了待機
        if not self.wait_for_prompt("Training Complete 7"):
            logger.error("Training failed")
            return results
        
        # 2Dトレーニング設定
        try:
            if self.wait_for_prompt(PromptPatterns.SELECT_2D_TRAINING.value):
                if self.config.enable_2d_training:
                    self.send_command(TestCommands.ENABLE_2D_TRAINING.value)
                    logger.info("2D training enabled")
                    # 2Dトレーニング完了待機
                    self.wait_for_prompt(PromptPatterns.TRAINING_2D_COMPLETE.value)
                else:
                    self.send_command(TestCommands.DISABLE_2D_TRAINING.value)
                    logger.info("2D training disabled")
        except TimeoutError:
            logger.warning("2D training prompt not found or timeout")
        
        # メモリテスト選択
        self.wait_for_prompt(PromptPatterns.SELECT_TEST_MODE.value)
        self.send_command(TestCommands.MEMORY_ACCESS_TEST.value)
        
        # テストバイト数設定
        self.wait_for_prompt(PromptPatterns.INPUT_OUT_VALUE.value)
        self.send_command(str(TestLimits.MAX_TEST_BYTES.value))
        
        # 各テストパターンを実行
        for pattern in self.config.test_patterns:
            try:
                self.wait_for_prompt(PromptPatterns.FREQUENCY_SELECT.value)
                self.send_command(f"{pattern:02d}")
                
                # テスト結果待機
                response = self.read_response(TestLimits.COMMAND_TIMEOUT.value)
                result = self.parse_test_result(response)
                
                results[f"pattern_{pattern}"] = result
                self.test_results.append(TestResult(
                    step=TestStep.MEMORY_TEST,
                    frequency=frequency,
                    pattern=pattern,
                    result=result,
                    message=response,
                    timestamp=time.time()
                ))
                
                # リピート選択
                try:
                    self.wait_for_prompt(PromptPatterns.REPEAT_MEMORY_TESTS.value)
                    self.send_command(TestCommands.END_TEST.value)
                except TimeoutError:
                    logger.warning("Repeat memory tests prompt not found")
                    
            except (TimeoutError, CommandError, TestResultError) as e:
                logger.error(f"Pattern {pattern} test failed: {e}")
                results[f"pattern_{pattern}"] = TestResult.UNKNOWN
                continue
        
        return results
    
    def run_diagnostics_test(self) -> TestResult:
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
        
        test_result = TestResult(
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
    
    def run_eye_pattern_test(self, pattern_type: EyePatternType, lane: int = 0, bit: int = 0) -> TestResult:
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
        
        test_result = TestResult(
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
    
    def run_comprehensive_eye_pattern_test(self) -> Dict[str, TestResult]:
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
            
            for frequency in frequencies:
                logger.info(f"Testing frequency: {frequency}MHz")
                results = self.run_frequency_test(frequency)
                
                # 結果をログ出力
                for pattern, result in results.items():
                    logger.info(f"{frequency}MHz {pattern}: {result.value}")
            
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

#!/usr/bin/env python3
"""
LPDDR Test Automation Unit Tests
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import serial
from lpddr_test_automation import (
    LPDDRAutomation, TestConfig, TestResult, TestStep, EyePatternType
)


class TestTestConfig(unittest.TestCase):
    """TestConfigクラスのテスト"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = TestConfig()
        self.assertEqual(config.port, "COM3")
        self.assertEqual(config.baudrate, 115200)
        self.assertEqual(config.timeout, 30.0)
        self.assertEqual(config.test_patterns, [1, 15])
        self.assertFalse(config.enable_2d_training)
        self.assertTrue(config.enable_eye_pattern)
        self.assertFalse(config.power_control_enabled)
    
    def test_custom_config(self):
        """カスタム設定のテスト"""
        config = TestConfig(
            port="/dev/ttyUSB0",
            baudrate=9600,
            timeout=10.0,
            test_patterns=[1, 2, 3],
            enable_2d_training=True,
            power_control_enabled=True,
            power_control_port="COM4"
        )
        self.assertEqual(config.port, "/dev/ttyUSB0")
        self.assertEqual(config.baudrate, 9600)
        self.assertEqual(config.timeout, 10.0)
        self.assertEqual(config.test_patterns, [1, 2, 3])
        self.assertTrue(config.enable_2d_training)
        self.assertTrue(config.power_control_enabled)
        self.assertEqual(config.power_control_port, "COM4")


class TestLPDDRAutomation(unittest.TestCase):
    """LPDDRAutomationクラスのテスト"""
    
    def setUp(self):
        """テスト前のセットアップ"""
        self.config = TestConfig(port="COM3", baudrate=115200)
        self.automation = LPDDRAutomation(self.config)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self.automation, 'serial_conn') and self.automation.serial_conn:
            self.automation.serial_conn = None
    
    @patch('serial.Serial')
    def test_connect_success(self, mock_serial):
        """接続成功のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = True
        mock_serial.return_value = mock_conn
        
        result = self.automation.connect()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.automation.serial_conn)
        mock_serial.assert_called_once_with(
            port="COM3",
            baudrate=115200,
            timeout=30.0
        )
    
    @patch('serial.Serial')
    def test_connect_failure(self, mock_serial):
        """接続失敗のテスト"""
        mock_serial.side_effect = serial.SerialException("Port not found")
        
        result = self.automation.connect()
        
        self.assertFalse(result)
        self.assertIsNone(self.automation.serial_conn)
    
    def test_disconnect(self):
        """切断のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = True
        self.automation.serial_conn = mock_conn
        
        self.automation.disconnect()
        
        mock_conn.close.assert_called_once()
    
    def test_send_command_success(self):
        """コマンド送信成功のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = True
        self.automation.serial_conn = mock_conn
        
        result = self.automation.send_command("test_command")
        
        self.assertTrue(result)
        mock_conn.write.assert_called_once_with(b"test_command\n")
    
    def test_send_command_failure(self):
        """コマンド送信失敗のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = False
        self.automation.serial_conn = mock_conn
        
        result = self.automation.send_command("test_command")
        
        self.assertFalse(result)
        mock_conn.write.assert_not_called()
    
    def test_read_response_success(self):
        """レスポンス読み取り成功のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = True
        mock_conn.read_until.return_value = b"test_response\n"
        self.automation.serial_conn = mock_conn
        
        response = self.automation.read_response()
        
        self.assertEqual(response, "test_response")
        mock_conn.read_until.assert_called_once_with(b'\n')
    
    def test_read_response_failure(self):
        """レスポンス読み取り失敗のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = False
        self.automation.serial_conn = mock_conn
        
        response = self.automation.read_response()
        
        self.assertEqual(response, "")
        mock_conn.read_until.assert_not_called()
    
    def test_parse_test_result(self):
        """テスト結果解析のテスト"""
        # PASSケース
        result = self.automation.parse_test_result("Test PASS")
        self.assertEqual(result, TestResult.PASS)
        
        result = self.automation.parse_test_result("pass")
        self.assertEqual(result, TestResult.PASS)
        
        # FAILケース
        result = self.automation.parse_test_result("Test FAIL")
        self.assertEqual(result, TestResult.FAIL)
        
        result = self.automation.parse_test_result("fail")
        self.assertEqual(result, TestResult.FAIL)
        
        # UNKNOWNケース
        result = self.automation.parse_test_result("Test UNKNOWN")
        self.assertEqual(result, TestResult.UNKNOWN)
        
        result = self.automation.parse_test_result("")
        self.assertEqual(result, TestResult.UNKNOWN)
    
    @patch('time.time')
    def test_wait_for_prompt_success(self, mock_time):
        """プロンプト待機成功のテスト"""
        mock_conn = Mock()
        mock_conn.is_open = True
        mock_conn.read_until.side_effect = [
            b"Please Hit number key\n",
            b"Training Complete 7\n"
        ]
        self.automation.serial_conn = mock_conn
        
        # time.time()をモックしてタイムアウトを回避
        mock_time.side_effect = [0, 1, 2]  # 3回の呼び出し
        
        result = self.automation.wait_for_prompt("Please Hit number key")
        
        self.assertTrue(result)
    
    @patch('time.time')
    def test_wait_for_prompt_timeout(self, mock_time):
        """プロンプト待機タイムアウトのテスト"""
        mock_conn = Mock()
        mock_conn.is_open = True
        mock_conn.read_until.return_value = b"other message\n"
        self.automation.serial_conn = mock_conn
        
        # time.time()をモックしてタイムアウトをシミュレート
        mock_time.side_effect = [0, 1, 2, 31]  # 31秒経過
        
        result = self.automation.wait_for_prompt("Please Hit number key", timeout=30.0)
        
        self.assertFalse(result)
    
    def test_determine_next_step_no_results(self):
        """結果がない場合の次ステップ決定テスト"""
        result = self.automation.determine_next_step()
        self.assertEqual(result, TestStep.FREQUENCY_SELECT)
    
    def test_determine_next_step_800mhz_pattern01_pass(self):
        """800MHz pattern 01 PASSの場合の次ステップ決定テスト"""
        from lpddr_test_automation import TestResult as TR
        
        # テスト結果を追加
        self.automation.test_results.append(TR(
            step=TestStep.MEMORY_TEST,
            frequency=800,
            pattern=1,
            result=TestResult.PASS,
            message="PASS",
            timestamp=time.time()
        ))
        
        result = self.automation.determine_next_step()
        self.assertEqual(result, TestStep.EYE_PATTERN)
    
    def test_determine_next_step_666mhz_pattern15_pass(self):
        """666MHz pattern 15 PASSの場合の次ステップ決定テスト"""
        from lpddr_test_automation import TestResult as TR
        
        # テスト結果を追加
        self.automation.test_results.append(TR(
            step=TestStep.MEMORY_TEST,
            frequency=666,
            pattern=15,
            result=TestResult.PASS,
            message="PASS",
            timestamp=time.time()
        ))
        
        result = self.automation.determine_next_step()
        self.assertEqual(result, TestStep.EYE_PATTERN)
    
    def test_determine_next_step_all_fail(self):
        """全て失敗した場合の次ステップ決定テスト"""
        from lpddr_test_automation import TestResult as TR
        
        # 失敗結果を追加
        self.automation.test_results.append(TR(
            step=TestStep.MEMORY_TEST,
            frequency=800,
            pattern=1,
            result=TestResult.FAIL,
            message="FAIL",
            timestamp=time.time()
        ))
        
        result = self.automation.determine_next_step()
        self.assertEqual(result, TestStep.DIAGNOSTICS)


class TestEyePatternType(unittest.TestCase):
    """EyePatternTypeのテスト"""
    
    def test_eye_pattern_types(self):
        """アイパターンタイプのテスト"""
        self.assertEqual(EyePatternType.TX.value, "tx")
        self.assertEqual(EyePatternType.RX.value, "rx")
        self.assertEqual(EyePatternType.SIMPLE_WRITE_READ.value, "simple_write_read")


class TestTestStep(unittest.TestCase):
    """TestStepのテスト"""
    
    def test_test_steps(self):
        """テストステップのテスト"""
        expected_steps = [
            "frequency_select", "training", "memory_test", 
            "diagnostics", "eye_pattern", "power_cycle", "complete"
        ]
        
        for step in TestStep:
            self.assertIn(step.value, expected_steps)


class TestTestResult(unittest.TestCase):
    """TestResultのテスト"""
    
    def test_test_results(self):
        """テスト結果のテスト"""
        self.assertEqual(TestResult.PASS.value, "PASS")
        self.assertEqual(TestResult.FAIL.value, "FAIL")
        self.assertEqual(TestResult.UNKNOWN.value, "UNKNOWN")


if __name__ == '__main__':
    # テストスイートの実行
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
Eye Pattern Test Analysis Logic Test Suite
解析ロジック改善実装のテストと検証
"""

import unittest
import time
import tempfile
import os
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Dict, Any

# テスト対象のモジュールをインポート
from lpddr_test_automation import LPDDRAutomation, TestConfig, EyePatternConfig, EyePatternResult
from visualization import LPDDRVisualizer, UnifiedTestResult, VisualizationData


class TestEyePatternAnalysisLogic(unittest.TestCase):
    """Eye Pattern解析ロジックのテストクラス"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.config = TestConfig(
            port="COM7",
            baudrate=115200,
            timeout=30.0,
            enable_eye_pattern=True,
            eye_pattern=EyePatternConfig()
        )
        
        # モックのシリアル接続を作成
        self.mock_serial = Mock()
        self.mock_serial.in_waiting = 0
        self.mock_serial.read.return_value = b""
        
        # LPDDRAutomationインスタンスを作成（シリアル接続はモック）
        self.automation = LPDDRAutomation(self.config)
        self.automation.serial_conn = self.mock_serial
    
    def test_signal_quality_evaluation(self):
        """信号品質評価のテスト"""
        # 成功ケース
        success_data = "Eye pattern test completed successfully. Timing: 2.5ns, Quality: excellent"
        quality_score = self.automation._evaluate_signal_quality(success_data)
        self.assertGreater(quality_score, 0.5)
        self.assertLessEqual(quality_score, 1.0)
        
        # 失敗ケース
        fail_data = "Error: test failed, timeout occurred"
        quality_score = self.automation._evaluate_signal_quality(fail_data)
        self.assertLess(quality_score, 0.5)
        self.assertGreaterEqual(quality_score, 0.0)
        
        # 空データケース
        empty_data = ""
        quality_score = self.automation._evaluate_signal_quality(empty_data)
        self.assertEqual(quality_score, 0.0)
    
    def test_timing_info_extraction(self):
        """タイミング情報抽出のテスト"""
        # タイミング情報を含むデータ
        timing_data = "Timing: 2.5ns, Latency: 1.2us"
        timing = self.automation._extract_timing_info(timing_data)
        self.assertGreater(timing, 0)
        
        # 数値のみのデータ
        numeric_data = "Test completed with value 3.14"
        timing = self.automation._extract_timing_info(numeric_data)
        self.assertGreater(timing, 0)
        
        # タイミング情報なしのデータ
        no_timing_data = "Test completed successfully"
        timing = self.automation._extract_timing_info(no_timing_data)
        self.assertEqual(timing, 0.0)
    
    def test_eye_pattern_result_analysis(self):
        """Eye Pattern結果解析のテスト"""
        # テストデータ
        test_data = "Eye pattern test completed successfully. Lane 5, Bit 1, Quality: 0.85"
        
        # 解析実行
        self.automation._analyze_eye_pattern_results(test_data)
        
        # 結果の確認
        self.assertEqual(len(self.automation.detailed_eye_pattern_results), 1)
        result = self.automation.detailed_eye_pattern_results[0]
        self.assertEqual(result.lane, 5)
        self.assertEqual(result.bit, 1)
        self.assertEqual(result.pattern_type, "tx")
        self.assertEqual(result.result, "PASS")
        self.assertGreater(result.quality, 0.0)
    
    def test_eye_pattern_analysis_summary(self):
        """Eye Pattern分析サマリーのテスト"""
        # テストデータを追加
        test_results = [
            EyePatternResult(
                lane=5, bit=1, pattern_type="tx", result="PASS",
                timing=2.5, quality=0.8, timestamp=time.time(),
                raw_data="Test 1 passed"
            ),
            EyePatternResult(
                lane=5, bit=2, pattern_type="tx", result="FAIL",
                timing=1.0, quality=0.3, timestamp=time.time(),
                raw_data="Test 2 failed"
            )
        ]
        
        self.automation.detailed_eye_pattern_results = test_results
        
        # サマリー取得
        summary = self.automation.get_eye_pattern_analysis_summary()
        
        # 結果の確認
        self.assertEqual(summary['total_tests'], 2)
        self.assertEqual(summary['pass_count'], 1)
        self.assertEqual(summary['fail_count'], 1)
        self.assertEqual(summary['pass_rate'], 50.0)
        self.assertIn(5, summary['lane_summary'])
        self.assertIn(1, summary['bit_summary'])
        self.assertIn(2, summary['bit_summary'])


class TestUnifiedDataStructure(unittest.TestCase):
    """統一されたデータ構造のテストクラス"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.visualizer = LPDDRVisualizer()
    
    def test_unified_test_result_creation(self):
        """統一されたテスト結果の作成テスト"""
        result = UnifiedTestResult(
            test_id="test_001",
            test_type="eye_pattern",
            frequency=800,
            pattern=0,
            result="PASS",
            timestamp=time.time(),
            quality_score=0.85,
            timing=2.5,
            lane=5,
            bit=1,
            raw_data="Test completed successfully"
        )
        
        self.assertEqual(result.test_id, "test_001")
        self.assertEqual(result.test_type, "eye_pattern")
        self.assertEqual(result.frequency, 800)
        self.assertEqual(result.result, "PASS")
        self.assertEqual(result.quality_score, 0.85)
        self.assertIsNotNone(result.metadata)
    
    def test_visualization_data_creation(self):
        """可視化データの作成テスト"""
        test_results = [
            UnifiedTestResult(
                test_id="test_001",
                test_type="eye_pattern",
                frequency=800,
                pattern=0,
                result="PASS",
                timestamp=time.time(),
                quality_score=0.85
            )
        ]
        
        viz_data = VisualizationData(
            test_results=test_results,
            eye_pattern_results={"test_001": "raw data"},
            summary_stats={"total_tests": 1},
            timestamp=time.time()
        )
        
        self.assertEqual(len(viz_data.test_results), 1)
        self.assertIn("test_001", viz_data.eye_pattern_results)
        self.assertEqual(viz_data.summary_stats["total_tests"], 1)
    
    def test_data_conversion(self):
        """データ変換のテスト"""
        # モックのテスト結果
        mock_results = [
            Mock(
                step=Mock(value="eye_pattern"),
                frequency=800,
                pattern=0,
                result=Mock(value="PASS"),
                timestamp=time.time(),
                message="Test completed"
            )
        ]
        
        eye_pattern_results = {"test_001": "Eye pattern test completed successfully"}
        
        # データ変換実行
        unified_data = self.visualizer.convert_to_unified_data(mock_results, eye_pattern_results)
        
        # 結果の確認
        self.assertIsInstance(unified_data, VisualizationData)
        self.assertGreater(len(unified_data.test_results), 0)
        self.assertIn("test_001", unified_data.eye_pattern_results)
        self.assertIn("total_tests", unified_data.summary_stats)


class TestVisualizationConsistency(unittest.TestCase):
    """可視化データの整合性テストクラス"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.visualizer = LPDDRVisualizer(output_dir=self.temp_dir)
    
    def tearDown(self):
        """テストのクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_unified_timeline_visualization(self):
        """統一されたタイムライン可視化のテスト"""
        # テストデータの作成
        test_results = [
            UnifiedTestResult(
                test_id="test_001",
                test_type="eye_pattern",
                frequency=800,
                pattern=0,
                result="PASS",
                timestamp=time.time(),
                quality_score=0.85
            )
        ]
        
        viz_data = VisualizationData(
            test_results=test_results,
            eye_pattern_results={},
            summary_stats={"total_tests": 1},
            timestamp=time.time()
        )
        
        # 可視化実行
        result_file = self.visualizer.visualize_test_timeline_unified(viz_data, save_plot=True)
        
        # 結果の確認
        self.assertIsNotNone(result_file)
        self.assertTrue(os.path.exists(result_file))
    
    def test_unified_dashboard_creation(self):
        """統一されたダッシュボード作成のテスト"""
        # テストデータの作成
        test_results = [
            UnifiedTestResult(
                test_id="test_001",
                test_type="eye_pattern",
                frequency=800,
                pattern=0,
                result="PASS",
                timestamp=time.time(),
                quality_score=0.85
            )
        ]
        
        viz_data = VisualizationData(
            test_results=test_results,
            eye_pattern_results={},
            summary_stats={"total_tests": 1, "pass_count": 1, "fail_count": 0},
            timestamp=time.time()
        )
        
        # ダッシュボード作成
        result_file = self.visualizer.create_interactive_dashboard_unified(viz_data, save_html=True)
        
        # 結果の確認
        self.assertIsNotNone(result_file)
        self.assertTrue(os.path.exists(result_file))
    
    def test_summary_report_generation(self):
        """サマリーレポート生成のテスト"""
        # テストデータの作成
        test_results = [
            UnifiedTestResult(
                test_id="test_001",
                test_type="eye_pattern",
                frequency=800,
                pattern=0,
                result="PASS",
                timestamp=time.time(),
                quality_score=0.85
            )
        ]
        
        viz_data = VisualizationData(
            test_results=test_results,
            eye_pattern_results={},
            summary_stats={"total_tests": 1, "pass_count": 1, "fail_count": 0},
            timestamp=time.time()
        )
        
        # レポート生成
        result_file = self.visualizer.generate_summary_report_unified(viz_data)
        
        # 結果の確認
        self.assertIsNotNone(result_file)
        self.assertTrue(os.path.exists(result_file))
        
        # ファイル内容の確認
        with open(result_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("LPDDR Test Results Summary Report", content)
            self.assertIn("Total Tests: 1", content)


class TestIntegration(unittest.TestCase):
    """統合テストクラス"""
    
    def test_end_to_end_analysis_flow(self):
        """エンドツーエンドの解析フローのテスト"""
        # 1. テスト設定の作成
        config = TestConfig(
            port="COM7",
            baudrate=115200,
            timeout=30.0,
            enable_eye_pattern=True,
            eye_pattern=EyePatternConfig()
        )
        
        # 2. モックのシリアル接続
        mock_serial = Mock()
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b""
        
        # 3. オートメーションインスタンスの作成
        automation = LPDDRAutomation(config)
        automation.serial_conn = mock_serial
        
        # 4. テストデータの解析
        test_data = "Eye pattern test completed successfully. Lane 5, Bit 1, Timing: 2.5ns"
        automation._analyze_eye_pattern_results(test_data)
        
        # 5. 分析サマリーの取得
        summary = automation.get_eye_pattern_analysis_summary()
        
        # 6. 可視化データの作成
        visualizer = LPDDRVisualizer()
        unified_data = visualizer.convert_to_unified_data([], automation.eye_pattern_results)
        
        # 7. 結果の確認
        self.assertEqual(len(automation.detailed_eye_pattern_results), 1)
        self.assertEqual(summary['total_tests'], 1)
        self.assertIsInstance(unified_data, VisualizationData)
        # Eye Pattern結果が変換されることを確認（eye_pattern_resultsが空でない場合）
        if automation.eye_pattern_results:
            self.assertGreater(len(unified_data.test_results), 0)
        else:
            # eye_pattern_resultsが空の場合は、test_resultsも空になる
            self.assertEqual(len(unified_data.test_results), 0)


def run_analysis_logic_tests():
    """解析ロジックのテストを実行"""
    print("🔧 Eye Pattern Test Analysis Logic Test Suite")
    print("=" * 60)
    
    # テストスイートの作成
    test_suite = unittest.TestSuite()
    
    # テストクラスの追加
    test_classes = [
        TestEyePatternAnalysisLogic,
        TestUnifiedDataStructure,
        TestVisualizationConsistency,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テストの実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 結果の表示
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_analysis_logic_tests()
    exit(0 if success else 1)

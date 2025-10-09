#!/usr/bin/env python3
"""
LPDDR Test Automation Visualization Module
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass

from constants import TestLimits, FileExtensions

# ログ設定
logger = logging.getLogger(__name__)

@dataclass
class UnifiedTestResult:
    """統一されたテスト結果データ構造"""
    test_id: str
    test_type: str  # 'memory', 'eye_pattern', 'diagnostics'
    frequency: int
    pattern: int
    result: str  # 'PASS', 'FAIL', 'UNKNOWN'
    timestamp: float
    quality_score: float = 0.0
    timing: float = 0.0
    lane: int = 0
    bit: int = 0
    raw_data: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class VisualizationData:
    """可視化用の統一データ構造"""
    test_results: List[UnifiedTestResult]
    eye_pattern_results: Dict[str, Any]
    summary_stats: Dict[str, Any]
    timestamp: float
    
    def __post_init__(self):
        if not self.test_results:
            self.test_results = []
        if not self.eye_pattern_results:
            self.eye_pattern_results = {}
        if not self.summary_stats:
            self.summary_stats = {}

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

class LPDDRVisualizer:
    """LPDDRテスト結果のビジュアライズクラス"""
    
    def __init__(self, output_dir: str = "visualization_output"):
        """
        ビジュアライザーを初期化
        
        Args:
            output_dir (str): 出力ディレクトリ
        """
        self.output_dir = output_dir
        self.eye_pattern_results: Dict[str, Any] = {}
        self._ensure_output_dir()
        
        # スタイル設定
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def _ensure_output_dir(self):
        """出力ディレクトリを作成"""
        os.makedirs(self.output_dir, exist_ok=True)
    
    def convert_to_unified_data(self, test_results: List[Any], eye_pattern_results: Dict[str, Any] = None) -> VisualizationData:
        """テスト結果を統一されたデータ構造に変換"""
        try:
            import time
            unified_results = []
            
            # 通常のテスト結果を変換
            for result in test_results:
                if hasattr(result, 'step') and hasattr(result, 'result'):
                    unified_result = UnifiedTestResult(
                        test_id=f"{result.step.value}_{result.frequency}_{result.pattern}",
                        test_type=self._get_test_type(result.step),
                        frequency=getattr(result, 'frequency', 0),
                        pattern=getattr(result, 'pattern', 0),
                        result=result.result.value if hasattr(result.result, 'value') else str(result.result),
                        timestamp=getattr(result, 'timestamp', time.time()),
                        quality_score=0.0,
                        timing=0.0,
                        raw_data=getattr(result, 'message', ''),
                        metadata={'step': result.step.value}
                    )
                    unified_results.append(unified_result)
            
            # Eye Pattern結果を変換（統一ロジック使用）
            if eye_pattern_results:
                logger.info(f"Converting {len(eye_pattern_results)} eye pattern results to unified format")
                for key, raw_data in eye_pattern_results.items():
                    # 統一された品質評価ロジックを使用
                    quality_score = self._extract_quality_from_eye_pattern(raw_data)
                    
                    # 品質スコアに基づいてPASS/FAILを判定（統一ロジック）
                    result_status = "PASS" if quality_score > 0.5 else "FAIL"
                    
                    # キーからレーンとビット情報を抽出
                    lane = 5  # デフォルトレーン
                    bit = 1   # デフォルトビット
                    
                    if 'tx_lane_' in key:
                        parts = key.split('_')
                        if len(parts) >= 5:
                            lane = int(parts[2])
                            bit = int(parts[4])
                    elif 'rx_lane_' in key:
                        parts = key.split('_')
                        if len(parts) >= 5:
                            lane = int(parts[2])
                            bit = int(parts[4])
                    
                    unified_result = UnifiedTestResult(
                        test_id=f"eye_pattern_{key}",
                        test_type="eye_pattern",
                        frequency=800,  # デフォルト周波数
                        pattern=0,
                        result=result_status,
                        timestamp=time.time(),
                        quality_score=quality_score,
                        timing=0.0,
                        lane=lane,
                        bit=bit,
                        raw_data=raw_data,
                        metadata={'eye_pattern_key': key, 'quality_score': quality_score}
                    )
                    unified_results.append(unified_result)
                    
                    logger.info(f"Converted eye pattern result {key}: quality={quality_score:.3f}, result={result_status}")
            
            # サマリー統計の計算
            summary_stats = self._calculate_summary_stats(unified_results)
            
            return VisualizationData(
                test_results=unified_results,
                eye_pattern_results=eye_pattern_results or {},
                summary_stats=summary_stats,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Failed to convert to unified data: {e}")
            import time
            return VisualizationData([], {}, {}, time.time())
    
    def _get_test_type(self, step) -> str:
        """テストステップからテストタイプを判定"""
        step_str = str(step.value).lower()
        if 'eye' in step_str or 'pattern' in step_str:
            return 'eye_pattern'
        elif 'diagnostic' in step_str:
            return 'diagnostics'
        else:
            return 'memory'
    
    def _extract_quality_from_eye_pattern(self, raw_data: str) -> float:
        """Eye Pattern生データから品質スコアを抽出（強化版ロジック）"""
        try:
            quality_score = 0.0
            
            # 1. 基本的な成功/失敗判定（強化版）
            if "successfully" in raw_data.lower():
                quality_score += 0.4
            elif "pass" in raw_data.lower():
                quality_score += 0.3
            elif "complete" in raw_data.lower():
                quality_score += 0.2
            
            # 2. エラーメッセージの検出と重み付け（強化版）
            error_indicators = {
                "error": -0.3,
                "fail": -0.4,
                "timeout": -0.2,
                "invalid": -0.2,
                "abort": -0.3,
                "exception": -0.3,
                "threshold": -0.1,  # 閾値エラー
                "signal quality": -0.2,  # 信号品質エラー
                "below threshold": -0.2  # 閾値以下エラー
            }
            
            for indicator, penalty in error_indicators.items():
                if indicator in raw_data.lower():
                    quality_score += penalty
            
            # 3. 成功メッセージの検出と重み付け（強化版）
            success_indicators = {
                "pass": 0.1,
                "success": 0.15,
                "complete": 0.1,
                "ok": 0.05,
                "finished": 0.1,
                "done": 0.05,
                "quality": 0.1,  # 品質情報の存在
                "timing": 0.05   # タイミング情報の存在
            }
            
            for indicator, bonus in success_indicators.items():
                if indicator in raw_data.lower():
                    quality_score += bonus
            
            # 4. 数値データの解析（強化版）
            import re
            numbers = re.findall(r'\d+\.?\d*', raw_data)
            if numbers:
                quality_score += 0.1
                for num_str in numbers:
                    try:
                        num = float(num_str)
                        if 0 < num < 1000:  # 合理的なタイミング範囲
                            quality_score += 0.05
                        elif 0.8 <= num <= 1.0:  # 品質スコア範囲
                            quality_score += 0.1
                    except ValueError:
                        continue
            
            # 5. データ量の評価（強化版）
            data_length = len(raw_data)
            if data_length > 100:  # 十分なデータ量
                quality_score += 0.1
            elif data_length < 20:  # データ不足
                quality_score -= 0.1
            
            # 6. 特定のキーワードの検出（強化版）
            quality_keywords = {
                "eye pattern": 0.1,
                "signal": 0.05,
                "timing": 0.05,
                "quality": 0.05,
                "margin": 0.05,
                "diagnostics": 0.05,  # 診断テスト
                "tx": 0.02,  # TXテスト
                "rx": 0.02   # RXテスト
            }
            
            for keyword, bonus in quality_keywords.items():
                if keyword in raw_data.lower():
                    quality_score += bonus
            
            # 7. パターン別の重み付け（強化版）
            if "tx" in raw_data.lower() and "rx" in raw_data.lower():
                quality_score += 0.05  # 両方のテストが含まれている
            elif "tx" in raw_data.lower():
                quality_score += 0.02  # TXテスト
            elif "rx" in raw_data.lower():
                quality_score += 0.02  # RXテスト
            
            # 8. スコアを0.0-1.0の範囲に正規化
            quality_score = max(0.0, min(1.0, quality_score))
            
            # 9. ログ出力（強化版）
            logger.debug(f"Enhanced quality evaluation: {quality_score:.3f} (data length: {data_length}, indicators: {len([k for k in quality_keywords.keys() if k in raw_data.lower()])})")
            
            return quality_score
            
        except Exception as e:
            logger.error(f"Failed to extract quality from eye pattern: {e}")
            return 0.0
    
    def _calculate_summary_stats(self, unified_results: List[UnifiedTestResult]) -> Dict[str, Any]:
        """統一された結果からサマリー統計を計算"""
        try:
            if not unified_results:
                return {
                    'total_tests': 0,
                    'pass_count': 0,
                    'fail_count': 0,
                    'pass_rate': 0.0,
                    'average_quality': 0.0,
                    'test_types': {},
                    'frequencies': {},
                    'patterns': {}
                }
            
            # 基本統計
            total_tests = len(unified_results)
            pass_count = sum(1 for r in unified_results if r.result == "PASS")
            fail_count = total_tests - pass_count
            pass_rate = (pass_count / total_tests * 100) if total_tests > 0 else 0.0
            average_quality = sum(r.quality_score for r in unified_results) / total_tests
            
            # テストタイプ別統計
            test_types = {}
            for result in unified_results:
                test_type = result.test_type
                if test_type not in test_types:
                    test_types[test_type] = {'total': 0, 'pass': 0, 'fail': 0}
                test_types[test_type]['total'] += 1
                if result.result == "PASS":
                    test_types[test_type]['pass'] += 1
                else:
                    test_types[test_type]['fail'] += 1
            
            # 周波数別統計
            frequencies = {}
            for result in unified_results:
                freq = result.frequency
                if freq not in frequencies:
                    frequencies[freq] = {'total': 0, 'pass': 0, 'fail': 0}
                frequencies[freq]['total'] += 1
                if result.result == "PASS":
                    frequencies[freq]['pass'] += 1
                else:
                    frequencies[freq]['fail'] += 1
            
            # パターン別統計
            patterns = {}
            for result in unified_results:
                pattern = result.pattern
                if pattern not in patterns:
                    patterns[pattern] = {'total': 0, 'pass': 0, 'fail': 0}
                patterns[pattern]['total'] += 1
                if result.result == "PASS":
                    patterns[pattern]['pass'] += 1
                else:
                    patterns[pattern]['fail'] += 1
            
            return {
                'total_tests': total_tests,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': pass_rate,
                'average_quality': average_quality,
                'test_types': test_types,
                'frequencies': frequencies,
                'patterns': patterns
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate summary stats: {e}")
            return {}
        
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
        logger.info("Creating eye pattern visualization")
        
        # データを解析してマトリックスを作成
        tx_results = np.zeros((TestLimits.MAX_LANES.value, TestLimits.MAX_BITS.value))
        rx_results = np.zeros((TestLimits.MAX_LANES.value, TestLimits.MAX_BITS.value))
        
        # 結果を解析（統一ロジック使用）
        for key, result in eye_pattern_results.items():
            try:
                # 統一された品質評価ロジックを使用
                quality_score = self._extract_quality_from_eye_pattern(result)
                
                # 品質スコアに基づいてPASS/FAILを判定
                is_pass = quality_score > 0.5  # 0.5を閾値とする
                result_value = quality_score if is_pass else 0.0
                
                # キーからレーンとビット情報を抽出（フォールバック付き）
                lane = 0
                bit = 0
                
                if 'tx_lane_' in key:
                    parts = key.split('_')
                    if len(parts) >= 5:
                        lane = int(parts[2])
                        bit = int(parts[4])
                    tx_results[lane, bit] = result_value
                elif 'rx_lane_' in key:
                    parts = key.split('_')
                    if len(parts) >= 5:
                        lane = int(parts[2])
                        bit = int(parts[4])
                    rx_results[lane, bit] = result_value
                else:
                    # デフォルト処理：キーに基づいてTX/RXを判定
                    if "tx" in key.lower() or "transmit" in key.lower():
                        # テスト結果のインデックスに基づいてレーンとビットを設定
                        test_index = int(key.split('_')[-1]) if key.split('_')[-1].isdigit() else 0
                        lane = test_index % TestLimits.MAX_LANES.value
                        bit = test_index % TestLimits.MAX_BITS.value
                        tx_results[lane, bit] = result_value
                    elif "rx" in key.lower() or "receive" in key.lower():
                        # テスト結果のインデックスに基づいてレーンとビットを設定
                        test_index = int(key.split('_')[-1]) if key.split('_')[-1].isdigit() else 0
                        lane = test_index % TestLimits.MAX_LANES.value
                        bit = test_index % TestLimits.MAX_BITS.value
                        rx_results[lane, bit] = result_value
                    else:
                        # デフォルトはTXとして扱う
                        test_index = int(key.split('_')[-1]) if key.split('_')[-1].isdigit() else 0
                        lane = test_index % TestLimits.MAX_LANES.value
                        bit = test_index % TestLimits.MAX_BITS.value
                        tx_results[lane, bit] = result_value
                
                logger.debug(f"Eye pattern result {key}: quality={quality_score:.3f}, pass={is_pass}, lane={lane}, bit={bit}")
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse eye pattern key: {key}, error: {e}")
                continue
        
        # プロット作成
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # TX結果のヒートマップ
        im1 = ax1.imshow(tx_results, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        ax1.set_title('TX Eye Pattern Results', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Bit Position', fontsize=12)
        ax1.set_ylabel('Lane Number', fontsize=12)
        ax1.set_xticks(range(TestLimits.MAX_BITS.value))
        ax1.set_yticks(range(TestLimits.MAX_LANES.value))
        
        # セルに値を表示
        for i in range(TestLimits.MAX_LANES.value):
            for j in range(TestLimits.MAX_BITS.value):
                text = ax1.text(j, i, f'{tx_results[i, j]:.0f}',
                              ha="center", va="center", color="black", fontweight='bold')
        
        # RX結果のヒートマップ
        im2 = ax2.imshow(rx_results, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        ax2.set_title('RX Eye Pattern Results', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Bit Position', fontsize=12)
        ax2.set_ylabel('Lane Number', fontsize=12)
        ax2.set_xticks(range(TestLimits.MAX_BITS.value))
        ax2.set_yticks(range(TestLimits.MAX_LANES.value))
        
        # セルに値を表示
        for i in range(TestLimits.MAX_LANES.value):
            for j in range(TestLimits.MAX_BITS.value):
                text = ax2.text(j, i, f'{rx_results[i, j]:.0f}',
                              ha="center", va="center", color="black", fontweight='bold')
        
        # カラーバーを追加
        cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8)
        cbar1.set_label('Test Result (1=PASS, 0=FAIL)', fontsize=10)
        
        cbar2 = plt.colorbar(im2, ax=ax2, shrink=0.8)
        cbar2.set_label('Test Result (1=PASS, 0=FAIL)', fontsize=10)
        
        plt.tight_layout()
        
        # 統計情報を追加
        tx_pass_rate = np.mean(tx_results) * 100
        rx_pass_rate = np.mean(rx_results) * 100
        
        fig.suptitle(f'Eye Pattern Test Results - TX Pass Rate: {tx_pass_rate:.1f}%, RX Pass Rate: {rx_pass_rate:.1f}%', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # 保存
        if save_plot:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eye_pattern_results_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            print(f"DEBUG: Saving eye pattern visualization to: {filepath}")  # デバッグ用
            print(f"DEBUG: Output directory exists: {os.path.exists(self.output_dir)}")  # デバッグ用
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"DEBUG: File saved successfully: {os.path.exists(filepath)}")  # デバッグ用
            logger.info(f"Eye pattern visualization saved to: {filepath}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
            
        return filepath if save_plot else ""
    
    def visualize_test_timeline(self, test_results: List[Any], 
                              save_plot: bool = True, show_plot: bool = False) -> str:
        """
        テスト実行タイムラインを可視化
        
        Args:
            test_results (List[Any]): テスト結果リスト
            save_plot (bool): プロットを保存するか
            show_plot (bool): プロットを表示するか
            
        Returns:
            str: 保存されたファイルパス
        """
        logger.info("Creating test timeline visualization")
        
        if not test_results:
            logger.warning("No test results to visualize")
            return ""
        
        # データを準備
        timestamps = [datetime.fromtimestamp(getattr(r, 'timestamp', 0)) for r in test_results]
        results = [getattr(r, 'result', None) for r in test_results]
        results = [getattr(r, 'value', str(r)) if hasattr(r, 'value') else str(r) for r in results]
        steps = [getattr(r, 'step', None) for r in test_results]
        steps = [getattr(s, 'value', str(s)) if hasattr(s, 'value') else str(s) for s in steps]
        frequencies = [getattr(r, 'frequency', 0) for r in test_results]
        patterns = [getattr(r, 'pattern', 0) for r in test_results]
        
        # 結果を数値に変換
        result_numeric = []
        for result in results:
            if result == "PASS":
                result_numeric.append(1)
            elif result == "FAIL":
                result_numeric.append(0)
            else:
                result_numeric.append(0.5)  # UNKNOWN
        
        # プロット作成
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # タイムライン表示
        colors = ['green' if r == 1 else 'red' if r == 0 else 'orange' for r in result_numeric]
        ax1.scatter(timestamps, result_numeric, c=colors, s=100, alpha=0.7)
        ax1.plot(timestamps, result_numeric, 'b-', alpha=0.3, linewidth=1)
        
        # 各ポイントにラベルを追加
        for i, (ts, result, step, freq, pattern) in enumerate(zip(timestamps, results, steps, frequencies, patterns)):
            label = f"{step}\n{freq}MHz P{pattern}\n{result}"
            ax1.annotate(label, (ts, result_numeric[i]), 
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=8, ha='left',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        ax1.set_title('Test Execution Timeline', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Test Result', fontsize=12)
        ax1.set_ylim(-0.1, 1.1)
        ax1.set_yticks([0, 0.5, 1])
        ax1.set_yticklabels(['FAIL', 'UNKNOWN', 'PASS'])
        ax1.grid(True, alpha=0.3)
        
        # ステップ別の分布
        step_counts = {}
        for step in steps:
            step_counts[step] = step_counts.get(step, 0) + 1
        
        ax2.bar(step_counts.keys(), step_counts.values(), color='skyblue', alpha=0.7)
        ax2.set_title('Test Steps Distribution', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Test Step', fontsize=12)
        ax2.set_ylabel('Count', fontsize=12)
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # 統計情報を追加
        pass_count = sum(1 for r in results if r == "PASS")
        fail_count = sum(1 for r in results if r == "FAIL")
        total_count = len(results)
        pass_rate = (pass_count / total_count) * 100 if total_count > 0 else 0
        
        fig.suptitle(f'Test Timeline Analysis - Total: {total_count}, Pass: {pass_count}, Fail: {fail_count}, Pass Rate: {pass_rate:.1f}%', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # 保存
        if save_plot:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_timeline_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            print(f"DEBUG: Saving timeline visualization to: {filepath}")  # デバッグ用
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"DEBUG: Timeline file saved successfully: {os.path.exists(filepath)}")  # デバッグ用
            logger.info(f"Test timeline visualization saved to: {filepath}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
            
        return filepath if save_plot else ""
    
    def create_interactive_dashboard(self, test_results: List[Any], 
                                   eye_pattern_results: Dict[str, str],
                                   save_html: bool = True) -> str:
        """
        インタラクティブなダッシュボードを作成
        
        Args:
            test_results (List[Any]): テスト結果リスト
            eye_pattern_results (Dict[str, str]): アイパターン結果辞書
            save_html (bool): HTMLファイルを保存するか
            
        Returns:
            str: 保存されたファイルパス
        """
        logger.info("Creating interactive dashboard")
        
        # サブプロットを作成
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Test Results Timeline', 'Eye Pattern Results', 
                          'Test Steps Distribution', 'Pass/Fail Summary'),
            specs=[[{"secondary_y": False}, {"type": "heatmap"}],
                   [{"type": "bar"}, {"type": "pie"}]]
        )
        
        # 1. タイムライン
        if test_results:
            timestamps = [datetime.fromtimestamp(getattr(r, 'timestamp', 0)) for r in test_results]
            results = [getattr(r, 'result', None) for r in test_results]
            results = [getattr(r, 'value', str(r)) if hasattr(r, 'value') else str(r) for r in results]
            result_numeric = [1 if r == "PASS" else 0 if r == "FAIL" else 0.5 for r in results]
            
            fig.add_trace(
                go.Scatter(x=timestamps, y=result_numeric, mode='markers+lines',
                          marker=dict(size=10, color=result_numeric, colorscale='RdYlGn'),
                          name='Test Results'),
                row=1, col=1
            )
        
        # 2. アイパターンヒートマップ
        if eye_pattern_results:
            tx_data = np.zeros((TestLimits.MAX_LANES.value, TestLimits.MAX_BITS.value))
            rx_data = np.zeros((TestLimits.MAX_LANES.value, TestLimits.MAX_BITS.value))
            
            for key, result in eye_pattern_results.items():
                try:
                    if 'tx_lane_' in key:
                        parts = key.split('_')
                        lane = int(parts[2])
                        bit = int(parts[4])
                        tx_data[lane, bit] = 1 if 'PASS' in result.upper() else 0
                    elif 'rx_lane_' in key:
                        parts = key.split('_')
                        lane = int(parts[2])
                        bit = int(parts[4])
                        rx_data[lane, bit] = 1 if 'PASS' in result.upper() else 0
                except (ValueError, IndexError):
                    continue
            
            fig.add_trace(
                go.Heatmap(z=tx_data, colorscale='RdYlGn', showscale=True,
                          name='TX Eye Pattern'),
                row=1, col=2
            )
        
        # 3. ステップ分布
        if test_results:
            step_counts = {}
            for result in test_results:
                step = getattr(result, 'step', None)
                step = getattr(step, 'value', str(step)) if hasattr(step, 'value') else str(step)
                step_counts[step] = step_counts.get(step, 0) + 1
            
            fig.add_trace(
                go.Bar(x=list(step_counts.keys()), y=list(step_counts.values()),
                      name='Step Distribution'),
                row=2, col=1
            )
        
        # 4. パス/フェイルサマリー
        if test_results:
            pass_count = 0
            fail_count = 0
            for r in test_results:
                result = getattr(r, 'result', None)
                result_value = getattr(result, 'value', str(result)) if hasattr(result, 'value') else str(result)
                if result_value == "PASS":
                    pass_count += 1
                elif result_value == "FAIL":
                    fail_count += 1
            unknown_count = len(test_results) - pass_count - fail_count
            
            fig.add_trace(
                go.Pie(labels=['PASS', 'FAIL', 'UNKNOWN'], 
                      values=[pass_count, fail_count, unknown_count],
                      name='Result Summary'),
                row=2, col=2
            )
        
        # レイアウトを更新
        fig.update_layout(
            title_text="LPDDR Test Automation Dashboard",
            title_x=0.5,
            height=800,
            showlegend=True
        )
        
        # 保存
        if save_html:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            fig.write_html(filepath)
            logger.info(f"Interactive dashboard saved to: {filepath}")
            return filepath
        
        return ""
    
    def generate_summary_report(self, test_results: List[Any], 
                              eye_pattern_results: Dict[str, str]) -> str:
        """
        サマリーレポートを生成
        
        Args:
            test_results (List[Any]): テスト結果リスト
            eye_pattern_results (Dict[str, str]): アイパターン結果辞書
            
        Returns:
            str: レポートの内容
        """
        logger.info("Generating summary report")
        
        report = []
        report.append("=" * 60)
        report.append("LPDDR Test Automation Summary Report")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # テスト結果サマリー
        if test_results:
            report.append("TEST RESULTS SUMMARY:")
            report.append("-" * 30)
            
            pass_count = 0
            fail_count = 0
            for r in test_results:
                result = getattr(r, 'result', None)
                result_value = getattr(result, 'value', str(result)) if hasattr(result, 'value') else str(result)
                if result_value == "PASS":
                    pass_count += 1
                elif result_value == "FAIL":
                    fail_count += 1
            unknown_count = len(test_results) - pass_count - fail_count
            total_count = len(test_results)
            
            report.append(f"Total Tests: {total_count}")
            if total_count > 0:
                report.append(f"PASS: {pass_count} ({pass_count/total_count*100:.1f}%)")
                report.append(f"FAIL: {fail_count} ({fail_count/total_count*100:.1f}%)")
                report.append(f"UNKNOWN: {unknown_count} ({unknown_count/total_count*100:.1f}%)")
            else:
                report.append("PASS: 0 (0.0%)")
                report.append("FAIL: 0 (0.0%)")
                report.append("UNKNOWN: 0 (0.0%)")
            report.append("")
            
            # ステップ別サマリー
            step_summary = {}
            for result in test_results:
                step = getattr(result, 'step', None)
                step = getattr(step, 'value', str(step)) if hasattr(step, 'value') else str(step)
                if step not in step_summary:
                    step_summary[step] = {'total': 0, 'pass': 0, 'fail': 0}
                step_summary[step]['total'] += 1
                
                result_obj = getattr(result, 'result', None)
                result_value = getattr(result_obj, 'value', str(result_obj)) if hasattr(result_obj, 'value') else str(result_obj)
                if result_value == "PASS":
                    step_summary[step]['pass'] += 1
                elif result_value == "FAIL":
                    step_summary[step]['fail'] += 1
            
            report.append("STEP-BY-STEP SUMMARY:")
            report.append("-" * 30)
            for step, stats in step_summary.items():
                pass_rate = stats['pass'] / stats['total'] * 100 if stats['total'] > 0 else 0
                report.append(f"{step}: {stats['pass']}/{stats['total']} ({pass_rate:.1f}%)")
            report.append("")
        
        # アイパターン結果サマリー
        if eye_pattern_results:
            report.append("EYE PATTERN TEST SUMMARY:")
            report.append("-" * 30)
            
            tx_results = [r for k, r in eye_pattern_results.items() if 'tx_lane_' in k]
            rx_results = [r for k, r in eye_pattern_results.items() if 'rx_lane_' in k]
            
            tx_pass = sum(1 for r in tx_results if 'PASS' in r.upper())
            rx_pass = sum(1 for r in rx_results if 'PASS' in r.upper())
            
            tx_rate = tx_pass/len(tx_results)*100 if len(tx_results) > 0 else 0
            rx_rate = rx_pass/len(rx_results)*100 if len(rx_results) > 0 else 0
            report.append(f"TX Eye Pattern Tests: {tx_pass}/{len(tx_results)} ({tx_rate:.1f}%)")
            report.append(f"RX Eye Pattern Tests: {rx_pass}/{len(rx_results)} ({rx_rate:.1f}%)")
            report.append("")
        
        # 推奨事項
        report.append("RECOMMENDATIONS:")
        report.append("-" * 30)
        
        if test_results:
            pass_rate = pass_count / total_count * 100 if total_count > 0 else 0
            
            if pass_rate >= 90:
                report.append("✓ Excellent test results. Memory interface is functioning properly.")
            elif pass_rate >= 70:
                report.append("⚠ Good test results with some issues. Consider signal optimization.")
            elif pass_rate >= 50:
                report.append("⚠ Moderate test results. Signal integrity issues detected.")
            else:
                report.append("✗ Poor test results. Significant signal integrity problems.")
        
        if eye_pattern_results:
            tx_pass_rate = tx_pass / len(tx_results) * 100 if tx_results else 0
            rx_pass_rate = rx_pass / len(rx_results) * 100 if rx_results else 0
            
            if tx_pass_rate < 80 or rx_pass_rate < 80:
                report.append("• Consider adjusting signal timing and voltage parameters")
                report.append("• Check for electromagnetic interference (EMI) issues")
                report.append("• Verify PCB routing and impedance matching")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def export_all_visualizations(self, test_results: List[Any], 
                                eye_pattern_results: Dict[str, str]) -> Dict[str, str]:
        """
        すべてのビジュアライゼーションをエクスポート
        
        Args:
            test_results (List[Any]): テスト結果リスト
            eye_pattern_results (Dict[str, str]): アイパターン結果辞書
            
        Returns:
            Dict[str, str]: エクスポートされたファイルのパス辞書
        """
        logger.info("Exporting all visualizations")
        
        exported_files = {}
        
        # アイパターン可視化
        if eye_pattern_results:
            eye_pattern_file = self.visualize_eye_pattern_results(
                eye_pattern_results, save_plot=True, show_plot=False)
            if eye_pattern_file:
                exported_files['eye_pattern'] = eye_pattern_file
        
        # タイムライン可視化
        if test_results:
            timeline_file = self.visualize_test_timeline(
                test_results, save_plot=True, show_plot=False)
            if timeline_file:
                exported_files['timeline'] = timeline_file
        
        # インタラクティブダッシュボード
        dashboard_file = self.create_interactive_dashboard(
            test_results, eye_pattern_results, save_html=True)
        if dashboard_file:
            exported_files['dashboard'] = dashboard_file
        
        # サマリーレポート
        report_content = self.generate_summary_report(test_results, eye_pattern_results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"summary_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        exported_files['summary_report'] = report_file
        
        logger.info(f"Exported {len(exported_files)} visualization files")
        return exported_files
    
    def plot_test_results(self, test_results: List[Any], 
                         save_plot: bool = True, show_plot: bool = False) -> str:
        """
        テスト結果の統合可視化（統一されたデータ構造を使用）
        
        Args:
            test_results (List[Any]): テスト結果リスト
            save_plot (bool): プロットを保存するか
            show_plot (bool): プロットを表示するか
            
        Returns:
            str: 保存されたファイルパス
        """
        logger.info("Creating comprehensive test results visualization with unified data structure")
        
        try:
            # 統一されたデータ構造に変換
            unified_data = self.convert_to_unified_data(test_results, self.eye_pattern_results)
            
            # 1. アイパターン結果の可視化
            if unified_data.eye_pattern_results:
                eye_pattern_file = self.visualize_eye_pattern_results(
                    unified_data.eye_pattern_results, 
                    save_plot=True, 
                    show_plot=False
                )
                logger.info(f"Eye pattern visualization saved: {eye_pattern_file}")
            
            # 2. テストタイムラインの可視化（統一データ使用）
            timeline_file = self.visualize_test_timeline_unified(
                unified_data, 
                save_plot=True, 
                show_plot=False
            )
            logger.info(f"Timeline visualization saved: {timeline_file}")
            
            # 3. インタラクティブダッシュボードの生成（統一データ使用）
            dashboard_file = self.create_interactive_dashboard_unified(
                unified_data,
                save_html=True
            )
            logger.info(f"Interactive dashboard saved: {dashboard_file}")
            
            # 4. サマリーレポートの生成（統一データ使用）
            report_file = self.generate_summary_report_unified(unified_data)
            logger.info(f"Summary report saved: {report_file}")
            
            # 5. 統合結果の表示
            if show_plot:
                # メインの統合プロットを作成
                fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
                
                # サブプロット1: テスト結果サマリー
                self._plot_test_summary_unified(ax1, unified_data)
                
                # サブプロット2: 周波数別結果
                self._plot_frequency_results_unified(ax2, unified_data)
                
                # サブプロット3: パターン別結果
                self._plot_pattern_results_unified(ax3, unified_data)
                
                # サブプロット4: 統計情報
                self._plot_statistics_unified(ax4, unified_data)
                
                plt.suptitle('LPDDR Test Results - Comprehensive Analysis (Unified)', 
                           fontsize=16, fontweight='bold')
                plt.tight_layout()
                
                if save_plot:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"comprehensive_test_results_unified_{timestamp}.png"
                    filepath = os.path.join(self.output_dir, filename)
                    plt.savefig(filepath, dpi=300, bbox_inches='tight')
                    logger.info(f"Comprehensive visualization saved: {filepath}")
                    return filepath
                else:
                    plt.show()
                    return ""
            
            return dashboard_file  # メインの出力としてダッシュボードを返す
            
        except Exception as e:
            logger.error(f"Failed to create comprehensive visualization: {e}")
            raise
    
    def _plot_test_summary(self, ax, test_results: List[Any]):
        """テスト結果サマリーのプロット"""
        try:
            # 結果の集計
            pass_count = sum(1 for result in test_results if hasattr(result, 'result') and result.result == 'PASS')
            fail_count = sum(1 for result in test_results if hasattr(result, 'result') and result.result == 'FAIL')
            unknown_count = len(test_results) - pass_count - fail_count
            
            labels = ['PASS', 'FAIL', 'UNKNOWN']
            sizes = [pass_count, fail_count, unknown_count]
            colors = ['#2ecc71', '#e74c3c', '#f39c12']
            
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title('Test Results Summary', fontweight='bold')
            
        except Exception as e:
            logger.warning(f"Failed to plot test summary: {e}")
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_frequency_results(self, ax, test_results: List[Any]):
        """周波数別結果のプロット"""
        try:
            frequencies = {}
            for result in test_results:
                if hasattr(result, 'frequency'):
                    freq = result.frequency
                    if freq not in frequencies:
                        frequencies[freq] = {'PASS': 0, 'FAIL': 0, 'UNKNOWN': 0}
                    status = getattr(result, 'result', 'UNKNOWN')
                    frequencies[freq][status] += 1
            
            if frequencies:
                freq_labels = list(frequencies.keys())
                pass_counts = [frequencies[f]['PASS'] for f in freq_labels]
                fail_counts = [frequencies[f]['FAIL'] for f in freq_labels]
                
                x = range(len(freq_labels))
                width = 0.35
                
                ax.bar([i - width/2 for i in x], pass_counts, width, label='PASS', color='#2ecc71')
                ax.bar([i + width/2 for i in x], fail_counts, width, label='FAIL', color='#e74c3c')
                
                ax.set_xlabel('Frequency (MHz)')
                ax.set_ylabel('Test Count')
                ax.set_title('Results by Frequency', fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(freq_labels)
                ax.legend()
            else:
                ax.text(0.5, 0.5, 'No frequency data available', ha='center', va='center', transform=ax.transAxes)
                
        except Exception as e:
            logger.warning(f"Failed to plot frequency results: {e}")
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_pattern_results(self, ax, test_results: List[Any]):
        """パターン別結果のプロット"""
        try:
            patterns = {}
            for result in test_results:
                if hasattr(result, 'pattern'):
                    pattern = result.pattern
                    if pattern not in patterns:
                        patterns[pattern] = {'PASS': 0, 'FAIL': 0, 'UNKNOWN': 0}
                    status = getattr(result, 'result', 'UNKNOWN')
                    patterns[pattern][status] += 1
            
            if patterns:
                pattern_labels = [f"Pattern {p}" for p in patterns.keys()]
                pass_counts = [patterns[p]['PASS'] for p in patterns.keys()]
                fail_counts = [patterns[p]['FAIL'] for p in patterns.keys()]
                
                x = range(len(pattern_labels))
                width = 0.35
                
                ax.bar([i - width/2 for i in x], pass_counts, width, label='PASS', color='#2ecc71')
                ax.bar([i + width/2 for i in x], fail_counts, width, label='FAIL', color='#e74c3c')
                
                ax.set_xlabel('Test Pattern')
                ax.set_ylabel('Test Count')
                ax.set_title('Results by Pattern', fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(pattern_labels)
                ax.legend()
            else:
                ax.text(0.5, 0.5, 'No pattern data available', ha='center', va='center', transform=ax.transAxes)
                
        except Exception as e:
            logger.warning(f"Failed to plot pattern results: {e}")
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_statistics(self, ax, test_results: List[Any]):
        """統計情報のプロット"""
        try:
            # 基本的な統計情報を表示
            total_tests = len(test_results)
            if total_tests == 0:
                ax.text(0.5, 0.5, 'No test results available', ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Test Statistics', fontweight='bold')
                ax.axis('off')
                return
                
            pass_count = sum(1 for result in test_results if hasattr(result, 'result') and result.result == 'PASS')
            fail_count = sum(1 for result in test_results if hasattr(result, 'result') and result.result == 'FAIL')
            pass_rate = (pass_count / total_tests * 100) if total_tests > 0 else 0
            
            stats_text = f"""
            Total Tests: {total_tests}
            PASS: {pass_count} ({pass_rate:.1f}%)
            FAIL: {fail_count}
            
            Success Rate: {pass_rate:.1f}%
            """
            
            ax.text(0.1, 0.5, stats_text, transform=ax.transAxes, fontsize=12,
                   verticalalignment='center', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
            ax.set_title('Test Statistics', fontweight='bold')
            ax.axis('off')
            
        except Exception as e:
            logger.warning(f"Failed to plot statistics: {e}")
            ax.text(0.5, 0.5, 'No statistics available', ha='center', va='center', transform=ax.transAxes)
    
    # 統一されたデータ構造を使用する新しい可視化メソッド
    def visualize_test_timeline_unified(self, unified_data: VisualizationData, 
                                      save_plot: bool = True, show_plot: bool = False) -> str:
        """統一されたデータ構造を使用したテストタイムライン可視化"""
        try:
            if not unified_data.test_results:
                logger.warning("No test results to visualize")
                return ""
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # タイムラインの作成
            timestamps = [datetime.fromtimestamp(r.timestamp) for r in unified_data.test_results]
            results = [r.result for r in unified_data.test_results]
            test_types = [r.test_type for r in unified_data.test_results]
            
            # 色分け
            colors = {'PASS': '#2ecc71', 'FAIL': '#e74c3c', 'UNKNOWN': '#f39c12'}
            markers = {'memory': 'o', 'eye_pattern': 's', 'diagnostics': '^'}
            
            for i, (timestamp, result, test_type) in enumerate(zip(timestamps, results, test_types)):
                color = colors.get(result, '#95a5a6')
                marker = markers.get(test_type, 'o')
                ax.scatter(timestamp, i, c=color, marker=marker, s=100, alpha=0.7)
            
            ax.set_xlabel('Time')
            ax.set_ylabel('Test Index')
            ax.set_title('Test Timeline (Unified Data Structure)')
            ax.grid(True, alpha=0.3)
            
            # 凡例
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#2ecc71', label='PASS'),
                Patch(facecolor='#e74c3c', label='FAIL'),
                Patch(facecolor='#f39c12', label='UNKNOWN')
            ]
            ax.legend(handles=legend_elements, loc='upper right')
            
            if save_plot:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"test_timeline_unified_{timestamp}.png"
                filepath = os.path.join(self.output_dir, filename)
                plt.savefig(filepath, dpi=300, bbox_inches='tight')
                logger.info(f"Unified timeline visualization saved: {filepath}")
                return filepath
            
            if show_plot:
                plt.show()
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to create unified timeline visualization: {e}")
            return ""
    
    def create_interactive_dashboard_unified(self, unified_data: VisualizationData, 
                                           save_html: bool = True) -> str:
        """統一されたデータ構造を使用したインタラクティブダッシュボード"""
        try:
            if not unified_data.test_results:
                logger.warning("No test results for dashboard")
                return ""
            
            # サブプロットの作成
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Test Results Summary', 'Quality Score Distribution', 
                              'Test Types Breakdown', 'Frequency Analysis'),
                specs=[[{"type": "pie"}, {"type": "histogram"}],
                       [{"type": "bar"}, {"type": "bar"}]]
            )
            
            # 1. テスト結果サマリー（円グラフ）
            result_counts = {}
            for result in unified_data.test_results:
                result_counts[result.result] = result_counts.get(result.result, 0) + 1
            
            fig.add_trace(
                go.Pie(labels=list(result_counts.keys()), 
                      values=list(result_counts.values()),
                      name="Test Results"),
                row=1, col=1
            )
            
            # 2. 品質スコア分布（ヒストグラム）
            quality_scores = [r.quality_score for r in unified_data.test_results if r.quality_score > 0]
            if quality_scores:
                fig.add_trace(
                    go.Histogram(x=quality_scores, name="Quality Scores"),
                    row=1, col=2
                )
            
            # 3. テストタイプ別結果（棒グラフ）
            test_type_stats = unified_data.summary_stats.get('test_types', {})
            if test_type_stats:
                types = list(test_type_stats.keys())
                pass_counts = [test_type_stats[t]['pass'] for t in types]
                fail_counts = [test_type_stats[t]['fail'] for t in types]
                
                fig.add_trace(
                    go.Bar(x=types, y=pass_counts, name="PASS", marker_color='#2ecc71'),
                    row=2, col=1
                )
                fig.add_trace(
                    go.Bar(x=types, y=fail_counts, name="FAIL", marker_color='#e74c3c'),
                    row=2, col=1
                )
            
            # 4. 周波数分析（棒グラフ）
            freq_stats = unified_data.summary_stats.get('frequencies', {})
            if freq_stats:
                frequencies = list(freq_stats.keys())
                pass_rates = [freq_stats[f]['pass'] / freq_stats[f]['total'] * 100 
                             for f in frequencies]
                
                fig.add_trace(
                    go.Bar(x=[f"{f}MHz" for f in frequencies], y=pass_rates, 
                          name="Pass Rate (%)", marker_color='#3498db'),
                    row=2, col=2
                )
            
            fig.update_layout(
                title_text="LPDDR Test Results Dashboard (Unified Data Structure)",
                showlegend=True,
                height=800
            )
            
            if save_html:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"dashboard_unified_{timestamp}.html"
                filepath = os.path.join(self.output_dir, filename)
                fig.write_html(filepath)
                logger.info(f"Unified dashboard saved: {filepath}")
                return filepath
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to create unified dashboard: {e}")
            return ""
    
    def generate_summary_report_unified(self, unified_data: VisualizationData) -> str:
        """統一されたデータ構造を使用したサマリーレポート生成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_report_unified_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("LPDDR Test Results Summary Report (Unified Data Structure)\n")
                f.write("=" * 60 + "\n\n")
                
                # 基本統計
                stats = unified_data.summary_stats
                f.write(f"Total Tests: {stats.get('total_tests', 0)}\n")
                f.write(f"PASS: {stats.get('pass_count', 0)} ({stats.get('pass_rate', 0):.1f}%)\n")
                f.write(f"FAIL: {stats.get('fail_count', 0)}\n")
                f.write(f"Average Quality Score: {stats.get('average_quality', 0):.2f}\n\n")
                
                # テストタイプ別統計
                f.write("Test Types Summary:\n")
                f.write("-" * 30 + "\n")
                for test_type, type_stats in stats.get('test_types', {}).items():
                    total = type_stats['total']
                    pass_count = type_stats['pass']
                    pass_rate = (pass_count / total * 100) if total > 0 else 0
                    f.write(f"{test_type}: {pass_count}/{total} ({pass_rate:.1f}%)\n")
                
                f.write("\n")
                
                # 周波数別統計
                f.write("Frequency Analysis:\n")
                f.write("-" * 30 + "\n")
                for freq, freq_stats in stats.get('frequencies', {}).items():
                    total = freq_stats['total']
                    pass_count = freq_stats['pass']
                    pass_rate = (pass_count / total * 100) if total > 0 else 0
                    f.write(f"{freq}MHz: {pass_count}/{total} ({pass_rate:.1f}%)\n")
                
                f.write("\n")
                
                # 詳細結果
                f.write("Detailed Results:\n")
                f.write("-" * 30 + "\n")
                for result in unified_data.test_results:
                    f.write(f"ID: {result.test_id}\n")
                    f.write(f"  Type: {result.test_type}\n")
                    f.write(f"  Frequency: {result.frequency}MHz\n")
                    f.write(f"  Pattern: {result.pattern}\n")
                    f.write(f"  Result: {result.result}\n")
                    f.write(f"  Quality Score: {result.quality_score:.2f}\n")
                    f.write(f"  Timestamp: {datetime.fromtimestamp(result.timestamp)}\n")
                    f.write("\n")
            
            logger.info(f"Unified summary report saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate unified summary report: {e}")
            return ""
    
    def _plot_test_summary_unified(self, ax, unified_data: VisualizationData):
        """統一データを使用したテスト結果サマリーのプロット"""
        try:
            stats = unified_data.summary_stats
            labels = ['PASS', 'FAIL']
            sizes = [stats.get('pass_count', 0), stats.get('fail_count', 0)]
            colors = ['#2ecc71', '#e74c3c']
            
            if sum(sizes) > 0:
                ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
            
            ax.set_title('Test Results Summary (Unified)', fontweight='bold')
            
        except Exception as e:
            logger.warning(f"Failed to plot unified test summary: {e}")
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_frequency_results_unified(self, ax, unified_data: VisualizationData):
        """統一データを使用した周波数別結果のプロット"""
        try:
            freq_stats = unified_data.summary_stats.get('frequencies', {})
            if freq_stats:
                frequencies = list(freq_stats.keys())
                pass_counts = [freq_stats[f]['pass'] for f in frequencies]
                fail_counts = [freq_stats[f]['fail'] for f in frequencies]
                
                x = range(len(frequencies))
                width = 0.35
                
                ax.bar([i - width/2 for i in x], pass_counts, width, label='PASS', color='#2ecc71')
                ax.bar([i + width/2 for i in x], fail_counts, width, label='FAIL', color='#e74c3c')
                
                ax.set_xlabel('Frequency (MHz)')
                ax.set_ylabel('Test Count')
                ax.set_title('Results by Frequency (Unified)', fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(frequencies)
                ax.legend()
            else:
                ax.text(0.5, 0.5, 'No frequency data available', ha='center', va='center', transform=ax.transAxes)
                
        except Exception as e:
            logger.warning(f"Failed to plot unified frequency results: {e}")
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_pattern_results_unified(self, ax, unified_data: VisualizationData):
        """統一データを使用したパターン別結果のプロット"""
        try:
            pattern_stats = unified_data.summary_stats.get('patterns', {})
            if pattern_stats:
                patterns = list(pattern_stats.keys())
                pass_counts = [pattern_stats[p]['pass'] for p in patterns]
                fail_counts = [pattern_stats[p]['fail'] for p in patterns]
                
                x = range(len(patterns))
                width = 0.35
                
                ax.bar([i - width/2 for i in x], pass_counts, width, label='PASS', color='#2ecc71')
                ax.bar([i + width/2 for i in x], fail_counts, width, label='FAIL', color='#e74c3c')
                
                ax.set_xlabel('Test Pattern')
                ax.set_ylabel('Test Count')
                ax.set_title('Results by Pattern (Unified)', fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels([f"Pattern {p}" for p in patterns])
                ax.legend()
            else:
                ax.text(0.5, 0.5, 'No pattern data available', ha='center', va='center', transform=ax.transAxes)
                
        except Exception as e:
            logger.warning(f"Failed to plot unified pattern results: {e}")
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_statistics_unified(self, ax, unified_data: VisualizationData):
        """統一データを使用した統計情報のプロット"""
        try:
            stats = unified_data.summary_stats
            total_tests = stats.get('total_tests', 0)
            
            if total_tests == 0:
                ax.text(0.5, 0.5, 'No test results available', ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Test Statistics (Unified)', fontweight='bold')
                ax.axis('off')
                return
            
            pass_count = stats.get('pass_count', 0)
            fail_count = stats.get('fail_count', 0)
            pass_rate = stats.get('pass_rate', 0)
            average_quality = stats.get('average_quality', 0)
            
            stats_text = f"""
            Total Tests: {total_tests}
            PASS: {pass_count} ({pass_rate:.1f}%)
            FAIL: {fail_count}
            Average Quality: {average_quality:.2f}
            
            Success Rate: {pass_rate:.1f}%
            """
            
            ax.text(0.1, 0.5, stats_text, transform=ax.transAxes, fontsize=12,
                   verticalalignment='center', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
            ax.set_title('Test Statistics (Unified)', fontweight='bold')
            ax.axis('off')
            
        except Exception as e:
            logger.warning(f"Failed to plot unified statistics: {e}")
            ax.text(0.5, 0.5, 'No statistics available', ha='center', va='center', transform=ax.transAxes)


def create_visualizer(output_dir: str = "visualization_output") -> LPDDRVisualizer:
    """
    ビジュアライザーのインスタンスを作成
    
    Args:
        output_dir (str): 出力ディレクトリ
        
    Returns:
        LPDDRVisualizer: ビジュアライザーインスタンス
    """
    return LPDDRVisualizer(output_dir)

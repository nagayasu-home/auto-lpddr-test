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

from constants import TestLimits, FileExtensions

# ログ設定
logger = logging.getLogger(__name__)

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
        self._ensure_output_dir()
        
        # スタイル設定
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def _ensure_output_dir(self):
        """出力ディレクトリを作成"""
        os.makedirs(self.output_dir, exist_ok=True)
        
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
        
        # 結果を解析
        for key, result in eye_pattern_results.items():
            try:
                if 'tx_lane_' in key:
                    parts = key.split('_')
                    lane = int(parts[2])
                    bit = int(parts[4])
                    tx_results[lane, bit] = 1 if 'PASS' in result.upper() else 0
                elif 'rx_lane_' in key:
                    parts = key.split('_')
                    lane = int(parts[2])
                    bit = int(parts[4])
                    rx_results[lane, bit] = 1 if 'PASS' in result.upper() else 0
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
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
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
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
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
            report.append(f"PASS: {pass_count} ({pass_count/total_count*100:.1f}%)")
            report.append(f"FAIL: {fail_count} ({fail_count/total_count*100:.1f}%)")
            report.append(f"UNKNOWN: {unknown_count} ({unknown_count/total_count*100:.1f}%)")
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
            
            report.append(f"TX Eye Pattern Tests: {tx_pass}/{len(tx_results)} ({tx_pass/len(tx_results)*100:.1f}%)")
            report.append(f"RX Eye Pattern Tests: {rx_pass}/{len(rx_results)} ({rx_pass/len(rx_results)*100:.1f}%)")
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


def create_visualizer(output_dir: str = "visualization_output") -> LPDDRVisualizer:
    """
    ビジュアライザーのインスタンスを作成
    
    Args:
        output_dir (str): 出力ディレクトリ
        
    Returns:
        LPDDRVisualizer: ビジュアライザーインスタンス
    """
    return LPDDRVisualizer(output_dir)

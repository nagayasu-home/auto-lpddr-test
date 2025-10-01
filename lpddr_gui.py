#!/usr/bin/env python3
"""
LPDDR Test Automation GUI
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import yaml
import os
from typing import Optional, Dict, Any

from lpddr_test_automation import LPDDRAutomation, TestConfig
from constants import (
    SerialSettings, TestPatterns, FrequencyMapping, GUIElements,
    ErrorMessages, SuccessMessages
)
from validators import ConfigValidator, StringValidator
from exceptions import ValidationError, ConfigurationError
from logger_config import get_test_logger
from visualization import LPDDRVisualizer

class LPDDRTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LPDDR Test Automation")
        self.root.geometry(f"{GUIElements.WINDOW_WIDTH.value}x{GUIElements.WINDOW_HEIGHT.value}")
        
        self.automation = None
        self.test_thread = None
        self.log_queue = queue.Queue()
        self.test_logger = get_test_logger()
        self.is_test_running = False
        self.test_progress = 0
        self.total_steps = 0
        self.visualizer = LPDDRVisualizer()
        
        self.setup_ui()
        self.load_default_config()
        
    def setup_ui(self):
        """UIをセットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 設定フレーム
        config_frame = ttk.LabelFrame(main_frame, text="接続設定", padding="5")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # シリアルポート設定
        ttk.Label(config_frame, text="シリアルポート:").grid(row=0, column=0, sticky=tk.W)
        self.port_var = tk.StringVar(value="/dev/ttyUSB0")
        port_combo = ttk.Combobox(config_frame, textvariable=self.port_var, width=15)
        port_combo['values'] = ("/dev/ttyUSB0", "/dev/ttyUSB1", "COM3", "COM4")
        port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(config_frame, text="ボーレート:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(config_frame, textvariable=self.baudrate_var, width=10)
        baudrate_combo['values'] = ("9600", "19200", "38400", "57600", "115200")
        baudrate_combo.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # テスト設定フレーム
        test_frame = ttk.LabelFrame(main_frame, text="テスト設定", padding="5")
        test_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 周波数選択
        ttk.Label(test_frame, text="テスト周波数:").grid(row=0, column=0, sticky=tk.W)
        self.freq_var = tk.StringVar(value="800,666")
        freq_entry = ttk.Entry(test_frame, textvariable=self.freq_var, width=20)
        freq_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # テストパターン選択
        ttk.Label(test_frame, text="テストパターン:").grid(row=1, column=0, sticky=tk.W)
        self.pattern_var = tk.StringVar(value="1,15")
        pattern_entry = ttk.Entry(test_frame, textvariable=self.pattern_var, width=20)
        pattern_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 制御ボタンフレーム
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="テスト開始", command=self.start_test)
        self.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="テスト停止", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Button(control_frame, text="設定保存", command=self.save_config).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="設定読み込み", command=self.load_config).grid(row=0, column=3, padx=(0, 5))
        
        # ビジュアライズボタン
        ttk.Button(control_frame, text="結果可視化", command=self.show_visualizations).grid(row=0, column=6, padx=(0, 5))
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            control_frame, 
            variable=self.progress_var, 
            maximum=GUIElements.PROGRESS_MAX.value,
            length=200
        )
        self.progress_bar.grid(row=0, column=4, padx=(10, 0))
        
        # ステータスラベル
        self.status_var = tk.StringVar(value="待機中")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=5, padx=(10, 0))
        
        # ログ表示フレーム
        log_frame = ttk.LabelFrame(main_frame, text="テストログ", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=GUIElements.LOG_HEIGHT.value, 
            width=GUIElements.LOG_WIDTH.value
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ログクリアボタン
        ttk.Button(log_frame, text="ログクリア", command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
        
        # 結果表示フレーム
        result_frame = ttk.LabelFrame(main_frame, text="テスト結果", padding="5")
        result_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.result_text = tk.Text(
            result_frame, 
            height=GUIElements.RESULT_HEIGHT.value, 
            width=GUIElements.RESULT_WIDTH.value
        )
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 結果エクスポートボタン
        ttk.Button(result_frame, text="結果エクスポート", command=self.export_results).grid(row=1, column=0, pady=(5, 0))
        
        # ビジュアライズエクスポートボタン
        ttk.Button(result_frame, text="可視化エクスポート", command=self.export_visualizations).grid(row=1, column=1, pady=(5, 0), padx=(5, 0))
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        
    def log_message(self, message: str, level: str = "INFO"):
        """ログメッセージを表示"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        
        self.log_text.insert(tk.END, f"{formatted_message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
        # ログレベルに応じて色分け（簡易版）
        if level == "ERROR":
            self.log_text.tag_add("error", f"end-2l", "end-1l")
            self.log_text.tag_config("error", foreground="red")
        elif level == "WARNING":
            self.log_text.tag_add("warning", f"end-2l", "end-1l")
            self.log_text.tag_config("warning", foreground="orange")
        elif level == "SUCCESS":
            self.log_text.tag_add("success", f"end-2l", "end-1l")
            self.log_text.tag_config("success", foreground="green")
    
    def clear_log(self):
        """ログをクリア"""
        self.log_text.delete(1.0, tk.END)
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """プログレスバーを更新"""
        if total > 0:
            progress = (current / total) * GUIElements.PROGRESS_MAX.value
            self.progress_var.set(progress)
        
        if message:
            self.status_var.set(message)
        
        self.root.update_idletasks()
    
    def validate_settings(self) -> bool:
        """設定の妥当性をチェック"""
        try:
            # ポートの検証
            StringValidator.validate_non_empty_string(self.port_var.get(), "ポート")
            
            # ボーレートの検証
            baudrate = int(self.baudrate_var.get())
            ConfigValidator.validate_baudrate(baudrate)
            
            # 周波数の検証
            freq_str = self.freq_var.get().strip()
            if not freq_str:
                raise ValidationError("周波数が設定されていません", field="frequencies")
            
            frequencies = [int(f.strip()) for f in freq_str.split(',')]
            ConfigValidator.validate_frequencies(frequencies)
            
            # パターンの検証
            pattern_str = self.pattern_var.get().strip()
            if not pattern_str:
                raise ValidationError("テストパターンが設定されていません", field="patterns")
            
            patterns = [int(p.strip()) for p in pattern_str.split(',')]
            ConfigValidator.validate_patterns(patterns)
            
            return True
            
        except (ValueError, ValidationError) as e:
            messagebox.showerror("設定エラー", f"設定値が無効です: {e}")
            return False
        except Exception as e:
            messagebox.showerror("設定エラー", f"予期しないエラー: {e}")
            return False
        
    def start_test(self):
        """テストを開始"""
        if self.is_test_running:
            messagebox.showwarning("警告", "テストが既に実行中です")
            return
        
        # 設定の検証
        if not self.validate_settings():
            return
        
        try:
            # 設定を取得
            config = TestConfig(
                port=self.port_var.get(),
                baudrate=int(self.baudrate_var.get()),
                timeout=30.0
            )
            
            # 周波数とパターンを解析
            frequencies = [int(f.strip()) for f in self.freq_var.get().split(',')]
            patterns = [int(p.strip()) for p in self.pattern_var.get().split(',')]
            
            # テスト進行状況の初期化
            self.total_steps = len(frequencies) * len(patterns) + 1  # +1 for diagnostics
            self.test_progress = 0
            self.is_test_running = True
            
            # テストを別スレッドで実行
            self.test_thread = threading.Thread(
                target=self.run_test_thread,
                args=(config, frequencies, patterns)
            )
            self.test_thread.daemon = True
            self.test_thread.start()
            
            # UI状態を更新
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("テスト実行中...")
            
            self.log_message("テストを開始しました", "INFO")
            
        except Exception as e:
            self.log_message(f"テスト開始に失敗しました: {e}", "ERROR")
            messagebox.showerror("エラー", f"テスト開始に失敗しました: {e}")
            self.is_test_running = False
            
    def run_test_thread(self, config, frequencies, patterns):
        """テスト実行スレッド"""
        try:
            self.automation = LPDDRAutomation(config)
            
            # 接続テスト
            self.log_queue.put(("接続を試行中...", "INFO"))
            self.update_progress(0, self.total_steps, "接続中...")
            
            if not self.automation.connect():
                self.log_queue.put((ErrorMessages.CONNECTION_FAILED.value, "ERROR"))
                return
                
            self.log_queue.put((SuccessMessages.CONNECTION_ESTABLISHED.value, "SUCCESS"))
            
            # 各周波数でテスト実行
            for i, frequency in enumerate(frequencies):
                self.log_queue.put((f"周波数 {frequency}MHz のテストを開始します", "INFO"))
                
                try:
                    results = self.automation.run_frequency_test(frequency)
                    
                    for pattern, result in results.items():
                        self.test_progress += 1
                        self.update_progress(self.test_progress, self.total_steps, f"{frequency}MHz パターン{pattern}")
                        
                        status = "SUCCESS" if result.value == "PASS" else "ERROR"
                        self.log_queue.put((f"{frequency}MHz {pattern}: {result.value}", status))
                        
                except Exception as e:
                    self.log_queue.put((f"周波数 {frequency}MHz のテストでエラー: {e}", "ERROR"))
            
            # 診断テスト実行
            self.log_queue.put(("診断テストを開始します", "INFO"))
            self.update_progress(self.test_progress, self.total_steps, "診断テスト実行中...")
            
            try:
                diag_result = self.automation.run_diagnostics_test()
                self.test_progress += 1
                self.update_progress(self.test_progress, self.total_steps, "診断テスト完了")
                
                status = "SUCCESS" if diag_result.result.value == "PASS" else "WARNING"
                self.log_queue.put((f"診断テスト結果: {diag_result.result.value}", status))
            except Exception as e:
                self.log_queue.put((f"診断テストでエラー: {e}", "ERROR"))
            
            # 最終レポート生成
            self.log_queue.put(("レポートを生成中...", "INFO"))
            self.generate_report()
            
        except Exception as e:
            self.log_queue.put((f"テスト実行中にエラーが発生しました: {e}", "ERROR"))
        finally:
            if self.automation:
                self.automation.disconnect()
            
            self.is_test_running = False
            self.log_queue.put(("テストが完了しました", "SUCCESS"))
            self.update_progress(self.total_steps, self.total_steps, "完了")
            
    def stop_test(self):
        """テストを停止"""
        if not self.is_test_running:
            return
        
        self.is_test_running = False
        
        if self.automation:
            self.automation.disconnect()
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("停止")
        self.log_message("テストが停止されました", "WARNING")
        
    def generate_report(self):
        """レポートを生成"""
        if not self.automation or not self.automation.test_results:
            return
            
        report = "=== LPDDR テストレポート ===\n\n"
        
        for result in self.automation.test_results:
            report += f"ステップ: {result.step.value}\n"
            report += f"周波数: {result.frequency}MHz\n"
            report += f"パターン: {result.pattern}\n"
            report += f"結果: {result.result.value}\n"
            report += f"メッセージ: {result.message}\n"
            report += "-" * 40 + "\n"
        
        # 総合判定
        memory_tests = [r for r in self.automation.test_results if r.step.value == "memory_test"]
        diag_tests = [r for r in self.automation.test_results if r.step.value == "diagnostics"]
        
        report += "\n=== 総合判定 ===\n"
        if any(r.result.value == "PASS" for r in memory_tests):
            report += "結果: メモリは正常に動作しています\n"
        elif any(r.result.value == "PASS" for r in diag_tests):
            report += "結果: メモリは動作している可能性がありますが不安定です\n"
        else:
            report += "結果: メモリが動作していません\n"
            
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, report)
        
    def save_config(self):
        """設定を保存"""
        # 設定の検証
        if not self.validate_settings():
            return
        
        try:
            config = {
                'serial': {
                    'port': self.port_var.get(),
                    'baudrate': int(self.baudrate_var.get())
                },
                'test': {
                    'frequencies': [int(f.strip()) for f in self.freq_var.get().split(',')],
                    'patterns': [int(p.strip()) for p in self.pattern_var.get().split(',')]
                }
            }
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".yaml",
                filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
                initialdir=os.getcwd()
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
                self.log_message(f"設定を保存しました: {filename}", "SUCCESS")
                messagebox.showinfo("保存完了", f"設定を {filename} に保存しました")
                
        except Exception as e:
            self.log_message(f"設定保存に失敗しました: {e}", "ERROR")
            messagebox.showerror("エラー", f"設定保存に失敗しました: {e}")
            
    def load_config(self):
        """設定を読み込み"""
        filename = filedialog.askopenfilename(
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 設定の適用
                self.port_var.set(config['serial']['port'])
                self.baudrate_var.set(str(config['serial']['baudrate']))
                self.freq_var.set(','.join(map(str, config['test']['frequencies'])))
                self.pattern_var.set(','.join(map(str, config['test']['patterns'])))
                
                self.log_message(f"設定を読み込みました: {filename}", "SUCCESS")
                messagebox.showinfo("読み込み完了", f"設定を {filename} から読み込みました")
                
            except Exception as e:
                self.log_message(f"設定読み込みに失敗しました: {e}", "ERROR")
                messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {e}")
    
    def load_default_config(self):
        """デフォルト設定を読み込み"""
        try:
            # デフォルト設定ファイルが存在する場合は読み込み
            default_config_path = "config.yaml"
            if os.path.exists(default_config_path):
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                self.port_var.set(config.get('serial', {}).get('port', '/dev/ttyUSB0'))
                self.baudrate_var.set(str(config.get('serial', {}).get('baudrate', 115200)))
                
                test_config = config.get('test', {})
                frequencies = test_config.get('frequencies', [800, 666])
                patterns = test_config.get('patterns', [1, 15])
                
                self.freq_var.set(','.join(map(str, frequencies)))
                self.pattern_var.set(','.join(map(str, patterns)))
                
                self.log_message("デフォルト設定を読み込みました", "INFO")
            else:
                # デフォルト値を使用
                self.port_var.set('/dev/ttyUSB0')
                self.baudrate_var.set('115200')
                self.freq_var.set('800,666')
                self.pattern_var.set('1,15')
                
        except Exception as e:
            self.log_message(f"デフォルト設定読み込みエラー: {e}", "WARNING")
            # フォールバック値
            self.port_var.set('/dev/ttyUSB0')
            self.baudrate_var.set('115200')
            self.freq_var.set('800,666')
            self.pattern_var.set('1,15')
    
    def export_results(self):
        """結果をエクスポート"""
        if not self.automation or not self.automation.test_results:
            messagebox.showwarning("警告", "エクスポートする結果がありません")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.get(1.0, tk.END))
                
                self.log_message(f"結果をエクスポートしました: {filename}", "SUCCESS")
                messagebox.showinfo("エクスポート完了", f"結果を {filename} に保存しました")
                
            except Exception as e:
                self.log_message(f"結果エクスポートに失敗しました: {e}", "ERROR")
                messagebox.showerror("エラー", f"結果エクスポートに失敗しました: {e}")
    
    def show_visualizations(self):
        """ビジュアライズ結果を表示"""
        if not self.automation or not self.automation.test_results:
            messagebox.showwarning("警告", "表示するテスト結果がありません")
            return
        
        try:
            # アイパターン結果がある場合は表示
            if hasattr(self.automation, 'eye_pattern_results') and self.automation.eye_pattern_results:
                self.visualizer.visualize_eye_pattern_results(
                    self.automation.eye_pattern_results, 
                    save_plot=True, 
                    show_plot=True
                )
            
            # タイムライン表示
            self.visualizer.visualize_test_timeline(
                self.automation.test_results,
                save_plot=True,
                show_plot=True
            )
            
            self.log_message("ビジュアライズ結果を表示しました", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"ビジュアライズ表示に失敗しました: {e}", "ERROR")
            messagebox.showerror("エラー", f"ビジュアライズ表示に失敗しました: {e}")
    
    def export_visualizations(self):
        """ビジュアライズ結果をエクスポート"""
        if not self.automation or not self.automation.test_results:
            messagebox.showwarning("警告", "エクスポートするテスト結果がありません")
            return
        
        try:
            # 出力ディレクトリを選択
            output_dir = filedialog.askdirectory(
                title="ビジュアライズ結果の保存先を選択",
                initialdir=os.getcwd()
            )
            
            if output_dir:
                # ビジュアライザーを新しいディレクトリで初期化
                visualizer = LPDDRVisualizer(output_dir)
                
                # アイパターン結果を取得
                eye_pattern_results = {}
                if hasattr(self.automation, 'eye_pattern_results'):
                    eye_pattern_results = self.automation.eye_pattern_results
                
                # すべてのビジュアライゼーションをエクスポート
                exported_files = visualizer.export_all_visualizations(
                    self.automation.test_results,
                    eye_pattern_results
                )
                
                # 結果を表示
                file_list = "\n".join([f"• {os.path.basename(path)}" for path in exported_files.values()])
                messagebox.showinfo(
                    "エクスポート完了", 
                    f"以下のファイルをエクスポートしました:\n\n{file_list}\n\n保存先: {output_dir}"
                )
                
                self.log_message(f"ビジュアライズ結果をエクスポートしました: {output_dir}", "SUCCESS")
                
        except Exception as e:
            self.log_message(f"ビジュアライズエクスポートに失敗しました: {e}", "ERROR")
            messagebox.showerror("エラー", f"ビジュアライズエクスポートに失敗しました: {e}")
                
    def check_log_queue(self):
        """ログキューをチェック"""
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    message, level = item
                    self.log_message(message, level)
                else:
                    # 後方互換性のため
                    self.log_message(str(item))
        except queue.Empty:
            pass
        
        # 定期的に再チェック
        self.root.after(GUIElements.QUEUE_CHECK_INTERVAL.value, self.check_log_queue)

def main():
    root = tk.Tk()
    app = LPDDRTestGUI(root)
    app.check_log_queue()  # ログキュー監視を開始
    root.mainloop()

if __name__ == "__main__":
    main()

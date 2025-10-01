#!/usr/bin/env python3
"""
LPDDR Test Automation GUI with Integrated Terminal
統合ターミナル機能付きLPDDRテスト自動化GUI
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import yaml
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from lpddr_test_automation import LPDDRAutomation, TestConfig
from constants import (
    SerialSettings, TestPatterns, FrequencyMapping, GUIElements,
    ErrorMessages, SuccessMessages
)
from validators import ConfigValidator, StringValidator
from exceptions import ValidationError, ConfigurationError
from logger_config import get_test_logger

# オプショナルインポート
try:
    from visualization import LPDDRVisualizer
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

try:
    from terminal_widget import TerminalWidget, TerminalWindow
    TERMINAL_AVAILABLE = True
except ImportError:
    TERMINAL_AVAILABLE = False


class LPDDRTestGUI:
    """LPDDRテスト自動化GUI（統合ターミナル機能付き）"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("LPDDR Test Automation")
        self.root.geometry(f"{GUIElements.WINDOW_WIDTH.value}x{GUIElements.WINDOW_HEIGHT.value}")
        
        # 基本変数
        self.automation = None
        self.test_thread = None
        self.log_queue = queue.Queue()
        self.test_logger = get_test_logger()
        self.is_test_running = False
        self.test_progress = 0
        self.total_steps = 0
        
        # オプショナル機能
        self.visualizer = LPDDRVisualizer() if VISUALIZATION_AVAILABLE else None
        self.terminal_window = None
        
        # UI変数
        self.port_var = tk.StringVar(value="/dev/ttyUSB0")
        self.baudrate_var = tk.StringVar(value="115200")
        self.freq_var = tk.StringVar(value="800,666")
        self.pattern_var = tk.StringVar(value="1,15")
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="待機中")
        
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
        port_combo = ttk.Combobox(config_frame, textvariable=self.port_var, width=15)
        port_combo['values'] = ("/dev/ttyUSB0", "/dev/ttyUSB1", "COM3", "COM4")
        port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(config_frame, text="ボーレート:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        baudrate_combo = ttk.Combobox(config_frame, textvariable=self.baudrate_var, width=10)
        baudrate_combo['values'] = ("9600", "19200", "38400", "57600", "115200")
        baudrate_combo.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # テスト設定フレーム
        test_frame = ttk.LabelFrame(main_frame, text="テスト設定", padding="5")
        test_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 周波数選択
        ttk.Label(test_frame, text="テスト周波数:").grid(row=0, column=0, sticky=tk.W)
        freq_entry = ttk.Entry(test_frame, textvariable=self.freq_var, width=20)
        freq_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # テストパターン選択
        ttk.Label(test_frame, text="テストパターン:").grid(row=1, column=0, sticky=tk.W)
        pattern_entry = ttk.Entry(test_frame, textvariable=self.pattern_var, width=20)
        pattern_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 制御ボタンフレーム
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # テスト制御ボタン
        self.start_button = ttk.Button(control_frame, text="テスト開始", command=self.start_test)
        self.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="テスト停止", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 5))
        
        # 設定ボタン
        ttk.Button(control_frame, text="設定保存", command=self.save_config).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="設定読み込み", command=self.load_config).grid(row=0, column=3, padx=(0, 5))
        
        # ターミナルボタン（利用可能な場合のみ）
        if TERMINAL_AVAILABLE:
            ttk.Button(control_frame, text="ターミナル", command=self.open_terminal).grid(row=0, column=4, padx=(0, 5))
        
        # ビジュアライズボタン（利用可能な場合のみ）
        if VISUALIZATION_AVAILABLE:
            ttk.Button(control_frame, text="結果可視化", command=self.show_visualizations).grid(row=0, column=5, padx=(0, 5))
        
        # プログレスバー
        self.progress_bar = ttk.Progressbar(
            control_frame, 
            variable=self.progress_var, 
            maximum=GUIElements.PROGRESS_MAX.value,
            length=200
        )
        self.progress_bar.grid(row=0, column=6, padx=(10, 0))
        
        # ステータスラベル
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=7, padx=(10, 0))
        
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
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        
        self.log_text.insert(tk.END, f"{formatted_message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
        # ログレベルに応じて色分け
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
            report += "結果: メモリは動作しているが不安定な可能性があります\n"
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
        """結果可視化を表示"""
        if not VISUALIZATION_AVAILABLE:
            messagebox.showwarning("警告", "可視化機能が利用できません")
            return
        
        if not self.automation or not self.automation.test_results:
            messagebox.showwarning("警告", "可視化する結果がありません")
            return
        
        try:
            self.visualizer.plot_test_results(self.automation.test_results)
            self.log_message("結果可視化を表示しました", "SUCCESS")
        except Exception as e:
            self.log_message(f"可視化表示に失敗しました: {e}", "ERROR")
            messagebox.showerror("エラー", f"可視化表示に失敗しました: {e}")
    
    def open_terminal(self):
        """ターミナルウィンドウを開く"""
        if not TERMINAL_AVAILABLE:
            messagebox.showwarning("警告", "ターミナル機能が利用できません")
            return
        
        if not self.terminal_window or not self.terminal_window.is_open():
            self.terminal_window = TerminalWindow(self.root, self.handle_terminal_command)
            self.terminal_window.show()
        else:
            self.terminal_window.focus()
    
    def handle_terminal_command(self, command: str) -> str:
        """ターミナルコマンドを処理"""
        parts = command.strip().split()
        if not parts:
            return ""
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        try:
            if cmd == "help":
                return self.get_terminal_help()
            elif cmd == "config":
                return self.handle_terminal_config(args)
            elif cmd == "connect":
                return self.handle_terminal_connect()
            elif cmd == "disconnect":
                return self.handle_terminal_disconnect()
            elif cmd == "test":
                return self.handle_terminal_test(args)
            elif cmd == "stop":
                return self.handle_terminal_stop()
            elif cmd == "status":
                return self.get_terminal_status()
            elif cmd == "log":
                return self.get_terminal_logs(args)
            elif cmd == "clear":
                return "Terminal cleared"
            else:
                return f"Unknown command: {cmd}. Type 'help' for available commands."
                
        except Exception as e:
            return f"Error: {e}"
    
    def get_terminal_help(self) -> str:
        """ターミナルヘルプを取得"""
        return """
LPDDR Test Automation Commands:

CONFIGURATION:
  config show                    - Show current configuration
  config port <port>             - Set serial port
  config baudrate <rate>         - Set baudrate
  config timeout <seconds>       - Set timeout
  config frequencies <freqs>     - Set test frequencies
  config patterns <patterns>     - Set test patterns

CONNECTION:
  connect                        - Connect to target board
  disconnect                     - Disconnect from target board

TESTING:
  test                           - Run full test sequence
  test freq <frequency>          - Run single frequency test
  test diag                      - Run diagnostics test only
  stop                           - Stop current test

INFORMATION:
  status                         - Show current status
  log [lines]                    - Show recent logs
  help                           - Show this help

Note: Commands are executed in the main GUI context.
        """
    
    def handle_terminal_config(self, args: List[str]) -> str:
        """ターミナル設定コマンドを処理"""
        if not args:
            return self.get_terminal_status()
            
        try:
            if args[0] == "show":
                return self.get_terminal_status()
            elif args[0] == "port" and len(args) > 1:
                self.port_var.set(args[1])
                return f"Port set to: {args[1]}"
            elif args[0] == "baudrate" and len(args) > 1:
                baudrate = int(args[1])
                ConfigValidator.validate_baudrate(baudrate)
                self.baudrate_var.set(str(baudrate))
                return f"Baudrate set to: {baudrate}"
            elif args[0] == "frequencies" and len(args) > 1:
                frequencies = [int(f.strip()) for f in args[1].split(',')]
                ConfigValidator.validate_frequencies(frequencies)
                self.freq_var.set(args[1])
                return f"Frequencies set to: {frequencies}"
            elif args[0] == "patterns" and len(args) > 1:
                patterns = [int(p.strip()) for p in args[1].split(',')]
                ConfigValidator.validate_patterns(patterns)
                self.pattern_var.set(args[1])
                return f"Patterns set to: {patterns}"
            else:
                return f"Unknown config command: {args[0]}"
                
        except (ValueError, ValidationError) as e:
            return f"Configuration error: {e}"
    
    def handle_terminal_connect(self) -> str:
        """ターミナル接続コマンドを処理"""
        if not self.validate_settings():
            return "Configuration error. Please check settings."
            
        try:
            config = TestConfig(
                port=self.port_var.get(),
                baudrate=int(self.baudrate_var.get()),
                timeout=30.0
            )
            
            self.automation = LPDDRAutomation(config)
            
            if self.automation.connect():
                return f"✓ Connected to {config.port} at {config.baudrate} baud"
            else:
                return f"✗ Failed to connect to {config.port}"
                
        except Exception as e:
            return f"Connection error: {e}"
    
    def handle_terminal_disconnect(self) -> str:
        """ターミナル切断コマンドを処理"""
        if self.automation:
            self.automation.disconnect()
            return "Disconnected from target board"
        else:
            return "Not connected"
    
    def handle_terminal_test(self, args: List[str]) -> str:
        """ターミナルテストコマンドを処理"""
        if not self.automation or not self.automation.serial_conn or not self.automation.serial_conn.is_open:
            return "Error: Not connected to target board. Use 'connect' command first."
            
        if self.is_test_running:
            return "Error: Test is already running. Use 'stop' command to stop current test."
            
        if not args:
            # フルテストシーケンスを開始
            self.start_test()
            return "Full test sequence started. Check main GUI for progress."
        elif args[0] == "freq" and len(args) > 1:
            try:
                frequency = int(args[1])
                # 単一周波数テストを開始
                self.start_single_frequency_test(frequency)
                return f"Single frequency test started: {frequency}MHz"
            except ValueError:
                return "Error: Invalid frequency value"
        elif args[0] == "diag":
            # 診断テストを開始
            self.start_diagnostics_test()
            return "Diagnostics test started"
        else:
            return f"Unknown test command: {args[0]}"
    
    def handle_terminal_stop(self) -> str:
        """ターミナル停止コマンドを処理"""
        if self.is_test_running:
            self.stop_test()
            return "Test stopped"
        else:
            return "No test is currently running"
    
    def get_terminal_status(self) -> str:
        """ターミナルステータスを取得"""
        status = []
        status.append("LPDDR Test Automation Status")
        status.append("=" * 40)
        
        # 接続ステータス
        if self.automation and self.automation.serial_conn and self.automation.serial_conn.is_open:
            status.append(f"Connection: ✓ Connected to {self.port_var.get()}")
        else:
            status.append("Connection: ✗ Disconnected")
        
        # テストステータス
        if self.is_test_running:
            status.append("Test Status: 🔄 Running")
        else:
            status.append("Test Status: ⏸ Ready")
        
        # 設定情報
        status.append(f"Port: {self.port_var.get()}")
        status.append(f"Baudrate: {self.baudrate_var.get()}")
        status.append(f"Frequencies: {self.freq_var.get()}")
        status.append(f"Patterns: {self.pattern_var.get()}")
        
        return "\n".join(status)
    
    def get_terminal_logs(self, args: List[str]) -> str:
        """ターミナルログを取得"""
        lines = 20
        if args and args[0].isdigit():
            lines = int(args[0])
            
        log_file = "logs/lpddr_test.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    return "".join(recent_lines)
            except Exception as e:
                return f"Error reading log file: {e}"
        else:
            return "No log file found"
    
    def start_single_frequency_test(self, frequency: int):
        """単一周波数テストを開始"""
        if not self.validate_settings():
            return
            
        try:
            config = TestConfig(
                port=self.port_var.get(),
                baudrate=int(self.baudrate_var.get()),
                timeout=30.0
            )
            
            frequencies = [frequency]
            patterns = [int(p.strip()) for p in self.pattern_var.get().split(',')]
            
            self.total_steps = len(patterns)
            self.test_progress = 0
            self.is_test_running = True
            
            self.test_thread = threading.Thread(
                target=self.run_test_thread,
                args=(config, frequencies, patterns)
            )
            self.test_thread.daemon = True
            self.test_thread.start()
            
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Single frequency test running...")
            
        except Exception as e:
            self.log_message(f"Single frequency test start failed: {e}", "ERROR")
    
    def start_diagnostics_test(self):
        """診断テストを開始"""
        if not self.automation or not self.automation.serial_conn or not self.automation.serial_conn.is_open:
            self.log_message("Not connected to target board", "ERROR")
            return
            
        self.is_test_running = True
        self.status_var.set("Diagnostics test running...")
        
        def diag_thread():
            try:
                self.log_queue.put(("診断テストを開始します", "INFO"))
                diag_result = self.automation.run_diagnostics_test()
                status = "SUCCESS" if diag_result.result.value == "PASS" else "ERROR"
                self.log_queue.put((f"診断テスト結果: {diag_result.result.value}", status))
                
            except Exception as e:
                self.log_queue.put((f"診断テストでエラー: {e}", "ERROR"))
            finally:
                self.is_test_running = False
                self.log_queue.put(("診断テストが完了しました", "SUCCESS"))
                self.update_progress(1, 1, "完了")
        
        self.test_thread = threading.Thread(target=diag_thread, daemon=True)
        self.test_thread.start()
    
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
    """メイン関数"""
    root = tk.Tk()
    app = LPDDRTestGUI(root)
    app.check_log_queue()  # ログキュー監視を開始
    root.mainloop()


if __name__ == "__main__":
    main()

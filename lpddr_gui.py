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
import time
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
        self.test_start_time = None
        self.last_input_time = None
        self.current_elapsed_time = 0
        self.elapsed_timer = None
        
        # オプショナル機能
        self.visualizer = LPDDRVisualizer() if VISUALIZATION_AVAILABLE else None
        self.terminal_window = None
        
        # UI変数
        self.port_var = tk.StringVar(value="/dev/ttyUSB0")
        self.baudrate_var = tk.StringVar(value="115200")
        self.freq_var = tk.StringVar(value="800")
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
        
        # 接続確認ボタン
        self.connect_button = ttk.Button(control_frame, text="接続確認", command=self.check_connection)
        self.connect_button.grid(row=0, column=0, padx=(0, 5))
        
        # テスト制御ボタン
        self.start_button = ttk.Button(control_frame, text="テスト開始", command=self.start_test)
        self.start_button.grid(row=0, column=1, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="テスト停止", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=(0, 5))
        
        # 設定ボタン
        ttk.Button(control_frame, text="設定保存", command=self.save_config).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(control_frame, text="設定読み込み", command=self.load_config).grid(row=0, column=4, padx=(0, 5))
        
        # ターミナルボタン（利用可能な場合のみ）
        if TERMINAL_AVAILABLE:
            ttk.Button(control_frame, text="ターミナル", command=self.open_terminal).grid(row=0, column=5, padx=(0, 5))
        
        # ビジュアライズボタン（利用可能な場合のみ）
        if VISUALIZATION_AVAILABLE:
            ttk.Button(control_frame, text="結果可視化", command=self.show_visualizations).grid(row=0, column=6, padx=(0, 5))
        
        # プログレスバー
        self.progress_bar = ttk.Progressbar(
            control_frame, 
            variable=self.progress_var, 
            maximum=GUIElements.PROGRESS_MAX.value,
            length=200
        )
        self.progress_bar.grid(row=0, column=7, padx=(10, 0))
        
        # ステータスラベル
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=8, padx=(10, 0))
        
        # 大きなフォントのステータス表示エリア
        status_display_frame = ttk.LabelFrame(main_frame, text="テスト状況", padding="10")
        status_display_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 経過時間表示（大きなフォント）
        self.elapsed_time_label = tk.Label(
            status_display_frame, 
            text="経過時間: 0秒", 
            font=("Arial", 16, "bold"),
            fg="blue"
        )
        self.elapsed_time_label.grid(row=0, column=0, padx=(0, 20))
        
        # 現在のテストパターン表示（大きなフォント）
        self.current_test_label = tk.Label(
            status_display_frame, 
            text="テスト状況: 待機中", 
            font=("Arial", 16, "bold"),
            fg="green"
        )
        self.current_test_label.grid(row=0, column=1)
        
        # ログ・結果表示フレーム（左右レイアウト）
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # ログ表示フレーム（左側）
        log_frame = ttk.LabelFrame(content_frame, text="テストログ", padding="5")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=GUIElements.LOG_HEIGHT.value, 
            width=GUIElements.LOG_WIDTH.value,
            maxundo=10000,  # undo履歴を増やす
            undo=True       # undo機能を有効にする
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ログクリアボタンとダウンロードボタン
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.grid(row=1, column=0, pady=(5, 0))
        
        ttk.Button(log_button_frame, text="ログクリア", command=self.clear_log).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(log_button_frame, text="テストログ保存", command=self.export_test_log).grid(row=0, column=1)
        
        # シリアルログ表示フレーム（右側）
        result_frame = ttk.LabelFrame(content_frame, text="シリアルログ", padding="5")
        result_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        self.result_text = scrolledtext.ScrolledText(
            result_frame, 
            height=GUIElements.RESULT_HEIGHT.value, 
            width=GUIElements.RESULT_WIDTH.value,
            maxundo=10000,  # undo履歴を増やす
            undo=True       # undo機能を有効にする
        )
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # シリアルログクリアボタンとダウンロードボタン
        serial_button_frame = ttk.Frame(result_frame)
        serial_button_frame.grid(row=1, column=0, pady=(5, 0))
        
        ttk.Button(serial_button_frame, text="シリアルログクリア", command=self.clear_results).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(serial_button_frame, text="シリアルログ保存", command=self.export_serial_log).grid(row=0, column=1)
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        content_frame.columnconfigure(0, weight=1)  # 左側（ログ）
        content_frame.columnconfigure(1, weight=1)  # 右側（結果）
        content_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
    def log_message(self, message: str, level: str = "INFO"):
        """ログメッセージを表示"""
        # メッセージが既にタイムスタンプ付きの場合はそのまま使用
        if message.startswith("["):
            formatted_message = message
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] [{level}] {message}"
        
        # シリアル通信ログは「テスト結果」エリアに表示
        if level == "SERIAL":
            self.result_text.insert(tk.END, f"{message}\n")
            self.result_text.see(tk.END)
            
            # シリアルログの行数制限（10000行を超えた場合は古いログを削除）
            lines = int(self.result_text.index('end-1c').split('.')[0])
            if lines > 10000:
                self.result_text.delete('1.0', '1000.0')
            
            # 入力要求時（Please Hit number key:で始まる）のタイマー制御
            if message.startswith("Please Hit number key:"):
                self.update_input_interval()  # 前回の入力要求からの経過時間を更新
        else:
            # その他のログは「テストログ」エリアに表示
            self.log_text.insert(tk.END, f"{formatted_message}\n")
            self.log_text.see(tk.END)
            
            # テストログの行数制限（5000行を超えた場合は古いログを削除）
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 5000:
                self.log_text.delete('1.0', '500.0')
        
        self.root.update_idletasks()
        
        # ログレベルに応じて色分け（テストログエリアのみ）
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
    
    def clear_results(self):
        """シリアルログをクリア"""
        self.result_text.delete(1.0, tk.END)
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """プログレスバーを更新"""
        if total > 0:
            progress = (current / total) * GUIElements.PROGRESS_MAX.value
            self.progress_var.set(progress)
            print(f"Progress updated: {current}/{total} = {progress}%")  # デバッグ用
            
            # プログレスバーを強制的に更新
            self.progress_bar.update()
        
        if message:
            # 経過時間がある場合は、経過時間を保持してメッセージを更新
            current_status = self.status_var.get()
            if "経過時間:" in current_status:
                # 経過時間部分を抽出
                parts = current_status.split(" - ", 1)
                if len(parts) > 1:
                    elapsed_part = parts[0]
                    self.status_var.set(f"{elapsed_part} - {message}")
                else:
                    self.status_var.set(message)
            else:
                self.status_var.set(message)
        
        # GUIを強制的に更新
        self.root.update_idletasks()
        self.root.update()
    
    def update_elapsed_time(self):
        """経過時間を更新（前回の入力要求からの経過時間）"""
        if self.last_input_time and self.is_test_running:
            elapsed = int(time.time() - self.last_input_time)
            self.current_elapsed_time = elapsed
            elapsed_text = f"経過時間: {elapsed}秒"
            
            # 大きなフォントの経過時間ラベルを更新
            self.elapsed_time_label.config(text=elapsed_text)
            
            # 現在のステータスから経過時間部分を除去
            current_status = self.status_var.get()
            if "経過時間:" in current_status:
                # 既存の経過時間部分を除去
                parts = current_status.split(" - ", 1)
                if len(parts) > 1:
                    current_status = parts[1]
                else:
                    current_status = ""
            
            # 新しいステータスを設定（経過時間を先頭に配置）
            if current_status:
                self.status_var.set(f"{elapsed_text} - {current_status}")
            else:
                self.status_var.set(elapsed_text)
            
            # 1秒後に再実行
            self.elapsed_timer = self.root.after(1000, self.update_elapsed_time)
    
    def start_input_timer(self):
        """入力要求時の経過時間タイマーを開始"""
        self.last_input_time = time.time()
        if not self.elapsed_timer:
            self.update_elapsed_time()
    
    def update_input_interval(self):
        """次の入力要求時の経過時間更新"""
        if self.last_input_time:
            # 前回の入力要求からの経過時間を計算
            interval = int(time.time() - self.last_input_time)
            self.current_elapsed_time = interval
            
            # 経過時間を表示
            elapsed_text = f"経過時間: {interval}秒"
            current_status = self.status_var.get()
            if "経過時間:" in current_status:
                parts = current_status.split(" - ", 1)
                if len(parts) > 1:
                    current_status = parts[1]
                else:
                    current_status = ""
            
            if current_status:
                self.status_var.set(f"{elapsed_text} - {current_status}")
            else:
                self.status_var.set(elapsed_text)
        
        # 新しい入力要求の時間を記録
        self.last_input_time = time.time()
    
    def stop_input_timer(self):
        """経過時間タイマーを停止"""
        if self.elapsed_timer:
            self.root.after_cancel(self.elapsed_timer)
            self.elapsed_timer = None
    
    def update_current_test_display(self, test_info: str):
        """現在のテストパターン表示を更新"""
        self.current_test_label.config(text=f"テスト状況: {test_info}")
    
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
            
            # 辞書形式の入力をチェック
            if pattern_str.startswith('{') or "'id'" in pattern_str:
                raise ValidationError(
                    "テストパターンは数値のみを入力してください。\n"
                    "例: 1,15 または 1 または 15\n"
                    "現在の入力: " + pattern_str[:50] + "...",
                    field="patterns"
                )
            
            try:
                patterns = [int(p.strip()) for p in pattern_str.split(',')]
                ConfigValidator.validate_patterns(patterns)
            except ValueError as ve:
                raise ValidationError(
                    f"テストパターンに無効な値が含まれています: {pattern_str}\n"
                    "正しい形式: 数値をカンマ区切りで入力 (例: 1,15)",
                    field="patterns"
                )
            
            return True
            
        except (ValueError, ValidationError) as e:
            messagebox.showerror("設定エラー", f"設定値が無効です: {e}")
            return False
        except Exception as e:
            messagebox.showerror("設定エラー", f"予期しないエラー: {e}")
            return False
    
    def validate_connection_settings(self) -> bool:
        """接続設定のみの妥当性をチェック（テストパターンは除外）"""
        try:
            # ポートの検証
            StringValidator.validate_non_empty_string(self.port_var.get(), "ポート")
            
            # ボーレートの検証
            baudrate = int(self.baudrate_var.get())
            ConfigValidator.validate_baudrate(baudrate)
            
            return True
            
        except (ValueError, ValidationError) as e:
            messagebox.showerror("接続設定エラー", f"接続設定が無効です: {e}")
            return False
        except Exception as e:
            messagebox.showerror("接続設定エラー", f"予期しないエラー: {e}")
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
            # シリアルログエリアをクリア
            self.clear_results()
            
            # テスト開始時間を記録
            self.test_start_time = time.time()
            
            # 設定を取得
            from lpddr_test_automation import EyePatternConfig
            eye_pattern_config = getattr(self, 'eye_pattern_config', {})
            eye_pattern = EyePatternConfig(
                default_lane=eye_pattern_config.get('default_lane', '5'),
                default_byte=eye_pattern_config.get('default_byte', '1'),
                diag_addr_low=eye_pattern_config.get('diag_addr_low', '0000'),
                continue_to_rx_after_tx=eye_pattern_config.get('continue_to_rx_after_tx', False),
                test_mode=eye_pattern_config.get('test_mode', 'tx_only'),
                diagnostics_mode=eye_pattern_config.get('diagnostics_mode', 'tx_eye_pattern')
            )
            
            config = TestConfig(
                port=self.port_var.get(),
                baudrate=int(self.baudrate_var.get()),
                timeout=30.0,
                enable_2d_training=getattr(self, 'enable_2d_training', False),
                enable_eye_pattern=getattr(self, 'enable_eye_pattern', False),
                eye_pattern=eye_pattern
            )
            
            # 周波数とパターンを解析
            freq_str = self.freq_var.get()
            print(f"DEBUG: freq_var.get() = '{freq_str}'")  # デバッグ用
            frequencies = [int(f.strip()) for f in freq_str.split(',')]
            patterns = [int(p.strip()) for p in self.pattern_var.get().split(',')]
            print(f"DEBUG: frequencies = {frequencies}")  # デバッグ用
            print(f"DEBUG: patterns = {patterns}")  # デバッグ用
            
            # テスト進行状況の初期化
            self.total_steps = len(frequencies) * len(patterns) + 1  # +1 for diagnostics
            self.test_progress = 0
            self.is_test_running = True
            
            # プログレスバーを初期化
            self.progress_var.set(0)
            self.progress_bar.update()
            print(f"Progress initialized: 0/{self.total_steps} = 0%")  # デバッグ用
            
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
            self.automation = LPDDRAutomation(config, gui_callback=self.log_message, gui_status_callback=self.update_current_test_display)
            
            # 接続テスト
            self.log_queue.put(("接続を試行中...", "INFO"))
            self.update_progress(0, self.total_steps, "接続中...")
            
            # 最初の入力要求時の経過時間タイマーを開始
            self.start_input_timer()
            
            if not self.automation.connect():
                self.log_queue.put((ErrorMessages.CONNECTION_FAILED.value, "ERROR"))
                return
                
            self.log_queue.put((SuccessMessages.CONNECTION_ESTABLISHED.value, "SUCCESS"))
            self.update_progress(0, self.total_steps, "接続完了")
            
            # 各周波数でテスト実行
            for i, frequency in enumerate(frequencies):
                self.log_queue.put((f"周波数 {frequency}MHz のテストを開始します", "INFO"))
                self.update_current_test_display(f"{frequency}MHz テスト開始")
                print(f"Starting frequency test: {frequency}MHz")  # デバッグ用
                
                try:
                    results = self.automation.run_frequency_test(frequency)
                    print(f"Frequency test completed: {frequency}MHz, results: {len(results)}")  # デバッグ用
                    
                    # 周波数テスト完了
                    self.log_queue.put((f"周波数 {frequency}MHz のテストが完了しました", "SUCCESS"))
                    
                    # 次の周波数がある場合、周波数選択メニューが表示される
                    if i < len(frequencies) - 1:
                        self.log_queue.put(("次の周波数のテストに移行します", "INFO"))
                        self.update_current_test_display("次の周波数に移行中...")
                        
                except Exception as e:
                    self.log_queue.put((f"周波数 {frequency}MHz のテストでエラー: {e}", "ERROR"))
                    print(f"Frequency test error: {frequency}MHz - {e}")  # デバッグ用
            
            # 診断テスト実行（設定に基づく）
            if getattr(self, 'require_diagnostics', True):
                self.log_queue.put(("診断テストを開始します", "INFO"))
                self.update_current_test_display("診断テスト実行中...")
                self.update_progress(self.test_progress, self.total_steps, "診断テスト実行中...")
                
                try:
                    diag_result = self.automation.run_diagnostics_test()
                    self.test_progress += 1
                    self.update_progress(self.test_progress, self.total_steps, "診断テスト完了")
                    self.update_current_test_display("診断テスト完了")
                    
                    status = "SUCCESS" if diag_result.result.value == "PASS" else "WARNING"
                    self.log_queue.put((f"診断テスト結果: {diag_result.result.value}", status))
                except Exception as e:
                    self.log_queue.put((f"診断テストでエラー: {e}", "ERROR"))
            else:
                self.log_queue.put(("診断テストはスキップされます", "INFO"))
                self.log_message("診断テストは設定により無効化されています", "INFO")
            
            # 最終レポート生成
            self.log_queue.put(("レポートを生成中...", "INFO"))
            self.update_current_test_display("レポート生成中...")
            self.generate_report()
            
        except Exception as e:
            self.log_queue.put((f"テスト実行中にエラーが発生しました: {e}", "ERROR"))
        finally:
            if self.automation:
                self.automation.disconnect()
            
            self.is_test_running = False
            self.log_queue.put(("テストが完了しました", "SUCCESS"))
            self.update_progress(self.total_steps, self.total_steps, "完了")
            self.update_current_test_display("テスト完了")
            
            # 経過時間タイマーを停止
            self.stop_input_timer()
    
    def stop_test(self):
        """テストを停止"""
        if not self.is_test_running:
            return
        
        self.is_test_running = False
        
        if self.automation:
            self.automation.disconnect()
        
        # 経過時間タイマーを停止
        self.stop_input_timer()
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("停止")
        self.update_current_test_display("テスト停止")
        self.log_message("テストが停止されました", "WARNING")
    
    def generate_report(self):
        """レポートを生成"""
        if not self.automation or not self.automation.test_results:
            return
            
        # レポートヘッダーをテストログに出力
        self.log_message("=== LPDDR テストレポート ===", "INFO")
        
        # 各テスト結果を個別に出力
        for result in self.automation.test_results:
            self.log_message(f"ステップ: {result.step.value}", "INFO")
            self.log_message(f"周波数: {result.frequency}MHz", "INFO")
            self.log_message(f"パターン: {result.pattern}", "INFO")
            self.log_message(f"結果: {result.result.value}", "INFO")
            self.log_message(f"メッセージ: {result.message}", "INFO")
            self.log_message("-" * 40, "INFO")
        
        # 総合判定
        memory_tests = [r for r in self.automation.test_results if r.step.value == "memory_test"]
        diag_tests = [r for r in self.automation.test_results if r.step.value == "diagnostics"]
        
        self.log_message("", "INFO")  # 空行
        self.log_message("=== 総合判定 ===", "INFO")
        
        if any(r.result.value == "PASS" for r in memory_tests):
            self.log_message("結果: メモリは正常に動作しています", "SUCCESS")
        elif any(r.result.value == "PASS" for r in diag_tests):
            self.log_message("結果: メモリは動作しているが不安定な可能性があります", "WARNING")
        else:
            self.log_message("結果: メモリが動作していません", "ERROR")
    
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
                
                # patternsが辞書のリストの場合はidを抽出
                patterns_config = config['test']['patterns']
                if isinstance(patterns_config, list) and patterns_config and isinstance(patterns_config[0], dict):
                    patterns = [p.get('id', 1) for p in patterns_config if 'id' in p]
                else:
                    patterns = patterns_config
                self.pattern_var.set(','.join(map(str, patterns)))
                
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
                self.log_message(f"設定ファイルを読み込み中: {default_config_path}", "INFO")
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                self.port_var.set(config.get('serial', {}).get('port', '/dev/ttyUSB0'))
                self.baudrate_var.set(str(config.get('serial', {}).get('baudrate', 115200)))
                
                test_config = config.get('test', {})
                frequencies = test_config.get('frequencies', [800])
                patterns_config = test_config.get('patterns', [1, 15])
                print(f"DEBUG: config.yaml frequencies = {frequencies}")  # デバッグ用
                
                # patternsが辞書のリストの場合はidを抽出
                if isinstance(patterns_config, list) and patterns_config and isinstance(patterns_config[0], dict):
                    patterns = [p.get('id', 1) for p in patterns_config if 'id' in p]
                else:
                    patterns = patterns_config
                
                freq_str = ','.join(map(str, frequencies))
                print(f"DEBUG: Setting freq_var to '{freq_str}' from config.yaml")  # デバッグ用
                self.freq_var.set(freq_str)
                self.pattern_var.set(','.join(map(str, patterns)))
                
                # 診断テスト設定を読み込み
                judgment_config = config.get('judgment', {})
                self.require_diagnostics = judgment_config.get('require_diagnostics', True)
                
                # 2Dトレーニングとアイパターンテスト設定を読み込み
                self.enable_2d_training = test_config.get('enable_2d_training', False)
                self.enable_eye_pattern = test_config.get('enable_eye_pattern', False)
                
                # アイパターンテストの詳細設定を読み込み
                eye_pattern_config = test_config.get('eye_pattern', {})
                self.eye_pattern_config = {
                    'default_lane': eye_pattern_config.get('default_lane', '5'),
                    'default_byte': eye_pattern_config.get('default_byte', '1'),
                    'diag_addr_low': eye_pattern_config.get('diag_addr_low', '0000'),
                    'continue_to_rx_after_tx': eye_pattern_config.get('continue_to_rx_after_tx', False),
                    'test_mode': eye_pattern_config.get('test_mode', 'tx_only'),
                    'diagnostics_mode': eye_pattern_config.get('diagnostics_mode', 'tx_eye_pattern')
                }
                
                self.log_message(f"デフォルト設定を読み込みました: {default_config_path}", "SUCCESS")
            else:
                # デフォルト値を使用
                self.log_message(f"設定ファイルが見つかりません: {default_config_path}", "WARNING")
                
                self.port_var.set('/dev/ttyUSB0')
                self.require_diagnostics = True  # デフォルトは診断テストを実行
                self.baudrate_var.set('115200')
                self.freq_var.set('800')
                self.pattern_var.set('1,15')
                
        except Exception as e:
            self.log_message(f"デフォルト設定読み込みエラー: {e}", "WARNING")
            # フォールバック値
            self.port_var.set('/dev/ttyUSB0')
            self.baudrate_var.set('115200')
            self.freq_var.set('800')
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

    def _get_timestamp_filename(self, prefix):
        """日時付きファイル名を生成"""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.txt"

    def export_test_log(self):
        """テストログをエクスポート"""
        log_content = self.log_text.get(1.0, tk.END).strip()
        if not log_content:
            messagebox.showwarning("警告", "エクスポートするテストログがありません")
            return
        
        default_filename = self._get_timestamp_filename("testlog")
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=os.getcwd(),
            initialfile=default_filename,
            title="テストログを保存"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                
                self.log_message(f"テストログをエクスポートしました: {filename}", "SUCCESS")
                messagebox.showinfo("エクスポート完了", f"テストログを {filename} に保存しました")
                
            except Exception as e:
                self.log_message(f"テストログエクスポートエラー: {e}", "ERROR")
                messagebox.showerror("エクスポートエラー", f"ファイルの保存に失敗しました: {e}")

    def export_serial_log(self):
        """シリアルログをエクスポート"""
        serial_content = self.result_text.get(1.0, tk.END).strip()
        if not serial_content:
            messagebox.showwarning("警告", "エクスポートするシリアルログがありません")
            return
        
        default_filename = self._get_timestamp_filename("seriallog")
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=os.getcwd(),
            initialfile=default_filename,
            title="シリアルログを保存"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(serial_content)
                
                self.log_message(f"シリアルログをエクスポートしました: {filename}", "SUCCESS")
                messagebox.showinfo("エクスポート完了", f"シリアルログを {filename} に保存しました")
                
            except Exception as e:
                self.log_message(f"シリアルログエクスポートエラー: {e}", "ERROR")
                messagebox.showerror("エクスポートエラー", f"ファイルの保存に失敗しました: {e}")
    
    def show_visualizations(self):
        """結果可視化を表示"""
        if not VISUALIZATION_AVAILABLE:
            messagebox.showwarning("警告", "可視化機能が利用できません")
            return
        
        if not self.automation:
            messagebox.showwarning("警告", "テストが実行されていません")
            return
        
        # テスト結果の確認（複数の形式に対応）
        test_results = []
        eye_pattern_results = {}
        
        # 1. 通常のテスト結果を確認
        if hasattr(self.automation, 'test_results') and self.automation.test_results:
            test_results = self.automation.test_results
        
        # 2. Eye Patternテスト結果を確認
        if hasattr(self.automation, 'eye_pattern_results') and self.automation.eye_pattern_results:
            eye_pattern_results = self.automation.eye_pattern_results
        
        # 3. 結果データが存在しない場合の処理
        if not test_results and not eye_pattern_results:
            messagebox.showwarning("警告", "可視化する結果がありません。\nテストを実行してから可視化してください。")
            return
        
        try:
            # ビジュアライザーにEye Pattern結果を設定
            if eye_pattern_results:
                self.visualizer.eye_pattern_results = eye_pattern_results
            
            # 可視化を実行
            result_file = self.visualizer.plot_test_results(test_results)
            self.log_message("結果可視化を表示しました", "SUCCESS")
            
            # 結果ファイルの情報を表示
            if result_file:
                self.log_message(f"可視化結果を保存しました: {result_file}", "INFO")
            
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
            
            self.automation = LPDDRAutomation(config, gui_callback=self.log_message, gui_status_callback=self.update_current_test_display)
            
            # 接続確認中のポップアップを表示
            self.show_connection_popup()
            
            if self.automation.connect():
                self.hide_connection_popup()
                return f"✓ Connected to {config.port} at {config.baudrate} baud"
            else:
                self.hide_connection_popup()
                return f"✗ Failed to connect to {config.port}"
                
        except Exception as e:
            self.hide_connection_popup()
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
            from lpddr_test_automation import EyePatternConfig
            eye_pattern_config = getattr(self, 'eye_pattern_config', {})
            eye_pattern = EyePatternConfig(
                default_lane=eye_pattern_config.get('default_lane', '5'),
                default_byte=eye_pattern_config.get('default_byte', '1'),
                diag_addr_low=eye_pattern_config.get('diag_addr_low', '0000'),
                continue_to_rx_after_tx=eye_pattern_config.get('continue_to_rx_after_tx', False),
                test_mode=eye_pattern_config.get('test_mode', 'tx_only'),
                diagnostics_mode=eye_pattern_config.get('diagnostics_mode', 'tx_eye_pattern')
            )
            
            config = TestConfig(
                port=self.port_var.get(),
                baudrate=int(self.baudrate_var.get()),
                timeout=30.0,
                enable_2d_training=getattr(self, 'enable_2d_training', False),
                enable_eye_pattern=getattr(self, 'enable_eye_pattern', False),
                eye_pattern=eye_pattern
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
    
    def show_connection_popup(self):
        """接続確認中のポップアップを表示"""
        self.connection_popup = tk.Toplevel(self.root)
        self.connection_popup.title("接続確認中")
        self.connection_popup.geometry("400x200")
        self.connection_popup.resizable(False, False)
        
        # 中央に配置
        self.connection_popup.transient(self.root)
        self.connection_popup.grab_set()
        
        # メインフレーム
        main_frame = ttk.Frame(self.connection_popup, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # アイコンとメッセージ
        icon_label = ttk.Label(main_frame, text="🔄", font=("Arial", 24))
        icon_label.pack(pady=(0, 10))
        
        message_label = ttk.Label(
            main_frame, 
            text="ターゲットデバイスとの接続を確認中...\n\n最大1分間お待ちください",
            font=("Arial", 12),
            justify=tk.CENTER
        )
        message_label.pack(pady=(0, 20))
        
        # プログレスバー
        self.connection_progress = ttk.Progressbar(
            main_frame, 
            mode='indeterminate',
            length=300
        )
        self.connection_progress.pack(pady=(0, 20))
        self.connection_progress.start()
        
        # キャンセルボタン
        cancel_button = ttk.Button(
            main_frame,
            text="キャンセル",
            command=self.cancel_connection
        )
        cancel_button.pack()
        
        # ウィンドウを中央に配置
        self.connection_popup.update_idletasks()
        x = (self.connection_popup.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.connection_popup.winfo_screenheight() // 2) - (200 // 2)
        self.connection_popup.geometry(f"400x200+{x}+{y}")
    
    def hide_connection_popup(self):
        """接続確認ポップアップを非表示"""
        if hasattr(self, 'connection_popup') and self.connection_popup:
            self.connection_popup.destroy()
            self.connection_popup = None
    
    def cancel_connection(self):
        """接続をキャンセル"""
        if hasattr(self, 'automation') and self.automation:
            self.automation.disconnect()
        self.hide_connection_popup()
        self.log_message("接続がキャンセルされました", "WARNING")
    
    def check_connection(self):
        """接続確認ボタンのハンドラー"""
        if not self.validate_connection_settings():
            self.log_message("設定エラー: 接続設定を確認してください", "ERROR")
            return
        
        # 接続確認中のポップアップを表示
        self.show_connection_popup()
        
        def connection_thread():
            try:
                from lpddr_test_automation import EyePatternConfig
                eye_pattern_config = getattr(self, 'eye_pattern_config', {})
                eye_pattern = EyePatternConfig(
                    default_lane=eye_pattern_config.get('default_lane', '5'),
                    default_byte=eye_pattern_config.get('default_byte', '1'),
                    diag_addr_low=eye_pattern_config.get('diag_addr_low', '0000'),
                    continue_to_rx_after_tx=eye_pattern_config.get('continue_to_rx_after_tx', False),
                    test_mode=eye_pattern_config.get('test_mode', 'tx_only'),
                    diagnostics_mode=eye_pattern_config.get('diagnostics_mode', 'tx_eye_pattern')
                )
                
                config = TestConfig(
                    port=self.port_var.get(),
                    baudrate=int(self.baudrate_var.get()),
                    timeout=30.0,
                    enable_2d_training=getattr(self, 'enable_2d_training', False),
                    enable_eye_pattern=getattr(self, 'enable_eye_pattern', False),
                    eye_pattern=eye_pattern
                )
                
                self.automation = LPDDRAutomation(config, gui_callback=self.log_message, gui_status_callback=self.update_current_test_display)
                
                self.log_message("接続テストを開始しています...", "INFO")
                connection_result = self.automation.connect()
                self.log_message(f"接続テスト結果: {connection_result}", "INFO")
                
                if connection_result:
                    self.hide_connection_popup()
                    self.log_message(f"✓ 接続確認成功: {config.port} ({config.baudrate} baud)", "SUCCESS")
                    self.log_message("ターゲットデバイスがLPDDRテストの準備完了状態です", "INFO")
                    self.status_var.set("接続済み")
                    self.log_message(f"GUI状態更新: {self.status_var.get()}", "INFO")
                else:
                    self.hide_connection_popup()
                    self.log_message(f"✗ 接続確認失敗: {config.port}", "ERROR")
                    self.log_message("ターゲットデバイスとの通信ができません", "ERROR")
                    self.status_var.set("接続失敗")
                    self.log_message(f"GUI状態更新: {self.status_var.get()}", "INFO")
                    
            except Exception as e:
                self.hide_connection_popup()
                self.log_message(f"✗ 接続確認エラー: {e}", "ERROR")
                self.status_var.set("接続エラー")
        
        # 別スレッドで接続確認を実行
        connection_thread_obj = threading.Thread(target=connection_thread, daemon=True)
        connection_thread_obj.start()


def main():
    """メイン関数"""
    root = tk.Tk()
    app = LPDDRTestGUI(root)
    app.check_log_queue()  # ログキュー監視を開始
    root.mainloop()


if __name__ == "__main__":
    main()

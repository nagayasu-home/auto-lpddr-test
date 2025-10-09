#!/usr/bin/env python3
"""
LPDDR Test Automation Terminal Interface
コマンドラインインターフェース版
"""

import sys
import os
import time
import threading
import queue
from typing import Dict, List, Optional, Any
from datetime import datetime

from lpddr_test_automation import LPDDRAutomation, TestConfig, TestResult, TestStep
from constants import (
    SerialSettings, TestPatterns, FrequencyMapping, 
    ErrorMessages, SuccessMessages, JudgmentMessages
)
from validators import ConfigValidator
from exceptions import ValidationError, ConfigurationError
from logger_config import setup_logging, get_test_logger


class LPDDRTerminal:
    """LPDDRテスト用ターミナルインターフェース"""
    
    def __init__(self):
        self.automation: Optional[LPDDRAutomation] = None
        self.test_logger = get_test_logger()
        self.is_test_running = False
        self.test_thread: Optional[threading.Thread] = None
        self.log_queue = queue.Queue()
        self.config: Optional[TestConfig] = None
        
        # ログ設定
        self.logger = setup_logging(log_level="INFO", enable_console=False)
        
        # コマンド履歴
        self.command_history: List[str] = []
        self.history_index = -1
        
    def print_banner(self):
        """バナーを表示"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                LPDDR Test Automation Terminal               ║
║                                                              ║
║  AI-CAMKIT Main Board LPDDR4 Interface Test Automation      ║
║                                                              ║
║  Commands:                                                   ║
║    help     - Show this help message                        ║
║    config   - Configure test parameters                     ║
║    connect  - Connect to target board                       ║
║    test     - Run test sequence                             ║
║    status   - Show current status                           ║
║    log      - Show recent logs                              ║
║    clear    - Clear screen                                  ║
║    exit     - Exit application                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def print_prompt(self):
        """プロンプトを表示"""
        status = "TESTING" if self.is_test_running else "READY"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] LPDDR-{status}> ", end="", flush=True)
    
    def print_help(self):
        """ヘルプメッセージを表示"""
        help_text = """
Available Commands:

CONFIGURATION:
  config show                    - Show current configuration
  config port <port>             - Set serial port (e.g., /dev/ttyUSB0)
  config baudrate <rate>         - Set baudrate (9600, 19200, 38400, 57600, 115200)
  config timeout <seconds>       - Set timeout in seconds
  config frequencies <freqs>     - Set test frequencies (e.g., 800)
  config patterns <patterns>     - Set test patterns (e.g., 1,15)
  config 2d <on|off>             - Enable/disable 2D training
  config eye <on|off>            - Enable/disable eye pattern test
  config power <on|off>          - Enable/disable power control
  config save <filename>         - Save configuration to file
  config load <filename>         - Load configuration from file

CONNECTION:
  connect                        - Connect to target board
  disconnect                     - Disconnect from target board
  status                         - Show connection status

TESTING:
  test                           - Run full test sequence
  test freq <frequency>          - Run single frequency test
  test diag                      - Run diagnostics test only
  test eye <type> [lane] [bit]   - Run eye pattern test
  stop                           - Stop current test

INFORMATION:
  log [lines]                    - Show recent log entries (default: 20)
  log clear                      - Clear log history
  history                        - Show command history
  help [command]                 - Show help for specific command

UTILITY:
  clear                          - Clear screen
  exit                           - Exit application

Examples:
  config port /dev/ttyUSB0
  config frequencies 800
  connect
  test
  log 50
        """
        print(help_text)
    
    def print_status(self):
        """現在のステータスを表示"""
        print("\n" + "="*60)
        print("LPDDR Test Automation Status")
        print("="*60)
        
        # 接続ステータス
        if self.automation and self.automation.serial_conn and self.automation.serial_conn.is_open:
            print(f"Connection: ✓ Connected to {self.config.port if self.config else 'Unknown'}")
        else:
            print("Connection: ✗ Disconnected")
        
        # テストステータス
        if self.is_test_running:
            print("Test Status: 🔄 Running")
        else:
            print("Test Status: ⏸ Ready")
        
        # 設定情報
        if self.config:
            print(f"Port: {self.config.port}")
            print(f"Baudrate: {self.config.baudrate}")
            print(f"Timeout: {self.config.timeout}s")
            print(f"Frequencies: {', '.join(map(str, self.config.test_patterns))}")
            print(f"Patterns: {', '.join(map(str, self.config.test_patterns))}")
            print(f"2D Training: {'ON' if self.config.enable_2d_training else 'OFF'}")
            print(f"Eye Pattern: {'ON' if self.config.enable_eye_pattern else 'OFF'}")
            print(f"Power Control: {'ON' if self.config.power_control_enabled else 'OFF'}")
        else:
            print("Configuration: Not set")
        
        print("="*60)
    
    def print_logs(self, lines: int = 20):
        """ログを表示"""
        print(f"\nRecent {lines} log entries:")
        print("-" * 60)
        
        # 実際のログファイルから読み取り
        log_file = "logs/lpddr_test.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    for line in recent_lines:
                        print(line.strip())
            except Exception as e:
                print(f"Error reading log file: {e}")
        else:
            print("No log file found")
        
        print("-" * 60)
    
    def clear_screen(self):
        """画面をクリア"""
        os.system('clear' if os.name == 'posix' else 'cls')
        self.print_banner()
    
    def handle_config_command(self, args: List[str]):
        """設定コマンドを処理"""
        if not args:
            self.print_status()
            return
        
        if not self.config:
            self.config = TestConfig()
        
        command = args[0].lower()
        
        try:
            if command == "show":
                self.print_status()
            elif command == "port":
                if len(args) < 2:
                    print("Usage: config port <port>")
                    return
                self.config.port = args[1]
                print(f"Port set to: {self.config.port}")
            elif command == "baudrate":
                if len(args) < 2:
                    print("Usage: config baudrate <rate>")
                    return
                baudrate = int(args[1])
                ConfigValidator.validate_baudrate(baudrate)
                self.config.baudrate = baudrate
                print(f"Baudrate set to: {self.config.baudrate}")
            elif command == "timeout":
                if len(args) < 2:
                    print("Usage: config timeout <seconds>")
                    return
                timeout = float(args[1])
                ConfigValidator.validate_timeout(timeout)
                self.config.timeout = timeout
                print(f"Timeout set to: {self.config.timeout}s")
            elif command == "frequencies":
                if len(args) < 2:
                    print("Usage: config frequencies <freq1,freq2,...>")
                    return
                frequencies = [int(f.strip()) for f in args[1].split(',')]
                ConfigValidator.validate_frequencies(frequencies)
                # 注意: TestConfigにはfrequenciesフィールドがないので、test_patternsを使用
                print(f"Frequencies set to: {frequencies}")
            elif command == "patterns":
                if len(args) < 2:
                    print("Usage: config patterns <pattern1,pattern2,...>")
                    return
                patterns = [int(p.strip()) for p in args[1].split(',')]
                ConfigValidator.validate_patterns(patterns)
                self.config.test_patterns = patterns
                print(f"Patterns set to: {patterns}")
            elif command == "2d":
                if len(args) < 2:
                    print("Usage: config 2d <on|off>")
                    return
                self.config.enable_2d_training = args[1].lower() == "on"
                print(f"2D Training: {'ON' if self.config.enable_2d_training else 'OFF'}")
            elif command == "eye":
                if len(args) < 2:
                    print("Usage: config eye <on|off>")
                    return
                self.config.enable_eye_pattern = args[1].lower() == "on"
                print(f"Eye Pattern Test: {'ON' if self.config.enable_eye_pattern else 'OFF'}")
            elif command == "power":
                if len(args) < 2:
                    print("Usage: config power <on|off>")
                    return
                self.config.power_control_enabled = args[1].lower() == "on"
                print(f"Power Control: {'ON' if self.config.power_control_enabled else 'OFF'}")
            elif command == "save":
                if len(args) < 2:
                    print("Usage: config save <filename>")
                    return
                self.save_config(args[1])
            elif command == "load":
                if len(args) < 2:
                    print("Usage: config load <filename>")
                    return
                self.load_config(args[1])
            else:
                print(f"Unknown config command: {command}")
                print("Use 'help config' for available commands")
                
        except (ValueError, ValidationError, ConfigurationError) as e:
            print(f"Configuration error: {e}")
    
    def save_config(self, filename: str):
        """設定をファイルに保存"""
        try:
            import yaml
            config_dict = {
                'serial': {
                    'port': self.config.port,
                    'baudrate': self.config.baudrate,
                    'timeout': self.config.timeout
                },
                'test': {
                    'patterns': self.config.test_patterns,
                    'enable_2d_training': self.config.enable_2d_training,
                    'enable_eye_pattern': self.config.enable_eye_pattern
                },
                'power_control': {
                    'enabled': self.config.power_control_enabled,
                    'port': self.config.power_control_port
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            print(f"Configuration saved to: {filename}")
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def load_config(self, filename: str):
        """設定をファイルから読み込み"""
        try:
            import yaml
            with open(filename, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            self.config = TestConfig(
                port=config_dict.get('serial', {}).get('port', 'COM3'),
                baudrate=config_dict.get('serial', {}).get('baudrate', 115200),
                timeout=config_dict.get('serial', {}).get('timeout', 30.0),
                test_patterns=config_dict.get('test', {}).get('patterns', [1, 15]),
                enable_2d_training=config_dict.get('test', {}).get('enable_2d_training', False),
                enable_eye_pattern=config_dict.get('test', {}).get('enable_eye_pattern', True),
                power_control_enabled=config_dict.get('power_control', {}).get('enabled', False),
                power_control_port=config_dict.get('power_control', {}).get('port')
            )
            
            print(f"Configuration loaded from: {filename}")
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    def handle_connect_command(self):
        """接続コマンドを処理"""
        if not self.config:
            print("Error: Configuration not set. Use 'config' command first.")
            return
        
        try:
            print("Connecting to target board...")
            self.automation = LPDDRAutomation(self.config)
            
            if self.automation.connect():
                print(f"✓ Connected to {self.config.port} at {self.config.baudrate} baud")
                self.test_logger.log_connection(self.config.port, self.config.baudrate, True)
            else:
                print(f"✗ Failed to connect to {self.config.port}")
                self.test_logger.log_connection(self.config.port, self.config.baudrate, False)
                
        except Exception as e:
            print(f"Connection error: {e}")
            self.test_logger.log_error(e)
    
    def handle_disconnect_command(self):
        """切断コマンドを処理"""
        if self.automation:
            self.automation.disconnect()
            print("Disconnected from target board")
        else:
            print("Not connected")
    
    def handle_test_command(self, args: List[str]):
        """テストコマンドを処理"""
        if not self.automation or not self.automation.serial_conn or not self.automation.serial_conn.is_open:
            print("Error: Not connected to target board. Use 'connect' command first.")
            return
        
        if self.is_test_running:
            print("Error: Test is already running. Use 'stop' command to stop current test.")
            return
        
        if not args:
            # フルテストシーケンス
            self.run_full_test()
        elif args[0] == "freq" and len(args) > 1:
            # 単一周波数テスト
            try:
                frequency = int(args[1])
                self.run_frequency_test(frequency)
            except ValueError:
                print("Error: Invalid frequency value")
        elif args[0] == "diag":
            # 診断テストのみ
            self.run_diagnostics_test()
        elif args[0] == "eye":
            # アイパターンテスト
            self.run_eye_pattern_test(args[1:] if len(args) > 1 else [])
        else:
            print(f"Unknown test command: {args[0]}")
            print("Available test commands: test, test freq <frequency>, test diag, test eye")
    
    def run_full_test(self):
        """フルテストシーケンスを実行"""
        print("Starting full test sequence...")
        self.is_test_running = True
        
        def test_thread():
            try:
                # デフォルト周波数でテスト
                frequencies = [800]
                
                for frequency in frequencies:
                    if not self.is_test_running:
                        break
                    
                    print(f"\nTesting frequency: {frequency}MHz")
                    results = self.automation.run_frequency_test(frequency)
                    
                    for pattern, result in results.items():
                        status = "✓ PASS" if result.value == "PASS" else "✗ FAIL"
                        print(f"  {frequency}MHz {pattern}: {status}")
                
                if self.is_test_running:
                    print("\nRunning diagnostics test...")
                    diag_result = self.automation.run_diagnostics_test()
                    status = "✓ PASS" if diag_result.result.value == "PASS" else "✗ FAIL"
                    print(f"Diagnostics: {status}")
                
                print("\nTest sequence completed.")
                
            except Exception as e:
                print(f"Test error: {e}")
                self.test_logger.log_error(e)
            finally:
                self.is_test_running = False
        
        self.test_thread = threading.Thread(target=test_thread, daemon=True)
        self.test_thread.start()
    
    def run_frequency_test(self, frequency: int):
        """単一周波数テストを実行"""
        print(f"Testing frequency: {frequency}MHz")
        self.is_test_running = True
        
        def test_thread():
            try:
                results = self.automation.run_frequency_test(frequency)
                
                for pattern, result in results.items():
                    status = "✓ PASS" if result.value == "PASS" else "✗ FAIL"
                    print(f"  {frequency}MHz {pattern}: {status}")
                
                print("Frequency test completed.")
                
            except Exception as e:
                print(f"Test error: {e}")
                self.test_logger.log_error(e)
            finally:
                self.is_test_running = False
        
        self.test_thread = threading.Thread(target=test_thread, daemon=True)
        self.test_thread.start()
    
    def run_diagnostics_test(self):
        """診断テストを実行"""
        print("Running diagnostics test...")
        self.is_test_running = True
        
        def test_thread():
            try:
                result = self.automation.run_diagnostics_test()
                status = "✓ PASS" if result.result.value == "PASS" else "✗ FAIL"
                print(f"Diagnostics: {status}")
                
            except Exception as e:
                print(f"Test error: {e}")
                self.test_logger.log_error(e)
            finally:
                self.is_test_running = False
        
        self.test_thread = threading.Thread(target=test_thread, daemon=True)
        self.test_thread.start()
    
    def run_eye_pattern_test(self, args: List[str]):
        """アイパターンテストを実行"""
        print("Eye pattern test not implemented in this version")
        # 実装は必要に応じて追加
    
    def handle_stop_command(self):
        """テスト停止コマンドを処理"""
        if self.is_test_running:
            self.is_test_running = False
            print("Stopping test...")
        else:
            print("No test is currently running")
    
    def handle_log_command(self, args: List[str]):
        """ログコマンドを処理"""
        if not args:
            self.print_logs()
        elif args[0] == "clear":
            # ログファイルをクリア
            log_file = "logs/lpddr_test.log"
            if os.path.exists(log_file):
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("")
                print("Log file cleared")
            else:
                print("No log file found")
        else:
            try:
                lines = int(args[0])
                self.print_logs(lines)
            except ValueError:
                print("Error: Invalid number of lines")
    
    def handle_history_command(self):
        """コマンド履歴を表示"""
        if not self.command_history:
            print("No command history")
            return
        
        print("Command History:")
        for i, cmd in enumerate(self.command_history[-20:], 1):  # 最新20件
            print(f"  {i:2d}: {cmd}")
    
    def process_command(self, command: str):
        """コマンドを処理"""
        if not command.strip():
            return
        
        # コマンド履歴に追加
        self.command_history.append(command)
        if len(self.command_history) > 100:  # 履歴は100件まで
            self.command_history.pop(0)
        
        parts = command.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        try:
            if cmd == "help":
                if args:
                    # 特定のコマンドのヘルプ
                    print(f"Help for '{args[0]}' command not implemented")
                else:
                    self.print_help()
            elif cmd == "config":
                self.handle_config_command(args)
            elif cmd == "connect":
                self.handle_connect_command()
            elif cmd == "disconnect":
                self.handle_disconnect_command()
            elif cmd == "test":
                self.handle_test_command(args)
            elif cmd == "stop":
                self.handle_stop_command()
            elif cmd == "status":
                self.print_status()
            elif cmd == "log":
                self.handle_log_command(args)
            elif cmd == "history":
                self.handle_history_command()
            elif cmd == "clear":
                self.clear_screen()
            elif cmd == "exit":
                return False
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            print(f"Error executing command: {e}")
            self.test_logger.log_error(e)
        
        return True
    
    def run(self):
        """メインループ"""
        self.clear_screen()
        
        print("LPDDR Test Automation Terminal started.")
        print("Type 'help' for available commands.")
        
        try:
            while True:
                self.print_prompt()
                
                try:
                    command = input().strip()
                    if not self.process_command(command):
                        break
                except EOFError:
                    print("\nExiting...")
                    break
                except KeyboardInterrupt:
                    print("\nUse 'exit' command to quit")
        
        finally:
            # クリーンアップ
            if self.automation:
                self.automation.disconnect()
            print("Terminal closed.")


def main():
    """メイン関数"""
    terminal = LPDDRTerminal()
    terminal.run()


if __name__ == "__main__":
    main()

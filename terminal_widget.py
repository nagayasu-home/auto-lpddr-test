#!/usr/bin/env python3
"""
Terminal Widget for LPDDR GUI
GUI内に埋め込まれるターミナルウィジェット
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import subprocess
import sys
import os
from typing import Optional, Callable, List
from datetime import datetime


class TerminalWidget:
    """GUI内に埋め込まれるターミナルウィジェット"""
    
    def __init__(self, parent_frame, command_callback: Optional[Callable] = None):
        self.parent_frame = parent_frame
        self.command_callback = command_callback
        self.command_history: List[str] = []
        self.history_index = -1
        self.current_input = ""
        self.is_processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """UIをセットアップ"""
        # ターミナルフレーム
        self.terminal_frame = ttk.LabelFrame(self.parent_frame, text="ターミナル", padding="5")
        self.terminal_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ターミナル出力エリア
        self.output_text = scrolledtext.ScrolledText(
            self.terminal_frame,
            height=15,
            width=80,
            font=("Consolas", 10),
            bg="black",
            fg="green",
            insertbackground="white"
        )
        self.output_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 入力フレーム
        input_frame = ttk.Frame(self.terminal_frame)
        input_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # プロンプトラベル
        self.prompt_label = ttk.Label(input_frame, text="LPDDR> ", font=("Consolas", 10))
        self.prompt_label.grid(row=0, column=0, sticky=tk.W)
        
        # 入力エントリ
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            input_frame,
            textvariable=self.input_var,
            font=("Consolas", 10),
            width=70
        )
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 送信ボタン
        self.send_button = ttk.Button(input_frame, text="送信", command=self.send_command)
        self.send_button.grid(row=0, column=2, padx=(5, 0))
        
        # クリアボタン
        self.clear_button = ttk.Button(input_frame, text="クリア", command=self.clear_output)
        self.clear_button.grid(row=0, column=3, padx=(5, 0))
        
        # グリッドの重み設定
        self.terminal_frame.columnconfigure(0, weight=1)
        self.terminal_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)
        
        # イベントバインディング
        self.input_entry.bind('<Return>', self.on_enter_pressed)
        self.input_entry.bind('<Up>', self.on_up_arrow)
        self.input_entry.bind('<Down>', self.on_down_arrow)
        self.input_entry.bind('<Tab>', self.on_tab_pressed)
        
        # 初期メッセージ
        self.print_welcome_message()
        
    def print_welcome_message(self):
        """ウェルカムメッセージを表示"""
        welcome = """
╔══════════════════════════════════════════════════════════════╗
║                LPDDR Test Automation Terminal               ║
║                                                              ║
║  AI-CAMKIT Main Board LPDDR4 Interface Test Automation      ║
║                                                              ║
║  Available Commands:                                         ║
║    help     - Show help message                              ║
║    config   - Configure test parameters                      ║
║    connect  - Connect to target board                       ║
║    test     - Run test sequence                             ║
║    status   - Show current status                           ║
║    log      - Show recent logs                              ║
║    clear    - Clear terminal                                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Type 'help' for more information.
        """
        self.append_output(welcome)
        
    def append_output(self, text: str, color: str = "green"):
        """出力エリアにテキストを追加"""
        self.output_text.config(state=tk.NORMAL)
        
        # 色タグを設定
        if color not in ["green", "red", "yellow", "blue", "white"]:
            color = "green"
        
        # タグを定義
        self.output_text.tag_configure("green", foreground="green")
        self.output_text.tag_configure("red", foreground="red")
        self.output_text.tag_configure("yellow", foreground="yellow")
        self.output_text.tag_configure("blue", foreground="blue")
        self.output_text.tag_configure("white", foreground="white")
        
        # テキストを追加
        self.output_text.insert(tk.END, text)
        
        # 色を適用
        if color != "green":
            start_line = self.output_text.index("end-1c linestart")
            end_line = self.output_text.index("end-1c")
            self.output_text.tag_add(color, start_line, end_line)
        
        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END)
        
    def print_prompt(self):
        """プロンプトを表示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prompt = f"\n[{timestamp}] LPDDR> "
        self.append_output(prompt)
        
    def send_command(self):
        """コマンドを送信"""
        command = self.input_var.get().strip()
        if not command:
            return
            
        # コマンド履歴に追加
        self.command_history.append(command)
        if len(self.command_history) > 100:
            self.command_history.pop(0)
        self.history_index = -1
        
        # プロンプトとコマンドを表示
        self.print_prompt()
        self.append_output(command + "\n")
        
        # 入力フィールドをクリア
        self.input_var.set("")
        
        # コマンドを処理
        self.process_command(command)
        
    def on_enter_pressed(self, event):
        """Enterキーが押された時の処理"""
        self.send_command()
        return "break"
        
    def on_up_arrow(self, event):
        """上矢印キーが押された時の処理（履歴）"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_var.set(self.command_history[-(self.history_index + 1)])
        return "break"
        
    def on_down_arrow(self, event):
        """下矢印キーが押された時の処理（履歴）"""
        if self.history_index > 0:
            self.history_index -= 1
            self.input_var.set(self.command_history[-(self.history_index + 1)])
        elif self.history_index == 0:
            self.history_index = -1
            self.input_var.set("")
        return "break"
        
    def on_tab_pressed(self, event):
        """Tabキーが押された時の処理（コマンド補完）"""
        command = self.input_var.get().strip()
        if command:
            # 簡単なコマンド補完
            completions = self.get_command_completions(command)
            if completions:
                if len(completions) == 1:
                    self.input_var.set(completions[0])
                else:
                    self.append_output(f"\nPossible completions: {', '.join(completions)}\n", "yellow")
        return "break"
        
    def get_command_completions(self, partial: str) -> List[str]:
        """コマンド補完候補を取得"""
        commands = [
            "help", "config", "connect", "disconnect", "test", "stop", 
            "status", "log", "clear", "history", "exit"
        ]
        return [cmd for cmd in commands if cmd.startswith(partial.lower())]
        
    def clear_output(self):
        """出力をクリア"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.print_welcome_message()
        
    def process_command(self, command: str):
        """コマンドを処理"""
        if self.is_processing:
            self.append_output("Previous command is still processing...\n", "yellow")
            return
            
        self.is_processing = True
        
        def process_thread():
            try:
                if self.command_callback:
                    result = self.command_callback(command)
                    if result:
                        self.append_output(f"{result}\n")
                else:
                    # デフォルトのコマンド処理
                    self.handle_default_command(command)
            except Exception as e:
                self.append_output(f"Error: {e}\n", "red")
            finally:
                self.is_processing = False
                
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
        
    def handle_default_command(self, command: str):
        """デフォルトのコマンド処理"""
        parts = command.strip().split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "help":
            self.show_help()
        elif cmd == "clear":
            self.clear_output()
        elif cmd == "history":
            self.show_history()
        elif cmd == "echo":
            self.append_output(" ".join(args) + "\n")
        elif cmd == "time":
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.append_output(f"Current time: {now}\n")
        elif cmd == "pwd":
            self.append_output(f"Current directory: {os.getcwd()}\n")
        elif cmd == "ls":
            try:
                files = os.listdir(".")
                self.append_output(f"Files: {', '.join(files)}\n")
            except Exception as e:
                self.append_output(f"Error: {e}\n", "red")
        else:
            self.append_output(f"Unknown command: {cmd}\n", "red")
            self.append_output("Type 'help' for available commands.\n", "yellow")
            
    def show_help(self):
        """ヘルプを表示"""
        help_text = """
Available Commands:

BASIC:
  help          - Show this help message
  clear         - Clear terminal output
  history       - Show command history
  echo <text>   - Echo text
  time          - Show current time
  pwd           - Show current directory
  ls            - List files in current directory

LPDDR TEST:
  config        - Configure test parameters
  connect       - Connect to target board
  disconnect    - Disconnect from target board
  test          - Run test sequence
  stop          - Stop current test
  status        - Show current status
  log           - Show recent logs

Note: LPDDR test commands are handled by the main GUI application.
        """
        self.append_output(help_text)
        
    def show_history(self):
        """コマンド履歴を表示"""
        if not self.command_history:
            self.append_output("No command history\n")
            return
            
        self.append_output("Command History:\n")
        for i, cmd in enumerate(self.command_history[-20:], 1):  # 最新20件
            self.append_output(f"  {i:2d}: {cmd}\n")
            
    def focus_input(self):
        """入力フィールドにフォーカス"""
        self.input_entry.focus_set()
        
    def insert_text(self, text: str, color: str = "white"):
        """テキストを挿入（外部から呼び出し用）"""
        self.append_output(text, color)
        
    def get_output_text(self) -> str:
        """出力テキストを取得"""
        return self.output_text.get(1.0, tk.END)


class TerminalWindow:
    """独立したターミナルウィンドウ"""
    
    def __init__(self, parent, command_callback: Optional[Callable] = None):
        self.parent = parent
        self.command_callback = command_callback
        self.window = None
        self.terminal_widget = None
        
    def show(self):
        """ターミナルウィンドウを表示"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("LPDDR Terminal")
        self.window.geometry("800x600")
        
        # ターミナルウィジェットを作成
        self.terminal_widget = TerminalWidget(self.window, self.command_callback)
        
        # ウィンドウが閉じられた時の処理
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def on_close(self):
        """ウィンドウが閉じられた時の処理"""
        if self.window:
            self.window.destroy()
            self.window = None
            self.terminal_widget = None
            
    def is_open(self) -> bool:
        """ウィンドウが開いているかチェック"""
        return self.window is not None and self.window.winfo_exists()
        
    def insert_text(self, text: str, color: str = "white"):
        """テキストを挿入"""
        if self.terminal_widget:
            self.terminal_widget.insert_text(text, color)
            
    def focus(self):
        """ウィンドウにフォーカス"""
        if self.window:
            self.window.lift()
            self.window.focus_set()

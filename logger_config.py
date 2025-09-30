#!/usr/bin/env python3
"""
LPDDR Test Automation Logger Configuration
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from constants import LogLevels, FileExtensions


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードを構造化フォーマットで出力"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 追加のコンテキスト情報があれば追加
        if hasattr(record, 'test_id'):
            log_entry['test_id'] = record.test_id
        if hasattr(record, 'frequency'):
            log_entry['frequency'] = record.frequency
        if hasattr(record, 'pattern'):
            log_entry['pattern'] = record.pattern
        if hasattr(record, 'step'):
            log_entry['step'] = record.step
        if hasattr(record, 'result'):
            log_entry['result'] = record.result
        if hasattr(record, 'port'):
            log_entry['port'] = record.port
        if hasattr(record, 'baudrate'):
            log_entry['baudrate'] = record.baudrate
        if hasattr(record, 'command'):
            log_entry['command'] = record.command
        if hasattr(record, 'response'):
            log_entry['response'] = record.response
        if hasattr(record, 'timeout'):
            log_entry['timeout'] = record.timeout
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        # 例外情報があれば追加
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False, indent=2)


class LPDDRLogger:
    """LPDDRテスト用ロガークラス"""
    
    def __init__(self, name: str = "lpddr_automation", log_level: str = LogLevels.INFO.value):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 既存のハンドラーをクリア
        self.logger.handlers.clear()
        
        # フォーマッターを設定
        self._setup_formatters()
        
        # ハンドラーを設定
        self._setup_handlers()
    
    def _setup_formatters(self):
        """フォーマッターを設定"""
        # コンソール用フォーマッター（読みやすい形式）
        self.console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ファイル用フォーマッター（構造化JSON）
        self.file_formatter = StructuredFormatter()
    
    def _setup_handlers(self):
        """ハンドラーを設定"""
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.console_formatter)
        self.logger.addHandler(console_handler)
        
        # ファイルハンドラー（ローテーション付き）
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "lpddr_test.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(file_handler)
        
        # エラーログ専用ハンドラー
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "lpddr_error.log"),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(error_handler)
    
    def get_logger(self) -> logging.Logger:
        """ロガーインスタンスを取得"""
        return self.logger


class TestLogger:
    """テスト専用ロガークラス"""
    
    def __init__(self, base_logger: logging.Logger, test_id: str = None):
        self.logger = base_logger
        self.test_id = test_id or f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def log_test_start(self, frequency: int, pattern: int = None):
        """テスト開始ログ"""
        extra = {
            'test_id': self.test_id,
            'frequency': frequency,
            'pattern': pattern,
            'step': 'test_start'
        }
        self.logger.info(f"テスト開始 - 周波数: {frequency}MHz, パターン: {pattern}", extra=extra)
    
    def log_test_result(self, frequency: int, pattern: int, result: str, message: str = ""):
        """テスト結果ログ"""
        extra = {
            'test_id': self.test_id,
            'frequency': frequency,
            'pattern': pattern,
            'result': result,
            'step': 'test_result'
        }
        self.logger.info(f"テスト結果 - {frequency}MHz パターン{pattern}: {result}", extra=extra)
        if message:
            self.logger.debug(f"詳細メッセージ: {message}", extra=extra)
    
    def log_connection(self, port: str, baudrate: int, success: bool):
        """接続ログ"""
        extra = {
            'test_id': self.test_id,
            'port': port,
            'baudrate': baudrate,
            'step': 'connection'
        }
        if success:
            self.logger.info(f"接続成功 - ポート: {port}, ボーレート: {baudrate}", extra=extra)
        else:
            self.logger.error(f"接続失敗 - ポート: {port}, ボーレート: {baudrate}", extra=extra)
    
    def log_command(self, command: str, response: str = None):
        """コマンドログ"""
        extra = {
            'test_id': self.test_id,
            'command': command,
            'step': 'command'
        }
        if response:
            extra['response'] = response
            self.logger.debug(f"コマンド実行 - {command} -> {response}", extra=extra)
        else:
            self.logger.debug(f"コマンド送信 - {command}", extra=extra)
    
    def log_timeout(self, operation: str, timeout: float):
        """タイムアウトログ"""
        extra = {
            'test_id': self.test_id,
            'operation': operation,
            'timeout': timeout,
            'step': 'timeout'
        }
        self.logger.warning(f"タイムアウト - 操作: {operation}, タイムアウト: {timeout}秒", extra=extra)
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """エラーログ"""
        extra = {
            'test_id': self.test_id,
            'step': 'error'
        }
        if context:
            extra.update(context)
        
        self.logger.error(f"エラー発生: {str(error)}", extra=extra, exc_info=True)
    
    def log_step(self, step: str, details: Dict[str, Any] = None):
        """ステップログ"""
        extra = {
            'test_id': self.test_id,
            'step': step
        }
        if details:
            extra.update(details)
        
        self.logger.info(f"ステップ実行: {step}", extra=extra)


def setup_logging(log_level: str = LogLevels.INFO.value, 
                 log_file: str = None,
                 enable_console: bool = True) -> logging.Logger:
    """ログ設定をセットアップ"""
    logger_config = LPDDRLogger(log_level=log_level)
    
    if log_file:
        # カスタムログファイルを追加
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logger_config.file_formatter)
        logger_config.logger.addHandler(file_handler)
    
    if not enable_console:
        # コンソールハンドラーを削除
        for handler in logger_config.logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                logger_config.logger.removeHandler(handler)
    
    return logger_config.get_logger()


def get_test_logger(test_id: str = None) -> TestLogger:
    """テストロガーを取得"""
    base_logger = logging.getLogger("lpddr_automation")
    return TestLogger(base_logger, test_id)


# デフォルトロガーの設定
default_logger = setup_logging()


def log_function_call(func):
    """関数呼び出しログデコレーター"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("lpddr_automation")
        logger.debug(f"関数呼び出し: {func.__name__} - 引数: {args}, キーワード引数: {kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"関数完了: {func.__name__} - 結果: {result}")
            return result
        except Exception as e:
            logger.error(f"関数エラー: {func.__name__} - エラー: {e}", exc_info=True)
            raise
    return wrapper


def log_performance(func):
    """パフォーマンスログデコレーター"""
    def wrapper(*args, **kwargs):
        import time
        logger = logging.getLogger("lpddr_automation")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"パフォーマンス: {func.__name__} - 実行時間: {execution_time:.3f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"パフォーマンス: {func.__name__} - 実行時間: {execution_time:.3f}秒 - エラー: {e}")
            raise
    return wrapper

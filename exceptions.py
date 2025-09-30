#!/usr/bin/env python3
"""
LPDDR Test Automation Custom Exceptions
"""


class LPDDRAutomationError(Exception):
    """LPDDR自動化の基底例外クラス"""
    pass


class ConnectionError(LPDDRAutomationError):
    """接続関連のエラー"""
    
    def __init__(self, message: str, port: str = None, baudrate: int = None):
        super().__init__(message)
        self.port = port
        self.baudrate = baudrate


class SerialConnectionError(ConnectionError):
    """シリアル接続エラー"""
    pass


class PowerControlError(ConnectionError):
    """電源制御エラー"""
    pass


class ConfigurationError(LPDDRAutomationError):
    """設定関連のエラー"""
    
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message)
        self.field = field
        self.value = value


class ValidationError(ConfigurationError):
    """設定バリデーションエラー"""
    pass


class TestExecutionError(LPDDRAutomationError):
    """テスト実行エラー"""
    
    def __init__(self, message: str, step: str = None, frequency: int = None, pattern: int = None):
        super().__init__(message)
        self.step = step
        self.frequency = frequency
        self.pattern = pattern


class TimeoutError(LPDDRAutomationError):
    """タイムアウトエラー"""
    
    def __init__(self, message: str, timeout: float = None, operation: str = None):
        super().__init__(message)
        self.timeout = timeout
        self.operation = operation


class CommandError(LPDDRAutomationError):
    """コマンド関連のエラー"""
    
    def __init__(self, message: str, command: str = None, response: str = None):
        super().__init__(message)
        self.command = command
        self.response = response


class TestResultError(LPDDRAutomationError):
    """テスト結果解析エラー"""
    
    def __init__(self, message: str, raw_response: str = None):
        super().__init__(message)
        self.raw_response = raw_response


class FileOperationError(LPDDRAutomationError):
    """ファイル操作エラー"""
    
    def __init__(self, message: str, filepath: str = None, operation: str = None):
        super().__init__(message)
        self.filepath = filepath
        self.operation = operation

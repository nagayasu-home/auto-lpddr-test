#!/usr/bin/env python3
"""
LPDDR Test Automation Validators
"""

import os
from typing import List, Optional, Union
from constants import (
    FrequencyMapping, TestPatterns, SerialSettings, 
    TestLimits, ErrorMessages
)
from exceptions import ValidationError


class ConfigValidator:
    """設定バリデータークラス"""
    
    @staticmethod
    def validate_baudrate(baudrate: int) -> None:
        """ボーレートの検証"""
        if not isinstance(baudrate, int):
            raise ValidationError(
                f"ボーレートは整数である必要があります: {baudrate}",
                field="baudrate",
                value=baudrate
            )
        
        if baudrate not in SerialSettings.SUPPORTED_BAUDRATES.value:
            raise ValidationError(
                f"{ErrorMessages.INVALID_BAUDRATE.value}: {baudrate}. "
                f"サポートされている値: {SerialSettings.SUPPORTED_BAUDRATES.value}",
                field="baudrate",
                value=baudrate
            )
    
    @staticmethod
    def validate_timeout(timeout: float) -> None:
        """タイムアウトの検証"""
        if not isinstance(timeout, (int, float)):
            raise ValidationError(
                f"タイムアウトは数値である必要があります: {timeout}",
                field="timeout",
                value=timeout
            )
        
        if timeout <= 0:
            raise ValidationError(
                f"{ErrorMessages.INVALID_TIMEOUT.value}: {timeout}",
                field="timeout",
                value=timeout
            )
    
    @staticmethod
    def validate_port(port: str) -> None:
        """ポートの検証"""
        if not isinstance(port, str):
            raise ValidationError(
                f"ポートは文字列である必要があります: {port}",
                field="port",
                value=port
            )
        
        if not port.strip():
            raise ValidationError(
                "ポート名が空です",
                field="port",
                value=port
            )
    
    @staticmethod
    def validate_frequency(frequency: int) -> None:
        """周波数の検証"""
        if not isinstance(frequency, int):
            raise ValidationError(
                f"周波数は整数である必要があります: {frequency}",
                field="frequency",
                value=frequency
            )
        
        if frequency not in FrequencyMapping.SUPPORTED_FREQUENCIES.value:
            raise ValidationError(
                f"{ErrorMessages.INVALID_FREQUENCY.value}: {frequency}. "
                f"サポートされている値: {FrequencyMapping.SUPPORTED_FREQUENCIES.value}",
                field="frequency",
                value=frequency
            )
    
    @staticmethod
    def validate_frequencies(frequencies: List[int]) -> None:
        """周波数リストの検証"""
        if not isinstance(frequencies, list):
            raise ValidationError(
                f"周波数はリストである必要があります: {frequencies}",
                field="frequencies",
                value=frequencies
            )
        
        if not frequencies:
            raise ValidationError(
                "周波数リストが空です",
                field="frequencies",
                value=frequencies
            )
        
        for freq in frequencies:
            ConfigValidator.validate_frequency(freq)
    
    @staticmethod
    def validate_pattern(pattern: int) -> None:
        """テストパターンの検証"""
        if not isinstance(pattern, int):
            raise ValidationError(
                f"テストパターンは整数である必要があります: {pattern}",
                field="pattern",
                value=pattern
            )
        
        if pattern < 0 or pattern > 99:
            raise ValidationError(
                f"テストパターンは0-99の範囲である必要があります: {pattern}",
                field="pattern",
                value=pattern
            )
    
    @staticmethod
    def validate_patterns(patterns: List[int]) -> None:
        """テストパターンリストの検証"""
        if not isinstance(patterns, list):
            raise ValidationError(
                f"テストパターンはリストである必要があります: {patterns}",
                field="patterns",
                value=patterns
            )
        
        if not patterns:
            raise ValidationError(
                "テストパターンリストが空です",
                field="patterns",
                value=patterns
            )
        
        for pattern in patterns:
            ConfigValidator.validate_pattern(pattern)
    
    @staticmethod
    def validate_test_bytes(test_bytes: int) -> None:
        """テストバイト数の検証"""
        if not isinstance(test_bytes, int):
            raise ValidationError(
                f"テストバイト数は整数である必要があります: {test_bytes}",
                field="test_bytes",
                value=test_bytes
            )
        
        if test_bytes <= 0:
            raise ValidationError(
                f"テストバイト数は正の数である必要があります: {test_bytes}",
                field="test_bytes",
                value=test_bytes
            )
    
    @staticmethod
    def validate_boolean(value: bool, field_name: str) -> None:
        """ブール値の検証"""
        if not isinstance(value, bool):
            raise ValidationError(
                f"{field_name}はブール値である必要があります: {value}",
                field=field_name,
                value=value
            )
    
    @staticmethod
    def validate_positive_integer(value: int, field_name: str) -> None:
        """正の整数の検証"""
        if not isinstance(value, int):
            raise ValidationError(
                f"{field_name}は整数である必要があります: {value}",
                field=field_name,
                value=value
            )
        
        if value <= 0:
            raise ValidationError(
                f"{field_name}は正の数である必要があります: {value}",
                field=field_name,
                value=value
            )


class FileValidator:
    """ファイル関連のバリデータークラス"""
    
    @staticmethod
    def validate_file_exists(filepath: str) -> None:
        """ファイルの存在確認"""
        if not os.path.exists(filepath):
            raise ValidationError(
                f"ファイルが存在しません: {filepath}",
                field="filepath",
                value=filepath
            )
    
    @staticmethod
    def validate_file_readable(filepath: str) -> None:
        """ファイルの読み取り可能性確認"""
        FileValidator.validate_file_exists(filepath)
        
        if not os.access(filepath, os.R_OK):
            raise ValidationError(
                f"ファイルが読み取り可能ではありません: {filepath}",
                field="filepath",
                value=filepath
            )
    
    @staticmethod
    def validate_file_writable(filepath: str) -> None:
        """ファイルの書き込み可能性確認"""
        # ディレクトリの存在確認
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            raise ValidationError(
                f"ディレクトリが存在しません: {directory}",
                field="directory",
                value=directory
            )
        
        # ファイルが存在する場合は書き込み可能性確認
        if os.path.exists(filepath):
            if not os.access(filepath, os.W_OK):
                raise ValidationError(
                    f"ファイルが書き込み可能ではありません: {filepath}",
                    field="filepath",
                    value=filepath
                )
        else:
            # ファイルが存在しない場合は、ディレクトリの書き込み可能性確認
            directory = os.path.dirname(filepath) or "."
            if not os.access(directory, os.W_OK):
                raise ValidationError(
                    f"ディレクトリが書き込み可能ではありません: {directory}",
                    field="directory",
                    value=directory
                )


class StringValidator:
    """文字列関連のバリデータークラス"""
    
    @staticmethod
    def validate_non_empty_string(value: str, field_name: str) -> None:
        """空でない文字列の検証"""
        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name}は文字列である必要があります: {value}",
                field=field_name,
                value=value
            )
        
        if not value.strip():
            raise ValidationError(
                f"{field_name}は空文字列であってはいけません",
                field=field_name,
                value=value
            )
    
    @staticmethod
    def validate_hex_string(value: str, field_name: str, length: Optional[int] = None) -> None:
        """16進数文字列の検証"""
        StringValidator.validate_non_empty_string(value, field_name)
        
        # 16進数文字のみかチェック
        if not all(c in '0123456789ABCDEFabcdef' for c in value):
            raise ValidationError(
                f"{field_name}は16進数文字列である必要があります: {value}",
                field=field_name,
                value=value
            )
        
        # 長さチェック
        if length is not None and len(value) != length:
            raise ValidationError(
                f"{field_name}の長さは{length}文字である必要があります: {value}",
                field=field_name,
                value=value
            )


class RangeValidator:
    """範囲関連のバリデータークラス"""
    
    @staticmethod
    def validate_range(value: Union[int, float], min_val: Union[int, float], 
                      max_val: Union[int, float], field_name: str) -> None:
        """値の範囲検証"""
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{field_name}は数値である必要があります: {value}",
                field=field_name,
                value=value
            )
        
        if value < min_val or value > max_val:
            raise ValidationError(
                f"{field_name}は{min_val}から{max_val}の範囲である必要があります: {value}",
                field=field_name,
                value=value
            )
    
    @staticmethod
    def validate_lane_number(lane: int) -> None:
        """レーン番号の検証"""
        RangeValidator.validate_range(
            lane, 0, TestLimits.MAX_LANES.value - 1, "lane"
        )
    
    @staticmethod
    def validate_bit_number(bit: int) -> None:
        """ビット番号の検証"""
        RangeValidator.validate_range(
            bit, 0, TestLimits.MAX_BITS.value - 1, "bit"
        )
